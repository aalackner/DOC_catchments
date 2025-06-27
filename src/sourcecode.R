library(tidyverse)


replace_less_than_var <- function(values, bad_quality_na = TRUE){ # function for replacing values at the detection limit with half values
  values_parsed <- values %>% as.character() %>% parse_number(locale = locale(decimal_mark = ","))
  
  which_intervals <- which(substring(values,1,1) == "[")
  which_less_than <- which(substring(values,1,1) == "<")
  ## Testa att ersätta alla värden under  högsta detektionsgränsen med halva högsta detektionsgränesn
  ## Ersätt istället med halva detektionsgränsen, det blir bättre då filerna läses in en och en
  if (length(which_less_than) > 0) {
    values_less_than_half <- values[which_less_than] %>% gsub(",", ".", .) %>% gsub("<","",.) %>% as.numeric()
    values_parsed[which_less_than] <- values_less_than_half/2}
  
  if (bad_quality_na == TRUE) {values_parsed[which_intervals] <- NA}
  else{
    values_intervals <- values[which_intervals] %>%
      gsub("\\[","", .) %>%
      gsub("\\]","", .) %>%
      gsub(",",".", .) %>%
      as.numeric()
    values_parsed[which_intervals] <- values_intervals}
  
  return(values_parsed)
}



into_table <- function(full.samples){
  df_sample <- full.samples$samples
  table <-  tibble()
  for (i in 1:length(df_sample$samplingDate)){
    
    # check that it is the right type of sample, we only want water chemistry
    if (!(df_sample$surveyType[[i]] %in% c("Vattenkemi i vattendrag",
                                         "Sparkprovtagning (tidsserier) v1",
                                         "Vattenkemi KEU, vattendrag", 
                                         "NA", NA))) {
      print(paste0("For mvm_id:", id, " sample: ", i,  " the type was: ", df_sample$surveyType[[i]]))
      next
    }
    
    # make an empty tibble where a single row is a single sample and add sample date, id and station id to the row.  
    row = tibble(sampling_date = date(), 
                 sample_id = integer(),
                 mvm_id = integer())
    
    row %>% add_row(sampling_date = df_sample$samplingDate[[i]], sample_id = df_sample$sampleId[[i]], mvm_id = df_sample$stationId[[i]]) -> row
    df <- df_sample$observations[[i]]
    for (j in 1: length(df_sample$observations[[i]]$propertyCode)){
      name = paste(df[j,]$propertyCode[1],gsub("[^[:alnum:] ]", "", df[j,]$observationValues[[1]]$unit), sep = "_" )
      
      if (length(name)[1] != 0){
        
        if (grepl("_NA", name)){                # removing the unit in case the unit was NA for example in pH
          name <- gsub("_NA.*", "", name)
        }
        
        value = replace_less_than_var(df[j,]$observationValues[[1]]$value)
        row[[name]] = value
      }
    }
    table %>% bind_rows(., row) -> table
    # if (i == 3){
    #   break
    # }
  }
  
  table %>% mutate(sampling_date = as.Date(sampling_date), year = year(sampling_date)) -> table
  # print(table)
  return(table)
}

combine_col <- function (data){
  ########## Sulfate  ##################
  
  ## add in other units when they are applicable and then coalessce through them 
  cols <- c("SO4_IC_mekvl", "SO4_IC_mgl SO4")
  
  # Check and add columns if they do not exist
  for (col in cols) {
    if (!col %in% names(data)) {
      data[[col]] <- NA  # Add the column with NA values
    }
  }
  
  data %>% mutate (SO4_M = coalesce(
    (SO4_IC_mekvl/2)/1000,
    `SO4_IC_mgl SO4` / ((32+ 4*16)*1000) 
  )) %>% select(-all_of(cols)) -> data
  
  ############## NO3 ###################
  
  cols <- c("NO2_NO3_N_µgl", "NO3_N_µgl")
  
  # Check and add columns if they do not exist
  for (col in cols) {
    if (!col %in% names(data)) {
      data[[col]] <- NA  # Add the column with NA values
    }
  }
  data %>% mutate (NO3_M = coalesce(
    (NO2_NO3_N_µgl)/(14.01*1000000),
    (NO3_N_µgl)/(14.01*1000000)))  %>% select(-all_of(cols)) -> data
  
  ############# cations & anions ##########################
  
  ## add in other units when they are applicable and then coalessce through them 
  
  cols <- c("K_mekvl", "K_mgl", "Ca_mekvl", "Ca_mgl", "Cl_mekvl", "Si_mgl", "Cl_mgl", "Na_mekvl", "Na_mgl","Fluorid_mgl", "Fluorid_mekvl", "Fe_µgl", "Mg_mekvl", "Mg_mgl", "NH4_N_µgl" )
  
  # Check and add columns if they do not exist
  for (col in cols) {
    if (!col %in% names(data)) {
      data[[col]] <- NA  # Add the column with NA values
    }
  }
  
  
  data %>% mutate (
    Cl_M = coalesce(
      Cl_mgl/(35.45 * 1000),
      Cl_mekvl/1000
    ),
    K_M = coalesce(
      K_mgl/(39.10 * 1000),
      K_mekvl/1000
    ), 
    Ca_M = coalesce(
      Ca_mgl/(40.08 * 1000),
      (Ca_mekvl/1000)/2
    ),
    Na_M = coalesce(
      Na_mgl/(35.45 * 1000),
      Na_mekvl/1000
    ),
    Mg_M = coalesce(
      Mg_mgl/(24.31 * 1000),
      (Mg_mekvl/1000)/2
    ),
    Fe_M = coalesce(
      Fe_µgl/(55.85 * 1000000)),
    Si_M = coalesce(
      Si_mgl/(28.09 * 1000)
    ),
    NH4_M = coalesce(
      NH4_N_µgl/(14.01*1000000)
    ),
    F_M = coalesce(
      Fluorid_mgl/(19.00 * 1000),
      Fluorid_mekvl/1000
    )) %>% select(-all_of(cols)) -> data
  
  return(data)
}

process_samples <- function(full.samples, csv.path, id) {
  
  # Try the operation and catch errors
  tryCatch({
    # Print number of samples and id
    print(paste("mvm_is: ", id, " # of samples :", length(full.samples$samples$sampleId)))
    overview <<- rbind(overview, data.frame(mvm_id = id, comment = length(full.samples$samples$sampleId)))
    # Step 2: Define the pipeline (assuming into_table() and combine_col() are defined elsewhere)
    full.samples %>%
      into_table(.) %>%
      # combine_col(.) %>%
      write.csv(., file = csv.path)
    
  }, error = function(e) {
    # Step 3: If an error occurs, add the id and error message to the fail_table
    fail_table <<- rbind(fail_table, data.frame(mvm_id = id, comment = e$message))
    
  })
}

get_samples <- function(folder, id) {
  
  # Try the operation and catch errors
  tryCatch({
    # Step 2: Define the pipeline (assuming into_table() and combine_col() are defined elsewhere)
    url.call <- paste0('https://miljodata.slu.se/api/observations-service/v2/full-samples/query?token=', my.token, '&stationIds=', id, '&fromYear=1990&toYear=2024&productType=Chemistry')
    json.path <- paste0(folder, "JSON\\", id, ".json" )
    
    full.samples<-fromJSON(url.call)
    
    ## Write as json to the folder
    write(toJSON(full.samples), file = json.path)
    
    return(full.samples)
  }, error = function(e) {
    # Step 3: If an error occurs, add the id and error message to the fail_table
    fail_table <<- rbind(fail_table, data.frame(mvm_id = id, comment = e$message))
    return(NA)
  })
}
