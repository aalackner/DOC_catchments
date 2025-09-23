#%%
import pandas as pd
import os
#%%

folder_q1  = "/home/anlr0006/code/DOC_catchments/results/slu_sgu/by_station/quartiles"
folder_all = r"/home/anlr0006/mnt/anna/My Documents/04_Projects/11_Lakes/01_data/03_processed_data/inter_peat/window"

folder_q2 = r"/home/anlr0006/mnt/anna/My Documents/04_Projects/11_Lakes/01_data/03_processed_data/inter_peat/by_station"

folder_q3 = r"/home/anlr0006/mnt/anna/My Documents/04_Projects/11_Lakes/01_data/03_processed_data/inter_peat/window/quartiles_area"

folder_q4  = "/home/anlr0006/code/DOC_catchments/results/slu_sgu/by_station"


#%%
# load all the csv file names in the folders
q1 = os.listdir(folder_q1)
q4 = os.listdir(folder_q4)

all = os.listdir(folder_all)

q2 = os.listdir(folder_q2)

q3 = os.listdir(folder_q3)

#%%
start = 0

for file in all:
    if file.endswith(".csv"):
        if start == 0 :
            result = pd.read_csv(os.path.join(folder_all, file))
        else: 
            df = pd.read_csv(os.path.join(folder_all, file))
            result = pd.concat([result, df])
        start += 1

result

#%%

#trendlakes
start = 0

for file in q2:
    if file.endswith(".csv"):
        if start == 0 :
            result_trend = pd.read_csv(os.path.join(folder_q2, file))
        else: 
            df = pd.read_csv(os.path.join(folder_q2, file))
            result_trend = pd.concat([result_trend, df])
        start += 1

result_trend



#%%
# one df with all of them, ad column name

start = 0

for file in q1:
    if file.endswith(".csv"):
        if start == 0 :
            results = pd.read_csv(os.path.join(folder_q1, file))
            results['file_name'] = file
        else: 
            df = pd.read_csv(os.path.join(folder_q1, file))
            df['file_name'] = file
            results= pd.concat([results, df])
        start += 1

results

start = 0

for file in q4:
    if file.endswith(".csv"):
        if start == 0 :
            results4 = pd.read_csv(os.path.join(folder_q4, file))
            results4['file_name'] = file
        else: 
            df = pd.read_csv(os.path.join(folder_q4, file))
            df['file_name'] = file
            results4= pd.concat([results4, df])
        start += 1

results4


# %%

df = pd.concat([results, results4])

import pandas as pd

# Step 1: Extract ID
df['id'] = df['mvm_id'].str.extract(r'(\d+)', expand=False)

# Step 2: Define percentage columns
percent_cols = ['peat_pct_Vatten', 'peat_pct_Mineraljord', 'peat_pct_Torv_total']

# ✅ Step 3: Convert percentages to decimals BEFORE multiplying
df[percent_cols] = df[percent_cols] / 100

# Step 4: Calculate weighted values
for col in percent_cols:
    df[f'{col}_weighted'] = df[col] * df['area_m2']

# Step 5: Group and aggregate
grouped = df.groupby('id').agg({
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

results_q1 = grouped.copy()
results_q1
# %%


start = 0

for file in q3:
    if file.endswith(".csv"):
        if start == 0 :
            results = pd.read_csv(os.path.join(folder_q3, file))
            results['file_name'] = file
        else: 
            df = pd.read_csv(os.path.join(folder_q3, file))
            df['file_name'] = file
            results= pd.concat([results, df])
        start += 1

results

# %%

df = results.copy()

import pandas as pd

# Step 1: Extract ID
df['id'] = df['mvm_id'].str.extract(r'(\d+)', expand=False)

# Step 2: Define percentage columns
percent_cols = ['peat_pct_Vatten', 'peat_pct_Mineraljord', 'peat_pct_Torv_total']

# ✅ Step 3: Convert percentages to decimals BEFORE multiplying
df[percent_cols] = df[percent_cols] / 100

# Step 4: Calculate weighted values
for col in percent_cols:
    df[f'{col}_weighted'] = df[col] * df['area_m2']

# Step 5: Group and aggregate
grouped = df.groupby('id').agg({
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

results_q3 = grouped.copy()
results_q3

# %%

all_q = pd.concat([results_q3, results_q1])

all_q['mvm_id'] = all_q['id']

final = pd.concat([all_q, result_trend, result])

#%%
import numpy as np

mask = final['ditch_perc_peat'].isna()

# First attempt: if ditch_perc_peat missing
# then compute percent if total_ditch_length is zero => 0, else compute ratio
final.loc[mask, 'ditch_perc_peat'] = np.where(
    final.loc[mask, 'total_ditch_length'] == 0,
    0,
    (final.loc[mask, 'line_ditch_in_peat'] / final.loc[mask, 'total_ditch_length']) * 100
)

# Fallback logic: where still null (maybe due to division by zero or other anomalies)
mask2 = final['ditch_perc_peat'].isna()
final.loc[mask2, 'ditch_perc_peat'] = (
    final.loc[mask2, 'ditch_length_in_peat'] / final.loc[mask2, 'total_ditch_length']
) * 100
#%%
df_final = final[['mvm_id', 'total_ditch_length', 'ditch_perc_peat', 'peat_pct_Vatten',	'peat_pct_Mineraljord'	,'peat_pct_Torv_total']]
df_final.drop_duplicates(subset='mvm_id', keep='first', inplace = True)
#%%

import matplotlib.pyplot as plt

# Choose numeric columns only (mvm_id is non-numeric and should be excluded)
columns_to_plot = [
    'total_ditch_length', 
    'ditch_perc_peat', 
    'peat_pct_Vatten', 
    'peat_pct_Mineraljord', 
    'peat_pct_Torv_total'
]

# Plot histograms
final[columns_to_plot].hist(bins=30, figsize=(12, 8), layout=(2, 3), grid=False)

plt.tight_layout()
plt.show()

# %%
file= r"/home/anlr0006/code/DOC_catchments/results/slu_sgu/peat_ditches_all.csv"
#file = r"/home/anlr0006/mnt/anna/My Documents/04_Projects/11_Lakes/01_data/03_processed_data/drivers/peat_ditches_all.csv"
df_final.loc[:, 'mvm_id'] = pd.to_numeric(df_final['mvm_id'], errors='coerce')
df_final.drop_duplicates(subset='mvm_id', keep='first').to_csv(file, index=False)

# %%

