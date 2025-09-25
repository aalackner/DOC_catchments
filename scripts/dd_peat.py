
#%% Only needed if used from terminal, otherwise the first block needs to be commented out
import argparse
parser = argparse.ArgumentParser()
parser.add_argument("-d", type=str, help="the ditch database")
parser.add_argument("-c", type=str, help="the catchments")
parser.add_argument("-pr", type=str, help="the peat raster")
parser.add_argument("-o", type=str, help="the output")
parser.add_argument("-id", type=str, help="the id variable", default="mvm_id")
parser.add_argument("-ln", type=str, help="if the ditch map is a gdb then the layer containing the ditches", default="Diken_vektor_Merge")
parser.add_argument("-st", type=int, help="the split threshold", default=1.1e8)
args = parser.parse_args()

id_var = args.id
#%% set the workspace and populate the gdb
import os.path
import rioxarray
import geopandas as gpd
import xarray as xr

#%%

def plot_peat_catchment(polygon, peat_gt1, lines_clip, lines_in_peat, perc, args_o, idx=None):
    """
    Plot peat raster with catchment polygon, clipped lines, and save figure.
    """
    try:
        print("[INFO] Starting plot_peat_catchment function...")

        # Setup color map
        print("[INFO] Setting up colormap and normalization...")
        cmap = mcolors.ListedColormap(['lightblue', 'white', 'green', 'forestgreen', 'darkgreen'])
        bounds = [-0.5, 0.5, 1.5, 2.5, 3.5, 4.5]
        norm = mcolors.BoundaryNorm(bounds, cmap.N)

        fig, ax = plt.subplots(figsize=(10, 10))
        print("[INFO] Created matplotlib figure and axes.")

        # Plot peat raster
        print("[INFO] Plotting peat raster...")
        peat_gt1[0].plot(ax=ax, cmap=cmap, norm=norm, alpha=0.6)

        # Plot polygon boundary
        print("[INFO] Plotting catchment polygon boundary...")
        gpd.GeoSeries(polygon.geometry).boundary.plot(ax=ax, edgecolor='black', linewidth=2, label='catchment')

        # Plot lines
        print(f"[INFO] Plotting {len(lines_clip)} clipped lines and {len(lines_in_peat)} lines in peat...")
        lines_clip.plot(ax=ax, color='orange', label='Ditch not in peat')
        lines_in_peat.plot(ax=ax, color='blue', linewidth=1, label='Ditch in peat')

        # Adjust colorbar
        print("[INFO] Adjusting colorbar...")
        cbar = plt.gcf().axes[-1]
        cbar.set_yticks([0, 1, 2, 3, 4])
        cbar.set_yticklabels(['water', 'mineral soil', 'peat >30cm', 'peat >40cm', 'peat >50cm'])

        # Set title and labels
        catchment_id = polygon[id_var] if id_var in polygon else idx
        print(f"[INFO] Setting title with catchment ID: {catchment_id}")
        plt.title(f"Catchment {catchment_id} with {perc:.0f}% in peat")
        plt.legend(loc='upper right')
        plt.xlabel("X (meters)")
        plt.ylabel("Y (meters)")

        # Shrink and center colorbar
        print("[INFO] Adjusting colorbar position...")
        pos = cbar.get_position()
        new_height = pos.height * 0.5
        center_y = pos.y0 + pos.height / 2
        new_y0 = center_y - new_height / 2
        cbar.set_position([pos.x0, new_y0, pos.width, new_height])
        plt.draw()

        # Save the figure
        print("[INFO] Saving figure...")
        maps_folder = os.path.join(os.path.split(args_o)[0], "maps")
        os.makedirs(maps_folder, exist_ok=True)
        filename = f"peat_{catchment_id}.jpeg"
        filepath = os.path.join(maps_folder, filename)
        fig.savefig(filepath)
        print(f"[SUCCESS] Figure saved to: {filepath}")
        plt.close(fig)

    except Exception as e:
        print(f"[ERROR] Failed to plot peat catchment: {e}")


from shapely.geometry import box
import geopandas as gpd
import os
import numpy as np
import pandas as pd
import rioxarray
import rasterio.features
from shapely.ops import unary_union
from shapely.geometry import shape
import gc

