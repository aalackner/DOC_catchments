# Script for calculating peat area
#%% Only needed if used from terminal, otherwise the first block needs to be commented out
import argparse
parser = argparse.ArgumentParser()
parser.add_argument("-r", type=str, help="the location for the mosaic")
parser.add_argument("-c", type=str, help="the catchments")
parser.add_argument("-o", type=str, help="the output")
parser.add_argument("-id", type=str, help="the id variable", default="mvmid")
parser.add_argument("-gdb", type=str, help="the gdb to use for intermediate steps", default="test.gdb")
args = parser.parse_args()

#%% load the environment variabl
import arcpy
from arcpy import env
from arcpy.sa import *

import sys

#%%

class Args:
    pass

args = Args()

args.id = "mvmid"  # Default value for id variable



# # # Example manual assignments
# args.c = r"data\aro_trendsjoar_106_250408.zip"
# args.o = r"results\slu_sgu\test.csv"
# args.r = r"input\Torvkarta\Klassad_torvkarta\ClassifiedPeatMap.tif"
# args.gdb = r"results\arcpy_workspace\test.gdb"  # Default value for gdb




#%% set the workspace and populate the gdb
import os.path

# arcpy.management.CreateFileGDB(os.path.dirname(args.gdb), os.path.basename(args.gdb), "CURRENT")
arcpy.env.workspace = os.path.join(args.gdb)

# SET PYTHON WORKING DIR
#os.chdir(os.path.join(r"C:\Users\anlr0006\repos-win\DOC_catchments\results\arcpy_workspace", args.gdb)) 

arcpy.env.overwriteOutput = True

from zipfile import ZipFile
import os
import pandas as pd

if os.path.exists(arcpy.env.workspace) == False:
    arcpy.management.CreateFileGDB(os.path.dirname(args.gdb), os.path.basename(args.gdb), "CURRENT")



if args.c.endswith('.zip'):
        
    with ZipFile(args.c, 'r') as zf:
        for file in zf.namelist():
                extracted_path = os.path.join(arcpy.env.workspace, file)
                if os.path.exists(extracted_path):
                    os.remove(extracted_path)  # Remove the existing file
                zf.extract(file, arcpy.env.workspace)

        # Go into the folder and rename any ö to o
        # Rename files with 'ö' to 'o'
        for filename in os.listdir(arcpy.env.workspace):
            if 'ö' in filename:
                os.rename(
                    os.path.join(arcpy.env.workspace, filename),
                    os.path.join(arcpy.env.workspace, filename.replace('ö', 'o'))
                )

    # Get the shapefile name
    shapefile = os.path.join(arcpy.env.workspace,os.path.splitext(os.path.basename(args.c))[0].replace('ö', 'o') + ".shp")
else:
    source_path = args.c
    out_loc = arcpy.env.workspace
    out_name =  os.path.split(arg.c)[1]

    arcpy.FeatureClassToFeatureClass_conversion(source_path, out_loc, out_name)
    shapefile = os.path.join(out_loc, out_name)

print(shapefile)

#%% Check id variable and availability of rasters
# ID
# Check if the specified field exists in the shapefile
fields = [field.name for field in arcpy.ListFields(shapefile)]

if args.id not in fields:
    
    print("Available fields in the shapefile:")
    for field in fields:
        print(f"- {field}")
    raise(KeyError(f"Field '{args.id}' not found in the shapefile '{args.c}'."))
else:
    print(f"Field '{args.id}' exists in the shapefile '{args.c}'.")

# check 

#%% Peat area

out_table =os.path.join(arcpy.env.workspace,r"output_table_peat")

print(f"Shapefile: {shapefile}")
print(f"Raster: {args.r}")
print(f"Output Table: {out_table}")



TabulateArea(
    in_zone_data = shapefile, 
    zone_field = args.id, 
    in_class_data = args.r,
    class_field = "Value",  
    out_table = out_table)

# Convert the output table to a CSV file
csv_output = args.o  # Ensure args.o ends with ".csv"

arcpy.conversion.ExportTable(in_table = out_table, 
                             out_table = csv_output)

data = pd.read_csv(csv_output)
data = data.rename(columns={'VALUE_0': "Vatten",
                            'VALUE_1': "Mineraljord",
                            'VALUE_2': "Torv_30",
                            'VALUE_3': "Torv_40",
                            'VALUE_4': "Torv_50"})

data['Total'] = data['Vatten'] + data['Mineraljord'] + data['Torv_30'] + data['Torv_40'] + data['Torv_50']
data['Peat_area'] = (data['Torv_30'] + data['Torv_40'] + data['Torv_50'])/data['Total']
data['Mineral'] = data['Mineraljord']/data['Total']
data.to_csv(csv_output, index=False)
# %%
