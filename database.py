"""
Kristoffer Langeland Knudsen
rainbowponyprincess@gmail.com
"""

import os
import bz2
import httplib
import sqlite3 as sql

global db


def initialize(filename):
    """
    Initialize the sqlite3 database. This provides access to the EVE Online database 
    dump, containing information about item names, reprocessing yields, and so on. 
    """

    global db

    if not os.path.isfile(filename):
        # Some skank has sabotaged the database. It's time for an update.        
        updateDatabase(filename)
        
    db = sql.connect(filename)



def updateDatabase(filename):
    """
    Update the EVE Online database dump. Awesome. 
    """

    print("Updating database...")
        
    print("Fetching sqlite database dump:")
    print("https://www.fuzzwork.co.uk/dump/sqlite-latest.sqlite.bz2")
    
    # All right - get the sqlite dump. 
    conn = httplib.HTTPSConnection("www.fuzzwork.co.uk")
    conn.request("GET", "/dump/sqlite-latest.sqlite.bz2")
    response = conn.getresponse()

    print("\tResponse: " + str(response.status) + " " + str(response.reason))
    print("\tFile size: " + str(response.length) + " bytes")
    
    if response.status != 200:
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
            print("\tDropping table: " + name)
            db.execute("DROP TABLE " + name + ";")
            db.commit()
        else:
            print("\tKeeping table: " + name)

    db.execute("VACUUM")
    db.close()
