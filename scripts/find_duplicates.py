#%% load leaflet 

import geopandas as gpd
import pandas as pd


#%% load the data

file = "\\\\storage.slu.se\\Home$\\anlr0006\\My Documents\\04_Projects\\11_Lakes\\01_data\\01_received\\All_stations.csv"


df = pd.read_csv(file)
df

#%%
import geopandas as gpd
from pyproj import Transformer

# Initialize the transformer
transformer = Transformer.from_crs("EPSG:3006", "EPSG:4326", always_xy=True)

# Drop rows with missing coordinates
df = df.dropna(subset=["Stationskoordinat E/Y", "Stationskoordinat N/X"])

# Apply transformation
df["lon"], df["lat"] = transformer.transform(
    df["Stationskoordinat E/Y"].values,
    df["Stationskoordinat N/X"].values
)

file_lakes = r"..\input\SMHI\shapefiles\SVARO_Vattenformommst.shx"
lakes = gpd.read_file(file_lakes)




#%% Find all the stations that are within the same lake polygon
# Create a GeoDataFrame from the DataFrame with lat/lon
gdf = gpd.GeoDataFrame(
    df,
    geometry=gpd.points_from_xy(df["Stationskoordinat E/Y"], df["Stationskoordinat N/X"]),
    crs="EPSG:3006"  # SWEREF 99 TM
)

# Buffer the lake polygons by 50 meters
lakes_buffered = lakes.copy()
lakes_buffered["geometry"] = lakes_buffered.geometry.buffer(50)

# Perform spatial join to find points within buffered lakes
gdf_lakes = gpd.sjoin(gdf, lakes_buffered, how="inner", predicate="within")

# Add points within lakes, colored by MS_CD
import matplotlib
# Generate a color map for unique MS_CD values
ms_cds = gdf_lakes["MS_CD"].unique()
colormap = matplotlib.colormaps.get_cmap("tab10")
ms_cd_to_color = {ms_cd: matplotlib.colors.rgb2hex(colormap(i % colormap.N)) for i, ms_cd in enumerate(ms_cds)}


# Find MS_CDs that are duplicates (appear more than once)
duplicate_ms_cds = gdf_lakes["MS_CD"][gdf_lakes["MS_CD"].duplicated(keep=False)]

# Filter gdf_lakes to only those with duplicate MS_CDs
gdf_lakes_duplicates = gdf_lakes[gdf_lakes["MS_CD"].isin(duplicate_ms_cds)]

# To ensure both points are visible even if they have the exact same coordinates,
# slightly offset overlapping points by a small amount based on their index.

# Group by coordinates to find duplicates
coord_groups = gdf_lakes_duplicates.groupby(["lat", "lon"])





#%%


import folium
import matplotlib
from math import cos, sin, pi
from branca.element import MacroElement, Figure, Template


# Create base map centered on mean coordinates
m = folium.Map(
    location=[df["lat"].mean(), df["lon"].mean()],
    zoom_start=6,
    tiles=None  # suppress default tiles
)

# Add Esri World Imagery layer (satellite)
folium.TileLayer(
    tiles="https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
    attr="Esri World Imagery",
    name="Esri Satellite",
    overlay=False,
    control=True
).add_to(m)



