#
#
#

import math
import database as db



global cfgtree

def initialize(configtree):
        
    global cfgtree
    cfgtree = configtree



def _getBaseMaterials(typeID):

    cursor = db.cursor()
    cursor.execute("SELECT materialTypeID as typeID, quantity "
                   "FROM industryActivityMaterials " +
                   "WHERE activityID = 1 AND typeID = ?", 
                   [typeID])

    return dict(cursor.fetchall())


def _getTotalMaterialsFor(typeID, runs, me):

    if runs == -1:
        raise Exception("Herp derp BPO derp")
        
    global cfgtree
    stationFactor = float(cfgtree.find('.//stationProductionEfficiency/default').text)
        
    materials = {}
        
    for typeID, quantity in _getBaseMaterials(typeID).items():
        if quantity == 1:
            materials[typeID] = runs 
            continue

        factor = float(100 - me) / 100
        materials[typeID] = int(math.ceil(runs * factor * stationFactor * quantity))

    return materials



class Blueprint:

    def __init__(self, elm):


        for attr in elm.attrib.keys():
            setattr(self, attr, elm.get(attr))

        integers = ['timeEfficiency', 'materialEfficiency', 'runs']

        for attr in integers:
            setattr(self, attr, int(getattr(self, attr)))
    
        
    def getTotalMaterials(self):

        return _getTotalMaterialsFor(self.typeID, self.runs, self.materialEfficiency)


    def getRecursiveMaterials(self):
        
        materials = self.getTotalMaterials()

        def updateMaterials(typeID, quantity):
            if typeID in materials:
                materials[typeID] += quantity
            else:
                materials[typeID] = quantity

        def removeMaterials(typeID):
            del materials[typeID]


        def getBlueprint(typeID):
                
            cursor = db.cursor()
            cursor.execute("SELECT typeID "
                           "FROM industryActivityProducts "
                           "WHERE activityID = 1 AND productTypeID = ?",
                           [typeID])
            
            res = cursor.fetchone()
                
            if res == None:
                return None

            (typeID, ) = res
            return typeID


        done = False

        while not done:

            done = True

            for typeID, quantity in materials.items():

                bpTypeID = getBlueprint(typeID)

                if bpTypeID == None:
                    continue
                
                done = False
    
                submaterials = _getTotalMaterialsFor(bpTypeID, quantity, 10)

                removeMaterials(typeID)

                for typeID, quantity in submaterials.items():
                    updateMaterials(typeID, quantity)
            

        return materials

        
        
    def isBPO(self):
        return self.runs == -1


    def __str__(self):
        return "{} [ME: {}, PE: {}, runs: {}]".format(self.typeName, 
                                                      self.materialEfficiency,
                                                      self.timeEfficiency,
                                                      self.runs)
