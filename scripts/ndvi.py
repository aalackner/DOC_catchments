#%% start logging 
from datetime import datetime
import logging
import sys

current_datetime = datetime.now().strftime("%Y_%m_%d")
str_current_datetime = str(current_datetime)
log_name =  "log_NDVI_"+str_current_datetime+".txt"
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    handlers=[
                        logging.FileHandler(log_name),
                        logging.StreamHandler()
                    ])


#%% connect to google earth engine

import ee
import geemap
# Authenticate
ee.Authenticate(auth_mode='notebook')
ee.Initialize(project='ee-anna-lackner')
print(ee.String('Hello from the Earth Engine servers!').getInfo())


#%% acess shapefiles to be used

import os
import pandas as pd
import geopandas as gpd

zip_catch = "shapefiles\\aro_omdrevsjöar_5437_250624\\aro_omdrevsjöar_5437_250624.shp"


# Load the shapefiles from the ZIP files
gdf_catch = gpd.read_file(zip_catch)

gdf_catch.to_crs(epsg=4326, inplace=True)

gdf_catch.rename(columns={"mvmid":"mvm_id"}, inplace = True)
#%%
import geopandas as gpd
from datetime import datetime

# Initialize the Earth Engine API
ee.Initialize()

# Function to calculate the last day of the month
def get_last_day_of_month(year, month):
    if month == "02":
        return f"{year}-{month}-29" if year % 4 == 0 and (year % 100 != 0 or year % 400 == 0) else f"{year}-{month}-28"
    elif month in ["04", "06", "09", "11"]:
        return f"{year}-{month}-30"
    return f"{year}-{month}-31"

# Function to convert GeoDataFrame row to Earth Engine FeatureCollection
def geo_to_ee(gdf_row):
    geometry = gdf_row.geometry
    mvm_id = gdf_row['mvm_id']
    if geometry.geom_type == 'Polygon':
        ee_geom = ee.Geometry.Polygon(list(geometry.exterior.coords))
    elif geometry.geom_type == 'MultiPolygon':
        polygons = [ee.Geometry.Polygon(list(poly.exterior.coords)) for poly in geometry.geoms]
        ee_geom = ee.Geometry.MultiPolygon(polygons)
    elif geometry.geom_type == 'Point':
        ee_geom = ee.Geometry.Point([geometry.x, geometry.y])
    else:
        logging.error('Unsupported geometry %s',str(geometry.geom_type) )
        raise ValueError(f"Unsupported geometry type: {geometry.geom_type}")
    return ee.FeatureCollection([ee.Feature(ee_geom).set('mvm_id', mvm_id)])

# Function to compute NDVI statistics for a specific mvm_id
def process_mvm_id(gdf_row, years, months, Landsat_NDVI, output_dir):
    mvm_id = gdf_row['mvm_id']
    logging.info(f"Processing mvm_id: {mvm_id}")
    shape = geo_to_ee(gdf_row)
    
    rows = []
    for year in years:
        for month in months:
            start_date = f"{year}-{month}-01"
            end_date = get_last_day_of_month(year, month)
            
            landsat_filtered = Landsat_NDVI \
                .filter(ee.Filter.date(start_date, end_date)) \
                .filterBounds(shape)
            
            image_count = landsat_filtered.size().getInfo()
            if image_count == 0:
                continue
            
            ndvi_mean = landsat_filtered.reduce(ee.Reducer.mean())
            
            stats_mean = ndvi_mean.reduceRegions(
                collection=shape,
                reducer=ee.Reducer.mean(),
                scale=30,
                tileScale=2
            )
            
            try:
                mean_info = stats_mean.getInfo()
                
                for i in range(len(mean_info['features'])):
                    rows.append({
                        'mvm_id': mvm_id,
                        'year': year,
                        'month': month,
                        'NDVI_mean': mean_info['features'][i]['properties'].get('mean', None),
                    })
            except Exception as e:
                    logging.error("Error processing stats for mvm_id {%s} (%s-%s): %s", str(mvm_id), str(year), str(month), e)
    
    if rows:
        output_path = os.path.join(output_dir, f"NDVI_{mvm_id}.csv")
        pd.DataFrame(rows).to_csv(output_path, index=False)
        logging.info(f"Saved results for mvm_id %s to %s", str(mvm_id), output_path)
    else:
        logging.info("No valid NDVI data found for mvm_id %s.", str(mvm_id))

# Main processing loop
def main():
    output_dir = "Output/NDVI_omdrev"
    os.makedirs(output_dir, exist_ok=True)
    
    months = [ "04", "05", "06", "07", "08", "09", "10", "11"]
    years = list(range(2000, 2024))
    Landsat_NDVI = ee.ImageCollection('LANDSAT/COMPOSITES/C02/T1_L2_8DAY_NDVI')
    
    for idx, gdf_row in gdf_catch.iterrows():
        try:
            process_mvm_id(gdf_row, years, months, Landsat_NDVI, output_dir)
        except Exception as e:
            logging.error("Error processing mvm_id %s: %s", str(gdf_row['mvm_id']), e)

if __name__ == "__main__":
    main()

#%% close logger
# Get the root logger (or any named logger if used)
logger = logging.getLogger()

# Iterate through all handlers and close them
for handler in logger.handlers[:]:  # Use a slice to clone the list while modifying
    handler.close()
    logger.removeHandler(handler)
# %%
