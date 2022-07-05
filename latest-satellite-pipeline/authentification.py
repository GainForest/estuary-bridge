# Authentification script

from pydrive.auth import GoogleAuth
from pydrive.drive import GoogleDrive
import ee

from os.path import isfile, join
from os import environ


def authenticate():

    # -- Google Earth Engine authentification : 
    # ref : https://developers.google.com/earth-engine/guides/python_install-conda#mac_6
    if not isfile(join(environ['HOME'], '.config/earthengine/credentials')) : ee.Authenticate() 
    ee.Initialize() 


    # -- PyDrive authentification : 
    # ref : https://medium.com/analytics-vidhya/how-to-connect-google-drive-to-python-using-pydrive-9681b2a14f20 
    # note : need also add yourself as a tester and '8090/' as redirect uri
    gauth = GoogleAuth()
    if not isfile('mycreds.txt') :
        # this need be done only once via the browser, then the credentials are loaded from file
        gauth.LocalWebserverAuth()
        gauth.SaveCredentialsFile('mycreds.txt')
    else : 
        gauth.LoadCredentialsFile('mycreds.txt')
        # Note : if you get an `Token has been expired or revoked.` error from pydrive, do : 
        # delete the file mycreds.txt, and re-authenticate
    drive = GoogleDrive(gauth)


    return drive