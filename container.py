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


        self.locationID = None
        self.locationName = None


    def addContents(self, assets):

        item = assets.find(".//row[@itemID='" + self.itemID + "']")

        self.locationID = item.get('locationID')
        self.locationName = self.__locationName()

        for row in item.iter('row'):            
            self.contents += [{'typeID' : row.get('typeID'),
                               'quantity' : row.get('quantity')}]

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


    def __itmYield(self):

        for itm in self.contents:
            
            cursor = db.cursor()
            cursor.execute("SELECT materialTypeID, quantity " +
                           "FROM invTypeMaterials " +
                           "WHERE typeID = ?",
                           [itm['typeID']])
            
            itm['yield'] = dict(map(lambda (id, n): (str(id), n), 
                                    cursor.fetchall()))




    def __itmValue(self):

        typeIDs = map(lambda itm: itm['typeID'], self.contents)
        prices = cache.getValues(typeIDs)            
        
        # Merge prices with the contents list. 
        for itm in self.contents:
            itm['value'] = prices[itm['typeID']]

        
    def __itmYieldValue(self):

        # First, determine which minerals to price. 
        typeIDs = reduce(lambda x, y: x.union(y),
                         map(lambda itm: set(itm['yield'].keys()), 
                             self.contents))
        
        self.yieldprices = prices = cache.getValues(typeIDs)        
        
        for itm in self.contents:            

            itm['yieldvalue'] = float(0)

            for typeID, n in itm['yield'].iteritems():
                if prices[typeID]:
                    itm['yieldvalue'] += n * prices[typeID]
                
            itm['yieldvalue'] /= itm['portionSize']

            
    ## --------------------------------------------------------------- ##


    def totalItems(self):
        return sum(map(lambda itm: itm['quantity'], self.contents))


    def totalTypes(self):
        return len(self.contents)


    def totalYield(self):
        
        names = {}
        total = {}

        for itm in self.contents:            
            for typeID, n in itm['yield'].iteritems():
                
                if typeID not in total:
                    total[typeID] = (n / itm['portionSize']) * itm['quantity']
                    names[typeID] = getName(typeID)
                else:
                    total[typeID] += (n / itm['portionSize']) * itm['quantity']

        return total, names


    def totalSellValue(self):
        return sum(map(lambda itm: itm['quantity'] * itm['value'] if itm['value'] else float(0), 
                       self.contents))


    def totalYieldValue(self):
        return sum(map(lambda itm: itm['quantity'] * itm['yieldvalue'], self.contents))


    def totalMaximumValue(self):
        return sum(map(lambda i: (i['quantity'] * 
                                  max(i['yieldvalue'], 
                                      i['value'])), 
                       self.contents))
