# DOC_catchments

This includes scripts for calculating catchemnt characteristics in Sweden based on different data sources used in spatial analysis of DOC trends.  

## Requirnments 
A requirnemnts file is included. Install the requirnemts by runnning (I would recommend in a virtual environment) 

```
pip install -r requirements.txt
```

## SMHI Climate

This script is based on the [SMHI PTHBV](https://www.smhi.se/data/ladda-ner-data/griddade-nederbord-och-temperaturdata-pthbv) data. A gridded dataset for daily precipitation and temperature for all of Sweden. 

The function relies on the two input files for PTHBV daily temperature and precipitation for all of Sweden which can be downloaded from the [SMHI website](https://www.smhi.se/data/ladda-ner-data/griddade-nederbord-och-temperaturdata-pthbv)

