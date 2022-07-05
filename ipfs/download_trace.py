# script to download the carbonplan-trace maps

# to install dependencies : 
#   conda create --name trace python=3.8
#   conda activate trace
#   pip install carbonplan-trace 
#   pip install aiohttp

from posixpath import join
from carbonplan_trace.v0.data import cat
from os.path import isfile, getsize
import subprocess
import json

####################################################################################################################################
# Download the data from carbonplan-trace

def save_ds(ds, ds_name) :
    """
        Saves the xarray.Datasey `ds` in a file called `ds_name`.
        It applies an encoding (zlib, compression level = 9) to the dataset to reduce the file size.

        To load the file back : 
            ds = xarray.open_dataset(ds_name)
    """
    # TO DO : check if, because of encoding, something special has to be done to load the dataset back using `xarray.open_dataset`
    comp = dict(zlib=True, complevel=9)
    encoding = {var: comp for var in ds.data_vars}
    ds.to_netcdf(ds_name, encoding=encoding)


def get_all_uploaded_filenames():
    """
        Returns a list containing all the filenames that are currently uploaded on Estuary.
    """
    api_answer = subprocess.check_output("curl -X GET -H 'Authorization: Bearer ESTcf525b58-b1d6-4b82-a312-5880e1c3ae87ARY' https://api.estuary.tech/content/list", shell=True,universal_newlines=True)
    uploads = json.loads(api_answer)

    all_names = []
    for upload in uploads : 
        all_names.append(upload['name'])

    return all_names


def is_in_Estuary(file_name):
    """
        Checks if `file_name` has already been uploaded on Estuary.

        TO DO : is there a way to do this not via the filename? i don't think so, because the information about an uploaded file are limited to : 
        ['id', 'cid', 'name', 'userId', 'description', 'size', 'active', 'offloaded', 'replication', 'aggregatedIn', 'aggregate', 'pinning', 'pinMeta', 'failed', 'location', 'dagSplit']
    """
    all_names = get_all_uploaded_filenames()
    return (file_name in all_names)


def upload_to_Estuary(ds_name, PATH = ''):
    """
        Uploads the file PATH/ds_name to Estuary (if it hasn't been uploaded before).

        Estuary is currently in its alpha testing phase. Because of this, a maximum of 32 GB per upload. This limit will increase soon.
        If your data's size is under 3.57 GB, the Filecoin storage deals will not immediately execute after the upload.

        TO DO : more efficient way to do that ? because for every upload we're querying all previous ones.
    """

    try : 

        ESTUARY_TOKEN = 'ESTcf525b58-b1d6-4b82-a312-5880e1c3ae87ARY'
        FILE_PATH = join(PATH, ds_name)
        FILE_NAME = ds_name
        command = "curl --progress-bar -X POST -H 'Authorization: Bearer {}' -F 'data=@{}' -F 'name={}' https://shuttle-1.estuary.tech/content/add".format(ESTUARY_TOKEN, FILE_PATH, FILE_NAME)
        subprocess.call(command , shell = True)
    
    except Exception as e : 
        print('    Could not upload to Estuary.')
        print('    Because : ', e)



def download_all_tiles(yearFilter = False, prefix = 'carbonplan_trace_emissions_30m'):
    """
        Downloads all the exploitable carbonplan-trace emissions map tiles. 
    """

    # Calculate the range of existing tiles 
    xN_range = ['{:02n}N'.format(n) for n in range(0, 81, 10)]
    xS_range = ['{:02n}S'.format(n) for n in range(10, 51, 10)]

    yW_range = ['{:03n}W'.format(n) for n in range(10, 181, 10)]
    yE_range = ['{:03n}E'.format(n) for n in range(0, 171, 10)]

    years_range = list(range(2001, 2021))

    latitudes = xN_range + xS_range
    longitudes = yW_range + yE_range

    # Iterate over tiles and download them
    for lat in latitudes : 
        for lon in longitudes :

            # Empty (& thus non-exploitable) tiles raise an exception, we just ignore them
            try : 

                # Download the tile from carbonplan-trace
                print('lat, lon : ', lat, lon)
                emissions_tile = cat.emissions_30m(lat=lat, lon=lon).to_dask()
                
                # Save the tile in a file for each year 
                if yearFilter : 

                    for year in years_range : 
                        yearly_emissions_tile = emissions_tile.loc[dict(year=year)]

                        file_name = prefix + '_' + str(year) + '_' + lat + '_' + lon + '.nc'
                        if not is_in_Estuary(file_name) : 
                            if not isfile(file_name) : 
                                save_ds(yearly_emissions_tile, file_name)
                            upload_to_Estuary(file_name)
                            subprocess.call("rm {}".format(file_name), shell=True)

                # Or save the tile with all 20 years
                else : 

                    file_name = prefix + '_' + lat + '_' + lon + '.nc'
                    if not is_in_Estuary(file_name) : 
                        if not isfile(file_name) : 
                            save_ds(emissions_tile, file_name)
                        upload_to_Estuary(file_name)
                        subprocess.call("rm {}".format(file_name), shell=True)
                    else : print('Already downloaded')


            except Exception as e : 
                print('    Could not download tile ', prefix + '_' + lat + '_' + lon + '.nc')
                print('    Because : ', e)



def check_downloaded():
    """
        Helper function to visually check which tiles were downloaded, compared to the Hansen map (https://storage.cloud.google.com/earthenginepartners-hansen/GFC-2020-v1.8/download.html)
    """
    all_files = [f for f in get_all_uploaded_filenames if 'carbon' in f]
    coord = [f[31:-3] for f in all_files[1:]]
    ne_coord = [e for e in coord if 'N' in e and 'E' in e]
    nw_coord = [e for e in coord if 'N' in e and 'W' in e]
    se_coord = [e for e in coord if 'S' in e and 'E' in e]
    sw_coord = [e for e in coord if 'S' in e and 'W' in e]

    return ne_coord, nw_coord, se_coord, sw_coord