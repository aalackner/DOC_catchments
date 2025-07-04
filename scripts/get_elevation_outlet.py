#%%
import os
os.chdir(r"C:\Users\anlr0006\repos-win\DOC_catchments\scripts")

#%% 
# First I would like to use the flow accumulation lines to find the outlet of my shapefile. 
import geopandas as gpd

flow_lines_path = r"C:\Users\anlr0006\repos-win\DOC_catchments\input\DEM_10m\flow_acc_lines_dissolved.shp.zip"
dem = r"C:\Users\anlr0006\repos-win\DOC_catchments\input\DEM_10m\slu_mosaik_10m\slu_mosaik_10m_reSamp.tif"

# Now I would like to use the flow lines to find the outlet of my shapefile.

# Define the output file path for the outlet shapefile
matchad_path = r"C:\Users\anlr0006\repos-win\DOC_catchments\input\SMHI\shapefiles\MatchadSVAROV2.zip"

matchad_area = gpd.read_file(f"zip://{matchad_path}")

matchad = gpd.read_file(f"zip://{matchad_path}")
flow_lines = gpd.read_file(f"zip://{flow_lines_path}")

# Find the intersection of all the points where the flow lines cross in and out of matchad
# Convert the matchad polygons to their boundaries (lines)
matchad['geometry'] = matchad.boundary

#%% 
# PLot the boundaries

import matplotlib.pyplot as plt

fig, ax = plt.subplots(figsize=(10, 10))
matchad.plot(ax=ax, color='blue', alpha=0.5)
matchad.head(5).plot(ax=ax, color='red', alpha=0.5)

#%% 
# Find the intersection of flow_lines with the matchad boundary
matchad_intersects = gpd.overlay(matchad, flow_lines, how='intersection', keep_geom_type=False)
# matchad_flow = gpd.overlay(flow_lines,matchad_area.head(100), how='intersection', keep_geom_type=False)
matchad_intersects


# %%
# Now let's find the elevation using the DEM for each possible outlet

# Save the intersection points to a temporary shapefile
intersects_path = r"C:\Users\anlr0006\repos-win\DOC_catchments\results\temp\outlet_points.shp"
matchad_intersects = matchad_intersects.explode(index_parts=False)  # Ensure single-part geometries  # Filter only Point geometries
matchad_intersects.to_file(intersects_path)

#%%
import arcpy

# Define the shapefile and DEM paths
shapefile_path = intersects_path
# Ensure the DEM file exists and is accessible
dem_path = r"C:\Users\anlr0006\repos-win\DOC_catchments\input\DEM_10m\slu_mosaik_10m\slu_mosaik_10m_reSamp.tif"
if not arcpy.Exists(dem_path):
    raise FileNotFoundError(f"DEM file not found: {dem_path}")
else:
    print(f"DEM file found: {dem_path}")

# Check if the shapefile and DEM are in the same CRS
shapefile_desc = arcpy.Describe(shapefile_path)
dem_desc = arcpy.Describe(dem_path)

if shapefile_desc.spatialReference.factoryCode != dem_desc.spatialReference.factoryCode:
    raise ValueError(f"CRS mismatch: Shapefile is in {shapefile_desc.spatialReference.name} "
                     f"while DEM is in {dem_desc.spatialReference.name}. Please reproject one of them.")
else:
    print("Shapefile and DEM are in the same CRS.")

# Add a new field to store elevation values
elevation_field = "elevation"

if not arcpy.ListFields(shapefile_path, elevation_field):
    arcpy.AddField_management(shapefile_path, elevation_field, "DOUBLE")
    print('Added elevation field to shapefile.')
else:
    print('Elevation field already exists in shapefile.')

# Check out the Spatial Analyst extension
if arcpy.CheckExtension("Spatial") == "Available":
    arcpy.CheckOutExtension("Spatial")
    print("Spatial Analyst extension checked out.")
else:
    raise RuntimeError("Spatial Analyst extension is not available.")

