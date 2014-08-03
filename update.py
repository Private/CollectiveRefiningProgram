"""
Kristoffer Langeland Knudsen
rainbowponyprincess@gmail.com
"""

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
        
    else:
        print("")
        print("   No update available")
    
    fetchUpdate(configtree)
    
## --------------------------------------------------------------- ##

def checkVersion(versionURL):

    localVersion = open('version')
    remoteVersion = urllib.urlopen(versionURL)
    
    res = StrictVersion(remoteVersion.read()) > StrictVersion(localVersion.read())

    localVersion.close()
    remoteVersion.close()    
    
    return res
    
## --------------------------------------------------------------- ##

def fetchUpdate(configtree):

    print("")
    print("\tRequesting update.")
    
    response = urllib2.urlopen(configtree.findtext(".//updates/core/url"))
    print("\tResponse: " + str(response.getcode()))

    archive = StringIO.StringIO(response.read())
 
    zip = zipfile.ZipFile(archive)

    print("\tReplacing files...")
    print("")
    
    for name in zip.namelist():
        (_, file) = os.path.split(name)
        print("\t\t" + file)
    