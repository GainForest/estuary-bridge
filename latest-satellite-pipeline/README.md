# :artificial_satellite: Satellite fetcher and saver

Pipeline that, provided with a `.geojson` file, does the following : 
- fetches the latest Sentinel-2 satellite images of the area of interest (AOI)
- downloads the corresponding tiles from Google Earth Engine (GEE)
- forever uploads it to the [Interplanetary File System](https://ipfs.io/) (IPFS) via [Estuary](https://estuary.tech/home)

## Supported satellites 
### [Sentinel-2 MSI: MultiSpectral Instrument, Level-2A](https://developers.google.com/earth-engine/datasets/catalog/COPERNICUS_S2_SR)
### [Planet & NICFI Basemaps for Tropical Forest Monitoring](https://developers.google.com/earth-engine/datasets/tags/nicfi)
Note that to enable support for `NICFI`, you need to follow the steps described [here](https://developers.planet.com/docs/integrations/gee/nicfi/) : 
1. Once you have a NICFI Planet account and are logged into Planet with that account, you can self administer access to the Basemaps in GEE by navigating to your Account Settings page.
2. Here you should see a “Access NICFI Data in Google Earth Engine” section. In this section, select the “Add to Earth Engine” button.
3. This will open a dialog with the three EE Image Collections, which house the NICFI Basemaps, and a field to enter the email associated with your GEE account (note this may be different from your Planet account). The three EE Image Collections are: Tropical Americas, Tropical Africa, Tropical Asia.

## Installing

Create a virtual environment for the project

    conda create --name sat-pipeline python=3.8

Activate it 

    conda activate sat-pipeline

And install the dependencies using 

    pip install earthengine-api --upgrade geemap pydrive


## Running the pipeline

Simply run 

    python3 latest_sat_img.py -sat [satellite] -start [earliest_date] -end [latest_date] -d [days] -w [weeks] -m [months] -file [path_to_file] -cloud [cloud_cover] -name [site_name] -cont [continent] -est [save_to_estuary]
    
where : 
- `satellite` : satellite to consider (`NICFI` or `S2`).
- `earliest_date` : earliest date to consider (format `YYYY-MM-DD` for `S2`, `YYYY-MM` also supported for `NICFI`).
- `latest_date` : latest date to consider (format `YYYY-MM-DD` for `S2`, `YYYY-MM` also supported for `NICFI`).
- `days` : alternatively, number of days to consider.
- `weeks` : alternatively, number of weeks to consider.
- `months` : alternatively, number of months to consider.
- `path_to_file` : path to the `.geojson` file of the AOI.
- `cloud_cover` : percentage of cloud cover we tolerate (only supported for `S2`). By default, it is set to `100`. 
- `site_name` : the AOI's name, for filenames purposes. By default, it is the `.geojson` filename.
- `continent` : the continent to consider for `NICFI`. Has to be one of `asia`, `americas`, or `africa`.
- `est` : whether to upload the resulting `.tiff` file(s) to Estuary.
