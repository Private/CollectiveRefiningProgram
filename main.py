"""
Kristoffer Langeland Knudsen
rainbowponyprincess@gmail.com

"""


import re
import sys
import urllib
import httplib
import os.path
import sqlite3 as sql
import xml.etree.ElementTree as ElementTree

def isEnabled(elm):    
    return elm.get('enabled') in ['true', 'True', '1', 'yes', 'Yes', None]

    
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


def main(configfile):

    print("")
    print('Using config file: ' + configfile)

    configtree = ElementTree.parse(file(configfile))

    db_file = configtree.findtext("./database/filename")
    cache_file = configtree.findtext("./cache/filename")

    print("   Database file:\t" + db_file)
    print("   Cahce file:\t\t" + cache_file)

    


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

    args = sys.argv[1:]

    configfile = args[0] if args else "config.xml" 
    main(configfile)
