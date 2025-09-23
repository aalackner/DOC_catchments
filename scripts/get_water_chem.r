# set up
library(tidyverse)
source("src/sourcecode.R")

# Acess the API
library(jsonlite)
library(sf)

## first we load the list of mvm_ids

mvm_ids <- st_read( "/home/anlr0006/mnt/anna/My Documents/04_Projects/11_Lakes/01_data/02_raw_data/catchments/aro_trendsjöar_130_250703/aro_trendsjöar_130_250703.shp")$mvmid



## load set up variables and library for accessing the API

my.token <- "PUJD93023KAS943HD"



folder <- "/home/anlr0006/mnt/anna/My Documents/04_Projects/11_Lakes/01_data/02_raw_data/chemistry/"

fail_table <- data.frame(
  mvm_id = integer(),
  comment = integer(),
  stringsAsFactors = FALSE
)

overview <- data.frame(
  mvm_id = integer(),
  comment = character(),
  stringsAsFactors = FALSE
)

# mvm_ids <- c("1280")

## Now we loop through all the mvm_ids accessing the json file, saving the raw json in case I need to ever access the metadata. And then moving on to saving it as a csv per station.

for (id in mvm_ids){
  
  full.samples <- get_samples(folder, id)
  full.samples <- fromJSON(paste0(folder,"JSON_pre/" ,id, ".JSON"))
  csv.path <- paste0(folder, "CSV_pre/", id, ".csv" )
  
  
  ## run the JSON through the functions combine_col and into_table to generate a single csv file for each station.
  process_samples(full.samples, csv.path, id)
  
  # Pause for 1 second in order to let the server also do other jobs
  # Sys.sleep(1) 
}

print(fail_table)

fail_table %>% write.csv(., file = 'fails.csv')

overview %>% write.csv(., file = 'overview.csv')

folder.csv <- paste0(folder, "CSV_pre")

#  List all files in the folder
files_in_folder <- list.files(path = folder.csv, full.names = TRUE)

# Filter for .csv files
csv_files <- files_in_folder %>%
  keep(~ str_detect(.x, "\\.csv$"))  # Keep only .csv files

# Step 3: Read and bind all .csv files into a single tibble
csv_files %>%
  map_dfr(~ read_csv(.x, col_types = cols(.default = "c"))) %>% 
  write.csv(.,file = paste0(folder, 'water_chem_combined_catchments_pre_2025.csv' ))
