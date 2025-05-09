
#%% files
path_vso = r"..\input\SMHI\shapefiles\VSO\VSO_polygon.shp"
path_omrade = r"..\input\SMHI\shapefiles\SVARO_Vattenformommstomrade.shp"
path_surface = r"..\input\SMHI\shapefiles\SVARO_Vattenformommst.shp"

#%% imports
import geopandas as gpd
import pandas as pd
import os

#%% find the lakes that overlap with the VSO polygons

# First we read in the VSO polygons 
vso = gpd.read_file(path_vso)
# Then we buffer it by 10 m to ensure that we catch all lakes that are within the VSO polygons
vso_buffered = vso.copy()
vso_buffered['geometry'] = vso.geometry.buffer(10)

# Then we read in the lakes
lakes = gpd.read_file(path_surface)
# Then we find the lakes that overlap with the VSO polygons
# Perform a spatial join to find intersections between lakes and VSO polygons
intersections = gpd.sjoin(lakes, vso_buffered, how="inner", predicate="intersects")

# Keep only relevant columns and rename the 'NVRID' column from VSO polygons

#%% Find the SVARO polygon for each lake 

# Read in the SVARO polygons
omrade_all = gpd.read_file(path_omrade) 

# Now for each lake in intersection we want to find the SVARO polygon that contains the lake which will have the same MS_CD 
omrade_filtered = omrade_all[omrade_all['MS_CD'].isin(intersections['MS_CD'])]


#%% Find the accumulated catchments for each omrade_filtered

for _, omrade_row in omrade_filtered.iterrows():

    VAROID = omrade_row['VAROID']
    # Find all VAROID in omrade_all that have the current omrade_row's VAROID as their VARO_DOWN
    accumulated_varoids = set()
    current_varoids = {VAROID}
    iteration_count = 0  # Safeguard counter

    while current_varoids and iteration_count < 1000:  # Safeguard to prevent infinite loop
        downstream_varoids = omrade_all[omrade_all['VARO_DOWN'].isin(current_varoids)]['VAROID'].tolist()
        accumulated_varoids.update(downstream_varoids)
        current_varoids = set(downstream_varoids)
        iteration_count += 1

    if iteration_count >= 1000:
        print(f"Warning: Loop terminated after reaching the maximum iteration limit for VAROID {VAROID}")
        # Include the initial VAROID in the accumulated set
    accumulated_varoids.add(VAROID)

    # Filter omrade_all to include only rows with VAROID in accumulated_varoids
    accumulated_geometries = omrade_all[omrade_all['VAROID'].isin(accumulated_varoids)]

    # Dissolve the geometries into a single geometry
    dissolved_geometry = accumulated_geometries.dissolve(by=None).geometry.iloc[0]

    # Store the result in a list for later use
    if 'results' not in locals():
        results = []
    results.append({
        'MS_CD': omrade_row['MS_CD'],
        'geometry': dissolved_geometry
    })

results_df = gpd.GeoDataFrame(results, crs=omrade_filtered.crs)

# Merge the results with the intersections  based on MS_CD

intersections = intersections.merge(results_df[['MS_CD', 'geometry']], on='MS_CD', suffixes=('', '_accumulated'))



#%% Filter out the largest catchment for each VSO polygon

intersections['area_accumulated'] = intersections.geometry_accumulated.area

# Filter out the largest catchment for each VSO polygon: group by NVRID and then only keep the one with the biggest area_accumulated
intersections_filtered = intersections.loc[intersections.groupby('NVRID')['area_accumulated'].idxmax()]


# remove if you want to save the lakes, keep if you want to save the catchments
intersections_filtered.geometry = intersections_filtered.geometry_accumulated


#%% 

import folium

omrade_filtered_map = omrade_filtered.to_crs(epsg=4326)

# results_df_map = results_df.to_crs(epsg=4326)

# Reproject VSO polygons to WGS 84 (EPSG:4326)
vso_map = vso.to_crs(epsg=4326)

# Reproject lakes to the same WGS 84 CRS
intersections_map = intersections.to_crs(epsg=4326)


intersections_filtered_map = intersections_filtered.to_crs(epsg=4326)

# Create a folium map centered on the lakes
map_center = [63.0, 15.0]  # Approximate center of Sweden
m = folium.Map(location=map_center, zoom_start=5)

#Add the VSO polygons to the map
for polygon in vso_map.geometry:
    folium.GeoJson(
        polygon,
        style_function=lambda _: {'color': 'blue', 'fillColor': 'blue', 'fillOpacity': 0.3},
        name="VSO Polygons"
    ).add_to(m)

    # Add the accumulated catchments to the map
for _, polygon_ in intersections_filtered_map.iterrows():
    folium.GeoJson(
        polygon_.geometry_accumulated,
        style_function=lambda _: {'color': 'orange', 'fillColor': 'orange', 'fillOpacity': 0.3},
        name="accumulated catchments"
    ).add_to(m)

# Add the lakes to the map
for _, lake in intersections_map.iterrows():
    folium.GeoJson(
        lake.geometry,
        style_function=lambda x: {'color': 'green', 'fillColor': 'green', 'fillOpacity': 0.5},
        name="Lakes"
    ).add_to(m)

# Add the lakes to the map
for _, lake_ in omrade_filtered_map.iterrows():
    folium.GeoJson(
        lake_.geometry,
        style_function=lambda x: {'color': 'red', 'fillColor': 'red', 'fillOpacity': 0.5},
        name="catchment"
    ).add_to(m)

# Add a layer control to toggle layers
folium.LayerControl().add_to(m)

# Display the map
m

# save ma
m.save(r"..\results\maps\SVARO_Vattenformommstomrade_VSO_map.html")
# %%
# Now we save it all (droping the geometry column and making geometry_accumulkated the geometry column)
intersections_filtered = intersections_filtered.drop(columns=['geometry_accumulated'])
intersections_filtered = intersections_filtered.rename(columns={'geometry_accumulated': 'geometry'})

# intersections_filtered.to_file(r"..\input\SMHI\shapefiles\SVARO_catchments_VSO.shp")

print("Done")
# %%
