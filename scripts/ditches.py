# Script for calculating peat area
#%% Only needed if used from terminal, otherwise the first block needs to be commented out
import argparse
parser = argparse.ArgumentParser()
parser.add_argument("-r", type=str, help="the raster")
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
# class Args:
#     pass

# args = Args()

# args.id = "mvmid"  # Default value for id variable



# # # Example manual assignments
# args.c = r"C:\Users\anlr0006\repos-win\DOC_catchments\data\aro_trendsjoar_106_250408.zip"
# args.o = r"C:\Users\anlr0006\repos-win\DOC_catchments\results\slu_sgu\ditch_test.csv"
# args.r = r"C:\Users\anlr0006\repos-win\DOC_catchments\input\Dikeskarta"
# args.gdb = r"C:\Users\anlr0006\repos-win\DOC_catchments\results\arcpy_workspace\test_ditches.gdb"

#%% set the workspace and populate the gdb
import os.path

# arcpy.management.CreateFileGDB(os.path.dirname(args.gdb), os.path.basename(args.gdb), "CURRENT")
arcpy.env.workspace = os.path.join(args.gdb)

# SET PYTHON WORKING DIR
#os.chdir(os.path.join(r"C:\Users\anlr0006\repos-win\DOC_catchments\results\arcpy_workspace", args.gdb)) 

arcpy.env.overwriteOutput = True

from zipfile import ZipFile
import os

if os.path.exists(arcpy.env.workspace) == False:
    arcpy.management.CreateFileGDB(os.path.dirname(args.gdb), os.path.basename(args.gdb), "CURRENT")

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

#%% Check id variable and availability of rasters
# ID
# Check if the specified field exists in the shapefile
fields = [field.name for field in arcpy.ListFields(shapefile)]

if args.id not in fields:
    print(f"Field '{args.id}' not found in the shapefile '{args.c}'.")
    print("Available fields in the shapefile:")
    for field in fields:
        print(f"- {field}")
else:
    print(f"Field '{args.id}' exists in the shapefile '{args.c}'.")

# check 

#%% Merge mosaic ditches

out_table = os.path.join(arcpy.env.workspace,"output_table_ditch")
output = os.path.join(args.r,"mosaic_ditches.gdb", "Diken_vektor_Merge")

if os.path.exists(os.path.join(args.r, "mosaic_ditches.gdb")) == False:
    arcpy.management.CreateFileGDB(args.r, "mosaic_ditches.gdb", "CURRENT")

    # Dynamically construct the input paths using args.r
    inputs = [
        os.path.join(args.r, "Vector", "Diken_vektor.shp"),
        os.path.join(args.r, "Vector", "Diken_vektor_1.shp"),
        os.path.join(args.r, "Vector", "Diken_vektor_2.shp"),
        os.path.join(args.r, "Vector", "Diken_vektor_3.shp")
    ]

# Join the inputs into a semicolon-separated string
    inputs_string = ";".join(inputs)


    print(f"Output path: {output}")

    arcpy.management.Merge(
        inputs=inputs_string,
        output=output,
        field_mappings=r'FID_1 "FID_1" true true false 11 Double 0 11,First,#,U:\slu\Dikeskarta\Vector\dikeskartan\Diken_vektor.shp,FID_1,-1,-1,U:\slu\Dikeskarta\Vector\Diken_vektor_1.shp,FID_1,-1,-1,U:\slu\Dikeskarta\Vector\Diken_vektor_2.shp,FID_1,-1,-1,U:\slu\Dikeskarta\Vector\Diken_vektor_3.shp,FID_1,-1,-1;VALUE "VALUE" true true false 15 Double 0 0,First,#,D:\vivan2\vivan_2_data\dikeskartan\Diken_vektor.shp,VALUE,-1,-1,U:\slu\Dikeskarta\Vector\Diken_vektor_1.shp,VALUE,-1,-1,U:\slu\Dikeskarta\Vector\Diken_vektor_2.shp,VALUE,-1,-1,U:\slu\Dikeskarta\Vector\Diken_vektor_3.shp,VALUE,-1,-1;fme_featur "fme_featur" true true false 50 Text 0 0,First,#,D:\vivan2\vivan_2_data\dikeskartan\Diken_vektor.shp,fme_featur,0,49,U:\slu\Dikeskarta\Vector\Diken_vektor_1.shp,fme_featur,0,49,U:\slu\Dikeskarta\Vector\Diken_vektor_2.shp,fme_featur,0,49,U:\slu\Dikeskarta\Vector\Diken_vektor_3.shp,fme_featur,0,49',
        add_source="NO_SOURCE_INFO"
    )

#%% Do the tabulate intersection

arcpy.analysis.TabulateIntersection(
    in_zone_features=shapefile,
    zone_fields=args.id,
    in_class_features=output,
    out_table= out_table,
    class_fields=None,
    sum_fields=None,
    xy_tolerance=None,
    out_units="METERS"
)

# Convert the output table to a CSV file
csv_output = args.o  # Ensure args.o ends with ".csv"

arcpy.conversion.ExportTable(in_table = out_table, 
                             out_table = csv_output)
# %%
