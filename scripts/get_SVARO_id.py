#%%
import geopandas as gpd

gdf_catch = gpd.read_file(r"zip://..//data//catch_316.zip").rename(columns={ 'Shape_Area':'area_m2' })


#%% get the stations

# Select relevant columns
gdf_stations = gdf_catch[['mvm_id', 'lat', 'lon', 'area_m2']].copy()

# Convert to GeoDataFrame using x_utlopp and y_utlopp as coordinates
gdf_stations = gpd.GeoDataFrame(
    gdf_stations,
    geometry=gpd.points_from_xy(gdf_stations['lon'], gdf_stations['lat']),
    crs="EPSG:3006"  
)
                              

gdf_stations.plot()


# %%
import geopandas as gpd
from shapely.geometry import Point
import matplotlib.pyplot as plt


# %%
svaro = gpd.read_file("zip://\\\\storage.slu.se\\Home$\\anlr0006\\My Documents\\04_Projects\\09_General\\01_GIS\\SVAR2022_delavrinningsomraden.zip").to_crs("EPSG:3006")

#%%
gdf_with_uuid = gpd.sjoin(gdf_stations, svaro[['ARO_UUID', 'geometry', 'AREA', 'AREA_UPSTREAM']], how='left', predicate='within').drop(columns=['index_right'])


# find the ones where the catchment from gdf_catch and the SVAR have less than 50% overlap of the svar area

# Merge gdf_catch with gdf_with_uuid to get ARO_UUID for each catchment
gdf_catch_with_uuid = gdf_catch.merge(
    gdf_with_uuid[['mvm_id', 'ARO_UUID']],
    on='mvm_id',
    how='left'
)

# Merge again with svaro to get the SVARO geometry and area columns
gdf_catch_with_svaro = gdf_catch_with_uuid.merge(
    svaro[['ARO_UUID', 'geometry', 'AREA', 'AREA_UPSTREAM']],
    on='ARO_UUID',
    how='left',
    suffixes=('', '_SVARO')
)

gdf_catch_with_svaro
#%%
# Now we want to find the % of geometry_SVARO that is within the catchment geometry

# Calculate intersection area between catchment and SVARO geometry
gdf_catch_with_svaro['intersection_area'] = gdf_catch_with_svaro.apply(
    lambda row: row['geometry'].intersection(row['geometry_SVARO']).area if row['geometry_SVARO'] is not None else 0,
    axis=1
)

# Calculate % of SVARO area within the catchment
gdf_catch_with_svaro['pct_svaro_in_catch'] = (
    gdf_catch_with_svaro['intersection_area'] / gdf_catch_with_svaro['AREA']
)

# Flag cases where less than 50% of SVARO area is within the catchment

mvm_funny = gdf_catch_with_svaro.loc[gdf_catch_with_svaro['pct_svaro_in_catch'] < 0.5]['mvm_id'].iloc[0:50]

##% 

# Find all SVARO areas that are within 100m of one of the gdf_stations in mvm_funny

# Filter gdf_stations to only those in mvm_funny
stations_funny = gdf_stations[gdf_stations['mvm_id'].isin(mvm_funny)]

# Buffer stations by 100 meters
stations_buffer = stations_funny.copy()
stations_buffer['geometry'] = stations_buffer.geometry.buffer(200)

# Spatial join: SVARO areas that intersect with any station buffer
svaro_near_funny = gpd.sjoin(
    svaro[['ARO_UUID', 'geometry', 'AREA', 'AREA_UPSTREAM']],
    stations_buffer[['geometry', 'mvm_id']],
    how='inner',
    predicate='intersects'
)




############################################# Pick out of all the funny ones the one 
# ##########################              that has the greatest overlap
#%%
from shapely.geometry import Point

