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


import key
import cache
import database



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


def main(configfile):
    
    versionfile = open('version', 'r')
    version = versionfile.read()

    print("")
    print("Collective Refining Program")
    print("Version: " + version)
    print("")

    print('Using config file: ' + configfile)

    configtree = ElementTree.parse(file(configfile))

    db_file = configtree.findtext("./database/filename")
    cache_file = configtree.findtext("./cache/filename")
    cache_directory = configtree.findtext("./cache/directory")
    
    print("   Database file:\t" + db_file)
    print("   Cache directory:\t" + cache_directory)
    print("   Cache file:\t\t" + cache_file)
    print("")

    database.initialize(db_file)
    cache.initialize(cache_directory, cache_file)

    ## All right - initialize the keys. 

    keys = []

    for elm in configtree.iter('apikey'):

        if not isEnabled(elm): continue
        
        keys += [key.fromXML(elm)]

    print("")
    print("Requesting AssetLists...")

    containers = [cache.getContainers(k) for k in keys]

    print("")
    print("Generating Output...")        

    for o in configtree.iter('output'):

        if not isEnabled(o): continue

        module = __import__(o.get('module'))
        module.output(containers, o.find("args").attrib)


if __name__ == "__main__":

    args = sys.argv[1:]

    configfile = args[0] if args else "config.xml" 
    main(configfile)
