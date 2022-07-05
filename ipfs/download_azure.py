# script to download the NAIP maps

# to install dependencies : 
#   conda create --name azure python=3.8
#   conda activate trace
#   pip install [matplotlib, numpy, rasterio, rtree, shapely, geopy]

# Source : https://planetarycomputer.microsoft.com/dataset/naip#Blob-Storage-Notebook

import tempfile
import urllib
from os.path import exists
import os
import subprocess

import matplotlib.pyplot as plt 
import numpy as np 
import rasterio 
import re
import rtree
import shapely 
import pickle

from download_trace import get_all_uploaded_filenames, is_in_Estuary, upload_to_Estuary

# The (preferred) copy of NAIP in the West Europe Azure region
blob_root = 'https://naipeuwest.blob.core.windows.net/naip'

# We maintain a spatial index of NAIP tiles using the [rtree](https://pypi.org/project/Rtree/) library
index_files = ['tile_index.dat', 'tile_index.idx', 'tiles.p']
index_blob_root = re.sub('/naip$','/naip-index/rtree/',blob_root)
temp_dir = os.path.join(tempfile.gettempdir(),'naip')
os.makedirs(temp_dir,exist_ok=True)


class NAIPTileIndex:
    """
    Utility class for performing NAIP tile lookups by location.
    """
    
    tile_rtree = None
    tile_index = None
    base_path = None
    
    def __init__(self, base_path=None):
        
        if base_path is None:
            
            base_path = temp_dir
            os.makedirs(base_path,exist_ok=True)
            
            for file_path in index_files:
                download_url(index_blob_root + file_path, base_path + '/' + file_path)
                
        self.base_path = base_path
        self.tile_rtree = rtree.index.Index(base_path + "/tile_index")
        self.tile_index = pickle.load(open(base_path  + "/tiles.p", "rb"))


    def lookup_tile(self, lat, lon):
        """"
        Given a lat/lon coordinate pair, return the list of NAIP tiles that contain
        that location.

        Returns a list of COG file paths.
        """

        point = shapely.geometry.Point(float(lon),float(lat))
        intersected_indices = list(self.tile_rtree.intersection(point.bounds))

        intersected_files = []
        tile_intersection = False

        for idx in intersected_indices:

            intersected_file = self.tile_index[idx][0]
            intersected_geom = self.tile_index[idx][1]
            if intersected_geom.contains(point):
                tile_intersection = True
                intersected_files.append(intersected_file)

        if not tile_intersection and len(intersected_indices) > 0:
            print('''Error: there are overlaps with tile index, 
                      but no tile completely contains selection''')   
            return None
        elif len(intersected_files) <= 0:
            print("No tile intersections")
            return None
        else:
            return intersected_files



def download_url(url,destination_filename=None):
    """
    Download a URL to a temporary file
    """
    
    if destination_filename is None:
        url_as_filename = url.replace('://', '_').replace('/', '_')    
        destination_filename = os.path.join(temp_dir,url_as_filename)    
    urllib.request.urlretrieve(url, destination_filename)  
    return destination_filename


def display_naip_tile(filename):
    """
    Display a NAIP tile using rasterio.
    """
    # TO DO : adapt this to saving the tiles 

    # NAIP tiles are enormous; downsize for plotting in this notebook
    dsfactor = 10
    
    with rasterio.open(filename) as raster:

        # NAIP imagery has four channels: R, G, B, IR
        #
        # Stack RGB channels into an image; we won't try to render the IR channel
        #
        # rasterio uses 1-based indexing for channels.
        h = int(raster.height/dsfactor)
        w = int(raster.width/dsfactor)
        r = raster.read(1, out_shape=(1, h, w))
        g = raster.read(2, out_shape=(1, h, w))
        b = raster.read(3, out_shape=(1, h, w))        
    
    rgb = np.dstack((r,g,b))
    
    fig = plt.figure(frameon=False); ax = plt.Axes(fig,[0., 0., 1., 1.]); 
    ax.set_axis_off(); fig.add_axes(ax)

    plt.imshow(rgb);
    raster.close()