def get_svaro_with_greatest_overlap(row, buffer=200):
    # Get the catchment geometry for the current mvm_id
    catchment = gpd.GeoDataFrame([row], geometry='geometry', crs="EPSG:3006")

    mvm_id = row['mvm_id']
    print(mvm_id)
        # Convert to GeoDataFrame using x_utlopp and y_utlopp as coordinates

    gdf_station = gpd.GeoSeries(
        data=[Point(row['lon'],row['lat'])],
        index=[row['mvm_id']],
        crs="EPSG:3006"  
    )

    gdf_station_buffered = gpd.GeoDataFrame(
        {'mvm_id': [mvm_id], 'geometry': [gdf_station.buffer(buffer).iloc[0]]},
        crs="EPSG:3006"
    )  # Buffer by 200m

    # Get the SVARO areas that intersect with this catchment within 100m of the station
    svaro_in_catch = gpd.sjoin(
    svaro[['ARO_UUID', 'geometry', 'AREA', 'AREA_UPSTREAM']],
    gdf_station_buffered,
    how='inner',
    predicate='intersects'
    ). rename(columns={'index': 'mvm_id'})


    if len(svaro_in_catch) == 1:
        print(f"Catchment mvm_id: {mvm_id}, \nOnly one SVARO area found within 200m: {svaro_in_catch['ARO_UUID'].iloc[0]}")
        return svaro_in_catch['ARO_UUID'].iloc[0]

    # calculoatre overlap with catchment for each svaro in catch
    # Perform spatial intersection to calculate overlap area between catchment and each SVARO geometry
        # Use overlay to get intersection geometries
    intersection = gpd.overlay(
            catchment[['mvm_id', 'geometry']],
            svaro_in_catch[['ARO_UUID', 'geometry', 'AREA', 'AREA_UPSTREAM']],
            how='intersection', keep_geom_type=False
        )
    

        # Calculate intersection area for each SVARO

    intersection['intersection_area'] = intersection.geometry.area

    #     # Calculate % of SVARO area overlapped by catchment
    intersection['pct_svaro_overlap'] = (intersection['intersection_area'] / intersection['AREA']).round(2)
    #     # Merge intersection percentages back to svaro_in_catch
    svaro_in_catch = svaro_in_catch.merge(
            intersection[['ARO_UUID', 'intersection_area', 'pct_svaro_overlap']],
            on='ARO_UUID',
            how='left'
        )
    
    # Choose the SVARO area with the greatest overlap
    if not svaro_in_catch.empty:
        max_overlap_svaro = svaro_in_catch.loc[svaro_in_catch['pct_svaro_overlap'].idxmax()]
        print(f"SVARO with greatest overlap: {max_overlap_svaro['ARO_UUID']}, Overlap: {max_overlap_svaro['pct_svaro_overlap']:.2%}")
        print(f"Other SVAROS with overlap: {svaro_in_catch[['pct_svaro_overlap']].sort_values(by='pct_svaro_overlap', ascending=False).values}")
        return max_overlap_svaro['ARO_UUID']
    else:
        print("No SVARO areas found within 200m of the station.")
        return None
    

# svaro_near_funny now contains all SVARO areas within 100m of a "funny" station

improved = gdf_catch.copy()


# Add a column 'ARO_UUID' by applying get_svaro_with_greatest_overlap to each row
improved['ARO_UUID'] = improved.apply(get_svaro_with_greatest_overlap, axis=1)
# improved

improved['SVARO_geometry'] = improved.apply(
    lambda row: svaro.loc[svaro['ARO_UUID'] == row['ARO_UUID'], 'geometry'].values[0]
    if row['ARO_UUID'] in svaro['ARO_UUID'].values else None,
    axis=1
)

improved['AREA_UPSTREAM'] = improved.apply(
    lambda row: svaro.loc[svaro['ARO_UUID'] == row['ARO_UUID'], 'AREA_UPSTREAM'].values[0]
    if row['ARO_UUID'] in svaro['ARO_UUID'].values else None,
    axis=1
)

improved['AREA'] = improved.apply(
    lambda row: svaro.loc[svaro['ARO_UUID'] == row['ARO_UUID'], 'AREA'].values[0]
    if row['ARO_UUID'] in svaro['ARO_UUID'].values else None,
    axis=1
)


improved_SVARO = improved.drop(columns=['geometry']).rename(columns={'SVARO_geometry': 'geometry'}).set_geometry('geometry', crs = "EPSG:3006")
# Ensure the directory exists

#%% 
import os


