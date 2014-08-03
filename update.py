"""
Kristoffer Langeland Knudsen
rainbowponyprincess@gmail.com
"""

import os
import time
import urllib
import urllib2
import zipfile
import StringIO
import os.path

from distutils.version import StrictVersion

import cache


def update(configtree):

    cache.resetUpdateTimer('core', time.time() + float(configtree.findtext('.//updates/core/timer')))

    # Download the version file, check if we need an update.
    if checkVersion(configtree.findtext(".//updates/core/version")):
        print("")
        print("   Update available.")
        fetchUpdate(configtree)
    else:
        print("")
        print("   No update available")
    
    fetchUpdate(configtree)
    
## --------------------------------------------------------------- ##

def checkVersion(versionURL):

    currentVersion = open('version').read()
    remoteVersion = urllib.urlopen(versionURL).read()
    
    return StrictVersion(remoteVersion) > StrictVersion(currentVersion)
    
## --------------------------------------------------------------- ##

def fetchUpdate(configtree):

    print("")
    print("\tRequesting update.")
    
    response = urllib2.urlopen(configtree.findtext(".//updates/core/url"))
    print("\tResponse: " + str(response.getcode()))

    archive = StringIO.StringIO(response.read())
 
    zip = zipfile.ZipFile(archive)
    zip.extractall()

    print("\tReplacing files...")
    print("")
   
    for name in zip.namelist():
        (path, file) = os.path.split(name)
        print(file)
        
        # Delete the old file.
        os.remove(file)
        
        # Move the new file into place.
        os.rename(name, file)

    # Clean up, and pretend nothing ever happened. 
    os.rmdir(path)