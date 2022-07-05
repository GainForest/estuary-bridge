# the function we look for is def get_weekly_satellite_mosaic(geojson, week) -> returns a ipfs link

# setting up the environment : 
#   conda create --name gee python=3.8
#   conda activate gee
#   pip install earthengine-api --upgrade
#   pip install geemap
#   pip install pydrive

from helper import *
from args_checker import *
from authentification import *

from time import sleep
import ee
import subprocess
import argparse

###########################################################################################
# Parsing the user's input 
parser = argparse.ArgumentParser()
parser.add_argument("-sat",     type = str, help = "Satellite to consider (S2, NICFI).")
parser.add_argument("-start",   type = str, help = "Earliest date to consider (format YYYY-MM-DD for S2, YYYY-MM also supported for NICFI)")
parser.add_argument("-end",     type = str, help = "Latest date to consider (format YYYY-MM-DDfor S2, YYYY-MM also supported for NICFI)")
parser.add_argument("-d",       type = int, help = "Number of days to consider.")
parser.add_argument("-w",       type = int, help = "Number of weeks to consider.")
parser.add_argument("-m",       type = int, help = "Number of months to consider.")
parser.add_argument("-file",    type = str, help = "Path to the .geojson file.")
parser.add_argument("-cloud",   type = int, help = "Percentage of cloud cover under which to filter.", default = 100)
parser.add_argument("-name",    type = str, help = "Site name. ")
parser.add_argument("-cont",    type = str, help = "Continent to consider for NICFI basemaps.")
parser.add_argument("-est",     type = int, help = "Whether to save to Estuary.", default = 1)
args = parser.parse_args()

satellite, earliest_day, latest_day, PATH_TO_GEOJSON, site_name, filter_clouds, continent, save_to_estuary = is_valid(args)

# ------ 
print()
print("Processing {} images for site {}, from {} to {} (with cloud cover up to {}%)".format(satellite, site_name, earliest_day, latest_day, filter_clouds))
sleep(1)
# ------

# Authenticate : 
drive = authenticate()

###########################################################################################
# Download the tiles from GEE to Google Drive

ee_geometry = extract_geometry(PATH_TO_GEOJSON)

######## - GEE specific functions

def bound(img) :
  return img.clip(ee_geometry)


def save_to_drive(img, fn, res):
    task = ee.batch.Export.image.toDrive(image=img,
                                        description=fn,
                                        scale=res,
                                        crs='EPSG:4326',
                                        region=ee_geometry,
                                        folder='sat_pipeline',
                                        skipEmptyTiles=True,
                                        fileFormat='GeoTIFF',
                                        maxPixels=1e13)
    return task


def get_satellite_img(sat, continent=None):
    # For optimized parameters to export Sentinel-2 data, see https://developers.google.com/earth-engine/datasets/catalog/COPERNICUS_S2_SR
    if sat == 'S2' : 
        s2 = ee.ImageCollection('COPERNICUS/S2_SR').filterDate(earliest_day,latest_day).filter(ee.Filter.lt('CLOUDY_PIXEL_PERCENTAGE',filter_clouds)).select(['B4', 'B3', 'B2'])
        site_s2 = s2.map(bound)
        site_img = site_s2.median().unitScale(0.0, 3000).multiply(255).toByte()
        file_name = 'S2-SR_10m' + '_' + site_name + '_' + earliest_day + '_' + latest_day + '_' + 'cloud' + str(filter_clouds)
        task = save_to_drive(site_img, file_name, 10)
    
    # For optimized parameters to export NICFI data, see https://developers.google.com/earth-engine/datasets/catalog/projects_planet-nicfi_assets_basemaps_americas#bands
    elif sat == 'NICFI' :
        nicfi = ee.ImageCollection('projects/planet-nicfi/assets/basemaps/{}'.format(continent)).filterDate(earliest_day,latest_day)
        site_nicfi = nicfi.map(bound)
        site_img = site_nicfi.median().visualize(**{"bands":["R","G","B"], "min":64,"max":5454,"gamma":1.8})
        file_name = 'NICFI_5m' + '_' + site_name + '_' + earliest_day + '_' + latest_day
        task = save_to_drive(site_img, file_name, 4.77)

    return file_name, task


file_name, task = get_satellite_img(satellite, continent)

if is_in_Estuary(file_name):
    print('...already on Estuary!')

else : 
    print('...exporting to Google Drive')
    task.start()

    status = task.status()['state']
    while (status == 'READY') or (status == 'RUNNING') : 
        sleep(60)
        status = task.status()['state']

    if status == 'FAILED' : 
        error = task.status()['error_message']
        print('... /!\ Could not download the image(s) from GEE : ', error)
        update_dict('errors.json', file_name, error)
    
    elif status == 'COMPLETED' :
        print('...task completed')

        ###########################################################################################
        # Download the tiles from the Google Drive Account to a local folder and upload to Estuary
        
        print('...downloading from Google Drive and uploading to Estuary')
        file_list = drive.ListFile({'q': "title contains '{}' and trashed=false".format(file_name)}).GetList()
        for file in file_list : 
            file_id = file['id']
            fn = file['title']
            dw_file = drive.CreateFile({'id': file_id})
            dw_file.GetContentFile(fn)
            
            if save_to_estuary :
                try : upload_to_Estuary(fn)
                except Exception as e : print('.../!\ Could not upload to Estuary : ', e)
            
            file.Delete()
            subprocess.call("rm {}".format(fn), shell=True)

        urls = retrieve_IPFS_urls(file_name)

        # Updating the mapping
        print('...updating the mapping')
        update_dict('mapping.json', file_name, urls)
        

        print('...all done!')


