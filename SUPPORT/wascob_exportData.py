## wascob_exportData.py
##
## Created by Peter Mead, USDA NRCS, 2013
## Updated by Chris Morse, USDA NRCS, 2020
##
## Exports WASCOB related data to shapefiles in PCS native to the project.

# ---------------------------------------------------------------------------
def print_exception():
    
    tb = sys.exc_info()[2]
    l = traceback.format_tb(tb)
    l.reverse()
    tbinfo = "".join(l)
    AddMsgAndPrint("\n----------ERROR Start-------------------\n",2)
    AddMsgAndPrint("Traceback Info: \n" + tbinfo + "Error Info: \n    " +  str(sys.exc_type)+ ": " + str(sys.exc_value) + "",2)
    AddMsgAndPrint("----------ERROR End-------------------- \n",2)

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
    f.write("\n################################################################################################################\n")
    f.write("Executing \"Wascob: Export Data\" Tool\n")
    f.write("User Name: " + getpass.getuser() + "\n")
    f.write("Date Executed: " + time.ctime() + "\n")
    f.write("ArcGIS Version: " + str(arcpy.GetInstallInfo()['Version']) + "\n")
    f.write("User Parameters:\n")
    f.write("\tInput Watershed: " + inWatershed + "\n")
    f.write("\tWorkspace: " + userWorkspace + "\n")   
    if len(outCoordsys) > 0:
        f.write("\tOutput Coord Sys: " + outCoordsys + "\n")
    else:
        f.write("\tOutput Coord Sys: BLANK\n") 
        
    f.close
    del f   

## ================================================================================================================
# Import system modules
import arcpy, sys, os, traceback, string

# Environment settings
arcpy.env.overwriteOutput = True

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
        
    # ---------------------------------------------- Input Parameters
    inWatershed = arcpy.GetParameterAsText(0)
    #outCoordsys = arcpy.GetParameterAsText(1)

    # ---------------------------------------------------------------------------- Define Variables 
    watershed_path = arcpy.Describe(inWatershed).CatalogPath
    watershedGDB_path = watershed_path[:watershed_path .find(".gdb")+4]
    watershedFD_path = watershedGDB_path + os.sep + "Layers"
    userWorkspace = os.path.dirname(watershedGDB_path)
    outputFolder = userWorkspace + os.sep + "gis_output"

    # Set path to log file and start logging
    textFilePath = userWorkspace + os.sep + os.path.basename(userWorkspace).replace(" ","_") + "_EngTools.txt"
    logBasicSettings()
   
    # ----------------------------------- Inputs to be converted to shp
    stationPoints = watershedFD_path + os.sep + "StationPoints"
    rStationPoints = watershedFD_path + os.sep + "RidgeStationPoints"
    tileLines = watershedFD_path + os.sep + "tileLines"
    ridgeLines = watershedFD_path + os.sep + "RidgeLines"
    stakeoutPoints = watershedFD_path + os.sep + "stakeoutPoints"
    referenceLines = watershedFD_path + os.sep + "ReferenceLine"

    # ----------------------------------- Possible Existing Feature Layers
    stations = "StationPoints"
    rstations = "RidgeStationPoints"
    tile = "TileLines"
    ridge = "RidgeLines"
    points = "StakeoutPoints"
    refLine = "Reference Line"
    
    # ------------------------ If lyrs present, clear any possible selections
    if arcpy.Exists(stations):
        arpcy.SelectLayerByAttribute_management(stations, "CLEAR_SELECTION", "")
    if arcpy.Exists(rstations):
        arpcy.SelectLayerByAttribute_management(rstations, "CLEAR_SELECTION", "")
    if arcpy.Exists(tile):
        arcpy.SelectLayerByAttribute_management(tile, "CLEAR_SELECTION", "")
    if arcpy.Exists(ridge):
        arcpy.SelectLayerByAttribute_management(ridge, "CLEAR_SELECTION", "")
    if arcpy.Exists(refLine):
        arcpy.SelectLayerByAttribute_management(refLine, "CLEAR_SELECTION", "")
    if arcpy.Exists(points):
        arcpy.SelectLayerByAttribute_management(points, "CLEAR_SELECTION", "")        

    # ----------------------------------------------------- Shapefile Outputs
    stationsOut = outputFolder + os.sep + "StationPoints.shp"
    rStationsOut = outputFolder + os.sep + "RidgeStationPoints.shp"
    tileOut = outputFolder + os.sep + "TileLines.shp"
    ridgeOut = outputFolder + os.sep + "RidgeLines.shp"
    pointsOut = outputFolder + os.sep + "StakeoutPoints.shp"
    linesOut = outputFolder + os.sep + "ReferenceLines.shp"

##    ### Too many variables for transforming to output coordinates. Provide a message advising the user to Project the outputs with standard ArcToolbox tools for projections. ###
##    # ---------------------------------- Set Parameters for Output Projection if necessary
##    change = False
##    if len(outCoordsys) > 0:
##        change = True
##        AddMsgAndPrint("\nSetting output coordinate system...",0)
##        tempCoordSys = gp.OutputCoordinateSystem
##        arcpy.env.outputCoordinateSystem = outCoordsys

    # ------------------------------------------------------------ Copy FC's to Shapefiles
    AddMsgAndPrint("\nCopying GPS layers to output Folder",0)
    if arcpy.Exists(stationPoints):
        arcpy.CopyFeatures_management(stationPoints, stationsOut)
    else:
        AddMsgAndPrint("\nUnable to find Station Points in project workspace. Copy failed. Export them manually.",1)
    if arcpy.Exists(rStationPoints):
        arcpy.CopyFeatures_management(rStationPoints, rStationsOut)
    else:
        AddMsgAndPrint("\nUnable to find Ridge Station Points in project workspace. Copy failed. Export them manually.",1)
    if arcpy.Exists(tileLines):
        arcpy.CopyFeatures_management(tileLines, tileOut)
    else:
        AddMsgAndPrint("\nUnable to find TileLines in project workspace. Copy failed. Export them manually.",1)
    if arcpy.Exists(ridgeLines):
        arcpy.CopyFeatures_management(ridgeLines, ridgeOut)
    else:
        AddMsgAndPrint("\nUnable to find Ridge Lines in project workspace. Copy failed. Export them manually.",1)
    if arcpy.Exists(stakeoutPoints):  
        arcpy.CopyFeatures_management(stakeoutPoints, pointsOut)
    else:
        AddMsgAndPrint("\nUnable to find stakeoutPoints in project workspace. Copy failed. Export them manually.",1)
    if arcpy.Exists(referenceLines):
        arcpy.CopyFeatures_management(referenceLines, linesOut)
    else:
        AddMsgAndPrint("\nUnable to find referenceLines in project workspace. Copy failed. Export them manually.",1)

    # --------------------------------------------------- Restore Environments if necessary
    AddMsgAndPrint("\nData was exported using the coordinate system of your project or DEM data!",0)
    AddMsgAndPrint("\nIf this coordinate system is not suitable for use with your GPS system, please use the ",0)
    AddMsgAndPrint("\nProject tool found in ArcToolbox under Data Management Tools, Projections and Transformations, ",0)
    AddMsgAndPrint("\nto re-project the exported data into a coordinate system suitable for your GPS system.\n",0)
    
    AddMsgAndPrint("\nProcessing Finished!",0)
        
except SystemExit:
    pass

except KeyboardInterrupt:
    AddMsgAndPrint("Interruption requested....exiting")

except:
    print_exception()
