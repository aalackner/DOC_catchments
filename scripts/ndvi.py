# %% 
import ee
import pandas as pd
import geopandas as gpd
from datetime import datetime

import os
import geopandas as gpd
# %% Load your shapefile
zip_catch = "shapefiles/catch_316.zip"

# Load the shapefiles from the ZIP files
gdf_catch = gpd.read_file(f"zip://{zip_catch}")

gdf_catch.to_crs(epsg=4326, inplace=True)
# %% 
# Initialize the Earth Engine API make sure this works!
ee.Authenticate(auth_mode='notebook')
ee.Initialize(project='ee-anna-lackner')
print(ee.String('Hello from the Earth Engine servers!').getInfo())

# %%
# Function to generate the correct last day of the month (handling leap years)
def get_last_day_of_month(year, month):
    if month == "02":  # Special handling for February (Leap Year)
        if (year % 4 == 0 and (year % 100 != 0 or year % 400 == 0)):  # Leap year check
            return f"{year}-{month}-29"  # Leap year (February 29)
        else:
            return f"{year}-{month}-28"  # Non-leap year (February 28)
    elif month in ["04", "06", "09", "11"]:  # 30-day months
        return f"{year}-{month}-30"
    else:  # 31-day months
        return f"{year}-{month}-31"
# Function to load the shapefile and convert it to a FeatureCollection
def geo_to_ee(gdf):
    features = []
    for idx, geometry in gdf.geometry.items():
        try:
            mvm_id = gdf.loc[idx, 'mvm_id']  # Extract mvm_id for this row
            
            # Check the geometry type and convert accordingly
            if geometry.geom_type == 'Polygon':
                ee_geom = ee.Geometry.Polygon(list(geometry.exterior.coords))
                features.append(ee.Feature(ee_geom).set('mvm_id', mvm_id))
            elif geometry.geom_type == 'MultiPolygon':
                polygons = [ee.Geometry.Polygon(list(poly.exterior.coords)) for poly in geometry.geoms]
                ee_geom = ee.Geometry.MultiPolygon(polygons)
                features.append(ee.Feature(ee_geom).set('mvm_id', mvm_id))
            elif geometry.geom_type == 'Point':
                ee_geom = ee.Geometry.Point([geometry.x, geometry.y])
                features.append(ee.Feature(ee_geom).set('mvm_id', mvm_id))
            else:
                print(f"Skipping unsupported geometry type: {geometry.geom_type}")
        except Exception as e:
            print(f"Error processing geometry {idx}: {e}")
    return ee.FeatureCollection(features)

# Function to generate rows for the DataFrame
def generate_ndvi_rows(gdf, years, months, Landsat_NDVI):
    yes_start = True # swithch to false if you want to start further along in the dataframe
    for idx, geometry in gdf.iterrows():
        if yes_start == False:
            mvm_id = geometry['mvm_id']
            print(f"Processing geometry with mvm_id: {mvm_id}")
            print("already done")
            if mvm_id == 34704:
                yes_start = True
        else:
            try:
                mvm_id = geometry['mvm_id']
                print(f"Processing geometry with mvm_id: {mvm_id}")
                
                # Convert the geometry to an Earth Engine object
                shape = geo_to_ee(gdf.loc[[idx]])  # Use the current row for the geometry
                print(f"Shape for mvm_id {mvm_id} converted to Earth Engine FeatureCollection.")
                
                for year in years:
                    for month in months:
                        print(f"Processing month: {month} for mvm_id {mvm_id} in {year}")
                        
                        start_date = f"{year}-{month}-01"
                        end_date = get_last_day_of_month(year, month)
                        
                        # Filter Landsat data
                        landsat_filtered = Landsat_NDVI \
                            .filter(ee.Filter.date(start_date, end_date)) \
                            .filterBounds(shape)
                        
                        image_count = landsat_filtered.size().getInfo()
                        print(f"Number of images for {month}-{year}: {image_count}")
                        
                        if image_count == 0:
                            print(f"No images for {month}-{year} and mvm_id {mvm_id}. Skipping.")
                            continue
                        
                        # Calculate statistics
                        ndvi_mean = landsat_filtered.reduce(ee.Reducer.mean())
                        ndvi_median = landsat_filtered.reduce(ee.Reducer.median())
                        ndvi_stdDev = landsat_filtered.reduce(ee.Reducer.stdDev())
                        
                        stats_mean = ndvi_mean.reduceRegions(
                            collection=shape,
                            reducer=ee.Reducer.mean(),
                            scale=30,
                            tileScale=2
                        )
                        
                        stats_median = ndvi_median.reduceRegions(
                            collection=shape,
                            reducer=ee.Reducer.median(),
                            scale=30,
                            tileScale=2
                        )
                        
                        stats_stdDev = ndvi_stdDev.reduceRegions(
                            collection=shape,
                            reducer=ee.Reducer.stdDev(),
                            scale=30,
                            tileScale=2
                        )
                        
                        try:
                            mean_info = stats_mean.getInfo()
                            median_info = stats_median.getInfo()
                            stdDev_info = stats_stdDev.getInfo()
                            
                            if 'features' in mean_info and len(mean_info['features']) > 0:
                                for i in range(len(mean_info['features'])):
                                    yield {
                                        'month': month,
                                        'year': year,
                                        'mvm_id': mvm_id,
                                        'NDVI_mean': mean_info['features'][i]['properties'].get('mean', None),
                                        'NDVI_median': median_info['features'][i]['properties'].get('median', None),
                                        'NDVI_stdDev': stdDev_info['features'][i]['properties'].get('stdDev', None),
                                    }
                        except Exception as e:
                            print(f"Error computing statistics for {month}-{year} and mvm_id {mvm_id}: {str(e)}")
                            yield {
                                'month': month,
                                'year': year,
                                'mvm_id': mvm_id,
                                'NDVI_mean': None,
                                'NDVI_median': None,
                                'NDVI_stdDev': None,
                            }
            except Exception as e:
                print(f"Error processing mvm_id {geometry['mvm_id']}: {e}")

# Load your shapefile (replace 'gdf_catch' with the actual GeoDataFrame name)
gdf = gdf_catch

# Define the months and years for which you want to calculate NDVI
months = ["01", "02", "03", "04", "05", "06", "07", "08", "09", "10", "11", "12"]
years = list(range(1990, 2024))

# Define the Landsat 8 NDVI Composite dataset (8-day composite)
Landsat_NDVI = ee.ImageCollection('LANDSAT/COMPOSITES/C02/T1_L2_8DAY_NDVI')

# Create the DataFrame directly from the generator
ndvi_rows = generate_ndvi_rows(gdf, years, months, Landsat_NDVI)
df = pd.DataFrame(ndvi_rows)

# Save the DataFrame to a CSV file
out_path = r"Output\NDVI.csv"
df.to_csv(out_path, index=False)
