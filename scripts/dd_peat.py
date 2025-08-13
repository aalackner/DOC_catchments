
#%% Only needed if used from terminal, otherwise the first block needs to be commented out
import argparse
parser = argparse.ArgumentParser()
parser.add_argument("-d", type=str, help="the ditch database")
parser.add_argument("-c", type=str, help="the catchments")
parser.add_argument("-pr", type=str, help="the peat raster")
parser.add_argument("-o", type=str, help="the output")
parser.add_argument("-id", type=str, help="the id variable", default="mvmid")

args = parser.parse_args()

#%%
# class Args:
#     pass

# args = Args()

# args.id = "mvm_id"  # Default value for id variable



# # # Example manual assignments
# args.c = r"\\storage.slu.se\Home$\anlr0006\My Documents\04_Projects\11_Lakes\01_data\02_raw_data\catchments\merged_catchments.zip"
# args.o = r"/home/anlr0006/code/DOC_catchments/results/slu_sgu/by_station"
# args.d = r"/home/anlr0006/code/DOC_catchments/input/mosaic_ditches.gdb"
# # args.pr = r"C:\Users\anlr0006\repos-win\DOC_catchments\input\Torvkarta\Klassad_torvkarta\ClassifiedPeatMap.tif"
# args.pr = r"/home/anlr0006/code/DOC_catchments/input/Klassad_torvkarta/ClassifiedPeatMap.tif"

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
        catchment_id = polygon['mvm_id'] if 'mvm_id' in polygon else idx
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
    poly_id = polygon['mvm_id'] if 'mvm_id' in polygon else idx
    
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
            sub_gdf = gpd.GeoDataFrame({'mvm_id': [sub_id], 'geometry': [sub]}, crs=crs)
            process_catchment_v2(sub_gdf.iloc[0], peat_raster_fp, lines, args_o, idx=sub_id, split_threshold=split_threshold, catchment_area = catchment_area)
        return  # Don't process the large polygon itself

    results_fp = os.path.join(args_o, f"peat_{poly_id}.csv")
    if os.path.exists(results_fp):
        print(f"Output CSV for mvm_id {poly_id} already exists at {results_fp}, skipping processing.")
        return

    print(f"\nStarting processing for polygon mvm_id: {poly_id}")

    results = {
        'mvm_id': poly_id,
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
    print(f"Finished processing polygon mvm_id: {poly_id}\n")



#%%
import geopandas as gpd
import rioxarray
import matplotlib.pyplot as plt
import numpy as np
from shapely.geometry import box
from shapely.geometry import shape
import dask
import dask.array as da


# Paths
gdb_path = args.d

layer_name = "Diken_vektor_Merge"

# polygon_fp = r"\\storage.slu.se\Home$\anlr0006\My Documents\04_Projects\11_Lakes\01_data\02_raw_data\catchments\merged_catchments.zip"
polygon_fp = args.c

peat_raster_fp = args.pr

# Load data
polygons = gpd.read_file(f"zip://{polygon_fp}").to_crs("EPSG:3006").sort_values(by='Shape_Area').iloc[-139:]
lines = gpd.read_file(gdb_path, layer=layer_name).to_crs("EPSG:3006")


#%%

import pandas as pd


import time

for idx, polygon in polygons.iterrows():
    start_time = time.time()
    process_catchment_v2(polygon, peat_raster_fp, lines, args.o, idx, crs = polygons.crs)
    gc.collect()

    elapsed_time = time.time() - start_time
    print(f"Processed mvm_id {polygon.get('mvm_id', idx)} in {elapsed_time:.2f} seconds.")


# %%

# ##################################### Doing it using the ditches raster #########################

# ditches_fp = r"C:\Users\anlr0006\repos-win\DOC_catchments\input\Dikeskarta\raster\Mosaic_ditches.tif"
# peat_fp = r"C:\Users\anlr0006\repos-win\DOC_catchments\input\Torvkarta\Klassad_torvkarta\ClassifiedPeatMap.tif"
# out_fp = r"C:\Users\anlr0006\repos-win\DOC_catchments\input\Dikeskarta\raster\Mosaic_ditches_aligned.tif"


# import numpy as np
# import xarray as xr
# import rioxarray
# import rasterio

# def block_sum(block):
#     # block is a 2D numpy array
#     pad_y = (2 - block.shape[0] % 2) % 2
#     pad_x = (2 - block.shape[1] % 2) % 2
#     if pad_y or pad_x:
#         block = np.pad(block, ((0, pad_y), (0, pad_x)), mode='constant', constant_values=0)
#     new_shape = (block.shape[0]//2, 2, block.shape[1]//2, 2)
#     reshaped = block.reshape(new_shape)
#     summed = reshaped.sum(axis=(1, 3)).astype(np.uint16)
#     return summed

# def padded_length(length, block=2):
#     return (length + block - 1) // block * block

# def pad_coords(coords, target_len):
#     current_len = len(coords)
#     if target_len <= current_len:
#         return coords[:target_len]
#     else:
#         pad_vals = np.full(target_len - current_len, coords[-1])
#         return np.concatenate([coords.values, pad_vals])


# # Open ditches raster with chunks for dask lazy loading
# ditch_data = rioxarray.open_rasterio(ditches_fp, chunks={'x': 512, 'y': 512}).squeeze()

# # Open peat raster for metadata
# peat = rioxarray.open_rasterio(peat_fp)
# with rasterio.open(peat_fp) as src:
#     peat_meta = src.meta.copy()

# # Calculate padded input lengths to handle odd sizes
# orig_len_y = ditch_data.sizes['y']
# orig_len_x = ditch_data.sizes['x']
# padded_len_y = padded_length(orig_len_y, 2)
# padded_len_x = padded_length(orig_len_x, 2)

# # Downsample coordinates of the original raster by 2 (use only existing, no padding here)
# # We'll generate final coords matching the aggregated shape below

# # Run aggregation with dask map_blocks
# aggregated_data = ditch_data.data.map_blocks(
#     block_sum,
#     dtype=np.uint16,
#     drop_axis=(0, 1),  # drop inside-block dims after aggregation
#     chunks=(ditch_data.chunks[0][0]//2, ditch_data.chunks[1][0]//2)
# )

# # Get full shape of aggregated data (after block_sum)
# # Get aggregated shape from data
# agg_shape_y, agg_shape_x = aggregated_data.shape

# # Downsample original coords by 2 (floor division)
# new_y_base = ditch_data['y'].values[:padded_len_y][::2]
# new_x_base = ditch_data['x'].values[:padded_len_x][::2]

# # Now crop or pad coordinates to exactly match aggregated shape
# def adjust_coords(coords, target_len):
#     if len(coords) > target_len:
#         # Crop to target length
#         return coords[:target_len]
#     elif len(coords) < target_len:
#         # Pad with last value
#         pad_len = target_len - len(coords)
#         return np.pad(coords, (0, pad_len), mode='edge')
#     else:
#         return coords

# new_y = adjust_coords(new_y_base, agg_shape_y)
# new_x = adjust_coords(new_x_base, agg_shape_x)

# # If coordinates are shorter than aggregated shape (due to padding), pad with last value
# if len(new_y) < agg_shape_y:
#     new_y = np.pad(new_y, (0, agg_shape_y - len(new_y)), constant_values=new_y[-1])
# if len(new_x) < agg_shape_x:
#     new_x = np.pad(new_x, (0, agg_shape_x - len(new_x)), constant_values=new_x[-1])

# # Wrap aggregated data into an xarray DataArray with coords and dims
# aggregated = xr.DataArray(
#     aggregated_data,
#     dims=('y', 'x'),
#     coords={'y': new_y, 'x': new_x},
#     name='aggregated_ditches'
# )

# # Update peat metadata for output raster (2x downsampling)
# peat_meta.update({
#     'dtype': 'uint16',
#     'count': 1,
#     'transform': peat.rio.transform() * rasterio.Affine.scale(2, 2)
# })

# # Save aggregated raster to disk with compression and tiling
# aggregated.rio.to_raster(
#     out_fp,
#     dtype='uint16',
#     compress='lzw',
#     driver='GTiff',
#     tiled=True,
#     blockxsize=512,
#     blockysize=512
# )

# print("Aggregation complete and saved to:", out_fp)


# #%%

# import rasterio

# # Load peat raster (metadata only)
# with rasterio.open(peat_fp) as peat:
#     peat_profile = peat.profile
#     peat_transform = peat.transform
#     peat_res = peat.res
#     peat_crs = peat.crs
#     peat_bounds = peat.bounds

# # Load the resampled ditches raster
# with rasterio.open(out_fp) as ditches:
#     ditches_profile = ditches.profile
#     ditches_transform = ditches.transform
#     ditches_res = ditches.res
#     ditches_crs = ditches.crs
#     ditches_bounds = ditches.bounds

# def bounds_overlap(bounds1, bounds2):
#     return not (
#         bounds1.right <= bounds2.left or
#         bounds1.left >= bounds2.right or
#         bounds1.top <= bounds2.bottom or
#         bounds1.bottom >= bounds2.top
#     )

# # Compare
# print("✅ CRS match:", peat_crs == ditches_crs)
# print("✅ Resolution match:", peat_res == ditches_res)
# print("✅ Transform match:", peat_transform == ditches_transform)
# print("✅ Bounds overlap:", bounds_overlap(peat_bounds, ditches_bounds))

# # %%
# import matplotlib.pyplot as plt
# import rasterio
# import numpy as np

# # Read central window
# with rasterio.open(out_fp) as ditches:
#     ditch_nodata = ditches.nodata
#     win = rasterio.windows.Window(ditches.width//2, ditches.height//2, 500, 500)
#     ditch_data = ditches.read(1, window=win)

# with rasterio.open(peat_fp) as peat:
#     peat_nodata = peat.nodata
#     peat_data = peat.read(1, window=win)

# # Mask nodata
# ditch_masked = np.ma.masked_equal(ditch_data, ditch_nodata)
# peat_masked = np.ma.masked_equal(peat_data, peat_nodata)

# # Plot
# plt.figure(figsize=(12,5))
# plt.subplot(1,2,1)
# plt.title("Ditches (resampled)")
# plt.imshow(ditch_masked, cmap='gray')

# plt.subplot(1,2,2)
# plt.title("Peat")
# plt.imshow(peat_masked, cmap='terrain')

# plt.tight_layout()
# plt.show()

