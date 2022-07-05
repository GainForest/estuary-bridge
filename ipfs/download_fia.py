""" Using azure (https://planetarycomputer.microsoft.com/dataset/fia#Blob-Storage-Notebook) 
"""

# conda create --name fia-azure python=3.8
# conda activate fia-azure
# pip install adlfs
# pip install fastparquet

import dask.dataframe as dd
from adlfs import AzureBlobFileSystem

# Not used directly, but either fastparquet or pyarrow needs to be installed
import fastparquet

storage_account_name = 'cpdataeuwest'
folder_name = 'cpdata/raw/fia'

fs = AzureBlobFileSystem(account_name=storage_account_name)
parquet_files = fs.glob(folder_name + '/*parquet')
print('Found {} Parquet files'.format(len(parquet_files)))

df = dd.read_parquet('az://' + folder_name + '/cond.parquet', storage_options={'account_name':storage_account_name}).compute()
# but that never ends for some reason