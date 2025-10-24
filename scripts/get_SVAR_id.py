#%%
import argparse
parser = argparse.ArgumentParser()
parser.add_argument("-c", type=str, help="the catchments either as .zip containing shp  or shp file")
parser.add_argument("-o", type=str, help="the output folder, for ids and .feather used in discharge.py")
parser.add_argument("-id", type=str, default = 'mvmid' ,help="the unique id column in the catchment shapefile")
parser.add_argument("-x",type = str, default = "x_utlopp", help = "lake outlet SWEREF TM99 x coordinate column name ")
parser.add_argument("-y",type = str, default = "y_utlopp", help = "lake outlet SWEREF TM99 y coordinate column name")
parser.add_argument("-svar", type=str, help="the svar delavrinningsområde either as .zip containing shp  or shp file")
parser.add_argument("-map", type=str, default = "false", help= "default is no generation of map, set to true map fill be saved in output folder")

args = parser.parse_args()
file_catch = args.c
output_folder = args.o
x_coord = args.x
y_coord = args.y
id_var = args.id
file_svar = args.svar
file_map = args.map
#%%
import geopandas as gpd

# file_catch = "data/corrected_all_sls.shp"
# output_folder = "corrected/runoff"
# x_coord = "x_utlopp"
# y_coord = "y_utlopp"
# id_var = "mvm_id"
# file_svar = "input/SMHI/SVAR2022_delavrinningsomraden.zip"
# file_map = "false"



# file_catch = "../data/test.shp"
# output_folder = "../test_results/runoff"
# x_coord = "x_utlopp"
# y_coord = "y_utlopp"
# id_var = "id"
# file_svar = "../input/SMHI/SVAR2022_delavrinningsomraden.zip"
# file_map = "true"
#%%

if file_catch.endswith('.shp'):
    cats = gpd.read_file(file_catch)
elif file_catch.endswith('.zip'):
    cats = gpd.read_file(f"zip://{file_catch}")
else:
    raise ValueError("Catchment file must be a .shp or .zip file.")
#%%

import geopandas as gpd
from pathlib import Path
import requests
import shutil

def download_svar(url: str, destination: Path) -> bool:
    """
    Attempt to download a file from the given URL to the destination path.
    Returns True on success, False otherwise.
    """
    try:
        print(f"Downloading svar data from {url}...")
        response = requests.get(url, stream=True)
        response.raise_for_status()

        # Ensure destination folder exists
        destination.parent.mkdir(parents=True, exist_ok=True)

        # Save file to destination
        with open(destination, "wb") as f:
            shutil.copyfileobj(response.raw, f)

        print(f"Download complete: {destination}")
        return True
    except Exception as e:
        print(f"Download failed: {e}")
        return False

# --- Main logic --- 
svar_download_url = "https://opendata-download.smhi.se/svar/SVAR2022_delavrinningsomraden.zip"
file_svar = Path(file_svar)

# Step 1: Check if the file exists, try to download if not
if not Path(file_svar).exists():
    print(f"{file_svar} does not exist. Attempting to download...")
    success = download_svar(svar_download_url, file_svar)
    if not success:
        raise FileNotFoundError(
            f"svar file could not be found or downloaded. Expected at: {file_svar}"
        )

# Step 2: Try to read the file with GeoPandas
if file_svar.suffix == '.shp':
    svar = gpd.read_file(file_svar)
elif file_svar.suffix == '.zip':
    svar = gpd.read_file(f"zip://{file_svar}")
else:
    raise ValueError("svar file must be a .shp or .zip file.")

#%%
# Ensure GeoDataFrame has a projected CRS for accurate area calculation
if not cats.crs or not cats.crs.is_projected:
    raise ValueError("GeoDataFrame must have a projected CRS to calculate area accurately.")

# Add area column (in square units of CRS, usually meters)
cats["area_m2"] = cats.geometry.area

# Check that necessary columns exist
required_cols = [x_coord, y_coord]
missing = [col for col in required_cols if col not in cats.columns]

if missing:
    print(
        f"Coordinates could not be found. Please enter valid column names.\n"
        f"Missing column(s): {', '.join(missing)}\n"
        f"The available columns are: {', '.join(cats.columns)}"
    )
else:
    # Select the required columns
    gdf_stations = cats[[id_var,"area_m2", x_coord, y_coord ]].copy()


#%% get the stations

# Convert to GeoDataFrame using x_utlopp and y_utlopp as coordinates
gdf_stations = gpd.GeoDataFrame(
    gdf_stations,
    geometry=gpd.points_from_xy(gdf_stations[x_coord], gdf_stations[y_coord]),
    crs="EPSG:3006"  
)
                              