# --- Splitting helper function ---
def split_polygon_into_quadrants(polygon):
    minx, miny, maxx, maxy = polygon.bounds
    midx = (minx + maxx) / 2
    midy = (miny + maxy) / 2

    quadrants = [
        box(minx, midy, midx, maxy),  # Top-left
        box(midx, midy, maxx, maxy),  # Top-right
        box(minx, miny, midx, midy),  # Bottom-left
        box(midx, miny, maxx, midy)   # Bottom-right
    ]

    sub_polygons = [polygon.intersection(q) for q in quadrants]
    return [p for p in sub_polygons if not p.is_empty]

# --- Main processing function ---
def process_catchment_v2(polygon, peat_raster_fp, lines, args_o, idx=None, crs = "EPSG:3006", split_threshold=1.1e8, catchment_area = None):  # 20 million m²
    """
    Process a catchment polygon. Automatically splits very large polygons into quadrants.
    """
    poly_id = polygon[id_var] if id_var in polygon else idx
    
    area = polygon.geometry.area

    if catchment_area is None: 
        catchment_area = area

    poly_geom = polygon.geometry

    # Check if polygon is too large
    if area > split_threshold:
        print(f"Polygon {poly_id} is large (area={area:.0f}). Splitting into quadrants...")
        sub_polys = split_polygon_into_quadrants(poly_geom)

        for i, sub in enumerate(sub_polys, start=1):
            sub_id = f"{poly_id}_Q{i}"
            sub_gdf = gpd.GeoDataFrame({id_var: [sub_id], 'geometry': [sub]}, crs=crs)
            process_catchment_v2(sub_gdf.iloc[0], peat_raster_fp, lines, args_o, idx=sub_id, split_threshold=split_threshold, catchment_area = catchment_area)
        return  # Don't process the large polygon itself

    results_fp = os.path.join(args_o, f"peat_{poly_id}.csv")
    if os.path.exists(results_fp):
        print(f"Output CSV for id {poly_id} already exists at {results_fp}, skipping processing.")
        return

    print(f"\nStarting processing for polygon id: {poly_id}")

    results = {
        id_var: poly_id,
        'perc_ditch_in_peat': np.nan,
        'total_ditch_length': np.nan,
        'ditch_length_in_peat': np.nan,
        'peat_pct_Vatten': np.nan,
        'peat_pct_Mineraljord': np.nan,
        'peat_pct_Torv_30': np.nan,
        'peat_pct_Torv_40': np.nan,
        'peat_pct_Torv_50': np.nan,
        'peat_pct_Torv_total': np.nan,
        'area_m2': area,
        'catch_area': catchment_area
    }

    try:
        peat = rioxarray.open_rasterio(peat_raster_fp, masked=True, chunks=True).rio.write_crs("EPSG:3006")
        peat_clip = peat.rio.clip_box(*polygon.geometry.bounds).compute()
        del peat
        gc.collect()
    except Exception as e:
        print(f"Failed clipping peat raster: {e}")
        pd.DataFrame([results]).to_csv(results_fp, index=False)
        return

    try:
        peat_masked = peat_clip.rio.clip([polygon.geometry], peat_clip.rio.crs, drop=False, invert=False).compute()
    except Exception as e:
        print(f"Failed masking peat raster: {e}")
        pd.DataFrame([results]).to_csv(results_fp, index=False)
        return

    try:
        peat_data = peat_masked.data[0]
        peat_data_flat = peat_data[~np.isnan(peat_data)]

        total_pixels = len(peat_data_flat)
        pixel_counts = {cls: (np.sum(peat_data_flat == cls) / total_pixels * 100) if total_pixels > 0 else 0 for cls in range(5)}

        results['peat_pct_Vatten'] = pixel_counts.get(0, 0)
        results['peat_pct_Mineraljord'] = pixel_counts.get(1, 0)
        results['peat_pct_Torv_30'] = pixel_counts.get(2, 0)
        results['peat_pct_Torv_40'] = pixel_counts.get(3, 0)
        results['peat_pct_Torv_50'] = pixel_counts.get(4, 0)
        results['peat_pct_Torv_total'] = results['peat_pct_Torv_30'] + results['peat_pct_Torv_40'] + results['peat_pct_Torv_50']

    except Exception as e:
        print(f"Failed calculating pixel percentages: {e}")

    try:
        lines_clip = gpd.clip(lines, polygon.geometry)
        peat_gt1 = peat_masked.where(peat_masked > 1)
        mask = peat_gt1[0].notnull().compute()
        mask_data = mask.values.astype('uint8')

        transform = peat_gt1.rio.transform()
        ys, xs = np.where(mask_data == 1)

        if len(xs) == 0 or len(ys) == 0:
            total_len = lines_clip.length.sum() if not lines_clip.empty else 0
            total_length = 0
            perc = 0
        else:
            minx, miny = transform * (xs.min(), ys.max() + 1)
            maxx, maxy = transform * (xs.max() + 1, ys.min())
            peat_mask_bbox = box(minx, miny, maxx, maxy)
            lines_pre = lines_clip[lines_clip.intersects(peat_mask_bbox)]

            mask_polygons = [shape(geom) for geom, val in rasterio.features.shapes(mask_data, transform=transform) if val == 1]
            peat_area = unary_union(mask_polygons)

            lines_in_peat = gpd.clip(lines_pre, peat_area) if not lines_pre.empty else gpd.GeoDataFrame(geometry=[])
            total_len = lines_clip.length.sum()
            total_length = lines_in_peat.length.sum()
            perc = (total_length / total_len) * 100 if total_len > 0 else 0

        results['perc_ditch_in_peat'] = perc
        results['total_ditch_length'] = total_len
        results['ditch_length_in_peat'] = total_length
    except Exception as e:
        print(f"Failed calculating line lengths: {e}")

    pd.DataFrame([results]).to_csv(results_fp, index=False)
    print(f"Finished processing polygon id: {poly_id}\n")