for (lat, lon), group in coord_groups:
    n = len(group)
    if n == 1:
        # Only one point, plot as is
        row = group.iloc[0]
        folium.CircleMarker(
            location=[lat, lon],
            radius=6,
            color=ms_cd_to_color[row["MS_CD"]],
            fill=True,
            fill_opacity=0.9,
            popup=(
                f"MS_CD: {row['MS_CD']}<br>"
                f"MVM_stations_ID (landuse): {row.get('MVM_stations_ID', 'N/A')}<br>"
                f"MD-MVM Id (sls): {row.get('MD-MVM Id', 'N/A')}<br>"
                f"MVMID(climate): {row.get('MVMID', 'N/A')}<br>"
                f"Coords: {lat:.5f}, {lon:.5f}"
            )
        ).add_to(m)
    else:
        # Offset each point in a small circle
        angle_step = 2 * pi / n
        offset_meters = 10  # ~10 meters
        # Approximate conversion from meters to degrees latitude/longitude
        meter_in_deg_lat = 1 / 111320
        meter_in_deg_lon = 1 / (40075000 * cos(lat * pi / 180) / 360)
        for i, (_, row) in enumerate(group.iterrows()):
            angle = i * angle_step
            dlat = offset_meters * meter_in_deg_lat * sin(angle)
            dlon = offset_meters * meter_in_deg_lon * cos(angle)
            folium.CircleMarker(
                location=[lat + dlat, lon + dlon],
                radius=6,
                color=ms_cd_to_color[row["MS_CD"]],
                fill=True,
                fill_opacity=0.9,
                popup=(
                    f"MS_CD: {row['MS_CD']}<br>"
                    f"MVM_stations_ID (landuse): {row.get('MVM_stations_ID', 'N/A')}<br>"
                    f"MD-MVM Id (sls): {row.get('MD-MVM Id', 'N/A')}<br>"
                    f"MVMID(climate): {row.get('MVMID', 'N/A')}<br>"
                    f"Coords: {lat:.5f}, {lon:.5f}"
                )
            ).add_to(m)


# # Add points
# for _, row in df.iterrows():
#     folium.CircleMarker(
#         location=[row["lat"], row["lon"]],
#         radius=4,
#         color="blue",
#         fill=True,
#         fill_opacity=0.7,
#         popup=f"Coords: {row['lat']:.5f}, {row['lon']:.5f}"
#     ).add_to(m)

# Add layer control to toggle layers
folium.LayerControl().add_to(m)

# Add a permanent information box (custom HTML)
info_html = """
<div style="
    position: fixed; 
    bottom: 50px; left: 50px; width: 500px; z-index:9999; 
    background-color: rgba(255,255,255,0.95); 
    border:2px solid #666; 
    border-radius:8px; 
    padding: 12px; 
    box-shadow: 2px 2px 8px #888;
    font-size: 14px;
">
    <b>Duplicate Stations in SMHI Lakes</b><br>
    This map shows stations within the same SMHI lake polygon.<br>
    Colored markers indicate duplicate <b>lakes</b>.<br>
    Overlapping points are offset for visibility.<br>
    There is a total of 630 lakes that contain duplicate stations.<br>
</div>
"""
info_box = MacroElement()
info_box._template = Template(f"""
{{% macro html(this, kwargs) %}}
    {info_html}
{{% endmacro %}}
""")
m.get_root().add_child(info_box)

# Save or display map
m.save("../results/maps/sweref_points_map.html")
m

# %%


# Export relevant columns from gdf_lakes_duplicates to CSV
# Prepare a DataFrame with the popup variables
csv_df = gdf_lakes_duplicates.copy()
csv_df = csv_df[[
    "MS_CD",
    "mvm_id"
]]
csv_df.to_csv("\\\\storage.slu.se\\Home$\\anlr0006\\My Documents\\04_Projects\\11_Lakes\\01_data\\01_received\\duplicate_lakes.csv", index=False)
# %%
import networkx as nx
# --- NEW: Find points NOT in any lake but within 100m of each other ---

# Get points not in any lake
gdf_not_in_lake = gdf[~gdf.index.isin(gdf_lakes.index)].copy()



# Find groups of points within 100m of each other using a spatial join
buffered = gdf_not_in_lake.copy()
buffered["geometry"] = buffered.geometry.buffer(10)
joined = gpd.sjoin(gdf_not_in_lake, buffered, how="left", predicate="within", lsuffix="1", rsuffix="2")

# Assign group ids: each group is a set of points within 100m of each other
edges = list(zip(joined.index, joined["index_2"]))
G = nx.Graph()
G.add_edges_from(edges)
groups = list(nx.connected_components(G))

# Map each index to a group id
index_to_group = {}
for group_id, group in enumerate(groups):
    for idx in group:
        index_to_group[idx] = group_id

gdf_not_in_lake["group_id"] = gdf_not_in_lake.index.map(index_to_group)

# Only keep groups with more than one point (i.e., actual clusters)
group_counts = gdf_not_in_lake["group_id"].value_counts()
duplicate_groups = group_counts[group_counts > 1].index
gdf_not_in_lake_duplicates = gdf_not_in_lake[gdf_not_in_lake["group_id"].isin(duplicate_groups)].copy()

