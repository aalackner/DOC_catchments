
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
# args.o = r"C:\Users\anlr0006\repos-win\DOC_catchments\results\slu_sgu\ditch_test.csv"
# args.d = r"\\storage.slu.se\Home$\anlr0006\My Documents\04_Projects\09_General\01_GIS\ditches\mosaic_ditches.gdb"
# args.pr = r"C:\Users\anlr0006\repos-win\DOC_catchments\input\Torvkarta\Klassad_torvkarta\ClassifiedPeatMap.tif"
# args.pr = r"\\storage.slu.se\Home$\anlr0006\My Documents\04_Projects\09_General\01_GIS\Klassad_torvkarta\ClassifiedPeatMap.tif"

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


def calculate_pixel_percentages(peat_masked):
    """
    Calculate percentage of pixels per peat class (0-4) inside the masked raster.

    Returns a dict with descriptive keys and a combined peat percentage.
    """
    print("Calculating pixel percentages per peat class inside polygon...")
    peat_data = peat_masked.data[0]  # Assuming single band
    peat_data_flat = peat_data.compressed() if hasattr(peat_data, 'compressed') else peat_data.flatten()
    peat_data_flat = peat_data_flat[~np.isnan(peat_data_flat)]

    pixel_counts = {}
    total_pixels = len(peat_data_flat)
    if total_pixels > 0:
        for cls in range(5):
            count_cls = np.sum(peat_data_flat == cls)
            pixel_counts[cls] = (count_cls / total_pixels) * 100
    else:
        pixel_counts = {cls: 0 for cls in range(5)}

    # Rename keys to descriptive names
    name_map = {
        0: "Vatten",
        1: "Mineraljord",
        2: "Torv_30",
        3: "Torv_40",
        4: "Torv_50"
    }

    pixel_counts_renamed = {name_map[k]: v for k, v in pixel_counts.items()}
    pixel_counts_renamed["Torv_total"] = (
        pixel_counts_renamed["Torv_30"] +
        pixel_counts_renamed["Torv_40"] +
        pixel_counts_renamed["Torv_50"]
    )
    print(f"Pixel percentages (renamed + total): {pixel_counts_renamed}")
    return pixel_counts_renamed

import numpy as np
import pandas as pd
import geopandas as gpd
from shapely.geometry import box
from shapely.ops import unary_union
import rasterio.features
import matplotlib.colors as mcolors