# gdf_stations.plot()
# %%
import geopandas as gpd
from shapely.geometry import Point
import matplotlib.pyplot as plt


# %%
svar = svar.to_crs("EPSG:3006")

#%%
gdf_with_uuid = gpd.sjoin(gdf_stations, svar[['ARO_UUID', 'geometry', 'AREA', 'AREA_UPSTREAM']], how='left', predicate='within').drop(columns=['index_right'])

# find the ones where the catchment from gdf_catch and the SVAR have less than 50% overlap of the svar area

# Merge gdf_catch with gdf_with_uuid to get ARO_UUID for each catchment
gdf_catch_with_uuid = cats.merge(
    gdf_with_uuid[[id_var, 'ARO_UUID']],
    on=id_var,
    how='left'
)

# Merge again with svar to get the svar geometry and area columns
gdf_catch_with_svar = gdf_catch_with_uuid.merge(
    svar[['ARO_UUID', 'geometry', 'AREA', 'AREA_UPSTREAM']],
    on='ARO_UUID',
    how='left',
    suffixes=('', '_svar')
)

gdf_catch_with_svar
#%%
# Now we want to find the % of geometry_svar that is within the catchment geometry

# Calculate intersection area between catchment and svar geometry
gdf_catch_with_svar['intersection_area'] = gdf_catch_with_svar.apply(
    lambda row: row['geometry'].intersection(row['geometry_svar']).area if row['geometry_svar'] is not None else 0,
    axis=1
)

# Calculate % of svar area within the catchment
gdf_catch_with_svar['pct_svar_in_catch'] = (
    gdf_catch_with_svar['intersection_area'] / gdf_catch_with_svar['AREA']
)

# Flag cases where less than 50% of svar area is within the catchment

mvm_funny = gdf_catch_with_svar.loc[gdf_catch_with_svar['pct_svar_in_catch'] < 0.5][id_var]

#%%

# Find all svar areas that are within 100m of one of the gdf_stations in mvm_funny

# Filter gdf_stations to only those in mvm_funny
stations_funny = gdf_stations[gdf_stations[id_var].isin(mvm_funny)]

# Buffer stations by 200 meters
stations_buffer = stations_funny.copy()
stations_buffer['geometry'] = stations_buffer.geometry.buffer(200)

# Spatial join: svar areas that intersect with any station buffer
svar_near_funny = gpd.sjoin(
    svar[['ARO_UUID', 'geometry', 'AREA', 'AREA_UPSTREAM']],
    stations_buffer[['geometry', id_var]],
    how='inner',
    predicate='intersects'
)




############################################# Pick out of all the funny ones the one 
# ##########################              that has the greatest overlap
#%%
from shapely.geometry import Point

def get_svar_with_greatest_overlap(row, id_var, x_coord, y_coord, buffer=200):
    # Get the catchment geometry for the current mvm_id
    catchment = gpd.GeoDataFrame([row], geometry='geometry', crs="EPSG:3006")

    mvm_id = row[id_var]
    print(mvm_id)
        # Convert to GeoDataFrame using x_utlopp and y_utlopp as coordinates

    gdf_station = gpd.GeoSeries(
        data=[Point(row[x_coord],row[y_coord])],
        index=[row[id_var]],
        crs="EPSG:3006"  
    )

    gdf_station_buffered = gpd.GeoDataFrame(
        {id_var: [mvm_id], 'geometry': [gdf_station.buffer(buffer).iloc[0]]},
        crs="EPSG:3006"
    )  # Buffer by 200m

    # Get the svar areas that intersect with this catchment within 100m of the station
    svar_in_catch = gpd.sjoin(
    svar[['ARO_UUID', 'geometry', 'AREA', 'AREA_UPSTREAM']],
    gdf_station_buffered,
    how='inner',
    predicate='intersects'
    ). rename(columns={'index': id_var})


    if len(svar_in_catch) == 1:
       # print(f"Catchment id: {mvm_id}, \nOnly one svar area found within 200m: {svar_in_catch['ARO_UUID'].iloc[0]}")
        return svar_in_catch['ARO_UUID'].iloc[0]

    # calculoatre overlap with catchment for each svar in catch
    # Perform spatial intersection to calculate overlap area between catchment and each svar geometry
        # Use overlay to get intersection geometries
    intersection = gpd.overlay(
            catchment[[id_var, 'geometry']],
            svar_in_catch[['ARO_UUID', 'geometry', 'AREA', 'AREA_UPSTREAM']],
            how='intersection', keep_geom_type=False
        )
    

        # Calculate intersection area for each svar

    intersection['intersection_area'] = intersection.geometry.area

    #     # Calculate % of svar area overlapped by catchment
    intersection['pct_svar_overlap'] = (intersection['intersection_area'] / intersection['AREA']).round(2)
    #     # Merge intersection percentages back to svar_in_catch
    svar_in_catch = svar_in_catch.merge(
            intersection[['ARO_UUID', 'intersection_area', 'pct_svar_overlap']],
            on='ARO_UUID',
            how='left'
        )
    
    if svar_in_catch['pct_svar_overlap'].isna().all():
        print("All pct_svar_overlap values are NaN for this row.")
        return None

    # Choose the svar area with the greatest overlap
    if not svar_in_catch.empty:
        max_overlap_svar = svar_in_catch.loc[svar_in_catch['pct_svar_overlap'].idxmax()]
        print(f"svar with greatest overlap: {max_overlap_svar['ARO_UUID']}, Overlap: {max_overlap_svar['pct_svar_overlap']:.2%}")
        print(f"Other svarS with overlap: {svar_in_catch[['pct_svar_overlap']].sort_values(by='pct_svar_overlap', ascending=False).values}")
        return max_overlap_svar['ARO_UUID']
    else:
        print("No svar areas found within 200m of the station.")
        return None
    

