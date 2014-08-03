"""
Kristoffer Langeland Knudsen
rainbowponyprincess@gmail.com
"""

import os
import re
import time
import urllib
import httplib
import sqlite3 as sql
import xml.etree.ElementTree as ElementTree

import database as db
import container

global cache
global cachedir

global cfgtree


def initialize(configtree, directory, filename):
    """

    """

    global cache
    global cachedir
    global cfgtree

    cfgtree = configtree     
    cachedir = directory

    if not os.path.exists(directory):
        # Someone nuked the cache directory! Bastards!
        os.makedirs(directory)

    if not os.path.isfile(filename):
        # No cache database is currently present, initialize a new one please.         
        initCacheDatabase(filename)

    cache = sql.connect(filename)

## --------------------------------------------------------------- ##


def checkUpdateTimer(timer):

    global cache
    
    cursor = cache.cursor()
    cursor.execute("SELECT updateAfter FROM updateTimers WHERE timer = ?", [timer])
    
    res = cursor.fetchone()
    if res:
        (t, ) = res
        return t > time.time()
    else:
        return True

def resetUpdateTimer(timer, time):

    global cache
    
    cursor = cache.cursor()
    
    # Does the timer exist?
    cursor.execute("SELECT * FROM updateTimers WHERE timer = ?", [timer])
    if cursor.fetchone():
        cursor.execute("UPDATE updateTimers SET updateAfter = ? WHERE timer = ?", [time, timer])
    else:
        cursor.execute("INSERT INTO updateTimers (timer, updateAfter) VALUES (?, ?)", [timer, time])

    cache.commit()
        
        
## --------------------------------------------------------------- ##


def getOutposts():

    global cachedir

    cache = getCache("Outposts")

    if cache:
        # All right! We already got a list of outposts, we're golden.
        return ElementTree.parse(cachedir + '/' + cache)    
    else:
        # No outposts are cached, pull a new list from the servers. 

        class VoidKey:
            def __init__(self): self.keyID = 'void'

            def getInfo(self): return {}
            def getPrefix(self): return "eve"
        
        (cachedUntil, filename) = fetchPage(VoidKey(), "ConquerableStationList.xml.aspx")
        putCache("Outposts", cachedUntil, filename)
        
        return ElementTree.parse(cachedir + '/' + filename)


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


