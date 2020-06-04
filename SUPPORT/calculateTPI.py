## calculateTPI.py
##
## Created by Peter Mead MN USDA NRCS, 2013
## Updated by Chris Morse, USDA NRCS, 2020
##
## Creates A Topographic Position Index for an area of interest.
#
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
    f.write("Executing \"Topographic Position Index\" Tool \n")
    f.write("User Name: " + getpass.getuser() + " \n")
    f.write("Date Executed: " + time.ctime() + " \n")
    f.write("ArcGIS Version: " + str(arcpy.GetInstallInfo()['Version']) + "\n")
    f.write("User Parameters:\n")
    f.write(" \tWorkspace: " + userWorkspace + " \n")   
    f.write(" \tInput DEM: " + DEM_aoi + " \n")
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
    inWatershed = arcpy.GetParameterAsText(1)
        
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

    # Set path to log file and start logging
    textFilePath = userWorkspace + os.sep + projectName + "_EngTools.txt"
    logBasicSettings()    

    # ---------------------------------- Datasets -------------------------------------------
    # -------------------------------------------------------------------- Temporary Datasets
    smoothDEM = watershedGDB_path + os.sep + "smoothDEM"
    DEMclip = watershedGDB_path + os.sep + "DEMclip"
    
    # -------------------------------------------------------------------- Permanent Datasets
    tpiOut = watershedGDB_path + os.sep + projectName + "_TPI"
        
    #-------------------------------------------------------------------- Get Raster Properties
    AddMsgAndPrint("\nGathering information about " + os.path.basename(DEM_aoi)+ ":",0) 
    desc = arcpy.Describe(DEM_aoi)
    sr = desc.SpatialReference
    units = sr.LinearUnitName
    cellSize = desc.MeanCellWidth
 
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
        
    # Print / Display DEM properties    
    AddMsgAndPrint("\tProjection Name: " + sr.Name,0)
    AddMsgAndPrint("\tXY Linear Units: " + units,0)
    AddMsgAndPrint("\tCell Size: " + str(desc.MeanCellWidth) + " x " + str(desc.MeanCellHeight) + " " + units,0)

    # ---------------------------------------------------------------------------- If user provided a mask clip inputs first.
    if clip:
        # Clip inputs to input Mask
        AddMsgAndPrint("\nClipping Input DEM to " + str(os.path.basename(inWatershed)) + "...",0) 
        tempMask = arcpy.sa.ExtractByMask(DEM_aoi, inWatershed)
        tempMask.save(DEMclip)
        AddMsgAndPrint("\tSuccessfully clipped " + str(os.path.basename(DEM_aoi)),0)  
        
        # Reset path to DEM
        DEM_aoi = DEMclip

    # --------------------------------------------------------------------------------- Create TPI
    AddMsgAndPrint("\nCalculating Topographic Position Index...",0)
    
    if not arcpy.Exists(smoothDEM):        
        # Smooth the DEM to generalize cell transitions
        AddMsgAndPrint("\tSmoothing the DEM...",0)    
        tempFocal = arcpy.sa.FocalStatistics(DEM_aoi, "RECTANGLE 3 3 CELL","MEAN","DATA")
        tempFocal.save(smoothDEM)

    # Subtract the original surface to create tpi
    AddMsgAndPrint("\tSubtracting original surface...",0)
    #gp.Minus_sa(smoothDEM, DEM_aoi, tpiOut)
    tempMinus = arcpy.sa.Minus(smoothDEM, DEM_aoi)
    tempMinus.save(tpiOut)
        
    AddMsgAndPrint("\n\tSuccessfully determined topographic cell positions...",0)

    # --------------------------------------------------------------------------------- Delete intermediate data
    datasetsToRemove = (smoothDEM,DEMclip)

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
    AddMsgAndPrint("\nAdding results to ArcMap...",0)
    
    arcpy.SetParameterAsText(2, tpiOut)
    
    AddMsgAndPrint("\tOverlay the results with a hillshade to best view cell transitions",0)

    AddMsgAndPrint("\nProcessing Complete!",0)
    
    #--------------------------------------------------------------------- Take care of Some HouseKeeping....
    arcpy.RefreshCatalog(watershedGDB_path)

except SystemExit:
    pass

except KeyboardInterrupt:
    AddMsgAndPrint("Interruption requested....exiting")

except:
    print_exception()    
