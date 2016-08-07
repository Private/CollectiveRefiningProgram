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


    def addBlueprintInfo(self, blueprints):

        print("")
        print("\t\tSetting blueprint info on container: " + self.name)
        
        blueprints = [blueprint for blueprint in blueprints
                      if blueprint.locationID == self.itemID]


        print("\t\tFound {} blueprints.".format(len(blueprints)))

        self.contents = blueprints


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

