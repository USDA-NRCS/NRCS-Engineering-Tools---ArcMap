## calculateCTI.py
##
## Created by Peter Mead MN USDA NRCS, 2013
## Updated by Chris Morse, USDA NRCS, 2020
##
## Creates A Compound Topographic Index for an area of interest.

## ================================================================================================================ 
def print_exception():
    
    tb = sys.exc_info()[2]
    l = traceback.format_tb(tb)
    l.reverse()
    tbinfo = "".join(l)
    AddMsgAndPrint(" \n----------ERROR Start------------------- \n",2)
    AddMsgAndPrint("Traceback Info:  \n" + tbinfo + "Error Info:  \n    " +  str(sys.exc_type)+ ": " + str(sys.exc_value) + "",2)
    AddMsgAndPrint("----------ERROR End--------------------  \n",2)

## ================================================================================================================    
def AddMsgAndPrint(msg, severity=0):
    # prints message to screen if run as a python script
    # Adds tool message to the geoprocessor
    # Split the message on  \n first, so that if it's multiple lines, a GPMessage will be added for each line

    print(msg)
    
    try:
        f = open(textFilePath,'a+')
        f.write(msg + " \n")
        f.close
        del f
    except:
        pass
    
    if severity == 0:
        arcpy.AddMessage(msg)
    elif severity == 1:
        arcpy.AddWarning(msg)
    elif severity == 2:
        arcpy.AddError(msg)

## ================================================================================================================
def logBasicSettings():    
    # record basic user inputs and settings to log file for future purposes

    import getpass, time

    f = open(textFilePath,'a+')
    f.write(" \n################################################################################################################ \n")
    f.write("Executing \"Compound Topographic Index\" tool \n")
    f.write("User Name: " + getpass.getuser() + " \n")
    f.write("Date Executed: " + time.ctime() + " \n")
    f.write("ArcGIS Version: " + str(arcpy.GetInstallInfo()['Version']) + "\n")
    f.write("User Parameters:\n")
    f.write(" \tWorkspace: " + userWorkspace + " \n")   
    f.write(" \tInput DEM: " + DEM_aoi + " \n")
    f.write(" \tInput Flow Accumulation Grid: " + FlowAccum + " \n")
    if len(zUnits) < 1:
        f.write(" \tInput Z Units: BLANK \n")
    else:
        f.write(" \tInput Z Units: " + str(zUnits) + " \n")
    if len(inWatershed) > 0:
        f.write(" \tClipping set to mask: " + inWatershed + " \n")
    else:
        f.write(" \tClipping: NOT SELECTED\n") 
        
    f.close
    del f

## ================================================================================================================
# Import system modules
import arcpy, sys, os, string, traceback

# Environment settings
arcpy.env.overwriteOutput = True
arcpy.env.geographicTransformations = "WGS_1984_(ITRF00)_To_NAD_1983"
arcpy.env.resamplingMethod = "BILINEAR"
arcpy.env.pyramid = "PYRAMIDS -1 BILINEAR DEFAULT 75 NO_SKIP"

### Version check
##version = str(arcpy.GetInstallInfo()['Version'])
##if version.find("10.") > 0:
##    ArcGIS10 = True
##else:
##    ArcGIS10 = False
#### Convert version string to a float value (needed for numeric comparison)
##versionFlt = float(version[0:4])
##if versionFlt < 10.5:
##    arcpy.AddError("\nThis tool requires ArcGIS version 10.5 or greater. Exiting...\n")
##    sys.exit()        

