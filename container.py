"""
Kristoffer Langeland Knudsen
rainbowponyprincess@gmail.com
"""

import xml.etree.ElementTree as ElementTree

import cache
import database as db


class Container:    
    """
    The Container class primarily manages a list of items - dictionaries representing
    an EVE item type, quantity, name and type information, etc. 
    """

    def __init__(self, itemID, name):

 
        self.name = name
        self.itemID = itemID

        self.contents = []
        self.refining_yield = []

        self.locationID = None
        self.locationName = None


    def addContents(self, assets):

        item = assets.find(".//row[@itemID='" + self.itemID + "']")

        self.locationID = item.get('locationID')
        self.locationName = self.__locationName()

        for row in item.iter('row'):            
            self.contents += [{'typeID' : row.get('typeID'),
                               'quantity' : int(row.get('quantity'))}]

        print("")
        print("      " + self.name)
        print("         " + self.locationName)
        print("         Containing " + str(len(self.contents)) + " item types")

        # So far, so good. Go though the contents and add information from the 
        # EVE Online database dump.

        self.__itmNames()
        self.__itmYield()
        self.__itmValue()
        
        self.__itmYieldValue()

        self.__totalYield()

    ## --------------------------------------------------------------- ##
    
    def __locationName(self):

        if not self.locationID:
            print("Skipping location for: " + self.name)
            return "Unknown Location"

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

            itm['yield'] = []
            
            cursor = db.cursor()
            cursor.execute("SELECT materialTypeID, quantity " +
                           "FROM invTypeMaterials " +
                           "WHERE typeID = ?",
                           [itm['typeID']])            

            for (id, n) in cursor.fetchall():

                cursor.execute("SELECT typeName FROM invTypes WHERE typeID = ?", [id])
                (name, ) = cursor.fetchone()
                  
                itm['yield'] += [{'name' : name,
                                  'typeID' : str(id),
                                  'quantity' : n}]


    def __itmYieldValue(self):

        for itm in self.contents:
            
            typeIDs = map(lambda r: r['typeID'], itm['yield'])
            
            prices = cache.getValues(typeIDs)

            itm['yieldvalue'] = sum(map(lambda r: r['quantity'] * prices[r['typeID']], itm['yield']))


    def __totalYield(self):

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
            for r in itm['yield']:                
                if __contains(self.refining_yield, r['typeID']):
                    __update(self.refining_yield, r['typeID'], r['quantity'])
                else:
                    __insert(self.refining_yield, r['typeID'], r['name'], r['quantity'])

        # Some pricing for the refinement yields would be nice as well.
        typeIDs = map(lambda r: r['typeID'], self.refining_yield)

        prices = cache.getValues(typeIDs)

        for r in self.refining_yield:
            r['value'] = prices[r['typeID']]

        
    ## --------------------------------------------------------------- ##
