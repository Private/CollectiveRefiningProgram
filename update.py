"""
Kristoffer Langeland Knudsen
rainbowponyprincess@gmail.com
"""

import time
import urllib
import urllib2
import zipfile

from distutils.version import StrictVersion

import cache


def update(configtree):

    print("")
    print("Checking for updates...")

    # Download the version file, check if we need an update.
    if checkVersion(configtree.findtext(".//updates/core/version")):
        print("\tUpdate available.")
        
    else:
        print("\tNo update available")
        
    cache.resetUpdateTimer('core', time.time() + float(configtree.findtext('.//updates/core/timer')))
    
## --------------------------------------------------------------- ##

def checkVersion(versionURL):

    currentVersion = open('version').read()
    remoteVersion = urllib.urlopen(versionURL).read()
    
    return StrictVersion(remoteVersion) > StrictVersion(currentVersion)
    
## --------------------------------------------------------------- ##

def fetchUpdate(configtree):

    print("\tDownloading update.")
    print("\t" + configtree.findtext(".//updates/core/url"))
    
    response = urllib2.urlopen(configtree.findtext(".//updates/core/url"))
    print("\tResponse: " + response.getcode())
    
    zip = zipfile.ZipFile(response, 'r')
    zip.extractall("./update")
    
    