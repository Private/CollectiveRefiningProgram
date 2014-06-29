
import re
import sys
import urllib
import httplib
import os.path
import sqlite3 as sql
import xml.etree.ElementTree as ElementTree

import updatedb

# Database!
global db

# Config!
configfile = "config.xml"

def getName(typeID):

    cursor = db.cursor()
    cursor.execute("SELECT typeName FROM invTypes WHERE typeID = ?", [typeID])
    return cursor.fetchone()[0]

    

def isEnabled(elm):    
    return elm.get('enabled') in ['true', 'True', '1', 'yes', 'Yes', None]

    
def marketStat(typeIDs, systemID, stat):
    
    params = {"hours" : 72,
              "usesystem" : systemID}
    
    typestr = '&'.join(map(lambda typeID: "typeid=" + typeID, typeIDs)) 
    
    conn = httplib.HTTPConnection("api.eve-central.com")
    conn.request("POST", "/api/marketstat", 
                 urllib.urlencode(params) + '&' + typestr)
    response = conn.getresponse()    

    if response.status != 200:
        print("EVE-Central Request: " + 
              str(response.status) + " " +
              str(response.reason))
        
    pricetree = ElementTree.parse(response)
    
    # Build a map containing the prices. 
    prices = {}
    
    def getMarketStat(elm, stat):        
        price = float(elm.find(stat).text) 
        return price if price != float(0) else None
    
    for elm in pricetree.iter('type'):
        prices[elm.get('id')] = getMarketStat(elm, stat) 

    return prices


def getPrices(typeIDs):

    global configfile

    configtree = ElementTree.parse(configfile)
    root = list(configtree.find('market'))[0]

    def __apply(f):
        
        def __(x, y):                        

            acc = {}
            for typeID in set(x.keys() + y.keys()):
                if typeID not in x or not x[typeID]:
                    acc[typeID] = y[typeID]
                    continue
                if typeID not in y or not y[typeID]:
                    acc[typeID] = x[typeID]
                    continue

                acc[typeID] = f(x[typeID], y[typeID])

            return acc

        return __

    def __min(elm):
        children = map(internal, list(elm))
        return reduce(__apply(min), children, {})

    def __max(elm):
        children = map(internal, list(elm))
        return reduce(__apply(max), children, {})

    def __avg(elm):
        children = map(internal, list(elm))
        return reduce(__apply(lambda x, y: (x + y) / 2), 
                      children, {})
        
    def __query(elm):

        cursor = db.cursor()
        cursor.execute("SELECT solarSystemID " +
                       "FROM mapSolarSystems " +
                       "WHERE solarSystemName=?",
                       [elm.get('system')])
        
        systemID = cursor.fetchone()[0]

        print("\tWaiting for market data: {}".format(elm.get('system')))

        return marketStat(typeIDs, systemID, elm.get('stat'))


    functions = {'min' : __min,
                 'max' : __max,
                 'avg' : __avg,
                 'query' : __query}

    def internal(elm):
        return functions[elm.tag](elm)

    return internal(root)


def getPatterns():

    global configfile

    configtree = ElementTree.parse(configfile)
    
    patterns = [re.compile(pattern.text) 
                for pattern in configtree.iter('pattern')
                if isEnabled(pattern)];
        
    return patterns


