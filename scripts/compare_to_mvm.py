"""
Script to compare which water bodies are in the MVM database and which ones are not.
"""
#%%
import geopandas as gpd
#%%
# file paths
mvm_path = r"..\input\SMHI\shapefiles\MDMVM_all_lake_stations.shp.zip"
# lakes_vso_path = r"..\input\SMHI\shapefiles\SVARO_lakes_VSO.shp"
lakes_vso_path = r"..\data\MatchadVattenV2.zip"
omdrev_path = r"C:\Users\anlr0006\repos-win\DOC_catchments\data\aro_omdrevsjoar_5127_250227.zip"
trend_path = r"C:\Users\anlr0006\repos-win\DOC_catchments\data\aro_trendsjoar_106_250408.zip"

#%%
# read in the files 

mvm = gpd.read_file(f"zip://{mvm_path}")
lakes_vso = gpd.read_file(lakes_vso_path)
omdrev= gpd.read_file(f"zip://{omdrev_path}")
trend = gpd.read_file(f"zip://{trend_path}").drop(columns=['AU_CD'])

#%%

# stations
from shapely.geometry import Point

omdrev_stations = omdrev.copy()
omdrev_stations['geometry'] = omdrev_stations.apply(
    lambda row: Point(row['x_utlopp'], row['y_utlopp']), axis=1
)

trend_stations = trend.copy()
trend_stations['geometry'] = trend_stations.apply(
    lambda row: Point(row['x_utlopp'], row['y_utlopp']), axis=1
)

#%% 
# Buffer the lakes to make sure all stations are included. 

buffer = 50

lakes_buffered = lakes_vso.copy()

lakes_buffered['geometry_lakes'] = lakes_buffered.geometry
lakes_buffered['geometry'] = lakes_vso.geometry.buffer(buffer)
mvm_in_lakes = gpd.sjoin(mvm, lakes_buffered, how="inner", predicate="intersects")

print(f"Number of lakes in vso: {len(lakes_vso)}")
print(f"Number of stations in mvm: {len(mvm)}")
print(f"Number of stations in mvm in lakes: {len(mvm_in_lakes)}")
print(f"Number of lakes in mvm: {len(mvm_in_lakes['geometry_lakes'].unique())}")

#%% Add a second geometry column t

mvm_in_omdrev = gpd.sjoin(omdrev_stations, lakes_buffered[['AU_CD', 'geometry']], how="inner", predicate="intersects")
mvm_in_trend = gpd.sjoin(trend_stations, lakes_buffered[['AU_CD', 'geometry']], how="inner", predicate="intersects")



print(f"Number of lakes in omdrev: {len(omdrev_stations)}")
print(f"Number of stations in omdrev in lakes: {len(mvm_in_omdrev)}")
print(f"Number of lakes in trend: {len(trend_stations)}")
print(f"Number of stations in trend in lakes: {len(mvm_in_trend)}")


#%%
# generating a map of the lakes and the mvm stations using folium
import folium



# Reproject VSO lakes polygons to WGS 84 (EPSG:4326)
lakes_vso_map = lakes_vso.to_crs(epsg=4326)

# Reproject lakes to the same WGS 84 CRS
mvm_in_lakes_map = mvm_in_lakes.to_crs(epsg=4326)

mvm_in_omdrev_map = mvm_in_omdrev.to_crs(epsg=4326)
mvm_in_trend_map = mvm_in_trend.to_crs(epsg=4326)

omdrev_stations_map = omdrev_stations.to_crs(epsg=4326)
trend_stations_map = trend_stations.to_crs(epsg=4326)



# Create a folium map centered on the lakes
map_center = [63.0, 15.0]  # Approximate center of Sweden
m = folium.Map(location=map_center, zoom_start=5)

# Add lakes polygons to the map
folium.GeoJson(
    lakes_vso_map,
    name="Lakes VSO",
    style_function=lambda x: {'color': 'blue', 'weight': 2, 'fillOpacity': 0.1}
).add_to(m)

#Add mvm in omdrev stations to the map
folium.GeoJson(
    mvm_in_omdrev_map,
    name="Omdrev Stations",
    style_function=lambda x: {'color': 'red', 'weight': 2, 'fillOpacity': 0.1} if x else {'color': 'red'}
).add_to(m) 

# Add trend stations to the map
folium.GeoJson(
    mvm_in_trend_map,
    name="Trend Stations",
    style_function=lambda x: {'color': 'green', 'weight': 2, 'fillOpacity': 0.1}
).add_to(m)




# Add a layer control to toggle layers
folium.LayerControl().add_to(m)

# Display the map
m

# %%

# Conclusion 

lakes_output = lakes_vso.copy().set_index('AU_CD')

# take the lakes shp and add a column for omdrev_station and one for trend station with always the corresponding mvm_id: 
# Count the number of omdrev and trend stations for each lake
omdrev_counts = mvm_in_omdrev.groupby('AU_CD').size()
trend_counts = mvm_in_trend.groupby('AU_CD').size()

# Map one mvm_id for each lake (if multiple, pick the first one)
omdrev_mvm_id = mvm_in_omdrev.groupby('AU_CD')['mvmid'].first()
trend_mvm_id = mvm_in_trend.groupby('AU_CD')['mvmid'].first()

# Add the columns to the lakes_vso dataframe
lakes_output = lakes_output.merge(omdrev_counts.rename('omdrev_count'), left_index=True, right_index=True, how='left')
lakes_output = lakes_output.merge(trend_counts.rename('trend_count'), left_index=True, right_index=True, how='left')
lakes_output = lakes_output.merge(omdrev_mvm_id.rename('omdrev_mvmid'), left_index=True, right_index=True, how='left')
lakes_output = lakes_output.merge(trend_mvm_id.rename('trend_mvmid'), left_index=True, right_index=True, how='left')

lakes_output.drop(columns=['AREA_UPS_1', 'ANS_LAN',
       'DISTRICT', 'INT_RB', 'AREA_m2', 'AREA_km2', 'SHAPE_Leng', 'SHAPE_Area',
       'OBJECTID_1', 'AREAL', 'SHAPE_Le_1', 'SHAPE_Ar_1', 'ORIG_FID']).to_file(r"..\results\slu_sgu\rw_station_overlap.shp", driver='ESRI Shapefile')

# %%
