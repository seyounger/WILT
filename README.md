# Wetness index based on landscape position and topography (WILT): Modifying TWI to reflect landscape position

An Arcpy script to calculate WILT - Wetness index based on landscape position and topography (WILT): Modifying TWI to reflect landscape position

## Requirements:

+ ArcGIS or the ability to run ArcPy scripts
+ Spatial analyst extension enabeled
+ 3D Analyst Extension enabeled

## Instructions:

Please read the paper to fully understand the methods before trying to run the tool https://doi.org/10.1016/j.jenvman.2019.109863

+ Open Arc map and open the WILT toolbox
+ Double click the WILT tool to open it
+ Provide points for water elevations (either streams or water bodies), a DEM, and a workplace
+ Click run

## Notes:

If you run the tool multiple times you will need to delete the raster value field in the water points file.

Make sure the extensions are enabeled.