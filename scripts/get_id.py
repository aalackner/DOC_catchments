# Parse arguments
import os
os.environ['PROJ_LIB'] = "/opt/conda/share/proj"


import argparse
parser = argparse.ArgumentParser()

parser.add_argument("-c", type=str, help="the catchments")
parser.add_argument("-o", type=str, help="the output")
parser.add_argument("-id", type=str, default='mvm_id', help="column name under which mvm id is stored. default is mvm_id")

args = parser.parse_args()
zip_catch = args.c
file_path = args.o
id = args.id 

import geopandas as gpd
import pandas as pd

cats = gpd.read_file(f"zip://{zip_catch}").replace(-9999,pd.NA)

with open(file_path, 'w') as f:
    f.write(','.join(map(str, cats[id].astype(int))))

print(f"There were {len(cats[id])} ids.")
print(f"Saved mvm_ids to {file_path}")