## --------------------------------------------------------------- ##


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

    global cfgtree
    global cachedir

    assets = ElementTree.parse(cachedir + '/' + assetlist)
    locations = ElementTree.parse(cachedir + '/' + locations)
    
    # Grab the items marked for the buyback program. 
    patterns = [re.compile(pattern.text) 
                for pattern in cfgtree.iter('pattern')];        
            
    containers = [container.Container(item.get('itemID'),
                                      item.get('itemName')) 
                  for item in locations.iter('row')
                  if any(map(lambda p: p.match(item.get('itemName')),
                             patterns))]
    
    for c in containers:
        c.addContents(assets)

    return containers
    

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

    # Dump the page to a file - brutal but effective, and it makes my job easier.
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
       "systemID" integer NOT NULL,
       "buy" double NOT NULL,
       "sell" double NOT NULL,
       "median" double NOT NULL,
       PRIMARY KEY ("systemID", "typeID")
    )
    """
    
    updateQuery = """
    CREATE TABLE "updateTimers" (
        "timer" varchar(30) NOT NULL,
        "updateAfter" double NOT NULL,
        PRIMARY KEY ("timer")
    )
    """

    cursor = db.cursor()
    cursor.execute(apiQuery)
    cursor.execute(marketQuery)
    cursor.execute(updateQuery)
    
    db.commit()
        
## --------------------------------------------------------------- ##    
## --------------------------------------------------------------- ##
## --------------------------------------------------------------- ##

def getValues(typeIDs):
    
    global cache
    global cfgtree

    values = {}
    
    cursor = cache.cursor()
    marketCacheTime = cfgtree.findtext(".//market/cachetime")


    # Look at the market expression, find determine which systems
    # we need data for. 
    systems = getMarketSystems(cfgtree.find(".//market/value"))

    refresh = {}
    for (systemName, systemID) in systems: refresh[systemID] = []

    # Pick out the itemIDs we need to fetch from eve-central
    for typeID in typeIDs:
 
        if not hasMarketGroup(typeID): 
            # No reason to query market data for items without a market group. 
            continue

        for (systemName, systemID) in systems:
            
            cursor.execute("SELECT cachedUntil " +
                           "FROM marketCache " +
                           "WHERE typeID = ? AND systemID = ?", 
                           [typeID, systemID])
        
            result = cursor.fetchone()
            if not result: 
                refresh[systemID] += [typeID]
                continue
                
            (cachedUntil, ) = result
                
            if time.time() > cachedUntil:
                refresh[systemID] += [typeID]
                continue


    updateHappened = False        

    # Query EVE-Central.com for the missing itemIDs.     
    for (systemName, systemID) in systems:

        if not refresh[systemID]: continue

        responsetree = marketStat(refresh[systemID], systemID)

        # All right, we have the new market prices. Put them in the cache. 
        
        for elm in responsetree.findall(".//type"):

            # Build a dict, keep the info handy.
            info = {'cacheTime' : time.time() + float(marketCacheTime),
                    'typeID' : elm.get('id'),
                    'systemID' : systemID,
                    'buy' : elm.findtext('buy/max'),
                    'sell' : elm.findtext('sell/min'),
                    'median' : elm.findtext('all/median')}
 
            # We're updating the cache database. Good. I love SQL - it's so nice and wonderful.
            # I'm trying to keep the SQL simple, so I'm using multiple queries. Sue me. 

            cursor.execute("SELECT typeID, systemID FROM marketCache WHERE typeID = :typeID AND systemID = :systemID",
                           info)
            
            if cursor.fetchone():
                # Update the row if a previous version is cached.
                cursor.execute("UPDATE marketCache " +
                               "SET cachedUntil = :cacheTime, buy = :buy, sell = :sell, median = :median " +
                               "WHERE typeID = :typeID AND systemID = :systemID ",
                               info)

            else:
                # Insert a row if no previous verion is cached.
                cursor.execute("INSERT INTO marketCache (typeID, cachedUntil, systemID, buy, sell, median) " +
                               "VALUES (:typeID, :cacheTime, :systemID, :buy, :sell, :median)", 
                               info)

        updateHappened = True

    if updateHappened:
        cache.commit()


    # Cache is up to date, evaluate the pricing expressions and return the results. 
    return evalValuation(typeIDs)


def hasMarketGroup(typeID):
    
    cursor = db.cursor()
    cursor.execute("SELECT marketGroupID FROM invTypes WHERE typeID = ?", [typeID])

    (marketGroupID, ) = cursor.fetchone()

    return marketGroupID != None


def getMarketSystems(elm):

    cursor = db.cursor()
    
    systemIDs = set([])

    for e in elm.findall('.//query'):

        cursor.execute("SELECT solarSystemID " +
                       "FROM mapSolarSystems " +
                       "WHERE solarSystemName = ?",
                       [e.get('system')])

        (systemID, ) = cursor.fetchone()

        systemIDs.add((e.get('system'), systemID))
    
    return systemIDs



def marketStat(typeIDs, systemID):
    
    params = {"hours" : 72,
              "usesystem" : systemID}
    
    typestr = '&'.join(map(lambda typeID: "typeid=" + typeID, typeIDs)) 
        
    conn = httplib.HTTPConnection("api.eve-central.com")
    conn.request("POST", "/api/marketstat", 
                 urllib.urlencode(params) + '&' + typestr)
    response = conn.getresponse()    
        
    return ElementTree.parse(response)
    

def evalValuation(typeIDs):

    global cache
    global cfgtree

    root = cfgtree.find('.//market/value/*')

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

        results = {}

        cursor = db.cursor()
        cursor.execute("SELECT solarSystemID " +
                       "FROM mapSolarSystems " +
                       "WHERE solarSystemName = ?",
                       [elm.get('system')])
        
        systemID = cursor.fetchone()[0]

        cursor = cache.cursor()
        for typeID in typeIDs:
            # Deathly super-super-hack! Don't do this, EVER!
            cursor.execute("SELECT " + elm.get('stat') + " FROM marketCache WHERE typeID = ? AND systemID = ?",
                           [typeID, systemID])

            dbres = cursor.fetchone()

            if dbres:
                (value, ) = dbres
                results[typeID] = float(value)
            else:
                results[typeID] = None

        return results


    functions = {'min' : __min,
                 'max' : __max,
                 'avg' : __avg,
                 'query' : __query}

    def internal(elm):
        return functions[elm.tag](elm)

    return internal(root)