def access_tile_by_coord(lat, lon, index = NAIPTileIndex(), filteredYears = None) :
    """
        Access a NAIP tile based on a lat/lon coordinate pair.
        Note: returns a list of tiles ordered by year, eg. [tile_2011, ..., tile_2019]
        # TO DO : check if it's reverse order or not reverse order
    """ 
    # TO DO : make a function that returns all the tiles given a geometry of coordinates
    naip_files = index.lookup_tile(lat, lon)

    if filteredYears is None :
        res = naip_files
    else :
        res = []
        for naip_file in naip_files : 
            year = re.findall(r'\/\d{4}\/', naip_file)[0][1:-1] 
            if year in filteredYears :
                res.append(naip_file)
                
    return res


# Spatial index that maps lat/lon to NAIP tiles
index = NAIPTileIndex()  

def parse_blob_filename(file_name):
    """
        help : https://www.regextester.com/ 
        eg. 'v002/al/2011/al_100cm_2011/30085/m_3008503_ne_16_1_20110815.tif'
            version/state/year/state_res_year/quadrangle/wtf.tif 
    """

    # TO DO : make parsing better, to be resilient to slightly different file names
    # https://planetarycomputer.microsoft.com/dataset/naip#Storage-Documentation


    # (2011,2013,2015,2017,2019)    

    version = re.findall(r'v002/', file_name)[0][:-1]
    state = re.findall(r'\/[a-z]{2}\/', file_name)[0][1:-1]                 # Two-letter state code.
    year = re.findall(r'\/\d{4}\/', file_name)[0][1:-1]                     # Four-digit year
    res = re.findall(r'\/\w+_\w+_\w+\/', file_name)[0][4:-6]                # String specification of image resolution
    quadrangle = re.findall(r'\/\d+\/', file_name.strip(year))[1][1:-1]     # USGS quadrangle identifier, specifying a 7.5 minute x 7.5 minute area
    blob_filename = re.findall(r'\w+.tif', file_name)[0]                    # The filename is preserved from USDA's original archive to allow consistent referencing across different copies of NAIP

    # Filenames are generally formatted as : m_[quadrangle]_[quarter-quad]_[utm zone]_[resolution]_[capture date].tif
    quarterquad = re.findall(r'\_[a-z]{2}\_', blob_filename)[0][1:-1]
    quadid = re.findall('{}(\d*)\_'.format(quadrangle), blob_filename)[0]

    # In some cases, an additional date may be appended to the filename; in these cases, the first date represents the capture date, and the second date 
    # represents the date at which a subsequent version of the image was released to allow for a correction. 
    # eg. v002/nc/2018/nc_060cm_2018/36077/m_3607744_se_18_060_20180903_20190210.tif


    # for some reason this is the combination needed to make filenames unique
    estuary_file_name = 'NAIP_{}_{}_{}_{}_{}_{}.tif'.format(year, res, state, quadrangle, quarterquad, quadid)

    return estuary_file_name


# Path to the /azure folder in $SCRATCH where the tiles are to be downloaded
path_to_scratch = '../../scratch/gsialelli/azure/'
# List all blobs that exist for NAIP
all_blob_filenames = [val[0] for val in list(index.tile_index.values())]
for blob_filename in all_blob_filenames : 
    estuary_file_name = parse_blob_filename(blob_filename)
    #if not is_in_Estuary(estuary_file_name) :
    if not exists(path_to_scratch + estuary_file_name):
        # Download the tile in /azure under the name `estuary_file_name`
        download_url(blob_root + '/' + blob_filename, path_to_scratch + estuary_file_name)
        # Upload the file to Estuary
        #upload_to_Estuary(estuary_file_name, path_to_scratch)
        # Download the file from scratch folder
        #subprocess.call("rm {}".format(join(path_to_scratch, estuary_file_name)), shell=True)

# to get number of files in /azure directory : len([name for name in os.listdir('.') if os.path.isfile(name)])
# TO DO : investigate http.client.RemoteDisconnected: Remote end closed connection without response