try:
    # Check out Spatial Analyst License        
    if arcpy.CheckExtension("Spatial") == "Available":
        arcpy.CheckOutExtension("Spatial")
    else:
        arcpy.AddError("Spatial Analyst Extension not enabled. Please enable Spatial analyst from the Tools/Extensions menu. Exiting...\n")
        sys.exit()

    # -------------------------------------------------------------------------------------------- Input Parameters
    DEM_aoi = arcpy.GetParameterAsText(0)
    zUnits = arcpy.GetParameterAsText(1)
    inWatershed = arcpy.GetParameterAsText(2)
        
    if len(inWatershed) > 0:
        clip = True
    else:
        clip = False
        
    # --------------------------------------------------------------------- Define Variables
    DEMpath = arcpy.Describe(DEM_aoi).CatalogPath
    # AOI DEM must be from a engineering tools file geodatabase
    if not DEMpath.find('_EngTools.gdb') > -1:
        arcpy.AddError("\n\nInput AOI DEM is not in a \"xx_EngTools.gdb\" file geodatabase.")
        arcpy.AddError("\n\nYou must provide a DEM prepared with the Define Area of Interest Tool. Exiting...")
        sys.exit()
        
    watershedGDB_path = DEMpath[:DEMpath.find(".gdb")+4]
    userWorkspace = os.path.dirname(watershedGDB_path)
    watershedGDB_name = os.path.basename(watershedGDB_path)
    projectName = arcpy.ValidateTableName(os.path.basename(userWorkspace).replace(" ","_"))

    # ---------------------------------- Datasets -------------------------------------------
    # -------------------------------------------------------------------- Temporary Datasets
    smoothDEM = watershedGDB_path + os.sep + "smoothDEM"
    ctiTemp = watershedGDB_path + os.sep + "ctiTemp"
    DEMclip = watershedGDB_path + os.sep + "DEMclip"
    FACclip = watershedGDB_path + os.sep + "FACclip"
    FDRclip = watershedGDB_path + os.sep + "FDRclip"
    
    # -------------------------------------------------------------------- Permanent Datasets
    Slope = watershedGDB_path + os.sep + projectName + "_Slope"    
    ctiOut = watershedGDB_path + os.sep + projectName + "_CTI"

    # -------------------------------------------------------------------- Required Existing Inputs
    FlowAccum = watershedGDB_path + os.sep + "flowAccumulation"

    # Set path to log file and start logging
    textFilePath = userWorkspace + os.sep + projectName + "_EngTools.txt"
    logBasicSettings()

    # ------------------------------------------------------------------- Check some parameters
    # Flow Accum and Flow Dir must be in project gdb
    if not arcpy.Exists(FlowAccum):
        AddMsgAndPrint("\n\nFlow Accumulation grid not found in same directory as " + str(os.path.basename(DEM_aoi)) + " (" + watershedGDB_path + "/" + watershedGDB_name + ")",2)
        AddMsgAndPrint("\nYou Must run the \"Create Stream\" Network Tool to create Flow Direction/Accumulation Grids. Exiting...\n",2)
        sys.exit()
        
    #-------------------------------------------------------------------- Get Raster Properties
    AddMsgAndPrint("\nGathering information about " + os.path.basename(DEM_aoi)+ ":",0)
    desc = arcpy.Describe(DEM_aoi)
    sr = desc.SpatialReference
    units = sr.LinearUnitName
    cellSize = desc.MeanCellWidth
    cellArea = cellSize * cellSize

    # Set horizontal units variable
    if sr.Type == "Projected":
        if units == "Meter" or units == "Meters":
            units = "Meters"
        elif units == "Foot" or units == "Feet" or units == "Foot_US":
            units = "Feet"
        else:
            AddMsgAndPrint("\tHorizontal DEM units could not be determined. Please use a projected DEM with meters or feet for horizontal units. Exiting...",2)
            sys.exit()
    else:
        AddMsgAndPrint("\t" + os.path.basename(DEM_aoi) + " is NOT in a Projected Coordinate System. Exiting...",2)
        sys.exit(0)
        
    # Set Z Factor for slope calculations    
    if zUnits == "Meters":
        if units == "Feet":
            Zfactor = 3.280839896
        if units == "Meters":
            Zfactor = 1
    elif zUnits == "Feet":           
        if units == "Feet":
            Zfactor = 1
        if units == "Meters":
            Zfactor = 0.3048                  
    elif zUnits == "Centimeters":   
        if units == "Feet":
            Zfactor = 0.03280839896
        if units == "Meters":
            Zfactor = 0.01
    elif zUnits == "Inches":
        if units == "Feet":
            Zfactor = 0.0833333
        if units == "Meters":
            Zfactor = 0.0254
        
    # Print / Display DEM properties    
    AddMsgAndPrint("\tProjection Name: " + sr.Name,0)
    AddMsgAndPrint("\tXY Linear Units: " + units,0)
    AddMsgAndPrint("\tElevation Values (Z): " + zUnits,0) 
    AddMsgAndPrint("\tCell Size: " + str(desc.MeanCellWidth) + " x " + str(desc.MeanCellHeight) + " " + units,0)

    # ---------------------------------------------------------------------------- If user provided a mask clip inputs first.
    if clip:
        # Clip inputs to input Mask
        AddMsgAndPrint("\nClipping Grids to " + str(os.path.basename(inWatershed)) + "...",0)
        tempMask = arcpy.sa.ExtractByMask(DEM_aoi, inWatershed)
        tempMask.save(DEMclip)
        AddMsgAndPrint("\tSuccessfully clipped " + str(os.path.basename(DEM_aoi)),0)
        
        tempMask2 = arcpy.sa.ExtractByMask(FlowAccum, inWatershed)
        tempMask2.save(FACclip)
        AddMsgAndPrint("\tSuccessfully clipped Flow Accumulation",0)
        
        # Reset paths to DEM and Flow Accum
        DEM_aoi = DEMclip
        FlowAccum = FACclip

    # --------------------------------------------------------------------------------- Calculate Slope Grid
    if not arcpy.Exists(Slope):
        AddMsgAndPrint("\nPreparing Slope Grid using a Z-Factor of " + str(Zfactor) + "",0)
        if not arcpy.Exists(smoothDEM):
            # Smooth the DEM to remove imperfections in drop
            AddMsgAndPrint("\tSmoothing the DEM...",0)    
            tempFocal = arcpy.sa.FocalStatistics(DEM_aoi, "RECTANGLE 3 3 CELL","MEAN","DATA")
            tempFocal.save(smoothDEM)

        # Calculate percent slope with proper Z Factor (create in Degrees to convert to radians for CTI)
        AddMsgAndPrint("\tCalculating percent slope...",0)
        tempSlope = arcpy.sa.Slope(smoothDEM, "DEGREE", Zfactor)
        tempSlope.save(Slope)
                       
    # --------------------------------------------------------------------------------- Create and Filter CTI
    # Calculate CTI
    AddMsgAndPrint("\nCalculating Compound Topographic Index...",0)
    #gp.SingleOutputMapAlgebra_sa("Ln((\""+str(FlowAccum)+"\" + 0.001) / (\""+str(Slope)+"\" / 100 + 0.001))", ctiTemp)

    # Updated formula (6/4/2020) is: ln(((flow accumulation + 1)*cellize)/(tan(slope))), where slope is in radians

    # Compute numerator
    ras1 = arcpy.sa.Raster(FlowAccum)
    ras2 = (ras1 + 1)*cellSize

    # Convert slope to radians
    ras3 = arcpy.sa.Raster(Slope)
    ras4 = (ras3 * 1.570796)/90

    # Compute denominator
    tan_ras4 = arcpy.sa.Con(ras4 > 0, arcpy.sa.Tan(ras4), 0.001)

    # Compute CTI
    tempSOMA = arcpy.sa.Ln(ras2/tan_ras4)
    tempSOMA.save(ctiTemp)
    AddMsgAndPrint("\n\tFiltering index values...",0)

    # Set Values < 0 to null
    conStatement = "Value <= 0"
    tempNull = arcpy.sa.SetNull(ctiTemp, ctiTemp, conStatement)
    tempNull.save(ctiOut)

    # --------------------------------------------------------------------------------- Delete intermediate data           
    datasetsToRemove = (smoothDEM,ctiTemp,DEMclip,FACclip)

    x = 0
    for dataset in datasetsToRemove:
        if arcpy.Exists(dataset):
            if x == 0:
                AddMsgAndPrint(" \nDeleting Temporary Data...",0)
                x += 1
            try:
                arcpy.Delete_management(dataset)
            except:
                pass
            
    del x, datasetsToRemove
    
    # ----------------------------------------------------------------------- Compact FGDB
    try:
        arcpy.Compact_management(watershedGDB_path)
        AddMsgAndPrint("\nSuccessfully Compacted FGDB: " + os.path.basename(watershedGDB_path),0)    
    except:
        pass

    # ------------------------------------------------------------ Prepare to Add to Arcmap
    arcpy.SetParameterAsText(3, ctiOut)    

    #----------------------------------------------------------------------- Finished!
    AddMsgAndPrint("\nProcessing Completed!",0)
    
    #--------------------------------------------------------------------- Take care of Some HouseKeeping....
    arcpy.RefreshCatalog(watershedGDB_path)

except SystemExit:
    pass

except KeyboardInterrupt:
    AddMsgAndPrint("Interruption requested....exiting")

except:
    print_exception()    