def process_catchment_v2(polygon, peat, lines, args_o, idx=None):
    """
    Process one catchment polygon with stepwise error handling:
    clip peat raster and lines,
    calculate line lengths in peat,
    calculate % of peat pixels per class within polygon,
    plot results if possible.

    Returns:
    - pandas.DataFrame: single row with results, NaNs where errors occurred
    """
    poly_id = polygon['mvm_id'] if 'mvm_id' in polygon else idx
    print(f"\nStarting processing for polygon mvm_id: {poly_id}")

    # Prepare default empty results dict with NaNs
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
    }

    try:
        poly_bounds = polygon.geometry.bounds
        print(f"Clipping peat raster to polygon bounding box: {poly_bounds}")
        peat_clip = peat.rio.clip_box(minx=poly_bounds[0], miny=poly_bounds[1],
                                     maxx=poly_bounds[2], maxy=poly_bounds[3])
    except Exception as e:
        print(f"Failed clipping peat raster bbox: {e}")
        return pd.DataFrame([results])

    try:
        print("Masking peat raster to polygon geometry...")
        peat_masked = peat_clip.rio.clip([polygon.geometry], peat_clip.rio.crs, drop=False, invert=False)
    except Exception as e:
        print(f"Failed masking peat raster: {e}")
        return pd.DataFrame([results])

    try:
        print("Calculating pixel percentages per peat class inside polygon...")
        peat_data = peat_masked.data[0].compute()  # Dask trigger
        peat_data_flat = peat_data[~np.isnan(peat_data)]

        total_pixels = len(peat_data_flat)

        pixel_counts = {}
        if total_pixels > 0:
            for cls in range(5):
                count_cls = np.sum(peat_data_flat == cls)
                pixel_counts[cls] = (count_cls / total_pixels) * 100
        else:
            pixel_counts = {cls: 0 for cls in range(5)}

        # Map pixel counts to descriptive names
        results['peat_pct_Vatten'] = pixel_counts.get(0, 0)
        results['peat_pct_Mineraljord'] = pixel_counts.get(1, 0)
        results['peat_pct_Torv_30'] = pixel_counts.get(2, 0)
        results['peat_pct_Torv_40'] = pixel_counts.get(3, 0)
        results['peat_pct_Torv_50'] = pixel_counts.get(4, 0)
        results['peat_pct_Torv_total'] = (results['peat_pct_Torv_30'] +
                                         results['peat_pct_Torv_40'] +
                                         results['peat_pct_Torv_50'])
        print(f"Pixel percentages: {results['peat_pct_Vatten']:.2f} water, {results['peat_pct_Mineraljord']:.2f} mineral soil, "
              f"{results['peat_pct_Torv_30']:.2f} Torv_30, {results['peat_pct_Torv_40']:.2f} Torv_40, {results['peat_pct_Torv_50']:.2f} Torv_50")
    except Exception as e:
        print(f"Failed calculating peat pixel percentages: {e}")

    try:
        print("Clipping lines to polygon...")
        lines_clip = gpd.clip(lines, polygon.geometry)
    except Exception as e:
        print(f"Failed clipping lines: {e}")
        lines_clip = gpd.GeoDataFrame(geometry=[])

    try:
        print("Filtering lines intersecting peat > 1 areas...")
        peat_gt1 = peat_masked.where(peat_masked > 1)
        mask = peat_gt1[0].notnull().compute()
        mask_data = mask.values.astype('uint8')

        transform = peat_gt1.rio.transform()

        ys, xs = np.where(mask_data == 1)
        if len(xs) == 0 or len(ys) == 0:
            print("No peat > 1 pixels found inside polygon, skipping peat lines clipping.")
            total_len = lines_clip.length.sum() if not lines_clip.empty else 0
            total_length = 0
            perc = 0
            lines_in_peat = gpd.GeoDataFrame(geometry=[])
        else:
            min_col, max_col = xs.min(), xs.max()
            min_row, max_row = ys.min(), ys.max()
            minx_peat, miny_peat = transform * (min_col, max_row+1)
            maxx_peat, maxy_peat = transform * (max_col+1, min_row)
            peat_mask_bbox = box(minx_peat, miny_peat, maxx_peat, maxy_peat)

            print(f"Pre-filtering lines by peat mask bounding box: {peat_mask_bbox.bounds}")
            lines_pre = lines_clip[lines_clip.intersects(peat_mask_bbox)]

            print("Polygonizing peat mask for precise clipping...")
            mask_polygons = []
            for geom, val in rasterio.features.shapes(mask_data, transform=transform):
                if val == 1:
                    mask_polygons.append(shape(geom))
            peat_area = unary_union(mask_polygons)

            print("Clipping lines to peat areas...")
            if len(lines_pre) > 0:
                lines_in_peat = gpd.clip(lines_pre, peat_area)
            else:
                lines_in_peat = gpd.GeoDataFrame(geometry=[])

            total_len = lines_clip.length.sum()
            total_length = lines_in_peat.length.sum()
            perc = (total_length / total_len) * 100 if total_len > 0 else 0

        results['perc_ditch_in_peat'] = perc
        results['total_ditch_length'] = total_len
        results['line_ditch_in_peat'] = total_length

        print(f"Total line length in polygon: {total_len:.2f} m")
        print(f"Line length inside peat: {total_length:.2f} m")
        print(f"Percentage of lines inside peat: {perc:.2f}%")
    except Exception as e:
        print(f"Failed processing line lengths in peat: {e}")

    # try:
    #     print("Generating plot...")
    #     plot_peat_catchment(polygon, peat_gt1, lines_clip, lines_in_peat, results['perc_ditch_in_peat'], args_o, idx)
    # except Exception as e:
    #     print(f"Failed to generate plot for mvm_id: {poly_id}: {e}")

    print(f"Finished processing polygon mvm_id: {poly_id}\n")

    results_df = pd.DataFrame([results])
    folder = os.path.join(os.path.split(args.o)[0], "by_station")
    os.makedirs(folder, exist_ok=True)
    results_fp = os.path.join(folder ,f"peat_{poly_id}.csv")
    results_df.to_csv(results_fp, index=False)
    return results_df



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

polygon_fp = args.c

peat_raster_fp = args.pr

# Load data
polygons = gpd.read_file(f"zip://{polygon_fp}").to_crs("EPSG:3006")
lines = gpd.read_file(gdb_path, layer=layer_name).to_crs("EPSG:3006")
peat = rioxarray.open_rasterio(peat_raster_fp, masked=True, chunks=True).rio.write_crs("EPSG:3006")

#%%

import pandas as pd


for idx, polygon in polygons.iloc[20:24].iterrows():
    df_res = process_catchment_v2(polygon, peat, lines, args.o, idx)



# %%
