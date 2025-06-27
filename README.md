# DOC_catchments

This includes scripts for calculating catchment characteristics in Sweden based on different data sources used in spatial analysis of DOC trends.  

# How to

## Snakemake
you can either run the workflow or parts of the workflow using snakemake and containers. Then you need to have apptainer and snakemake installed. 

## individual scripts in your own environment
You can also run individual scripts and make sure you are running it in a conda or python environment that has the requirnments installed. these will differ from script to script. 

If you want to run individual scripts check the script to make sure you use the right arguments rom the terminal or change the input files in the script.

# Scripts

## Climate

name:   climate_aggregation.py

This script is based on the [SMHI PTHBV](https://www.smhi.se/data/ladda-ner-data/griddade-nederbord-och-temperaturdata-pthbv) data. A gridded dataset for daily precipitation and temperature for all of Sweden. It takes shapefiles and extractes the mean weighted daily temperature and precipitation from PT HBV climate data. 

The function relies on the two input files for PTHBV daily temperature and precipitation for all of Sweden which can be downloaded from the [SMHI website](https://www.smhi.se/data/ladda-ner-data/griddade-nederbord-och-temperaturdata-pthbv). 

These input rasters can also be found on the ivm slu gis server: \\ivm-gis.vatten.slu.se\gisdata_ivm\4_smhi\PTHBV\data_archive_1980to2023 

## Discharge

name:   discharge.py
        get_SVARO_id.py

## PLC 8 

name:   PLC8.py

PLC8 soil type aggregations

## Soil Depth

name:   soil_depth.py

## MVM water chemistry

name:    get_water_chem.r

## NDVI 

Uses Google Earth Engine to download NDVI from Landsat data, as monthly timeseries for each catchment.
