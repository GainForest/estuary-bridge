###########################################################################################
# Helper functions

import geemap
import subprocess
import config 
import json
from os.path import join, isfile

def retrieve_IPFS_urls(fn):
    """
        Returns a list the IPFS URLs of the files that contain `fn` in their name. 
    """
    api_answer = subprocess.check_output("curl -X GET -H 'Authorization: Bearer {}' https://api.estuary.tech/content/list".format(config.ESTUARY_TOKEN), shell=True,universal_newlines=True)
    uploads = json.loads(api_answer)

    urls = []
    for upload in uploads : 
        if (fn in upload['name']) :
            url = 'https://dweb.link/ipfs/' + upload['cid']
            urls.append(url)
    
    return urls


def get_all_uploaded_filenames():
    """
        Returns a list containing all the filenames that are currently uploaded on Estuary.
    """
    api_answer = subprocess.check_output("curl -X GET -H 'Authorization: Bearer {}' https://api.estuary.tech/content/list".format(config.ESTUARY_TOKEN), shell=True,universal_newlines=True)
    uploads = json.loads(api_answer)

    all_names = []
    for upload in uploads : 
        all_names.append(upload['name'])

    return all_names


def is_in_Estuary(file_name):
    """
        Checks if `file_name` has already been uploaded on Estuary.
    """
    all_names = get_all_uploaded_filenames()
    return any(file_name in name for name in all_names)


def upload_to_Estuary(f, PATH = ''):
    """
        Uploads the file PATH/f to Estuary (if it hasn't been uploaded before).
    """

    FILE_PATH = join(PATH, f)
    FILE_NAME = f
    command = "curl --progress-bar -X POST -H 'Authorization: Bearer {}' -F 'data=@{}' -F 'name={}' https://shuttle-1.estuary.tech/content/add".format(config.ESTUARY_TOKEN, FILE_PATH, FILE_NAME)
    subprocess.call(command , shell = True)


def extract_geometry(geojson_fn):
    """
        Earth Engine works with EE objects, not .geojson objects.
        This function extracts the geometry from the .geojson file using geemap.
    """
    ee_object = geemap.geojson_to_ee(geojson_fn)
    ee_geometry = ee_object.geometry() 
    return ee_geometry


def update_dict(file, key, value):
    """
        Updates the dictionary contained in `file` (or initialize it if it doesn't exist)
        with the `key`:`value` pair.
    """
    if not isfile(file) :
        init_dict = {key : value}
        with open(file, 'w') as f : json.dump(init_dict, f)
    else : 
        with open(file) as f : ex_dict = json.load(f)
        ex_dict[key] = value
        with open(file, 'w') as f : json.dump(ex_dict, f)
