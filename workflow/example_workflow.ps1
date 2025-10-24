$cats = ".\data\corrected_merged.shp"
$id = "mvm_id"

# Collected input file 
$ditchdatabase = ".\input\Dikeskarta\mosaic_ditches.gdb"
$peat = ".\input\Torvkarta\Klassad_torvkarta\ClassifiedPeatMap.tif"

$climate_folder = ".\input\SMHI"
$jennings = ".\input\jennings\jennings_et_al_2018_file4_temp50_raster.tif"

$emep = ".\input\EMEP\data" 

$hk = "\\storage.slu.se\Home$\anlr0006\My Documents\04_Projects\09_General\01_GIS\HK.shp"
$eco = "\\storage.slu.se\Home$\anlr0006\My Documents\04_Projects\09_General\01_GIS\ekoreg_2006_sweref99.shp"

$svar = "\\storage.slu.se\Home$\anlr0006\My Documents\04_Projects\09_General\01_GIS\SVAR2022_delavrinningsomraden.zip"
$x = "x_utlopp"
$y = "y_utlopp"





# Collected Outputs
$o_soil_depth = "test_results\soil_depth.csv"
$o_ndvi = "test_results\ndvi"
$o_hk = "test_results\hk.csv"
$o_emep = "test_results\emep.csv"
$o_climate = "test_results\climate_by_station"
$o_peat = "test_results\dd_peat"
$o_runoff = "test_results\runoff_trend"


# Activating the correct environment

.venv\Scripts\activate

Write-Output "environment activated"

python scripts\dd_peat.py -o $o_peat -d $ditchdatabase -pr $peat -c $cats -id $id 

Write-Output "peat and ditch done"

python scripts\soil_depth.py -r "default"  -c $cats -o  $o_soil_depth -id $id

Write-Output "soil depth done"

python scripts/precip_as_snow.py -f $climate_folder -t $jennings  -c $cats -o  $o_climate -id $id > "log/climate_log.txt"

Write-Output "climate done"

python scripts/emep.py -f $emep  -c $cats -o  $o_emep -id $id -sy 1990 -ey 2024  > "log/emep_log.txt"

Write-Output "emep done"

python scripts/High_coast_ecoregions.py -hk $hk -c $cats -o  $o_hk -id $id -eco $eco -cent "False" > "log/hk_log.txt"

Write-Output "HK done"

python scripts/get_SVAR_id.py  -c $cats  -o  $o_runoff -id $id -svar $svar -map "false" > "log/get_SVAR_log.txt"


python scripts/discharge.py  -o  $o_runoff -id $id > "log/discharge_log.txt"

Write-Output "runoff done"

python scripts/ndvi.py  -c $cats  -o  $o_ndvi -id $id -sy 2005 -ey 2024

Write-Output "NDVI done"

deactivate

Rscript scripts/get_water_chem.r >> log/chem.log
