# Parse arguments
import argparse
parser = argparse.ArgumentParser()
parser.add_argument("-f", type=str, help="folder for the the raster")
parser.add_argument("-c", type=str, help="the catchments")
parser.add_argument("-o", type=str, help="the output")
parser.add_argument("-sy", type=int, help="start year")
parser.add_argument("-ey", type=int, help="end year")
parser.add_argument("-res", type=str, help="daily (default) or month(ly) resolution")


args = parser.parse_args()
date_range = slice(f"{args.sy}-01-01", f"{args.ey}-12-31")
zip_catch = args.c
output_file = args.o

resolution = args.res

# packages needed to run discharge application 
from shapely.geometry import Polygon
import os
import geopandas as gpd
import rioxarray # initiated rioxarray GIS refernced xarrays (Is needed!)
import xarray as xr
from shapely.geometry import mapping
import pandas as pd
import numpy as np

# functions for climate agggregation

def extract_var (mvm_id,  cats, id_var, df, var, date_range): 
    cat = cats.loc[cats[id_var] == mvm_id]
    # re_cat= cat.to_crs(precip.rio.crs) # reproject to match 

    # Open Netcdf

    if var == 'precip':
        var = 'pr'
    else:
        var = 'tas'

    
    precip = df.sel(time = date_range)

    precip.rio.write_crs("epsg:3021", inplace=True)
    re_cat= cat.to_crs(precip.rio.crs)

    minx, miny, maxx, maxy = re_cat.total_bounds
    buffer = max(2000, min(maxx-minx, maxy-miny)*0.05)
    minx, miny, maxx, maxy = re_cat['geometry'].buffer(buffer).total_bounds

    clipped_= precip.rio.clip_box(minx = minx, miny=miny, maxx = maxx, maxy = maxy)

    X = clipped_['x'].to_numpy()
    Y = clipped_['y'].to_numpy()


    res = 4000

    xmin = min(X) -res/2
    ymin = min(Y)-res/2
    xmax = max(X)+res/2
    ymax = max(Y)+res/2


    cols = list(np.arange(xmin, xmax, res))
    rows = list(np.arange(ymin, ymax, res))

    polygons = []
    for x in cols[:]:
        for y in rows[:]:
            polygons.append(Polygon([(x,y), (x+res, y), (x+res, y+res), (x, y+res)]))

    # make the grid squares

    grid = gpd.GeoDataFrame({'geometry':polygons}).reset_index(names = 'grid_id')
    grid.crs = precip.rio.crs
    # Perform overlay operation to find the intersection
    intersection = gpd.overlay(grid, re_cat, how='intersection')

    # Calculate the area of each resulting polygon
    intersection['overlap_area'] = intersection.geometry.area

    # Group by grid polygon and sum the overlap areas
    overlap_area_per_grid = intersection.groupby('grid_id')['overlap_area'].sum()

    # Merge the calculated overlap areas back to the grid GeoDataFrame
    grid = grid.merge(overlap_area_per_grid, left_on='grid_id', right_index=True, how='left')
    grid['overlap_area'] = grid['overlap_area'].fillna(0)
    grid['overlap_area'] = grid['overlap_area']/(res**2)

    total = grid['overlap_area'].sum() # find the total area in gridcells

    grid['overlap_area'] = grid['overlap_area'] / total # now add up to average pr in the cacthment if multiplied by each days 

    matrix = grid['overlap_area'].values.reshape(len(X), len(Y))
    # print(len(matrix), len(matrix.T),len(X), len(Y))


    # Create xarray DataArray
    weights = xr.DataArray(matrix, dims=('x', 'y'), coords={'x': X, 'y': Y})
    weights.attrs['crs'] = precip.rio.crs


    weighted = clipped_[var] * weights

    summed = weighted.sum(dim=('x', 'y'))
    time_series = summed.to_dataframe(name = var+ '_avg').drop(columns = 'crs').reset_index()
    #time_series['mvm_id'] = mvm_id


    # ts_extent = clipped_[var].mean(dim=('x', 'y')).to_dataframe(name = var + '_extent').drop(columns = 'crs').reset_index()

    # time_series = time_series.merge(ts_extent, on = 'time')

    return time_series

