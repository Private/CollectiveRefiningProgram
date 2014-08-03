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
import update
import database


def isEnabled(elm):    
    return elm.get('enabled') in ['true', 'True', '1', 'yes', 'Yes', None]


def main(configfile):
    
    versionfile = open('version', 'r')
    version = versionfile.read()

    print("")
    print("Collective Refining Program")
    print("Version: " + version)
    print("")

    print('Using config file: ' + configfile)

    global configtree
    configtree = ElementTree.parse(file(configfile))

    db_file = configtree.findtext(".//updates/database/filename")
    cache_file = configtree.findtext("./cache/filename")
    cache_directory = configtree.findtext("./cache/directory")
    
    print("   Database file:\t" + db_file)
    print("   Cache directory:\t" + cache_directory)
    print("   Cache file:\t\t" + cache_file)
    print("")

    database.initialize(configtree)
    cache.initialize(configtree, cache_directory, cache_file)

    ## Good, do we need an update. 
    
    print("")
    print("Checking for updates...")

    if cache.checkUpdateTimer('core'):
        update.update(configtree)
    
    print("")
    
    ## All right - initialize the keys. 

    keys = []

    for elm in configtree.iter('apikey'):

        if not isEnabled(elm): continue
        
        keys += [key.fromXML(elm)]

    print("")
    print("Requesting AssetLists...")
    print("")
    
    containers = []

    for k in keys:
        containers += cache.getContainers(k)

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