# Extract unique 'ARO_UUID' values, convert to a list, and format as a comma-separated string
unique_aro_ids = improved['ARO_UUID'].dropna().unique()
aro_id_list = ",".join(map(str, unique_aro_ids))

# Save to a file
output_path = "results/SVAR/ARO_UUID_catch_316.txt"
with open(output_path, "w") as file:
    file.write(aro_id_list)

improved.to_feather("results/SVAR/catch_316_ARO.feather")

print(f"Unique ARO_UUIDs saved to: {output_path}")


# %%
# look into runoff for lakes
catch = gdf_catch.copy().to_crs("EPSG:4326")
station = gdf_with_uuid.loc[gdf_with_uuid['mvm_id'].isin(catch['mvm_id'])].to_crs("EPSG:4326")
svar = svaro.loc[svaro['ARO_UUID'].isin(station['ARO_UUID'])].to_crs("EPSG:4326")
# Ensure gdf_samples_joined is defined before this line
# Convert both columns to string for matching
# samples = gdf_samples_joined.loc[
#     gdf_samples_joined['stationId'].astype(str).isin(station['mvm_id'].astype(str))
# ].copy().to_crs("EPSG:4326")
# Convert geometry_svaro to the same CRS
# samples['geometry_svaro'] = samples['geometry_svaro'].to_crs("EPSG:4326") if hasattr(samples['geometry_svaro'], 'to_crs') else samples['geometry_svaro'].apply(lambda geom: geom if geom is None else gpd.GeoSeries([geom], crs="EPSG:3006").to_crs("EPSG:4326").iloc[0])

#%%
# plot 
import folium
from shapely.geometry import mapping
# Ensure output directory exists
import os
from folium import Html, Popup, Marker
from folium.elements import MacroElement
from jinja2 import Template

# Get centroid of the catchments for map centering

# Set map center to approximate center of Sweden (latitude, longitude)
m = folium.Map(location=[62.0, 15.0], zoom_start=4, tiles="cartodbpositron")

from folium import TileLayer
TileLayer(
    tiles='https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',
    attr='Esri World Imagery',
    name='Esri Satellite',
    overlay=False,
    control=True,
    show=False
).add_to(m)

svaro_near_funny = svaro_near_funny.to_crs("EPSG:4326").drop_duplicates(subset=['ARO_UUID'])
improved_SVARO = improved_SVARO.to_crs("EPSG:4326")
# Create FeatureGroups for catchments and SVARO areas
catchment_group = folium.FeatureGroup(name="Catchments", show=True)
svaro_group = folium.FeatureGroup(name="SVAR Areas found", show=True)
svar_group = folium.FeatureGroup(name="SVAR Areas", show=True)
improved_group = folium.FeatureGroup(name="Improved Catchments", show=True)

# Add all improved catchment polygons to the improved group with popups
for _, row in improved_SVARO.iterrows(): 
    folium.GeoJson(
        mapping(row.geometry),
        name=f"Improved Catchment {row['mvm_id']}",
        style_function=lambda x: {"color": "purple", "fillOpacity": 0.2},
        tooltip=f"Improved SVAR mvm_id: {row['ARO_UUID']} \n {row['mvm_id']}",
        popup=folium.Popup(f"Improved:{row['ARO_UUID']} \n {row['mvm_id']}", max_width=250)
    ).add_to(improved_group)

# Add all catchment polygons to the catchment group with popups
for _, row in catch.iterrows():
    folium.GeoJson(
        mapping(row.geometry),
        name=f"Catchment {row['mvm_id']}",
        style_function=lambda x: {"color": "blue", "fillOpacity": 0.2},
        tooltip=f"Catchment mvm_id: {row['mvm_id']}",
        popup=folium.Popup(f"Catchment mvm_id: {row['mvm_id']}", max_width=250)
    ).add_to(catchment_group)

# Add all SVARO area polygons to the SVARO group with popups
for _, row in svar.iterrows():
    folium.GeoJson(
        mapping(row.geometry),
        name=f"SVAR Area {row['ARO_UUID']}",
        style_function=lambda x: {"color": "green", "fillOpacity": 0.2},
        tooltip=f"SVAR Area ARO_UUID: {row['ARO_UUID']}",
        popup=folium.Popup(f"SVAR Area ARO_UUID: {row['ARO_UUID']}", max_width=250)
    ).add_to(svaro_group)


