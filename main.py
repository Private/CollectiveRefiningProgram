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
import container


def isEnabled(elm):    
    return elm.get('enabled') in ['true', 'True', '1', 'yes', 'Yes', None]


def main(userconfig):
    
    versionfile = open('version', 'r')
    version = versionfile.read()
    versionfile.close()
    
    print("")
    print("Collective Refining Program")
    print("Version: " + version)
    print("")

    print('Using userconfig:\t' + userconfig)
    
    userconfig = ElementTree.parse(open(userconfig, 'r'))

    configfile = userconfig.findtext(".//config")

    print('Using config file:\t' + configfile)

    configtree = ElementTree.parse(open(configfile, 'r'))

    db_file = configtree.findtext(".//updates/database/filename")
    cache_file = configtree.findtext("./cache/filename")
    cache_directory = configtree.findtext("./cache/directory")

    print("")
    print("   Database file:\t" + db_file)
    print("   Cache directory:\t" + cache_directory)
    print("   Cache file:\t\t" + cache_file)
    print("")

    cache.initialize(configtree, userconfig, cache_directory, cache_file)

    ## Good, do we need an update? 
    
    print("")
    print("Checking for software updates...")

    if cache.checkUpdateTimer('core'):
        update.update(configtree)
    
    print("")    
    print("Checking for EVE online database updates...")

    if cache.checkUpdateTimer('database'):
        database.update(configtree)

    # Load the game data.
    
    container.initialize(configtree)
    database.initialize(configtree)
    
    ## All right - initialize the keys. 

    keys = []

    for elm in userconfig.iter('apikey'):

        if not isEnabled(elm): continue
        
        keys += [key.fromXML(elm)]

    print("")
    print("Requesting AssetLists...")
    
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

    configfile = args[0] if args else "userconfig.xml" 
    main(configfile)