# svar_near_funny now contains all svar areas within 100m of a "funny" station

improved = gdf_catch_with_svar.copy()


# Add a column 'ARO_UUID' by applying get_svar_with_greatest_overlap to each row
improved['ARO_UUID'] = improved.apply(
    lambda row: get_svar_with_greatest_overlap(row , id_var, x_coord, y_coord,buffer=200),
    axis=1
)
# improved

improved['svar_geometry'] = improved.apply(
    lambda row: svar.loc[svar['ARO_UUID'] == row['ARO_UUID'], 'geometry'].values[0]
    if row['ARO_UUID'] in svar['ARO_UUID'].values else None,
    axis=1
)

improved['AREA_UPSTREAM'] = improved.apply(
    lambda row: svar.loc[svar['ARO_UUID'] == row['ARO_UUID'], 'AREA_UPSTREAM'].values[0]
    if row['ARO_UUID'] in svar['ARO_UUID'].values else None,
    axis=1
)

improved['AREA'] = improved.apply(
    lambda row: svar.loc[svar['ARO_UUID'] == row['ARO_UUID'], 'AREA'].values[0]
    if row['ARO_UUID'] in svar['ARO_UUID'].values else None,
    axis=1
)
   
#%% Rewrite of above chunk
# Try to fill in the empty ones with station coordinates used instead 
improved_filled = improved.loc[improved['svar_geometry'].isna()].copy()

if not improved_filled.empty:
    # Apply updated matching logic using station_x and station_y
    improved_filled['ARO_UUID'] = improved_filled.apply(
        lambda row: get_svar_with_greatest_overlap(row, id_var, 'station_x', 'station_y', buffer=200),
        axis=1
    )

    # Fill svar_geometry
    improved_filled['svar_geometry'] = improved_filled.apply(
        lambda row: svar.loc[svar['ARO_UUID'] == row['ARO_UUID'], 'geometry'].values[0]
        if row['ARO_UUID'] in svar['ARO_UUID'].values else None,
        axis=1
    )

    # Fill AREA_UPSTREAM
    improved_filled['AREA_UPSTREAM'] = improved_filled.apply(
        lambda row: svar.loc[svar['ARO_UUID'] == row['ARO_UUID'], 'AREA_UPSTREAM'].values[0]
        if row['ARO_UUID'] in svar['ARO_UUID'].values else None,
        axis=1
    )

    # Fill AREA
    improved_filled['AREA'] = improved_filled.apply(
        lambda row: svar.loc[svar['ARO_UUID'] == row['ARO_UUID'], 'AREA'].values[0]
        if row['ARO_UUID'] in svar['ARO_UUID'].values else None,
        axis=1
    )
    
    improved.update(improved_filled)
#%%

improved_svar = improved.drop(columns=['geometry']).rename(columns={'svar_geometry': 'geometry'}).set_geometry('geometry', crs = "EPSG:3006")

#%%    
import os

if not os.path.exists(output_folder):
    os.makedirs(output_folder)

output_path = os.path.join(output_folder, "ARO_UUID.txt")
output_feather = os.path.join(output_folder, "cats_svar2022.feather")
#%%

# Extract unique 'ARO_UUID' values, convert to a list, and format as a comma-separated string
unique_aro_ids = improved['ARO_UUID'].dropna().unique()
aro_id_list = ",".join(map(str, unique_aro_ids))


with open(output_path, "w") as file:
    file.write(aro_id_list)


improved.to_feather(output_feather)

