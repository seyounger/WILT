#-------------------------------------------------------------------
# Author:		Seth Younger
#-------------------------------------------------------------------
# Change log:
# 12/1/2020 - better names for outputs and more instructional informaiton
#-------------------------------------------------------------------

import os, time, sys
import arcpy
from arcpy import env, AddMessage
from arcpy.sa import *

class Toolbox(object):
  def __init__(self):
    """Define the toolbox (the name of the toolbox is the name of the
    .pyt file)."""
    self.label = "WILT Toolbox"
    self.alias = "WILT"

    # List of tool classes associated with this toolbox
    self.tools = [WILT, CTI]

class WILT(object):
  def __init__(self):
    """Define the tool (tool name is the name of the class)."""
    self.label      = "WILT"
    self.description  = 	"This tool uses a DEM and points representing surface water " + \
                "to calculate the Wetness Index Based on Landscape Position and Topography " + \
                "or WILT, which is described in Bitew et al. 2020." + \
                " https://doi.org/10.1016/j.jenvman.2019.109863. " + \
                "Note: The Spatial Analyst and 3D Analyst Extensions need to be activated. " + \
                "Water cell points need to be developed for your site using surface water locations, " + \
                "including lakes and streams. Well data can also be used where available. "

  def getParameterInfo(self):
    #Define parameter definitions
    WorkSpace = arcpy.Parameter(
      displayName="Select a folder to save outputs to",
      name="workSpace",
      datatype="DEWorkspace",
      parameterType="Required",
      direction="Input")

    WaterCells = arcpy.Parameter(
      displayName="Water Cell Points",
      name="WaterCells",
      datatype="GPFeatureLayer",
      parameterType="Required",
      direction="Input")
    
    WaterCells.filter.list = ["Point"]

    DEM = arcpy.Parameter(
      displayName="DEM",
      name="DEM",
      datatype="GPRasterLayer",
      parameterType="Required",
      direction="Input")

    prefix = arcpy.Parameter(
      displayName="Output file prefix",
      name="prefix",
      datatype="GPString",
      parameterType="Required",
      direction="Input")

    parameters = [WorkSpace, WaterCells, DEM, prefix]     

    return parameters

  def isLicensed(self): #optional
    """Allow the tool to execute, only if the ArcGIS 3D Analyst extension 
    is available."""
    try:
      if arcpy.CheckExtension("3D") != "Available":
        raise Exception
    except Exception:
      return False # tool cannot be executed

    return True # tool can be executed

    """Allow the tool to execute, only if the ArcGIS Spatial Analyst extension 
    is available."""
    try:
      if arcpy.CheckExtension("Spatial") != "Available":
        raise Exception
    except Exception:
      return False # tool cannot be executed

    return True # tool can be executed

  def updateParameters(self, parameters): #optional
    """Modify the values and properties of parameters before internal
    validation is performed.  This method is called whenever a parameter
    has been changed."""
    return

  def updateMessages(self, parameters):
    """Modify the messages created by internal validation for each tool
    parameter.  This method is called after internal validation."""
    return

  def execute(self, parameters, messages):
    # Check out any necessary licenses
    arcpy.CheckOutExtension("Spatial")
    arcpy.CheckOutExtension("3D")

    # Environment settings
    env.overwriteOutput = True
    
    # Define variables
    # Workspace from parameters
    env.workspace = parameters[0].valueAsText
    WaterCells = parameters[1].valueAsText
    DEM = parameters[2].valueAsText
    prefix = parameters[3].valueAsText
    # Define model created variables
    WaterElev = prefix + "WaterElev.shp"
    DEM_Points = prefix + "dem_points.shp"
    
    # Environment settings from the DEM
    env.extent = DEM
    env.cellSize = DEM
    # cellsize of the DEM as a float for calculations
    description = arcpy.Describe(DEM)
    size = description.children[0].meanCellHeight
    AddMessage("The DEM cell size is " + str(size) + " meters")

    # Execute Fill
    AddMessage("Filling DEM")
    FillDEM = Fill(DEM)

    # Execute Flow Direction
    AddMessage("Running Flow Direction tool")
    FlowDir = FlowDirection(FillDEM, "FORCE")

    # Execute Flow Accumulation
    AddMessage("Running Flow Accumulation Tool")
    FlowAcc = FlowAccumulation(FlowDir, "","INTEGER")

    # Calculate SCA
    AddMessage("Calculating Specific Contributing Area")
    sca = (FlowAcc + size) * (size * size)

    # Extract water cell elevation to points
    AddMessage("Running extract values to points tool")
    ExtractValuesToPoints(WaterCells, DEM, WaterElev, "INTERPOLATE", "VALUE_ONLY")

    # Krig water surface from water cell elevations
    AddMessage("Kriging water surface from water cell elevations")
    kModelOrdinary = KrigingModelOrdinary("SPHERICAL")
    kRadius = RadiusVariable(12)
    # Execute Kriging
    GroundwaterT2 = Kriging(WaterElev, "RASTERVALU", kModelOrdinary, env.cellSize, kRadius, "")
    GroundwaterT2.save(prefix + "GW_elev_from_streams.tif")

    # Calculate water table depth
    AddMessage("Calculating groundwater depth")
    waterTable = (DEM - GroundwaterT2)

    # Calculate water table depths less than 0.2 to 0.2, the rest stay the same
    AddMessage("Reclassify GW depths < 0.2m to 0.2m")
    waterTable2 = Con(waterTable < 0.2, 0.2, waterTable)
    waterTable2.save(prefix + "GW_depth.tif")

    # Convert DEM to Points
    arcpy.RasterToPoint_conversion(FillDEM, DEM_Points, "Value")
    AddMessage("Converting DEM to points")

    # Near distance between each DEM cell and water cells
    AddMessage("Calculating near distance to water cells")
    arcpy.Near_analysis(DEM_Points, WaterCells, "", "NO_LOCATION", "NO_ANGLE")

    # Convert near distance to raster
    AddMessage("Converting near distance to raster")
    DeltaX = arcpy.PointToRaster_conversion(DEM_Points, "NEAR_DIST")

    # Calculate Delta X's less than 5 to 5, the rest stay the same
    AddMessage("Running Con on near distance raster")
    deltaX5 = Con(DeltaX < 5,5, DeltaX)

    # ScaGWX
    AddMessage("Calculating scaGWX")
    scaGWX = sca / (waterTable2 * deltaX5)

    # Calculate Slope
    AddMessage("Calculating Slope")
    slope = Slope(FillDEM, "DEGREE", 1)

    # Convert Slope from degrees to Radians
    AddMessage("Converting slope from degrees to radians")
    slopeRadians = (slope * 0.0174532925)

    # Calculate TAN of Slope
    arcpy.AddMessage("Calculating Tan of slope")
    TanSlope = Tan(slopeRadians)

    # Calculate TanSlope's of 0 to 0.001, the rest stay the same
    AddMessage("Running Con on TanSlope")
    TanSlope_0 = Con(TanSlope  <=  0,0.001, TanSlope)

    # Calculate SCAGW
    AddMessage("Calculating SCAGW")
    SCAGW = sca / waterTable2

    # Calculate WILT using sqrt(dx^2+dy^2)
    AddMessage("Calculating WILT")
    #sqrt(waterTable2^2+deltaX5^2)
    dx2 = Power(waterTable2, 2)
    dy2 = Power(deltaX5, 2)
    dy_dx_plus = Plus(dx2, dy2)
    dy_dx_sqrt = SquareRoot(dy_dx_plus)
    scaGWX2 = sca / dy_dx_sqrt
    WILT = Ln(scaGWX2 / TanSlope_0)
    AddMessage("Saving WILT")
    WILTG.save(prefix + "WILT.tif")

    # Check in any necessary licenses
    arcpy.CheckInExtension("Spatial")
    arcpy.CheckInExtension("3D")


