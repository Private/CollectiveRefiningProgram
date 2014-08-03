"""
Kristoffer Langeland Knudsen
rainbowponyprincess@gmail.com
"""

import os
import bz2
import urllib2
import sqlite3 as sql

global db


def initialize(configtree):
    """
    Initialize the sqlite3 database. This provides access to the EVE Online database 
    dump, containing information about item names, reprocessing yields, and so on. 
    """

    global db
    filename = configtree.findtext(".//updates/database/filename")

    if not os.path.isfile(filename):
        # Some skank has sabotaged the database. It's time for an update.        
        updateDatabase(configtree)
        
    db = sql.connect(filename)


def cursor():

    global db
    return db.cursor()


def updateDatabase(configtree):
    """
    Update the EVE Online database dump. Awesome. 
    """

    url = configtree.findtext(".//updates/database/url")
    filename = configtree.findtext(".//updates/database/filename")
    
    print("Updating database...")
        
    print("Fetching sqlite database dump:")
    print(url)
    
    # All right - get the sqlite dump. 
    response = urllib2.urlopen(url)

    print("\tResponse: " + str(response.getcode()))
    
    if response.getcode() != 200:
        return

    print("Downloading...")
    dump = response.read()
        
    print("Decompressing...")
    dump = bz2.decompress(dump)
        
    # Let's put it in a file. 
    sqlitefile = open(filename, 'wb')
    sqlitefile.write(dump)
    
    print("Trimming...")

    trimDatabase(filename)
        
    print("Wrote file: " + filename) 
    print("Done!")


def trimDatabase(filename):

    # This is a hardcoded list for now, deal with it. 
    tables = ['invTypes',
              'invGroups',
              'invTypeMaterials',
              'mapSolarSystems',
              'staStations']

    db = sql.connect(filename)

    cursor = db.cursor()
    cursor.execute("SELECT name, type FROM sqlite_master WHERE type='table'")

    for name, _ in cursor.fetchall():
        
        if name not in tables:
            db.execute("DROP TABLE " + name + ";")
            db.commit()

    db.execute("VACUUM")
    db.close()
