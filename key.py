"""
Kristoffer Langeland Knudsen
rainbowponyprincess@gmail.com


"""

import urllib
import httplib

import xml.etree.ElementTree as ElementTree




def fromXML(elm):

    print("Preparing key: " + elm.get('note'))

    keyID = elm.findtext('keyID')
    vCode = elm.findtext('vCode')

    ## Request key type from the EVE API servers.     
    info = {"keyID" : keyID, "vCode" : vCode}

    conn = httplib.HTTPSConnection("api.eveonline.com")
    conn.request("GET", "/account/APIKeyInfo.xml.aspx?" + urllib.urlencode(info))
    response = conn.getresponse()
    
    apiinfo = ElementTree.parse(response)

    key = apiinfo.find(".//key")
    t = key.get('type')

    print("   Type: \t\t" + t)
    
    handlers = {'Character' : Character,
                'Account' : Character,
                'Corporation' : Corporation}
    
    return handlers[t](keyID, vCode, elm, key)

    
class Character:
    """
    
    """
    
    def __init__(self, keyID, vCode, elm, key):
        
        self.note = elm.get('note')
        self.keyID = keyID
        self.vCode = vCode

        charIDs = [e.get('characterID') for e in key.iter('row')]
        charNames = [e.get('characterName') for e in key.iter('row')]

        requestedName = elm.findtext('character')
        
        if len(charIDs) == 1:
            
            print("   Found character: \t" + charNames[0])
            self.charID = charIDs[0]

        elif not requestedName:
            
            print("   WARNING: Multiple characters found - defaulting to '" + charNames[0] + "'")
            self.charID[0]

        else:

            try:
                # Look for the requested name.
                self.charID = charNames.index(requestedName) 
            except e:
                # Default to the first charID.
                print("   WARNING: No character matched name '" + requestedName + "'")
                print("            Defaulting to character '" + charNames[0] + "'")

                self.charID = charIDs[0]


    def getInfo(self):
        return {'keyID' : self.keyID,
                'vCode' : self.vCode,
                'characterID' : self.charID}        

    def getPrefix(self):
        return 'char'


class Corporation:
    """

    """

    def __init__(self, keyID, vCode, elm, key):
        
        self.note = elm.get('note')
        self.keyID = keyID
        self.vCode = vCode
        

    def getInfo(self):
        return {'keyID' : self.keyID,
                'vCode' : self.vCode}

                
    def getPrefix(self):
        return 'corp'
