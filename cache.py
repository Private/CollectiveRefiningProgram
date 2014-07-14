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

    cacheName = key.keyID + "/AssetList"

    cache = getCache(cacheName)

    if cache:
        # Good, a cached version was found. Use that shit!

        print("      Cached AssetList found.")
        
        return buildContainers(cache)
    else:
        # No cached version was found, dial the API servers! 

        print("      No cached AssetList.")

        (timeout, filename) = requestAPI(key, "AssetList.xml.aspx")
        putCache(cacheName, timeout, filename)

        return buildContainers(filename)


def buildContainers(xmlfile):

    global cachedir

    root = ElementTree.parse(cachedir + '/' + xmlfile)

    return []



    
## --------------------------------------------------------------- ##
# A few generic api-cache functions. 

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
    cursor.execute("INSERT INTO apiCache (cacheName, cachedUntil, file) VALUES (?, ?, ?)",
                   [cacheName, cachedUntil, filename])    
    cache.commit()



def requestAPI(key, page):

    prefix = key.getPrefix()
    info = key.getInfo()
    
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

        
def cansFromAPI(info, prefix):
        
    # Parse the XML
    itemtree = ElementTree.parse(response)

    # Grab the non-empty items. 
    containers = [{'itemID': item.get('itemID'), 
                   'typeID': item.get('typeID')} 
                  for item in itemtree.iter('row')
                  if list(item)]
    
    currentTime = itemtree.findtext('currentTime')
    cachedUntil = itemtree.findtext('cachedUntil')
    
    # Turns out the AssetList will include corp offices as items. If you don't own the 
    # station, the Locations call will fail with error 135. This is a rather crude hack 
    # to get around that - ignore all offices.
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