def daily_climate( catchments,temperature_path = "SMHI_pthbv_pr_1980_2024_daily.nc" , precipitation_path = "SMHI_pthbv_tas_1980_2024_daily.nc", id_variable = 'mvm_id', date_range = slice("2010-01-01", "2014-12-31")):

    """ Requirnments are for the file paths to exist, for the catchment shapefile to be in crs EPSG:3006 """

# first we check if the files provided actually exist

    if not os.path.isfile(precipitation_path):
        raise FileNotFoundError(f"The precipitation file path {precipitation_path} does not exist.")
    if not os.path.isfile(temperature_path):
        raise FileNotFoundError(f"The temperature file path {temperature_path} does not exist.")

# check whether the crs is correct  
    if catchments.crs !=  'EPSG:3006':
        raise KeyError(f"The crs is not a valid, please convert to EPSG:3006.")
    
    if id_var not in catchments.columns:
        raise KeyError(f"Column '{id_var}' not found in GeoDataFrame. Please choose an existing column instead.")

    climate_data = pd.DataFrame(columns= ['time', 'pr_avg', id_var, 'tas_avg'], dtype  = 'object')    
    failed = []
    mvm_id = catchments[id_var].to_list()

    precipitation = xr.open_dataset(precipitation_path, decode_coords="all")
    temperature = xr.open_dataset(temperature_path, decode_coords="all")

    for id in mvm_id:
        print("ID in list:", mvm_id.index(id)+1, "of", len(mvm_id))

        try:
            precip= extract_var(id, catchments, id_var = id_variable, df = precipitation, var = 'precip', date_range = date_range)
            temp = extract_var(id, catchments , id_var = id_variable, df = temperature,  var = 'temp', date_range = date_range)
            temp['time'] = temp['time'].dt.date
            precip['time'] = precip['time'].dt.date
            current = precip.merge(temp, on = 'time', )
            current['mvm_id'] = id

            # If resolution is "month", aggregate data
            if resolution == "month":
                current['time'] = pd.to_datetime(current['time'])
                current = current.groupby(current['time'].dt.to_period('M')).agg({
                    'pr_avg': 'sum',  # Sum precipitation for the month
                    'tas_avg': 'mean',  # Average temperature for the month
                    'mvm_id': 'first'  # Keep the ID
                }).reset_index()
                current['time'] = current['time'].dt.to_timestamp()


            climate_data = pd.concat([climate_data if not climate_data.empty else None,current], axis = 0)
        except Exception as e:
            print(f"Error processing ID {id}: {e}")
            failed.append(id)
    
    print(failed)

    return(climate_data)


# first load in your cacthment shapefile make sure its in SWEREF TM99 if you load just the shapefile you have to manually set the projection
# cats = gpd.read_file(r"shapefile.shp").replace(-9999,pd.NA) # Fixed cacthments
# cats.crs = 'EPSG:3006'

# or if you have it as a zip file you can load it with the projection

cats = gpd.read_file(f"zip://{zip_catch}").replace(-9999,pd.NA)

if "mvm_id" not in cats.columns:
    # check for mvmid
    if 'mvmid' in cats.columns:
        cats['mvm_id'] = cats['mvmid'] 

# Check if mvm_id is in the columns of the shapefile
if 'mvm_id' not in cats.columns:
    # If not, check which columns the user could use instead
    available_columns = cats.columns.tolist()
    print(f"Available columns in the GeoDataFrame: {available_columns}")
    raise KeyError(f"Column 'mvm_id' not found in GeoDataFrame. Please choose an existing column instead.") 



# select which variable is your id column in the, in my case its called mvm_id. This is to loop through all the ids of your shapefile.
id_var = 'mvm_id'

# change directory to the folder containing your input files and give the names of your input files. 


precipitation_path = os.path.join(args.f, "SMHI_pthbv_pr_1980_2024_daily.nc")
temperature_path = os.path.join(args.f,"SMHI_pthbv_tas_1980_2024_daily.nc")

# Run the function daily climate to generate a df that has an id column a time column and then both precipitation and temperature aggregated for each cacthment. 
daily = daily_climate(catchments = cats,temperature_path = temperature_path , precipitation_path = precipitation_path, id_variable = "mvm_id", date_range = date_range)



daily.to_csv(args.o, index = False)
