"""
Kristoffer Langeland Knudsen
rainbowponyprincess@gmail.com
"""

import time
import urllib

from distutils.version import StrictVersion

import cache


def update(configtree):

    print("")
    print("Checking for updates...")

    # Download the version file, check if we need an update.
    if checkVersion(configtree.findtext(".//updates/core/version")):
        print("Update available.")
        
    else:
        print("No update available")
        
    cache.resetUpdateTimer('core', time.time() + float(configtree.findtext('.//updates/core/timer')))
    
## --------------------------------------------------------------- ##

def checkVersion(versionURL):

    currentVersion = open('version').read()
    remoteVersion = urllib.urlopen(versionURL).read()
    
    return StrictVersion(remoteVersion) > StrictVersion(currentVersion)
    
## --------------------------------------------------------------- ##
