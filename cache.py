"""
Kristoffer Langeland Knudsen
rainbowponyprincess@gmail.com
"""

import os
import time
import urllib
import httplib
import sqlite3 as sql
import xml.etree.ElementTree as ElementTree

global cache
global cachedir


def initialize(directory, filename):
    """

    """

    global cache
    global cachedir
    
    cachedir = directory

    if not os.path.exists(directory):
        # Someone nuked the cache directory! Bastards!
        os.makedirs(directory)

    if not os.path.isfile(filename):
        # No cache database is currently present, initialize a new one please.         
        initCacheDatabase(filename)

    cache = sql.connect(filename)



def getContainers(key):

    global cachedir

    print("   Processing key: " + key.note)

    assetCache = getCache(key.keyID + "/AssetList")
    locationsCache = getCache(key.keyID + "/Locations")

    if assetCache:
        # Good, a cached version was found. Use that shit!

        print("      AssetList: \tCACHED")
        
        return buildContainers(assetCache, locationsCache)
    else:
        # No cached version was found, dial the API servers! 

        print("      AssetList: \tNOT CACHED")

        # Turns out the Locations are on a different cache timer than the 
        # AssetLists. Effectively, you can have an old AssetList, with a 
        # new Location list, missing names and causing crashes. 
        
        # I'm caching the Locations with the AssetLists to avoid this - 
        # after all, a list of Locations is useless if it doesn't match 
        # the AssetList, no matter how old the AssetList is.

        # The fix is simple: I cache the Locations on the same timer as 
        # the assetlist.

        (cachedUntil, assetFile) = fetchPage(key, 'AssetList.xml.aspx')
        (_, locationsFile) = fetchPage(key, 'Locations.xml.aspx', 
                                       {'IDs' : ','.join(containerIDs(assetFile))})
        
        putCache(key.keyID + "/AssetList", cachedUntil, assetFile)
        putCache(key.keyID + "/Locations", cachedUntil, locationsFile)

        return buildContainers(assetFile, locationsFile)

def containerIDs(assetlist):

    tree = ElementTree.parse(cachedir + '/' + assetlist)

    # Grab the non-empty items. 
    containers = [{'itemID': item.get('itemID'), 
                   'typeID': item.get('typeID')} 
                  for item in tree.iter('row')
                  if list(item)]
    
    # Turns out the AssetList will include corp offices as items. If you don't own the 
    # station, the Locations call will fail with error 135. This is a rather crude hack 
    # to get around that - ignore all offices.
    return [c['itemID'] for c in containers if c['typeID'] != '27']


def buildContainers(assetlist, locations):

    global cachedir

    assets = ElementTree.parse(cachedir + '/' + assetlist)
    locations = ElementTree.parse(cachedir + '/' + locations)

    
    currentTime = assets.findtext('currentTime')
    cachedUntil = assets.findtext('cachedUntil')
        
    
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


    return []



    
## --------------------------------------------------------------- ##

def getCache(cacheName):
    """
    Return the cached API response, or None if no suitable cache is available. 
    """
    
    global cache

    cursor = cache.cursor()
    cursor.execute("SELECT cachedUntil, file FROM apiCache WHERE cacheName = ?", [cacheName])

    res = cursor.fetchone()

    if not res: return None

    now = time.time()
    (timeout, filename) = res

    if now > timeout: return None

    return filename
    

def putCache(cacheName, cachedUntil, filename):

    global cache

    cursor = cache.cursor()
    cursor.execute("SELECT * FROM apiCache WHERE cacheName = ?",
                   [cacheName])

    if cursor.fetchone():
        # Update the row if a previous version is cached.
        cursor.execute("UPDATE apiCache SET cachedUntil = ?, file = ? WHERE cacheName = ?",
                       [cachedUntil, filename, cacheName])
    else:
        # Insert a row if no previous verion is cached.
        cursor.execute("INSERT INTO apiCache (cacheName, cachedUntil, file) VALUES (?, ?, ?)",
                       [cacheName, cachedUntil, filename])    

    cache.commit()

## --------------------------------------------------------------- ##

def fetchPage(key, page, additional_info = {}):

    prefix = key.getPrefix()
    info = {}
    info.update(key.getInfo())
    info.update(additional_info)
    
    conn = httplib.HTTPSConnection("api.eveonline.com")
    conn.request("GET", "/" + prefix + "/" + page + "?" + urllib.urlencode(info))
    response = conn.getresponse()
        
    body = response.read()

    filename = key.keyID + '.' + page
        
    f = open(cachedir + '/' + filename, 'w')
    f.write(body)
    f.close()
 
    # All right - I'll need a timer on the cache. 
    root = ElementTree.fromstring(body)

    currentTime = time.strptime(root.findtext("currentTime"),
                                "%Y-%m-%d %H:%M:%S")
    cachedUntil = time.strptime(root.findtext("cachedUntil"),
                                "%Y-%m-%d %H:%M:%S")

    time_left = time.mktime(cachedUntil) - time.mktime(currentTime)

    return (time.time() + time_left, filename)
    
## --------------------------------------------------------------- ##

def initCacheDatabase(filename):

    db = sql.connect(filename)

    apiQuery = """
    CREATE TABLE "apiCache" (
      "cacheName" varchar(100) NOT NULL,
      "cachedUntil" double NOT NULL,
      "file" varchar(100) NOT NULL,
      PRIMARY KEY ("cacheName")
    )
    """
        
    marketQuery = """
    CREATE TABLE "marketCache" (
       "typeID" integer NOT NULL,
       "cachedUntil" double NOT NULL,
       PRIMARY KEY ("typeID")
    )
    """

    cursor = db.cursor()
    cursor.execute(apiQuery)
    cursor.execute(marketQuery)
        
## --------------------------------------------------------------- ##    

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