#---------------------------------------------------------------------------
# Compound topographic wetness index
#---------------------------------------------------------------------------
class CTI(object):
  def __init__(self):
    """Define the tool (tool name is the name of the class)."""
    self.label      =     "CTI"
    self.description  =   "Calculates the compound topographic index (CTI) or 'soil wetness' transformation. https://wikispaces.psu.edu/display/AnthSpace/Compound+Topographic+Index"

  def getParameterInfo(self):
    #Define parameter definitions
    WorkSpace = arcpy.Parameter(
      displayName="Select a folder to save outputs to",
      name="workSpace",
      datatype="DEWorkspace",
      parameterType="Required",
      direction="Input")

    DEM = arcpy.Parameter(
      displayName="DEM",
      name="DEM",
      datatype="GPRasterLayer",
      parameterType="Required",
      direction="Input")

    CTI = arcpy.Parameter(
      displayName="Output CTI",
      name="CTI",
      datatype="GPRasterLayer",
      parameterType="Required",
      direction="Output")

    prefix = arcpy.Parameter(
      displayName="Output file prefix",
      name="prefix",
      datatype="GPString",
      parameterType="Required",
      direction="Input")

    parameters = [WorkSpace, DEM, CTI, prefix]     

    return parameters

  def isLicensed(self): #optional
    """Allow the tool to execute, only if the ArcGIS 3D Analyst extension 
    is available."""
    try:
      if arcpy.CheckExtension("3D") != "Available":
        raise Exception
    except Exception:
      return False # tool cannot be executed

    return True # tool can be executed

    """Allow the tool to execute, only if the ArcGIS Spatial Analyst extension 
    is available."""
    try:
      if arcpy.CheckExtension("Spatial") != "Available":
        raise Exception
    except Exception:
      return False # tool cannot be executed

    return True # tool can be executed

  def updateParameters(self, parameters): #optional
    """Modify the values and properties of parameters before internal
    validation is performed.  This method is called whenever a parameter
    has been changed."""
    return

  def updateMessages(self, parameters):
    """Modify the messages created by internal validation for each tool
    parameter.  This method is called after internal validation."""
    return

  def execute(self, parameters, messages):
    # Check out any necessary licenses
    arcpy.CheckOutExtension("Spatial")

    # Environment settings
    env.overwriteOutput = True

    # Define variables
    # Workspace from parameters
    env.workspace = parameters[0].valueAsText
    DEM = parameters[1].valueAsText
    CTI = parameters[2].valueAsText
    prefix = parameters[3].valueAsText

    # Environment settings from the DEM
    env.extent = DEM
    env.cellSize = DEM    
    # cellsize of the DEM as a float for calculations
    description = arcpy.Describe(DEM)
    size = description.children[0].meanCellHeight
    area = (size * size)
    AddMessage("The DEM cell size is " + str(size) + " meters")
    AddMessage("The DEM cell area is " + str(area) + " square meters")

    #Set message about running and run the calculation
    AddMessage("Running CTI")
    fd = FlowDirection(DEM)
    sca = FlowAccumulation(fd)
    slope = ( Slope(DEM) * 1.570796 ) / 90
    tan_slp = Con( slope > 0, Tan(slope), 0.001 )
    corr_sca = ( sca + 1 ) * size
    CTI = Ln ( corr_sca / tan_slp )
    CTI.save (parameters[2].valueAsText)

    #Set message about running
    AddMessage("CTI Complete")  
    
    # Check in any necessary licenses
    arcpy.CheckInExtension("Spatial")
