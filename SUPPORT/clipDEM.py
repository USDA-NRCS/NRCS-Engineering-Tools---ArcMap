## clipDEM.py
##
## Created by Peter Mead, Adolfo Diaz, USDA NRCS, 2013
## Updated by Chris Morse, USDA NRCS, 2019
##
## Clip a DEM to an area of interest

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
    f.write("\n##################################################################\n")
    f.write("Executing \"Clip DEM to AOI\" Tool" + "\n")
    f.write("User Name: " + getpass.getuser() + "\n")
    f.write("Date Executed: " + time.ctime() + "\n")
    f.write("ArcGIS Version: " + str(arcpy.GetInstallInfo()['Version']) + "\n")    
    f.write("User Parameters:\n")
    f.write("\tWorkspace: " + userWorkspace + "\n")
    f.write("\tInput DEM: " + inputDEM + "\n")
    f.write("\tOutput DEM: " + outputDEM + "\n")
    
    f.close
    del f

## ================================================================================================================
# Import system modules
import arcpy, sys, os, traceback

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

# Main - wrap everything in a try statement
try:
    # Check out Spatial Analyst License
    if arcpy.CheckExtension("Spatial") == "Available":
        arcpy.CheckOutExtension("Spatial")
    else:
        arcpy.AddError("\nSpatial Analyst Extension not enabled. Please enable Spatial Analyst from the Tools/Extensions menu. Exiting...\n")
        sys.exit()

    arcpy.SetProgressorLabel("Setting Variables")
    # --------------------------------------------------------------------- Input Parameters
    inputDEM = arcpy.GetParameterAsText(0)
    inMask = arcpy.GetParameterAsText(1)
    outputDEM = arcpy.GetParameterAsText(2)

    # --------------------------------------------------------------------- Directory Paths
    userWorkspace = os.path.dirname(os.path.realpath(outputDEM))
    demName = os.path.splitext(os.path.basename(outputDEM))[0]

    # log inputs and settings to file
    textFilePath = userWorkspace + os.sep + os.path.basename(userWorkspace).replace(" ","_") + "_EngTools.txt"
    logBasicSettings()
    
    # --------------------------------------------------------------------- Basic Checks before processing
    arcpy.SetProgressorLabel("Validating Inputs")
    AddMsgAndPrint("\nValidating Inputs...",0)
    
    # Exit if no AOI provided
    if not int(arcpy.GetCount_management(inMask).getOutput(0)) > 0:
        AddMsgAndPrint("\nNo area of interest was provided, you must digitize or select a mask. Exiting...",2)
        sys.exit()
        
    # Exit if AOI contains more than 1 digitized area.
    if int(arcpy.GetCount_management(inMask).getOutput(0)) > 1:
        AddMsgAndPrint("\nYou can only digitize one Area of Interest or provide a single feature. Please try again. Exiting...",2)
        sys.exit()
        
    # Exit if mask isn't a polygon
    if arcpy.Describe(inMask).ShapeType != "Polygon":
        AddMsgAndPrint("\nYour Area of Interest must be a polygon layer. Exiting...",2)
        sys.exit()

    # --------------------------------------------------------------------- Gather DEM Info
    arcpy.SetProgressorLabel("Gathering information about input DEM file")
    AddMsgAndPrint("\nInformation about input DEM file " + os.path.basename(inputDEM)+ ":",0)
    
    desc = arcpy.Describe(inputDEM)
    sr = desc.SpatialReference
    cellSize = desc.MeanCellWidth
    units = sr.LinearUnitName

    # Coordinate System must be a Projected type in order to continue.
    if sr.Type == "Projected":
        AddMsgAndPrint("\n\tInput Projection Name: " + sr.Name,0)
        AddMsgAndPrint("\tXY Linear Units: " + units,0)
        AddMsgAndPrint("\tCell Size: " + str(desc.MeanCellWidth) + " x " + str(desc.MeanCellHeight) + " " + units,0)
    else:
        AddMsgAndPrint("\n\n\t" + os.path.basename(inputDEM) + " is NOT in a Projected Coordinate System. Exiting...",2)
        sys.exit(0)

    # -------------------------------------------------------------------- Clip DEM to AOI
    arcpy.SetProgressorLabel("Clipping DEM to Area of Interest")
    AddMsgAndPrint("\nClipping DEM to Area of Interest...",0)
    
    maskedDEM = arcpy.sa.ExtractByMask(inputDEM, inMask)
    maskedDEM.save(outputDEM)
    
    AddMsgAndPrint("\n\tSuccessully Clipped " + os.path.basename(inputDEM) + " to Area of Interest!",0)

    # ------------------------------------------------------------------------------------------------ FIN!
    AddMsgAndPrint("\nProcessing Complete!\n",0)
    
    # -------------------------------------------------------------------- Cleanup
    arcpy.RefreshCatalog(userWorkspace)

# -----------------------------------------------------------------------------------------------------------------

except SystemExit:
    pass

except KeyboardInterrupt:
    AddMsgAndPrint("Interruption requested. Exiting...")

except:
    print_exception()   
