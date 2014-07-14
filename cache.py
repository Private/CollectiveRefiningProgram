"""
Kristoffer Langeland Knudsen
rainbowponyprincess@gmail.com
"""

import urllib
import httplib
import sqlite3 as sql
import xml.etree.ElementTree as ElementTree


class Cache:
    """
    The Cache manages the caches - both on the EVE API pages, and the market 
    information. The two are largely separated, but I keep them both in here
    because the name fits both.     
    """

    def __init__(self, filename):
        self.db = sql.connect(filename)


    def marketRequest(itemID, stat):
        """

        """
        
        pass


    def apiRequest(key, page):
        """

        """

        pass

    ## --------------------------------------------------------------- ##
        
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
