

$input_file = "\\storage.slu.se\Home$\anlr0006\My Documents\04_Projects\11_Lakes\01_data\02_raw_data\catchments\merged_catchments.zip"
$ditchdatabase = "C:\Users\anlr0006\repos-win\DOC_catchments\input\Dikeskarta\mosaic_ditches.gdb"
$peat = "C:\Users\anlr0006\repos-win\DOC_catchments\input\Torvkarta\Klassad_torvkarta\ClassifiedPeatMap.tif"
$id = "mvm_id"




# then the ones that dont need the arcpy env

.venv\Scripts\activate

Write-Output "environment activated"

python scripts\dd_peat.py -o C:\Users\anlr0006\repos-win\DOC_catchments\results\slu_sgu\by_station\quartiles_area -d $ditchdatabase -pr $peat -c $input_file -id $id >> results/slu_sgu/output_shell_merged_catchments_4.txt

Write-Output "peat and ditch done"

# python scripts\soil_depth.py -r "default"  -c $input_file -o  C:\Users\anlr0006\repos-win\DOC_catchments\results\slu_sgu\soil_depth_merged_catchments.csv

deactivate

Write-Output "environment deactivated"

Write-Output "done soil depth"

<# # ARPY

Write-Output "This is actually commented out why is it printing?????"

(& "C:\Users\anlr0006\AppData\Local\Programs\ArcGIS\Pro\bin\Python\Scripts\conda.exe" "shell.powershell" "hook") | Out-String | Invoke-Expression

conda activate C:\Users\anlr0006\repos-win\DOC_catchments\arcpy_env



python scripts\peat_area.py -o \results\slu_sgu\peat_classified_merged_catchments.csv -pr C:\Users\anlr0006\repos-win\DOC_catchments\input\Torvkarta\Klassad_torvkarta\ClassifiedPeatMap.tif -c $input_file -r input\Torvkarta\Klassad_torvkarta\ClassifiedPeatMap.tif -gdb C:\Users\anlr0006\repos-win\DOC_catchments\results\arcpy_workspace\test.gdb -id $id


python scripts\ditches.py -o C:\Users\anlr0006\repos-win\DOC_catchments\results\slu_sgu\ditches_merged_catchments.csv -c $input_file -r C:\Users\anlr0006\repos-win\DOC_catchments\input\Dikeskarta -gdb C:\Users\anlr0006\repos-win\DOC_catchments\results\arcpy_workspace\test.gdb -id $id

# conda deactivate #>