def cansFromAPI(info, prefix):
    
    conn = httplib.HTTPSConnection("api.eveonline.com")
    conn.request("GET", "/" + prefix + "/AssetList.xml.aspx?" + urllib.urlencode(info))
    response = conn.getresponse()

    print("API Request (Assets): " + 
          str(response.status) + " " +
          str(response.reason))

    # Parse the XML
    itemtree = ElementTree.parse(response)

    # Grab the non-empty items. 
    containers = [{'itemID': item.get('itemID'), 
                   'typeID': item.get('typeID')} 
                  for item in itemtree.iter('row')
                  if list(item)]
    
    currentTime = itemtree.findtext('currentTime')
    cachedUntil = itemtree.findtext('cachedUntil')

    # Turns out the AssetList will include corp hangars as items. If you don't own the 
    # station, the Locations call will fail with error 135. This is a rather crude hack 
    # to get around that. 
    containers = [c for c in containers if c['typeID'] != '27']
    
    info['IDs'] = ','.join(map(lambda c: c['itemID'], containers))

    # Fetch the container names, we need those. 
    conn.request("GET", "/" + prefix + "/Locations.xml.aspx?" + urllib.urlencode(info))
    response = conn.getresponse()

    print("API Request (Locations): " + 
          str(response.status) + " " +
          str(response.reason))

    locationtree = ElementTree.parse(response)
    
    # Grab the items marked for the buyback program. 
    patterns = getPatterns()
    cans = [Can(item.get('itemID'),
                item.get('locationID'),
                item.get('itemName'),
                currentTime, cachedUntil) 
            for item in locationtree.iter('row')
            if any(map(lambda p: p.match(item.get('itemName')),
                       patterns))]
    
    def getContents(item):
        return map(lambda i: {'typeID' : i.get('typeID'),
                              'quantity' : int(i.get('quantity'))}, 
                   (list(item.iter('row'))))
    
    for can in cans:
        for item in itemtree.iter('row'):
            if item.get('itemID') == can.itemID:
                can.locationID = item.get('locationID')
                can.contents = getContents(item)

    return cans


def processCharacter(keyID, vCode, charID):
        
    info = {"keyID" : keyID,
            "vCode" : vCode,
            "characterID" : charID}
    
    cans = cansFromAPI(info, "char")

    print("Found " + str(len(cans)) + " containers of interest.")
    if not cans: return    

    for can in cans:        
        can.valuate()
        
    return cans


def processCorp(keyID, vCode):

    info = {"keyID" : keyID,
            "vCode" : vCode}

    cans = cansFromAPI(info, "corp")

    print("Found " + str(len(cans)) + " containers of interest.")
    if not cans: return    
    
    for can in cans:        
        can.valuate()

    return cans


def main(args):

    global db
    global configfile
    
    if args:
        configfile = args[0]

    print('Using config file: ' + configfile)

    configtree = ElementTree.parse(file(configfile))

    dbfile = configtree.findtext("./database/filename")

    if not os.path.isfile(dbfile):
        # Some skank has sabotaged the database. It's time for an update.        
        updatedb.updateDatabase(dbfile)

    db = sql.connect(dbfile)

    cans = []

    for c in configtree.iter('character'):        

        if not isEnabled(c): continue

        print("")
        print("Processing character: " + c.get('note'))

        if c.findtext('charID'):
            processCharacter(c.findtext('keyID'), 
                             c.findtext('vCode'), 
                             c.findtext('charID'))
            continue

        if c.findtext('name'):
            keyID = c.findtext('keyID')
            vCode = c.findtext('vCode')
            name = c.findtext('name')

            # API lookup for the char id, process as above. 
            
            info = {'keyID' : keyID,
                    'vCode' : vCode}

            conn = httplib.HTTPSConnection("api.eveonline.com")
            conn.request("GET", "/account/Characters.xml.aspx?" + urllib.urlencode(info))
            response = conn.getresponse()

            tree = ElementTree.parse(response)

            for row in tree.iter('row'):
                if name == row.get('name'):
                    charactercans = processCharacter(keyID, vCode, row.get('characterID'))
                    cans += charactercans if charactercans else []

    for c in configtree.iter('corporation'):

        if not isEnabled(c): continue

        print("")
        print("Processing corporation: " + c.get('note'))
        
        corpcans = processCorp(c.findtext('keyID'), c.findtext('vCode'))
        cans += corpcans if corpcans else []

    print("")
    print("Generating output...")        

    for o in configtree.iter('output'):

        if not isEnabled(o): continue

        module = __import__(o.get('module'))
        module.output(cans, o.find("args").attrib)


if __name__ == "__main__":
    main(sys.argv[1:])
