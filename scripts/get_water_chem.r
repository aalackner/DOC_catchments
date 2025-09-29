# set up
library(tidyverse)
source("src/sourcecode.R")

# Acess the API
library(jsonlite)
library(sf)

## first we load the list of mvm_ids

mvm_ids <- st_read( "data/test.shp")$id



## load set up variables and library for accessing the API

my.token <- "PUJD93023KAS943HD"



folder <- "test_results/chemistry"

# Check and create main folder
if (!dir.exists(folder)) {
  dir.create(folder, recursive = TRUE)
}

# Create subfolders JSON and CSV inside it
json_folder <- file.path(folder, "JSON")
csv_folder  <- file.path(folder, "CSV")

if (!dir.exists(json_folder)) {
  dir.create(json_folder)
}

if (!dir.exists(csv_folder)) {
  dir.create(csv_folder)
}



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


## Now we loop through all the mvm_ids accessing the json file, saving the raw json in case I need to ever access the metadata. And then moving on to saving it as a csv per station.

for (id in mvm_ids){
  
  full.samples <- get_samples(folder, id) # Only needed if JSON has never been downloaded
  # full.samples <- fromJSON(file.path(folder, "JSON", paste0(id, ".JSON")))
  csv.path <- file.path(folder, "CSV", paste0(id, ".csv"))
  
  
  ## run the JSON through the functions combine_col and into_table to generate a single csv file for each station.
  process_samples(full.samples, csv.path, id)
  
  # Pause for 1 second in order to let the server also do other jobs
  # Sys.sleep(1) 
}

print(fail_table)

fail_table %>% write.csv(., file = 'fails.csv')

overview %>% write.csv(., file = 'overview.csv')



#  List all files in the folder
files_in_folder <- list.files(path = csv_folder, full.names = TRUE)

# Filter for .csv files
csv_files <- files_in_folder %>%
  keep(~ str_detect(.x, "\\.csv$"))  # Keep only .csv files

# Step 3: Read and bind all .csv files into a single tibble
csv_files %>%
  map_dfr(~ read_csv(.x, col_types = cols(.default = "c"))) %>% 
  write.csv(.,file = file.path(folder, "chem_combined.csv"), row.names = FALSE)
