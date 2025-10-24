# Getting Started

In order to extract catchment characteristics, it is necessary to have catchments in the form of either a shapefile (.shp) or a zip file (.zip) file. The path for this, and all other input data, can be customized for each script. The scripts are written to work best with catchments that are in SWEREF TM99, ESPG:3006. 

In addition it is necessary to have python and R environments that can run the code. The requirements are defined below. 

## Features

This repository includes the extractions various catchment characteristics within Swedish Catchments split into the following categories: 

| Characteristic | Workflow | Output | Required Input|
|----------------|----------|---------|--------------|
|[Soil Depth](#soil-depth) | soil_depth.py| summary statistic on soil depth in the catchment| SGU Jorddjupsmodell|
|[Climate](#climate)|precip_as_snow.py|daily temp, precipitation, and precipitation as snow for each catchment|SMHI PT-HBV; Jennings et al, 2018 precipitation threshold|
|[Deposition](#deposition)|emep.py|monthly total N and S deposition for each catchment | EMEP MSC-W* |
|[High coast and ecogegions](#high-coast-and-ecoregions)|High_coast_ecoregions.py|% of catchemnt below highest coast line and outlet ecoregion|highest coast line, Swedish ecoregions|
|[Peat and Ditches](#peat-and-ditches)|dd_peat.py|ditch density, % peat|SLU ditch map, SLU peat map|
|[NDVI](#ndvi)|ndvi.py|monthly summer NDVI timeseries|Landsat 8-Day NDVI composite*|
|[Runoff](#runoff)|get_SVAR_id.py & discharge|S-HYPE daily runoff|SMHI S-HYPE data|
|[Water chemistry](#water-chemistry)|get_water_chem.r|water chemistry samples for all stations|MVM database*|
|[Compilation](#compilation)|compilation.rmd|catchment characteristics and timeseries of water chemistry|output of above scripts|

*Download via API included in the script.   

# Requirements

## Input Data

While some input data is downloaded as part of the script, many scripts require, manual downloads before the extraction can be run. You can find exact information on the requirements of each script. 

## Environments 

All the python scripts run on a venv or conda env based on the requirements_py.txt file. Download of the water chemistry data is in R, instructions are specified in the [section on water chemistry](#water-chemistry).  These can be installed using: 

**Conda**

```bash
conda create -n py-gis --file requirements_py.txt
```


```bash
conda activate py-gis 
```

**Virtual environments**

```bash
python -m venv venv
source venv/bin/activate  # On Windows use `venv\Scripts\activate`
pip install -r requirements_py.txt
```

### R

Download of the water chemistry data and aggregation of all the data into a single file is in R. For this you can us either a renv or a conda env 

```bash
conda create -n r-env --file requirements_r.txt
```

or 

R-env instructions.... Or at least a state of the script something something...


___

# Extractions

## Soil Depth 

soil_depth.py

**args:** 
- -r    raster for SGU soil depth map 
- -c    catchment shapefile
- -o    output file as a .csv
- -id   id variable as str, default: "mvm_id"

Dependencies:

rasterio, geopandas , numpy,  pandas


**Input:**

SGU Soil Depth Map can be downloaded from [SGU's website](https://www.sgu.se/produkter-och-tjanster/geologiska-data/jordarter--geologiska-data/jorddjupsdata/), where you can also find more detailed information about the soil depth model used for the generation of the data. 

**Output:** 

A .csv file containing a row for each catchment with id, mean soil depth of the catchment, standard deviation of soil depth, the minimum soil depth, the maximum soil depth, the 25th percentile, 75th percentile. 

In the same folder as the output file you will also get a txt file "failed_soil_depth.txt" With error ,messages for each catchment for which the script did not succeed. 

**Example:**

```bash
python scripts\soil_depth.py -r "path\to\soil\depth\jorddjup_10x10m.tif"  -c "path\to\catchments.shp" -o  "path\to\results\soil_depth.csv" -id "id"
```

## Climate

precip_as_snow.py

**args:** 
- -f    folder for SMHI PT-HBV files 
- -c    catchment shapefile
- -o    output folder for by station result
- -t    gridded threshold form Jenson 2017 as .tif
- -id   id variable as str, default: "mvm_id"

**Dependencies:**

rasterio, geopandas , numpy,  pandas, xarray, shapely, gc, 


**Input:** 

SMHI PT-HBV daily gridded data can be downloaded from [SMHI's website](https://www.smhi.se/data/sok-oppna-data-i-utforskaren/pthbv-griddade-dygnsvarden-av-temperatur-och-nederbord-over-sverige-sedan-ar-1961), where you can also find more detailed information about the dataset used for the generation of the precipitation and temperature data.

The threshold temperature for when precipitation falls as snow vs rain was taken from [Jennings et al, 2018](https://doi.org/10.1038/s41467-018-03629-7) and the gridded data for snow thresholds can be found at  https://doi.org/10.5061/dryad.c9h35. The jennings_et_al_2018_file4_temp50_raster.tif is needed for this script. 

If the lake is not in the gridded thresholds from Jennings et al, 2018 then a threshold of 0 °C is used as default threshold. 

**Output:** 

In the output folder there will be a csv for each id, containing daily area weighted precipitation in mm/day (pr), temperature in  °C (tas), and precipitation as snow in water equivalence of mm (pr_snow), as well as the specific temperature at which precipitation turns to snow according to Jennings et al, 2018 (snow_threshold). 
 

**Example:**

```bash
python scripts/precip_as_snow.py -f "input/SMHI_folder" -t "path/to/jennings_et_al_2018_file4_temp50_raster.tif"  -c "path/to/catchments.shp" -o  "path/to/results/climate_by_station" -id "id" > "log/climate_log.txt"
```

## Deposition

emep.py

**args:** 
- -f    folder for emep data (can be empty is download is set to True) 
- -c    catchment shapefile
- -o    output file
- -sy   start year as integer
- -ey   end year as integer
- -id   id variable as str, default: "mvm_id"
- -d    download required, default "False", if "True" will the data from the thredds.met.no server 

**Dependencies:**

rioxarray, geopandas , numpy,  pandas, requests, shapely,


**Input:** 

The deposition in sulfur and nitrogen is extracted from the [EMEP MSC-W](https://emep.int/mscw/mscw_moddata.html) modelled air concentrations and depositions. Total deposition is used including wet and dry deposition of both sulfur and nitrogen:

Total S = DDEP_SOX_m2Grid + WDEP_SOX
TOTAL N = DDEP_OXN_m2Grid + WDEP_OXN + DDEP_RDN_m2Grid + WDEP_RDN

**Output:** 

The output file is a .csv file with monthly mean and median deposition of Sulfur and Nitrogen in kg/ha/yr across each catchment. 
 

**Example:**

```bash
python scripts/emep.py -f "input/EMEP/data"  -c "data/test.shp" -o  "test_results/emep.csv" -id "id" -sy 1990 -ey 1995  > "log/emep_log.txt"
```

## High Coast and Ecoregions

High_coast_ecoregions.py

**args:** 
- -hk   shapefile for the highest coast line  
- -eco  shapefile for swedish ecoregions
- -c    catchment shapefile
- -o    output file
- -id   id variable as str, default: "mvm_id"
- -x    column name in shapefile of catchments for x coordinate of outlet 
- -y    column name in shapefile of catchments for y coordinate of outlet
- -cent if set to "True" it will find teh ecoregion of the center of the catchment. default: "False"

**Dependencies:**

geopandas , numpy,  pandas, shapely, matplot


**Input:** 

The ecoregions used here are the Swedish limnological ekoregions and are described further by [Naturvardsverket](https://www.havochvatten.se/download/18.276e7ae81443563a7504843/1708690754325/nv-handbok-2007-3-kartlaggning-och-analys-av-ytvatten.pdf). The file is stored in the SMHI's geodatabse and is accessible upon request. 

The highest coast line represents the highest coastline as described by [Påsse & Daniels, 2015](https://resource.sgu.se/produkter/rm/rm137-rapport.pdf). This shapefile is not publicly available to my knowledge. 

Since both of these are no longer easily findable, please contact me if you would like to use this data. 

**Output:** 

The output file is a .csv file with % below the highest coast line (pct_below_HK), and the ecoregion (ekor). 
 

**Example:**

```bash
python scripts/High_coast_ecoregions.py -hk "file/to/hk.shp"  -c "data/test.shp" -o  "test_results/hk.csv" -id "id" -eco "path/to/eco.shp" -cent "True" > "log/hk_log.txt"
```

## Peat and ditches

*dd_peat.py*

Alternatively if ditches and peat want to be looked at separately,  *ditches.py* and *peat_area.py* can be used but these rely on a [arcpy environment](https://pro.arcgis.com/en/pro-app/latest/arcpy/get-started/installing-arcpy.htm). 

**args:** 
- -d   vector version of the SLU ditch map, can be A .gdb with a layername or a folder with shapefiles that make up the entire dataset. 
- -c    catchment shapefile (can be .zip containing shapefile) 
- -o    output folder
- -id   id variable as str, default: "mvm_id"
- -pr   peat raster of the SLU ClassifiedPeatMap.tif
- -ln   layer name, only applies if the ditch map is a gdb with a single layer as the ditches. default: " 
- -st   split threshold this is the size of catchment at which the catchment gets subdivided, default: 1.1e8




**Dependencies:**

geopandas , numpy,  pandas, shapely, dask, rioxarray, xarray,  rasterio, gc, fiona


**Input:** 


To get the ditch length for each catchment a vectorized version of the [SLU Ditch map](https://www.slu.se/en/environment/statistics-and-environmental-data/environmental-data-catalogue/slu-ditch-maps/) was used. It can be downloaded from the [Swedish Forest Agency's FTP server](https://www.skogsstyrelsen.se/e-tjanster-och-kartor/karttjanster/geodatatjanster/ftp/) as a geotiff. 

In order to get a vectorized version the raster files were [skeletonised](https://www.whiteboxgeo.com/manual/wbt_book/available_tools/image_processing_tools.html?highlight=skeleton#linethinning) and [vectorised](https://www.whiteboxgeo.com/manual/wbt_book/available_tools/data_tools.html?search=rasterlines) using [Whitebox Tools](https://www.whiteboxgeo.com/manual/wbt_book/intro.html). 

For determining peat in the catchment the [SLU Peat Map](https://www.slu.se/en/environment/statistics-and-environmental-data/environmental-data-catalogue/peat-map-of-the-forest-land/) was used. The SLU Peat Map can be [downloaded from SLU](https://gis.slu.se/data/peat_1_0/). The version needed for this script is the Klassad_torvkarta, the classified peat map. 

**Output:** 

The final output is a file "peat_ditches.csv" in the given output folder which contains the total ditch length in m (total_ditch_length), the percentage of ditches in peat (ditch_perc_peat), the ditch density inside the catchment in m/m2 (ditch_density_m_m2), the percentage of the catchment that is open water in the peat map (peat_pct_Vatten), the percentage of the catchment that is mineral soil (peat_pct_Mineraljord), the percentage of the catchment that is peat >= 30cm of depth(peat_pct_Torv_total).  

In the process a folder, *by_station*, will be created that stores the peat information for each catchment. This is because my computer has 64GB RAM, so the size of catchment I can process is limited, so if the catchment is too big than it is split into subdivisions. The script in the end goes through all the files saved in by_station and aggregates all the data into a single row for each catchment. You can set this threshold in using the -st parameter. 
 

**Example:**

```bash
python scripts/dd_peat.py -d "input/Dikeskarta/mosaic_ditches.gdb"  -c "path/to/catchments.shp" -pr "input\Torvkarta\Klassad_torvkarta\ClassifiedPeatMap.tif" -o  "path/to/results/folder/peat_ditches" -id "id" > "log/dd_peat_log.txt"
```

## NDVI

ndvi.py

**args:** 

- -c    catchment shapefile (can be .zip containing shapefile) 
- -o    output folder
- -id   id variable as str, default: "mvm_id"
- -sy   start year as integer, default: 1990
- -ey   end year as integer, default: 2024
- -log  log folder, default: log





**Dependencies:**

ee, geemap, logging, geopandas 


**Input:** 

There is no additional input needed except for the catchments. However, this script relies on google earth engione so you will need to authenticate your google earth engine account, and create a project 'ndvi-omdrev' as that is what gets initialized. 

The script uses google earth engine to get the preprocessed NDVI data from [LANDSAT/COMPOSITES/C02/T1_L2_8DAY_NDVI](https://developers.google.com/earth-engine/datasets/catalog/LANDSAT_COMPOSITES_C02_T1_L2_8DAY_NDVI). This was choosen as it has the longest time series covering Sweden.


**Output:** 

In the output folder a csv for each id: NDVI_{id}.csv with a timeseries of monthly min, max, median NDVI for the summer months (May to Oktober).  


**Example:**

```bash
python scripts/ndvi.py  -c "data/test.shp"  -o  "test_results/ndvi" -id "id" -sy 1996 -ey 1998
```

## Runoff

To get runoff for each catchment, it is necessary to complete three seperate steps: First use get_SVAR_id.py to generate ARO_UUID ids that can then be entered into [NADIA](https://vattenwebb.smhi.se/nadia/) to download the discharge needed for discharge.py to generate runoff for each catchment based on [SMHI's S-HYPE data](https://www.smhi.se/data/sjoar-och-vattendrag/vattenwebb/om-tjanster-i-vattenwebb/data-for-delavrinningsomraden---sotvatten). 

get_SVAR_id.py > NADIA (manually) > discharge.py

### get_SVAR_id.py

**args:** 

- -c    catchment shapefile (can be .zip containing shapefile) 
- -o    output folder
- -svar SVAR delavrinningsområde file .shp or .zip, if path is given that does not yet exist, file will be downloaded from SMHI as .zip.
- -id   id variable as str, default: "mvm_id"
- -x    column name in shapefile of catchments for x coordinate of outlet 
- -y    column name in shapefile of catchments for y coordinate of outlet
- -map "true" or "false" to indicate whether a map should be made of the catchments and their corresponding SVAR catchment

**Dependencies:**

geopandas


**Input:** 

SVAR2022 delavrinnings område should be provided, or a empty .zip path needs to be given to which the script downloads the .zip of the SVAR2022 sub-catchemnts. These subcatchemnts can also be downloaded directly from [SMHI'website](https://www.smhi.se/data/sok-oppna-data-i-utforskaren/se-hy-delavrinningsomraden-svar2022). 


**Output:** 


There are three outputs from this script: 

ARO_UUID.txt: a textfile with all the ARO_UUID ids. The content of this file should be copy and pasted into NADIA for download of S-HYPE data. 

cats_svar2022.feather: a feather, that is needed in combination with the NADIA output, as input for discharge.py to generate station weighted runoff for each catchment. 

catchments_svar.html: A map of the catchemnts, stations, and corresponding SVAR2022 catchemnt. This output is optional and can be controlled with -map. 


**Example:**

```bash
python scripts/get_SVAR_id.py  -c "data/test.shp"  -o  "test_results/runoff" -id "id" -svar "input\SMHI\SVAR2022_delavrinningsomraden.zip" -map "true"
```

### NADIA

Using NADIA is necessary to go on with calculating runoff for each catchment. Follow the below steps before running discharge.py:

1. go to [NADIA](https://vattenwebb.smhi.se/nadia/)
2. copy and paste the content of ARO_UUID.txt into the text box provided. 
3. select Tidsteg: dygn and the time range in which you're interrested
4. Download the data by clicking: 'skicka'
5. save the downloaded .csv file and use it as input for discharge.py

### discharge.py

**args:** 

- -o    output folder (same as get_SVAR_id.py) 
- -id   id variable as str, default: "mvm_id"
- -f    filename of nadia output, should be placed inside -o, default: "2025-data.csv" 

**Dependencies:**

geopandas, re, pandas

**Input:** 

Output of [get_SVAR_id.py](#get_svar_idpy), cats_svaro.feather, and [NADIA](#nadia) output in output folder.  


**Output:** 

The final output for this script is daily_discharge.csv, a csv with daily modelled discharge for the catchment, including model uncertainty for the corresponding SMHI sub-catchemnt (Subid). 


**Example:**

```bash
python scripts/discharge.py  -o  "test_results/runoff" -id "id" -f "2025-data.csv"
```


## Water Chemistry

get_water_chem.r

**args**

In this file you will need to go into the script and set the paths and token manually. 

**Dependencies:**

jsonlite, tidyverse, sf (only if ids come from shapefile)

**Input:** 

There are two paths to change in the R script: 

1. The folder to use to place the results including intermediate steps. 
2. Where to take the ids from. These need to be the MVM database station ids.



**Output:** 

There are some intermediary folders that contain the data for individual stations. These are to prevent the need to recall the API, if you hadd stations. 

The main output is 'water_chem_combined.csv', a csv containing water chemistry samples between 1970 and 2025. 


**Example:**

```bash
Rscript scripts/get_water_chem.r >> log/chem.log
```

## Compilation/processing

**compilation.rmd** takes the files produced by the processes described above and runs through post processing to compile timeseries of water chemistry and a summary file of catchemt characteristics. 

The file can be used in partto process different catchmnet characteristics or the whole datset. File paths need to be adjusted with the script.

**Output:**

There are 2 main types of output files: water chemistry time series, and catchemnt characteristics. 

*Inside compilation.rmd catchemnt characteristics are called "drivers". 

