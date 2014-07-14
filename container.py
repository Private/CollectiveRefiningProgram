

class Container:    
    """
    The Container class primarily manages a list of items - dictionaries representing
    an EVE item type, quantity, name and type information, etc. 
    """

    def __init__(self, itemID, locationID, name,                  
                 currentTime = "Unknown", 
                 cachedUntil = "Unknown"):

 
        self.itemID = itemID
        self.locationID = locationID
        self.location = "Unknown Location"

        self.name = name
        self.contents = []

        self.currentTime = currentTime
        self.cachedUntil = cachedUntil

    
    def __canLocation(self):

        if not self.locationID:
            print("Skipping location for: " + self.name)
            return

        cursor = db.cursor()
        cursor.execute("SELECT solarSystemName " +
                       "FROM mapSolarSystems " +
                       "WHERE solarSystemID = ?", 
                       [self.locationID])

        try:
            (location,) = cursor.fetchone()
            self.location = location
            return
        except TypeError:
            pass            
        
        cursor.execute("SELECT solarSystemID, stationName " +
                       "FROM staStations " +
                       "WHERE stationID = ?",
                       [self.locationID])

        try:
            (solarSystemID, name) = cursor.fetchone()
            self.location = name
            return
        except TypeError:
            pass

        # All right - get the outposts. 
        conn = httplib.HTTPSConnection("api.eveonline.com")
        conn.request("GET", "/eve/ConquerableStationList.xml.aspx")
        response = conn.getresponse()

        print("API Request (Conquerable Stations): " + 
              str(response.status) + " " +
              str(response.reason))

        # Parse the XML
        outposttree = ElementTree.parse(response)

        for elm in outposttree.iter('row'):
            if elm.get('stationID') == self.locationID:
                self.location = elm.get('stationName')
                return
                
        print("Found no location for can: " + can.name)

        

    def __itmNames(self):
        
        for itm in self.contents:
            # Look up the name in the database, save it.             
            cursor = db.cursor()
            cursor.execute("SELECT typeName, groupID, portionSize " + 
                           "FROM invTypes " + 
                           "WHERE typeID = ?",
                           [itm['typeID']])

            (name, groupID, portionSize) = cursor.fetchone()
            itm['name'] = name
            itm['portionSize'] = portionSize

            cursor = db.cursor()
            cursor.execute("SELECT groupName " +
                           "FROM invGroups " +
                           "WHERE groupID = ?", 
                           [groupID])
            
            groupName = cursor.fetchone()[0]
            itm['groupName'] = groupName


    def __itmValue(self):

        print("Fetching item market stats...")
        
        typeIDs = map(lambda itm: itm['typeID'], self.contents)
        prices = getPrices(typeIDs)            
        
        # Merge prices with the contents list. 
        for itm in self.contents:
            itm['value'] = prices[itm['typeID']]
        

    def __itmYield(self):

        for itm in self.contents:
            
            cursor = db.cursor()
            cursor.execute("SELECT materialTypeID, quantity " +
                           "FROM invTypeMaterials " +
                           "WHERE typeID = " + itm['typeID'])
            
            itm['yield'] = dict(map(lambda (id, n): (str(id), n), 
                                    cursor.fetchall()))


    def __itmYieldValue(self):

        print("Fetching yield market stats...")

        # First, determine which minerals to price. 
        typeIDs = reduce(lambda x, y: x.union(y),
                         map(lambda itm: set(itm['yield'].keys()), 
                             self.contents))
        
        self.yieldprices = prices = getPrices(typeIDs)        
        
        for itm in self.contents:            

            itm['yieldvalue'] = float(0)

            for typeID, n in itm['yield'].iteritems():
                if prices[typeID]:
                    itm['yieldvalue'] += n * prices[typeID]
                else:
                    print("<WARNING> Missing price information: " + getName(typeID))
                
            itm['yieldvalue'] /= itm['portionSize']


    def valuate(self):
        print("")
        print("Valuating '" + self.name + "'")
        print("") 

        self.__canLocation()

        self.__itmNames()
        self.__itmValue()
        self.__itmYield()
        self.__itmYieldValue()


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