#%%



#%%
import geopandas as gpd
import rioxarray
import matplotlib.pyplot as plt
import numpy as np
from shapely.geometry import box
from shapely.geometry import shape
import dask
import dask.array as da

#%%

# Load in the vectors of the ditches
gdb_path = args.d
layer_name = args.ln

import geopandas as gpd
import os
from pathlib import Path
import fiona

def load_geodata(gdb_path):
    gdb_path = Path(gdb_path)
    
    if gdb_path.suffix == ".gdb":
        
        try:
            print("Reading gdb") # Try to load the specified layer
            gdf = gpd.read_file(gdb_path, layer=layer_name).to_crs("EPSG:3006")
            return gdf
        except ValueError as e:
            # Layer not found – list all layers and raise an error with that info
            available_layers = fiona.listlayers(gdb_path)
            raise ValueError(
                f"Layer '{layer_name}' not found in GDB. Available layers: {available_layers}"
            ) from e

    elif gdb_path.is_dir():
        # Look for all .shp files
        shp_files = list(gdb_path.glob("*.shp"))
        if not shp_files:
            raise FileNotFoundError(f"No shapefiles found in folder: {gdb_path}")

        # Read and combine all shapefiles into one GeoDataFrame
        gdf_list = [gpd.read_file(shp).to_crs("EPSG:3006") for shp in shp_files]
        merged_gdf = gpd.GeoDataFrame(pd.concat(gdf_list, ignore_index=True), crs="EPSG:3006")
        return merged_gdf

    else:
        raise ValueError(f"Path must be a .gdb or a directory with .shp files: {gdb_path}")

lines = load_geodata(gdb_path)

#%%


polygon_fp = args.c

peat_raster_fp = args.pr
split_threshold = args.st

# Load data

if polygon_fp.endswith('.zip'):
    polygons = gpd.read_file(f"zip://{polygon_fp}").to_crs("EPSG:3006")
    
else:
    polygons = gpd.read_file(polygon_fp).to_crs("EPSG:3006")




#%%

import pandas as pd
import time

from pathlib import Path

output_folder = Path(args.o)
output_folder.mkdir(parents=True, exist_ok=True)

output_st = os.path.join(output_folder, "peat_by_station")
output_st = Path(output_st)
output_st.mkdir(parents=True, exist_ok=True)