# Use the Extract Values to Points tool to get elevation values
temp_output = r"C:\Users\anlr0006\repos-win\DOC_catchments\results\temp\temp_with_elevation.shp"
arcpy.sa.ExtractValuesToPoints(shapefile_path, dem_path, temp_output, "INTERPOLATE", "ALL")


#%%
import matplotlib.pyplot as plt

temp_output = r"C:\Users\anlr0006\repos-win\DOC_catchments\results\temp\temp_with_elevation.shp"

shapefile = gpd.read_file(temp_output)

# Drop 'elevation' and rename RASTERVALU to 'elevation'
shapefile = shapefile.drop(columns=['elevation'])
shapefile = shapefile.rename(columns={'RASTERVALU': 'elevation'})

fig, ax = plt.subplots(figsize=(10, 10))
shapefile.plot(ax=ax, color='blue', alpha=0.5, markersize=1)

# Filter rows with elevation >= 0, but ensure at least one row per unique AU_CD
def filter_elevation(group):
    if (group['elevation'] >= 0).any():
        return group[group['elevation'] >= 0]
    else:
        return group

shapefile = shapefile.groupby("AU_CD", group_keys=False).apply(filter_elevation)
shapefile_outlet = shapefile.loc[shapefile.groupby("AU_CD")["elevation"].idxmin()]

shapefile_outlet.plot(ax=ax, color='red', alpha=0.5)
# Save the outlet points to a new shapefile
outlet_path = r"C:\Users\anlr0006\repos-win\DOC_catchments\results\slu_sgu\outlet_points_elevation.shp"
shapefile_outlet.to_file(outlet_path)

print(f"Outlet points saved for {len(shapefile_outlet)} of 421 catchments to {outlet_path}")

#%% 
# %%
#Putting it all together and then checking what they look like using folium
import pandas as pd


# Read the shapefiles
outlets =  gpd.read_file(outlet_path)

outlets


#%%
dict_elevation = {
    '657573-698433': 0.0,
    '658250-666111': 12,
}

dict_coordinates = {'657573-698433': (6575786, 699966),
    '658250-666111': (6582662, 665718)}

#%%
import folium

# Step 1: Add missing rows to outlets based on matchad
missing_au_cd = set(matchad['AU_CD']).difference(set(outlets['AU_CD']))
missing_rows = matchad[matchad['AU_CD'].isin(missing_au_cd)].copy()

# Step 2: Add coordinates and elevation to the new rows
missing_rows['elevation'] = missing_rows['AU_CD'].map(dict_elevation)
missing_rows['geometry'] = missing_rows['AU_CD'].map(lambda x: gpd.points_from_xy([dict_coordinates[x][1]], [dict_coordinates[x][0]])[0])

# Append the missing rows to outlets
outlets = pd.concat([outlets, missing_rows], ignore_index=True)


# Convert to WGS 84 for mapping
outlets_wgs84 = outlets.to_crs("EPSG:4326")
matchad_wgs84 = matchad.to_crs("EPSG:4326")

# Step 4: Map matchad and outlet points with popups
m = folium.Map(location=[62.0, 15.0], zoom_start=6)

# Add matchad boundaries with popups
for _, row in matchad_wgs84.iterrows():
    folium.GeoJson(
        row.geometry,
        name=f"Catchment: {row['AU_CD']}",
        style_function=lambda x: {'color': 'blue', 'weight': 2},
        tooltip=folium.Tooltip(f"AU_CD: {row['AU_CD']}")
    ).add_to(m)

# Add outlet points with popups
for _, row in outlets_wgs84.iterrows():
    folium.Marker(
        location=[row.geometry.y, row.geometry.x],
        popup=f"AU_CD: {row['AU_CD']}, Elevation: {row['elevation']}"
    ).add_to(m)

m


# %%

# outlets[['AU_CD', 'elevation', 'geometry']].to_file(r"C:\Users\anlr0006\repos-win\DOC_catchments\results\slu_sgu\outlet_points_elevation.shp")
# %%