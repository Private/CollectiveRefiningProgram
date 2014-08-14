"""
Kristoffer Langeland Knudsen
rainbowponyprincess@gmail.com
"""

import xml.etree.ElementTree as ElementTree

import math

import cache
import database as db


## --------------------------------------------------------------- ##


global cfgtree

def initialize(configtree):
        
    global cfgtree
    cfgtree = configtree
    

## --------------------------------------------------------------- ##


class Container:    
    """
    The Container class primarily manages a list of items - dictionaries representing
    an EVE item type, quantity, name and type information, etc. 
    """

    def __init__(self, itemID, name):

 
        self.name = name
        self.itemID = itemID

        self.contents = []
        self.mineralContent = []
        self.attainableYield = []

        self.locationID = None
        self.locationName = None


    def addContents(self, assets):

        item = assets.find(".//row[@itemID='" + self.itemID + "']")

        self.locationID = item.get('locationID')
        self.locationName = self.__locationName(assets)

        for row in item.iter('row'):            
            self.contents += [{'typeID' : row.get('typeID'),
                               'quantity' : int(row.get('quantity'))}]

        print("")
        print("      " + self.name)
        print("         " + str(self.locationName))
        print("         Containing " + str(len(self.contents)) + " item types")

        # So far, so good. Go though the contents and add information from the 
        # EVE Online database dump.

        self.__itmNames()
        self.__itmYield()
        self.__itmValue()
        
        self.__itmYieldValue()

        self.__totalYield()

    ## --------------------------------------------------------------- ##
    
    def __locationName(self, assets):

        if not self.locationID:
            # We're a container inside another container, like a can in a corp hangar.
            # Find the parent's location, or the parent's parent's...
            # The ElementTree doesn't carry parent pointers around, so we have to do this
            # the long way. 
            
            def __findLocationID(elm, locationID):
                if elm.get('itemID') == self.itemID:
                    return locationID
                
                if elm.get('locationID'):
                    locationID = elm.get('locationID')

                for e in elm:
                    recurse = __findLocationID(e, locationID)
                    if recurse: return recurse
                
                return None
            
            self.locationID = __findLocationID(assets.getroot(), None)

            if not self.locationID:
                print("Skipping location for: " + self.name)
                return "Unknown Location"

        # This shit is woodoo. Not my fault, it's straight out of the twisted inner workings of EVE.
        # Apparently, corp keys will yield locations in the 66xxxxxx and 67xxxxxx range.
        # These don't map to real locations, so some magic is in order.
        # Apparently: 
        #   The 66-locations become real locations if you subtract 6000001.
        #   The 67-locations become real if you subtract 6000000.
                
        if self.locationID.startswith('66'): self.locationID = str(int(self.locationID) - 6000001)
        if self.locationID.startswith('67'): self.locationID = str(int(self.locationID) - 6000000)
                
        cursor = db.cursor()
        cursor.execute("SELECT solarSystemName " +
                       "FROM mapSolarSystems " +
                       "WHERE solarSystemID = ?", 
                       [self.locationID])

        try:
            (location,) = cursor.fetchone()
            return location
        except TypeError:
            pass            
        
        cursor.execute("SELECT solarSystemID, stationName " +
                       "FROM staStations " +
                       "WHERE stationID = ?",
                       [self.locationID])

        try:
            (solarSystemID, name) = cursor.fetchone()
            return name
        except TypeError:
            pass

        
        outposts = cache.getOutposts()
            
        for elm in outposts.iter('row'):
            if elm.get('stationID') == self.locationID:
                return elm.get('stationName')
        
        
        print("WARNING: Found no location for " + self.name)

        
    def __itmNames(self):
        
        for itm in self.contents:
            # Look up the name in the database, save it.             
            cursor = db.cursor()
            cursor.execute("SELECT typeName, groupID, portionSize, volume " + 
                           "FROM invTypes " + 
                           "WHERE typeID = ?",
                           [itm['typeID']])

            (name, groupID, portionSize, volume) = cursor.fetchone()
            itm['name'] = name
            itm['volume'] = volume
            itm['portionSize'] = portionSize

            cursor = db.cursor()
            cursor.execute("SELECT groupName " +
                           "FROM invGroups " +
                           "WHERE groupID = ?", 
                           [groupID])
            
            groupName = cursor.fetchone()[0]
            itm['groupName'] = groupName


    def __itmValue(self):

        typeIDs = map(lambda itm: itm['typeID'], self.contents)
        prices = cache.getValues(typeIDs)            
        
        # Merge prices with the contents list. 
        for itm in self.contents:
            itm['value'] = prices[itm['typeID']]


    def __itmYield(self):
    
        for itm in self.contents:

            itm['mineralContent'] = []
            itm['attainableYield'] = []
                
            cursor = db.cursor()
            cursor.execute("SELECT materialTypeID, quantity " +
                           "FROM invTypeMaterials " +
                           "WHERE typeID = ?",
                           [itm['typeID']])            

            for (id, n) in cursor.fetchall():

                cursor.execute("SELECT typeName FROM invTypes WHERE typeID = ?", [id])
                (name, ) = cursor.fetchone()
                  
                itm['mineralContent'] += [{'name' : name,
                                           'typeID' : str(id),
                                           'quantity' : n}]
                itm['attainableYield'] += [{'name' : name,
                                            'typeID' : str(id),
                                            'quantity' : math.floor(self.__refEff() * n)}]


    def __itmYieldValue(self):
    
        for itm in self.contents:
            
            typeIDs = map(lambda r: r['typeID'], itm['attainableYield'])
            
            prices = cache.getValues(typeIDs)

            itm['yieldValue'] = sum(map(lambda r: r['quantity'] * prices[r['typeID']], itm['attainableYield']))


    def __totalYield(self):

        # Some utility functions. 
        def __contains(ref_yield, typeID):
            return any(map(lambda r: r['typeID'] == typeID, ref_yield))

        def __update(ref_yield, typeID, quantity):
            for r in ref_yield:
                if r['typeID'] == typeID:
                    r['quantity'] += quantity

        def __insert(ref_yield, typeID, name, quantity):
            ref_yield += [{'name' : name,
                           'typeID' : typeID,
                           'quantity' : quantity}]

        for itm in self.contents:            
            for r in itm['mineralContent']:                
                if __contains(self.mineralContent, r['typeID']):
                    __update(self.mineralContent, 
                             r['typeID'], 
                             r['quantity'] * itm['quantity'])
                else:
                    __insert(self.mineralContent, 
                             r['typeID'], 
                             r['name'], 
                             r['quantity'] * itm['quantity'])

        # Some pricing for the refinement yields would be nice as well.
        typeIDs = map(lambda r: r['typeID'], self.mineralContent)

        prices = cache.getValues(typeIDs)

        for r in self.mineralContent:
            r['value'] = prices[r['typeID']]

        # Calculate the refining yield. 
        for r in self.mineralContent:            
            
            # Copy the dict from the mineral contents, and adjust the quantity.
            r = dict(r)
            r['quantity'] = self.__refEff() * r['quantity']

            self.attainableYield += [r]

        
    ## --------------------------------------------------------------- ##

    def __refEff(self):
    
        global cfgtree
        return float(cfgtree.findtext(".//valuation/refiningEfficiency")) / 100