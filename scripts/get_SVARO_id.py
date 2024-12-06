#%%
import geopandas as gpd

gdf_catch = gpd.read_file("zip://input/shapefile/catchments.zip")
# %%

stations = gdf_catch[['lat','lon','mvm_id']]

# %%
import geopandas as gpd
from shapely.geometry import Point
import matplotlib.pyplot as plt



# Create GeoDataFrame directly
gdf = gpd.GeoDataFrame(
    stations,
    geometry=gpd.points_from_xy(stations["lon"], stations["lat"]),
    crs="EPSG:3006"  # SWEREF 99 TM
)
# %%
svaro = gpd.read_file("results/SVARO/aro.gpkg").to_crs("EPSG:3006")
gdf_with_uuid = gpd.sjoin(gdf, svaro[['ARO_UUID', 'geometry', 'AREA', 'AREA_UPSTREAM']], how='left', predicate='within').drop(columns=['index_right'])

gdf_with_uuid
# %%
# Ensure the directory exists
import os
os.makedirs("results/SVARO", exist_ok=True)

# Extract unique 'ARO_UUID' values, convert to a list, and format as a comma-separated string
unique_aro_ids = gdf_with_uuid['ARO_UUID'].dropna().unique()
aro_id_list = ",".join(map(str, unique_aro_ids))

# Save to a file
output_path = "results/SVARO/ARO_UUID.txt"
with open(output_path, "w") as file:
    file.write(aro_id_list)

print(f"Unique ARO_UUIDs saved to: {output_path}")

# %%