for idx, polygon in polygons.iterrows():
    start_time = time.time()
    process_catchment_v2(polygon, peat_raster_fp, lines, output_st, idx, crs = polygons.crs, split_threshold=split_threshold)
    gc.collect()

    elapsed_time = time.time() - start_time
    print(f"Processed id {polygon.get(id_var, idx)} in {elapsed_time:.2f} seconds.")

#%%
import os
from pathlib import Path

# output_folder = r"../test_results/dd_peat" 

output_st = os.path.join(output_folder, "peat_by_station")
output_st = Path(output_st)
output_st.mkdir(parents=True, exist_ok=True)

output_file = os.path.join(output_folder, "peat_ditches.csv")

import pandas as pd

q3 = os.listdir(output_st)
q3
#%%
original_dir = os.getcwd()
os.chdir(output_st)

start = 0


for file in q3:
    if file.endswith(".csv"):
        if start == 0 :
            results = pd.read_csv(os.path.join( file))
            results['file_name'] = file
        else: 
            df = pd.read_csv(os.path.join( file))
            df['file_name'] = file
            results= pd.concat([results, df])
        start += 1


os.chdir(original_dir)
#%%

results[id_var] = results[id_var].astype(str)

# Step 1: Extract ID
results[id_var] = results[id_var].str.extract(r'(\d+)', expand=False)

# Step 2: Define percentage columns
percent_cols = ['peat_pct_Vatten', 'peat_pct_Mineraljord', 'peat_pct_Torv_total']

# ✅ Step 3: Convert percentages to decimals BEFORE multiplying
results[percent_cols] = results[percent_cols] / 100

# Step 4: Calculate weighted values
for col in percent_cols:
    results[f'{col}_weighted'] = results[col] * results['area_m2']

# Step 5: Group and aggregate
grouped = results.groupby(id_var).agg({
    'total_ditch_length': 'sum',
    'ditch_length_in_peat': 'sum',
    'area_m2': 'sum',
    'catch_area': 'first',  # assumes consistent per ID
    **{f'{col}_weighted': 'sum' for col in percent_cols}
})

# Step 6: Compute final area-weighted percentages
for col in percent_cols:
    grouped[col] = grouped[f'{col}_weighted'] / grouped['catch_area']

# Step 7: Convert back to percentages (0–100)
grouped[percent_cols] = grouped[percent_cols] * 100

# Step 8: Clean up
grouped.drop(columns=[f'{col}_weighted' for col in percent_cols], inplace=True)
grouped.reset_index(inplace=True)

# Final result
import numpy as np

grouped["ditch_perc_peat"] = np.where(
    (grouped['total_ditch_length'] == 0),
    0,
    (grouped['ditch_length_in_peat'] / grouped['total_ditch_length']) * 100
)

final = grouped.copy()


############ ADD IN THE COLLECTION OF ALL OF IT BACK TOGETHER ###########
########### SHOULD COME FROM COLLECT_SPLIT_VARS.PY  #####################

#%%
#%%
import numpy as np

mask = final['ditch_perc_peat'].isna()

# First attempt: if ditch_perc_peat missing
# then compute percent if total_ditch_length is zero => 0, else compute ratio
final.loc[mask, 'ditch_perc_peat'] = np.where(
    final.loc[mask, 'total_ditch_length'] == 0,
    0,
    (final.loc[mask, 'ditch_length_in_peat'] / final.loc[mask, 'total_ditch_length']) * 100
)

# Fallback logic: where still null (maybe due to division by zero or other anomalies)
mask2 = final['ditch_perc_peat'].isna()
final.loc[mask2, 'ditch_perc_peat'] = (
    final.loc[mask2, 'ditch_length_in_peat'] / final.loc[mask2, 'total_ditch_length']
) * 100
#%%

final['ditch_density_m_m2'] = final['total_ditch_length']/final['catch_area']


df_final = final[[id_var, 'total_ditch_length',
                   'ditch_perc_peat','ditch_density_m_m2',
                     'peat_pct_Vatten',	'peat_pct_Mineraljord'	,
                     'peat_pct_Torv_total']].copy()

# df_final.drop_duplicates(subset=id_var, keep='first', inplace = True)

# %%
#file = r"/home/anlr0006/mnt/anna/My Documents/04_Projects/11_Lakes/01_data/03_processed_data/drivers/peat_ditches_all.csv"
df_final.to_csv(output_file, index=False)