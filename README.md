# Wetness index based on landscape position and topography (WILT): Modifying TWI to reflect landscape position

An Arcpy script to calculate WILT - Wetness index based on landscape position and topography (WILT): Modifying TWI to reflect landscape position

## Requirements to run the script:

+ ArcGIS or the ability to run ArcPy scripts, I haven't been able to test this in ArcPro
+ Spatial Analyst extension enabled
+ 3D Analyst Extension enabled

## Instructions to run the tool in ArcGIS:

Please read the paper to fully understand the methods before trying to run the tool https://doi.org/10.1016/j.jenvman.2019.109863

+ Open Arc map
+ Navigate to and pen the WILT toolbox
+ Double click the WILT tool to open it
+ Provide points for water elevations (either streams or water bodies), a DEM, a workspace and file prefix
+ Click run
+ The resulting WILT raster has WILT at the end of the filename

## Notes:

+ If you run the tool multiple times you will need to delete the raster value field in the water points file.
+ Make sure the extensions are enabled.