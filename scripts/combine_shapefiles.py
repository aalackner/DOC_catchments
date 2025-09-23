#%%
import geopandas as gpd
import pandas as pd
import os

folder = r"\\storage.slu.se\Home$\anlr0006\My Documents\04_Projects\11_Lakes\01_data\02_raw_data\catchments"

file_1 = os.path.join(folder, "aro_trendsjöar_130_250703", "aro_trendsjöar_130_250703.shp")
file_2 = os.path.join(folder, "aro_omdrevsjöar_6194_250701", "aro_omdrevsjöar_6194_250701.shp")

file_3 = os.path.join(folder, "merged_catchments", "merged_catchments.shp")

#%%

# Load shapefiles
gdf_1 = gpd.read_file(file_1)
gdf_2 = gpd.read_file(file_2)   

concat = gpd.GeoDataFrame(pd.concat([gdf_1, gdf_2], ignore_index=True))

concat.drop_duplicates(subset = "mvmid").rename(columns={"mvmid": "mvm_id"}).to_file(file_3, driver='ESRI Shapefile') 

test = gdf_2.iloc[0:3].rename(columns={"mvmid": "mvm_id"})

test.to_file(os.path.join(folder,"test", "test.shp"), driver='ESRI Shapefile')



# %%