# Add svaro_near_funny polygons with ARO_UUID as popup
for _, row in svaro_near_funny.iterrows():
    folium.GeoJson(
        mapping(row.geometry),
        name=f"Nearby SVAR {row['ARO_UUID']}",
        style_function=lambda x: {"color": "orange", "fillOpacity": 0.3},
        tooltip=f"Nearby SVARO ARO_UUID: {row['ARO_UUID']}",
        popup=folium.Popup(f"Nearby SVARO ARO_UUID: {row['ARO_UUID']}", max_width=250)
    ).add_to(svar_group)



# Create FeatureGroups for sample points and their SVARO polygons
# sample_points_group = folium.FeatureGroup(name="Sample Points", show=True)
# sample_svaro_group = folium.FeatureGroup(name="Sample SVARO Areas", show=True)

# # Add all sample points (geometry_sample) to the sample_points_group with popups
# for _, row in samples.iterrows():
#     # Add the sample point
#     folium.Marker(
#         [row['geometry_sample'].y, row['geometry_sample'].x],
#         popup=f"Sample stationId: {row['stationId']}",
#         icon=folium.Icon(color="purple", icon="flask")
#     ).add_to(sample_points_group)
#     # Add the corresponding SVARO polygon if it exists
#     if row['geometry_svaro'] is not None and not row['geometry_svaro'].is_empty:
#         folium.GeoJson(
#             mapping(row['geometry_svaro']),
#             name=f"Sample SVARO {row['ARO_UUID']}",
#             style_function=lambda _: {"color": "orange", "fillOpacity": 0.15},
#             tooltip=f"Sample SVARO ARO_UUID: {row['ARO_UUID']}",
#             popup=folium.Popup(f"Sample SVARO ARO_UUID: {row['ARO_UUID']}", max_width=250)
#         ).add_to(sample_svaro_group)

# # Add the groups to the map
# sample_points_group.add_to(m)
# sample_svaro_group.add_to(m)

# Add the groups to the map
svar_group.add_to(m)
catchment_group.add_to(m)
svaro_group.add_to(m)

improved_group.add_to(m)

# Add all station points directly to the map
for _, row in station.iterrows():
    point = row.geometry
    folium.Marker(
        [point.y, point.x],
        popup=f"Station mvm_id: {row['mvm_id']}",
        icon=folium.Icon(color="red", icon="info-sign")
    ).add_to(m)

# Add a permanent window with a description using folium.Html and folium.Popup
from folium import Html, Popup, Marker
from folium import Div
from branca.element import MacroElement
from jinja2 import Template
# Add a simple info box using folium's Div element

description_html = """
<b>Catchments and SVARO Areas Map</b><br>
- <span style='color:blue;'>Blue polygons</span>: Catchments with &lt;50% SVARO overlap<br>
- <span style='color:green;'>Green polygons</span>: SVARO areas<br>
- <span style='color:red;'>Red markers</span>: Station outlets<br>
<br>
Use the layer control to toggle visibility.<br>
Only 50 catchments are displayed (out of 4000+).
"""

# Custom HTML for a fixed info box in the bottom left of the window
info_box_html = f"""
<div style="
    position: fixed;
    bottom: 30px;
    left: 30px;
    z-index: 9999;
    background: white;
    padding: 16px 24px;
    border: 2px solid #666;
    border-radius: 10px;
    box-shadow: 2px 2px 8px rgba(0,0,0,0.25);
    font-size: 15px;
    max-width: 420px;
    min-width: 320px;
    opacity: 0.97;
">
{description_html}
</div>
"""

class FixedInfoBox(MacroElement):
    def __init__(self, html):
        super().__init__()
        self._template = Template(f"""
            {{% macro script(this, kwargs) %}}
                var infoBox = `{html}`;
                $('body').append(infoBox);
            {{% endmacro %}}
        """)