print(f"Unique ARO_UUIDs saved to: {output_path}")


#%%

#%%
import sys


if file_map == "false":
    print("Condition met. Exiting script.")
    sys.exit()
    
# Rest of the script continues here if condition is False
print("Generating map ...")

# plot 
import folium
from shapely.geometry import mapping
# Ensure output directory exists
import os
from folium import Html, Popup, Marker
from folium.elements import MacroElement
from jinja2 import Template

# Get centroid of the catchments for map centering
catch = cats.loc[cats['mvm_id'].isin(['4034', '4026'])].copy().to_crs("EPSG:4326")
station = gdf_with_uuid.loc[gdf_with_uuid[id_var].isin(catch[id_var])].to_crs("EPSG:4326")
svar = svar.loc[svar['ARO_UUID'].isin(station['ARO_UUID'])].to_crs("EPSG:4326")

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

svar_near_funny = svar_near_funny.to_crs("EPSG:4326").drop_duplicates(subset=['ARO_UUID'])
improved_svar = improved_svar.to_crs("EPSG:4326")
# Create FeatureGroups for catchments and svar areas
catchment_group = folium.FeatureGroup(name="Catchments", show=True)
svar_group = folium.FeatureGroup(name="SVAR Areas found", show=True)
svar_group = folium.FeatureGroup(name="SVAR Areas", show=True)
improved_group = folium.FeatureGroup(name="Improved Catchments", show=True)

# Add all improved catchment polygons to the improved group with popups
for _, row in improved_svar.iterrows(): 
    folium.GeoJson(
        mapping(row.geometry),
        name=f"Improved Catchment {row[id_var]}",
        style_function=lambda x: {"color": "purple", "fillOpacity": 0.2},
        tooltip=f"Improved SVAR id: {row['ARO_UUID']} \n {row[id_var]}",
        popup=folium.Popup(f"Improved:{row['ARO_UUID']} \n {row[id_var]}", max_width=250)
    ).add_to(improved_group)

# Add all catchment polygons to the catchment group with popups
for _, row in catch.iterrows():
    folium.GeoJson(
        mapping(row.geometry),
        name=f"Catchment {row[id_var]}",
        style_function=lambda x: {"color": "blue", "fillOpacity": 0.2},
        tooltip=f"Catchment id: {row[id_var]}",
        popup=folium.Popup(f"Catchment id: {row[id_var]}", max_width=250)
    ).add_to(catchment_group)

# Add all svar area polygons to the svar group with popups
for _, row in svar.iterrows():
    folium.GeoJson(
        mapping(row.geometry),
        name=f"SVAR Area {row['ARO_UUID']}",
        style_function=lambda x: {"color": "green", "fillOpacity": 0.2},
        tooltip=f"SVAR Area ARO_UUID: {row['ARO_UUID']}",
        popup=folium.Popup(f"SVAR Area ARO_UUID: {row['ARO_UUID']}", max_width=250)
    ).add_to(svar_group)


# Add svar_near_funny polygons with ARO_UUID as popup
for _, row in svar_near_funny.iterrows():
    folium.GeoJson(
        mapping(row.geometry),
        name=f"Nearby SVAR {row['ARO_UUID']}",
        style_function=lambda x: {"color": "orange", "fillOpacity": 0.3},
        tooltip=f"Nearby svar ARO_UUID: {row['ARO_UUID']}",
        popup=folium.Popup(f"Nearby svar ARO_UUID: {row['ARO_UUID']}", max_width=250)
    ).add_to(svar_group)


# Add the groups to the map
svar_group.add_to(m)
catchment_group.add_to(m)
svar_group.add_to(m)

improved_group.add_to(m)

# Add all station points directly to the map
for _, row in station.iterrows():
    point = row.geometry
    folium.Marker(
        [point.y, point.x],
        popup=f"Station id: {row[id_var]}",
        icon=folium.Icon(color="red", icon="info-sign")
    ).add_to(m)

# Add a permanent window with a description using folium.Html and folium.Popup
from folium import Html, Popup, Marker
from folium import Div
from branca.element import MacroElement
from jinja2 import Template
# Add a simple info box using folium's Div element

description_html = """
<b>Catchments and svar Areas Map</b><br>
- <span style='color:blue;'>Blue polygons</span>: Catchments with &lt;50% svar overlap<br>
- <span style='color:green;'>Green polygons</span>: svar areas<br>
- <span style='color:red;'>Red markers</span>: Station outlets<br>
<br>
Use the layer control to toggle visibility.<br>.
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

output_map = os.path.join(output_folder, "catchments_svar.html")

# # Save to HTML
m.save(output_map)

print(f"Map saved to {output_map}")


# %%
