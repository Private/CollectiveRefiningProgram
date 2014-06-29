
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


class Can:    

    def __init__(self, itemID, locationID, name, 
                 currentTime = "Unknown", 
                 cachedUntil = "Unknown"):
 
        self.itemID = itemID
        self.locationID = locationID
        self.location = "Unknown Location"

        self.name = name
        self.contents = []

        self.currentTime = currentTime
        self.cachedUntil = cachedUntil

    
    def __canLocation(self):

        if not self.locationID:
            print("Skipping location for: " + self.name)
            return

        cursor = db.cursor()
        cursor.execute("SELECT solarSystemName " +
                       "FROM mapSolarSystems " +
                       "WHERE solarSystemID = ?", 
                       [self.locationID])

        try:
            (location,) = cursor.fetchone()
            self.location = location
            return
        except TypeError:
            pass            
        
        cursor.execute("SELECT solarSystemID, stationName " +
                       "FROM staStations " +
                       "WHERE stationID = ?",
                       [self.locationID])

        try:
            (solarSystemID, name) = cursor.fetchone()
            self.location = name
            return
        except TypeError:
            pass

        # All right - get the outposts. 
        conn = httplib.HTTPSConnection("api.eveonline.com")
        conn.request("GET", "/eve/ConquerableStationList.xml.aspx")
        response = conn.getresponse()

        print("API Request (Conquerable Stations): " + 
              str(response.status) + " " +
              str(response.reason))

        # Parse the XML
        outposttree = ElementTree.parse(response)

        for elm in outposttree.iter('row'):
            if elm.get('stationID') == self.locationID:
                self.location = elm.get('stationName')
                return
                
        print("Found no location for can: " + can.name)

        

    def __itmNames(self):
        
        for itm in self.contents:
            # Look up the name in the database, save it.             
            cursor = db.cursor()
            cursor.execute("SELECT typeName, groupID, portionSize " + 
                           "FROM invTypes " + 
                           "WHERE typeID = ?",
                           [itm['typeID']])

            (name, groupID, portionSize) = cursor.fetchone()
            itm['name'] = name
            itm['portionSize'] = portionSize

            cursor = db.cursor()
            cursor.execute("SELECT groupName " +
                           "FROM invGroups " +
                           "WHERE groupID = ?", 
                           [groupID])
            
            groupName = cursor.fetchone()[0]
            itm['groupName'] = groupName


    def __itmValue(self):

        print("Fetching item market stats...")
        
        typeIDs = map(lambda itm: itm['typeID'], self.contents)
        prices = getPrices(typeIDs)            
        
        # Merge prices with the contents list. 
        for itm in self.contents:
            itm['value'] = prices[itm['typeID']]
        

    def __itmYield(self):

        for itm in self.contents:
            
            cursor = db.cursor()
            cursor.execute("SELECT materialTypeID, quantity " +
                           "FROM invTypeMaterials " +
                           "WHERE typeID = " + itm['typeID'])
            
            itm['yield'] = dict(map(lambda (id, n): (str(id), n), 
                                    cursor.fetchall()))


    def __itmYieldValue(self):

        print("Fetching yield market stats...")

        # First, determine which minerals to price. 
        typeIDs = reduce(lambda x, y: x.union(y),
                         map(lambda itm: set(itm['yield'].keys()), 
                             self.contents))
        
        self.yieldprices = prices = getPrices(typeIDs)        
        
        for itm in self.contents:            

            itm['yieldvalue'] = float(0)

            for typeID, n in itm['yield'].iteritems():
                if prices[typeID]:
                    itm['yieldvalue'] += n * prices[typeID]
                else:
                    print("<WARNING> Missing price information: " + getName(typeID))
                
            itm['yieldvalue'] /= itm['portionSize']


    def valuate(self):
        print("")
        print("Valuating '" + self.name + "'")
        print("") 

        self.__canLocation()

        self.__itmNames()
        self.__itmValue()
        self.__itmYield()
        self.__itmYieldValue()


    def totalItems(self):
        return sum(map(lambda itm: itm['quantity'], self.contents))


    def totalTypes(self):
        return len(self.contents)


    def totalYield(self):
        
        names = {}
        total = {}

        for itm in self.contents:            
            for typeID, n in itm['yield'].iteritems():
                
                if typeID not in total:
                    total[typeID] = (n / itm['portionSize']) * itm['quantity']
                    names[typeID] = getName(typeID)
                else:
                    total[typeID] += (n / itm['portionSize']) * itm['quantity']

        return total, names


    def totalSellValue(self):
        return sum(map(lambda itm: itm['quantity'] * itm['value'] if itm['value'] else float(0), 
                       self.contents))


    def totalYieldValue(self):
        return sum(map(lambda itm: itm['quantity'] * itm['yieldvalue'], self.contents))


    def totalMaximumValue(self):
        return sum(map(lambda i: (i['quantity'] * 
                                  max(i['yieldvalue'], 
                                      i['value'])), 
                       self.contents))
    

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