info_box = FixedInfoBox(info_box_html)
info_box.add_to(m)

# add measuring tool in meters
from folium.plugins import MeasureControl
measure_control = MeasureControl(primary_length_unit='meters', secondary_length_unit='kilometers')
measure_control.add_to(m)


folium.LayerControl().add_to(m)


os.makedirs("../results/maps", exist_ok=True)

# Save to HTML
m.save("../results/maps/aro_316_catch_funny.html")

m



# %%

#Lets try it differently, lets use the coordinates for the station instead. 
import pandas as pd
from shapely.geometry import Point

samples = pd.read_csv("\\\\storage.slu.se\\Home$\\anlr0006\\My Documents\\04_Projects\\11_Lakes\\01_data\\02_raw_data\\stations_omdrev.csv")
gdf_samples = gpd.GeoDataFrame(
    samples,
    geometry=gpd.points_from_xy(samples['stationCoordinateX'], samples['stationCoordinateY']),
    crs="EPSG:3006"
)

# Perform spatial join and keep both geometries (sample point and SVARO polygon)
gdf_samples_joined = gpd.sjoin(
    gdf_samples, 
    svaro[['ARO_UUID', 'geometry', 'AREA', 'AREA_UPSTREAM']], 
    how='left', 
    predicate='within'
).drop(columns=['index_right'])

# Rename SVARO geometry to avoid overwriting the sample point geometry
gdf_samples_joined = gdf_samples_joined.rename(columns={'geometry': 'geometry_sample'})
gdf_samples_joined['geometry_svaro'] = svaro.set_index('ARO_UUID').loc[gdf_samples_joined['ARO_UUID']]['geometry'].values

# Set geometry back to sample points for further spatial operations if needed
gdf_samples_joined = gpd.GeoDataFrame(gdf_samples_joined, geometry='geometry_sample', crs="EPSG:3006")

# Merge gdf_samples_joined with gdf_catch to retain both geometries (sample point and catchment)
# Assume 'stationId' in gdf_samples_joined matches 'mvm_id' in gdf_catch
# Ensure both columns are of the same type (int)
gdf_samples_joined['mvm_id'] = gdf_samples_joined['stationId']



# Merge and keep both geometries by renaming catchment geometry before merging
gdf_catch_renamed = gdf_catch[['mvm_id', 'geometry', 'area_m2']]
gdf_catch_renamed['mvm_id'] = gdf_catch_renamed['mvm_id'].astype(int) 

gdf_catch_renamed['geometry_catchment'] = gdf_catch['geometry'].copy()
gdf_samples_joined = gdf_samples_joined.merge(
    gdf_catch_renamed,
    on='mvm_id',
    how='left'
)



# Calculate intersection area between catchment and SVARO geometry

gdf_samples_joined['intersection_area'] = gdf_samples_joined.apply(
    lambda row: row['geometry_catchment'].intersection(row['geometry_svaro']).area 
    if row['geometry_catchment'] is not None and row['geometry_svaro'] is not None else 0,
    axis=1
)

# Calculate % of SVARO area covered by the catchment
gdf_samples_joined['pct_svaro_in_catch'] = (
    gdf_samples_joined['intersection_area'] / gdf_samples_joined['AREA']
)

# Calculate % of catchment area covered by SVARO geometry
gdf_samples_joined['pct_catch_in_svaro'] = (
    gdf_samples_joined['intersection_area'] / gdf_samples_joined['area_m2']
)


# next step is to find the catchments that have the coordinate of the station not in the catchment these are wrnog cacthments and need to be redone. 



# Find catchments where:
# - less than 50% of SVARO area is in the catchment
# - less than 50% of catchment area is in SVARO
# - OR the sample point is not within the catchment geometry
mvm_funny = gdf_samples_joined.loc[
    (
        # (gdf_samples_joined['pct_svaro_in_catch'] < 0.5) &
        # (gdf_samples_joined['pct_catch_in_svaro'] < 0.5) &
        (~gdf_samples_joined.apply(
            lambda row: row['geometry_catchment'].contains(row['geometry_sample']), axis=1
        ))
    )
]['mvm_id'].astype(str)



# %%