# Assign a color to each group
colormap2 = matplotlib.colormaps.get_cmap("tab20")
group_ids = sorted(gdf_not_in_lake_duplicates["group_id"].unique())
group_to_color = {gid: matplotlib.colors.rgb2hex(colormap2(i % colormap2.N)) for i, gid in enumerate(group_ids)}

# reproject to WGS84 for folium
gdf_not_in_lake_duplicates = gdf_not_in_lake_duplicates.to_crs("EPSG:4326")

print(f"There is a total of {len(gdf_not_in_lake_duplicates)} stations that are within 10m of each other grouped into {len(duplicate_groups)} groups.")

# %%
# Create a new map for points not in lakes
m2 = folium.Map(
    location=[gdf_not_in_lake_duplicates.geometry.y.mean(), gdf_not_in_lake_duplicates.geometry.x.mean()],
    zoom_start=6,
    tiles=None
)

# Add Esri World Imagery layer
folium.TileLayer(
    tiles="https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
    attr="Esri World Imagery",
    name="Esri Satellite",
    overlay=False,
    control=True
).add_to(m2)


# Add points not in lakes, colored by group_id
for group_id, group in gdf_not_in_lake_duplicates.groupby("group_id"):
    n = len(group)
    angle_step = 2 * pi / n if n > 1 else 0
    offset_meters = 10  # ~10 meters
    meter_in_deg_lat = 1 / 111320
    for i, (_, row) in enumerate(group.iterrows()):
        lat = row.geometry.y
        lon = row.geometry.x
        if n == 1:
            dlat = dlon = 0
        else:
            angle = i * angle_step
            dlat = offset_meters * meter_in_deg_lat * sin(angle)
            # Longitude degree length depends on latitude
            meter_in_deg_lon = 1 / (40075000 * cos(lat * pi / 180) / 360)
            dlon = offset_meters * meter_in_deg_lon * cos(angle)
        folium.CircleMarker(
            location=[lat + dlat, lon + dlon],
            radius=6,
            color=group_to_color[group_id],
            fill=True,
            fill_opacity=0.9,
            popup=(
                f"group_id: {group_id}<br>"
                f"MS_CD: {row.get('MS_CD', 'N/A')}<br>"
                f"MVM_stations_ID (landuse): {row.get('MVM_stations_ID', 'N/A')}<br>"
                f"MD-MVM Id (sls): {row.get('MD-MVM Id', 'N/A')}<br>"
                f"MVMID(climate): {row.get('MVMID', 'N/A')}<br>"
                f"Coords: {lat:.5f}, {lon:.5f}"
            )
        ).add_to(m2)
 

folium.LayerControl().add_to(m2)

# Add info box
info_html2 = """
<div style="
    position: fixed; 
    bottom: 50px; left: 50px; width: 500px; z-index:9999; 
    background-color: rgba(255,255,255,0.95); 
    border:2px solid #666; 
    border-radius:8px; 
    padding: 12px; 
    box-shadow: 2px 2px 8px #888;
    font-size: 14px;
">
    <b>Nearby Stations Map</b><br>
    This map shows stations not in any SMHI lake polygon,<br>
    but within 100 meters of each other.<br>
    Colored markers indicate different groups.<br>
    Overlapping points are offset for visibility.<br>
    There is a total of 1,258 stations that are within 10m of each other<br>
    grouped into 629 groups.<br>
</div>
"""
info_box2 = MacroElement()
info_box2._template = Template(f"""
{{% macro html(this, kwargs) %}}
    {info_html2}
{{% endmacro %}}
""")
m2.get_root().add_child(info_box2)

# Save or display map
m2.save("../results/maps/nearby_points_map.html")
m2
# %%
# Export

csv_df = gdf_not_in_lake_duplicates.copy()
csv_df = csv_df[[
    "group_id",
    "mvm_id"
]]
csv_df.to_csv("\\\\storage.slu.se\\Home$\\anlr0006\\My Documents\\04_Projects\\11_Lakes\\01_data\\01_received\\duplicate_proximity.csv", index=False)
# %%