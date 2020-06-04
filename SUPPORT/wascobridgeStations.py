## wascobridgeStations.py
## 
## Created by Matt Patton, USDA NRCS, 2016
## Revised by Chris Morse, USDA NRCS, 2020
##
## Creates points at user specified interval along digitized or provided lines,
## Derives stationing distances and XYZ values, providing Z values in feet,
## as well as interpolating the line(s) to 3d using the appropriate Zfactor.

# ---------------------------------------------------------------------------
def print_exception():
    
    tb = sys.exc_info()[2]
    l = traceback.format_tb(tb)
    l.reverse()
    tbinfo = "".join(l)
    AddMsgAndPrint("----------ERROR Start-------------------",2)
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
    f.write("Executing \"8. Wascob Ridge Layout and Profile\" tool")
    f.write("User Name: " + getpass.getuser() + "\n")
    f.write("Date Executed: " + time.ctime() + "\n")
    f.write("ArcGIS Version: " + str(arcpy.GetInstallInfo()['Version']) + "\n")
    f.write("User Parameters:\n")
    f.write("\tWorkspace: " + userWorkspace + "\n")
    f.write("\tInput Dem: " + arcpy.Describe(DEM_aoi).CatalogPath + "\n")
    f.write("\tInterval: " + str(interval) + "\n")
    
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

    # Check out 3D Analyst License        
    if arcpy.CheckExtension("3D") == "Available":
        arcpy.CheckOutExtension("3D")
    else:
        arcpy.AddError("3D Analyst Extension not enabled. Please enable 3D Analyst from the Tools/Extensions menu. Exiting...\n")
        sys.exit()

    #----------------------------------------------------------------------------------------- Input Parameters
    inWatershed = arcpy.GetParameterAsText(0)
    inputLine = arcpy.GetParameterAsText(1)
    interval = arcpy.GetParameterAsText(2)                
 
    # --------------------------------------------------------------------- Variables
    watershed_path = arcpy.Describe(inWatershed).CatalogPath
    watershedGDB_path = watershed_path[:watershed_path .find(".gdb")+4]
    watershedFD_path = watershedGDB_path + os.sep + "Layers"
    userWorkspace = os.path.dirname(watershedGDB_path)
    outputFolder = userWorkspace + os.sep + "gis_output"
    tables = outputFolder + os.sep + "tables"
    stakeoutPoints = watershedFD_path + os.sep + "stakeoutPoints"
    
    if not arcpy.Exists(outputFolder):
        arcpy.CreateFolder_management(userWorkspace, "gis_output")
    if not arcpy.Exists(tables):
        arcpy.CreateFolder_management(outputFolder, "tables") 

    DEM_aoi = watershedGDB_path + os.sep + os.path.basename(userWorkspace).replace(" ","_") + "_Project_DEM"    
    #DEM_aoi = watershedGDB_path + os.sep + "Project_DEM"
    zUnits = "Feet"

    # Set path to log file and start logging
    textFilePath = userWorkspace + os.sep + os.path.basename(userWorkspace).replace(" ","_") + "_EngTools.txt"
    logBasicSettings()
    
    # --------------------------------------------------------------------- Permanent Datasets
    outLine = watershedFD_path + os.sep + "RidgeLines"
    outPoints = watershedFD_path + os.sep + "RidgeStationPoints"
    pointsTable = tables + os.sep + "ridgestations.dbf"
    stakeoutTable = tables + os.sep + "ridgestakeoutPoints.dbf"
    outLineLyr = "RidgeLines"
    outPointsLyr = "RidgeStationPoints"

    # --------------------------------------------------------------------- Temp Datasets
    lineTemp = watershedFD_path + os.sep + "lineTemp"
    routes = watershedFD_path + os.sep + "routes"
    stationTable = watershedGDB_path + os.sep + "stationTable"
    stationEvents = watershedGDB_path + os.sep + "stationEvents"
    stationTemp = watershedFD_path + os.sep + "stations"
    stationLyr = "stations"
    stationBuffer = watershedFD_path + os.sep + "stationsBuffer"
    stationElev = watershedGDB_path + os.sep + "stationElev"
    
    # --------------------------------------------------------------------- Check some parameters
    AddMsgAndPrint("\nChecking inptus...",0)
    # Exit if interval not set propertly
    try:
        float(interval)
    except:
        AddMsgAndPrint("\tStation Interval was invalid; cannot set interpolation interval. Exiting...",2)
        sys.exit()
        
    interval = float(interval)
    
    if not arcpy.Exists(DEM_aoi):
        AddMsgAndPrint("\tMissing Project_DEM from FGDB. Can not perform raster analysis.",2)
        AddMsgAndPrint("\tProject_DEM must be in the same geodatabase as your input watershed.",2)
        AddMsgAndPrint("\tCheck your the source of your provided watershed. Exiting...",2)
        sys.exit()
    
    # ---------------------------------- Retrieve Raster Properties
    desc = arcpy.Describe(DEM_aoi)
    sr = desc.SpatialReference
    units = sr.LinearUnitName
    cellSize = desc.MeanCellWidth
    
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
        
    # zUnits are feet because we are using WASCOB project DEM
    # This Zfactor is used for expressing elevations from input data as feet, regardless of input z-units. But z-units are feet in this toolbox. Redundant.
    Zfactor = 1
    
    # ------------------------------------------------------------- Delete [previous toc lyrs if present
    # Copy the input line before deleting the TOC layer reference in case input line IS the previous line selected from the TOC
    arcpy.CopyFeatures_management(inputLine, lineTemp)
    
    if arcpy.Exists(outLineLyr):
        AddMsgAndPrint("\nRemoving previous layers from ArcMap",0)
        arcpy.Delete_management(outLineLyr)
    if arcpy.Exists(outPointsLyr):
        arcpy.Delete_management(outPointsLyr)

    # ------------------------------------------------------------- Copy input and create routes / points
    # Check for fields: if user input is previous line they will already exist
    if len(arcpy.ListFields(lineTemp,"ID")) < 1:
        arcpy.AddField_management(lineTemp, "ID", "LONG", "", "", "", "", "NULLABLE", "NON_REQUIRED", "")
    if len(arcpy.ListFields(lineTemp,"NO_STATIONS")) < 1:
        arcpy.AddField_management(lineTemp, "NO_STATIONS", "LONG", "", "", "", "", "NULLABLE", "NON_REQUIRED", "")
    if len(arcpy.ListFields(lineTemp,"FROM_PT")) < 1:
        arcpy.AddField_management(lineTemp, "FROM_PT", "LONG", "", "", "", "", "NULLABLE", "NON_REQUIRED", "")
    if len(arcpy.ListFields(lineTemp,"LENGTH_FT")) < 1:
        arcpy.AddField_management(lineTemp, "LENGTH_FT", "DOUBLE", "", "", "", "", "NULLABLE", "NON_REQUIRED", "")

    expression = "!shape.length@feet!"
    arcpy.CalculateField_management(lineTemp, "LENGTH_FT", expression, "PYTHON")
    del expression

    # Calculate number of stations / remainder
    AddMsgAndPrint("\nCalculating the number of stations",0)
    AddMsgAndPrint("\tStation Point interval: " + str(interval) + " Feet",0)
    rows = arcpy.UpdateCursor(lineTemp)
    row = rows.next()
    while row:
        row.ID = row.OBJECTID
        if row.LENGTH_FT < interval:
            AddMsgAndPrint("\tThe Length of line " + str(row.ID) + " is less ",2)
            AddMsgAndPrint("\tthan the specified interval of " + str(interval) + " feet.",2)
            AddMsgAndPrint("\tChoose a lower interval or supply a longer line. Exiting...",2)
            sys.exit()
        exp = row.LENGTH_FT / interval - 0.5 + 1
        row.NO_STATIONS = str(round(exp))
        row.FROM_PT = 0
        rows.updateRow(row)
        AddMsgAndPrint("\tLine " + str(row.ID) + " Total Length: " + str(int(row.LENGTH_FT)) + " Feet",0)
        AddMsgAndPrint("\tEquidistant stations (Including Station 0): " + str(row.NO_STATIONS),0)
        remainder = (row.NO_STATIONS * interval) - row.LENGTH_FT
        if remainder > 0:
            AddMsgAndPrint("\tPlus 1 covering the remaining " + str(int(remainder)) + " feet\n",0)

        row = rows.next()
        
    del row
    del rows
    del remainder

    # Create Table to hold station values
    arcpy.CreateTable_management(watershedGDB_path, "stationTable")
    arcpy.AddField_management(stationTable, "ID", "LONG", "", "", "", "", "NULLABLE", "NON_REQUIRED", "")
    arcpy.AddField_management(stationTable, "STATION", "LONG", "", "", "", "", "NULLABLE", "NON_REQUIRED", "")
    arcpy.AddField_management(stationTable, "POINT_X", "DOUBLE", "", "", "", "", "NULLABLE", "NON_REQUIRED", "")
    arcpy.AddField_management(stationTable, "POINT_Y", "DOUBLE", "", "", "", "", "NULLABLE", "NON_REQUIRED", "")    
    arcpy.AddField_management(stationTable, "POINT_Z", "DOUBLE", "", "", "", "", "NULLABLE", "NON_REQUIRED", "")

    # Calculate location for each station along the line
    rows = arcpy.SearchCursor(lineTemp)
    row = rows.next()
    while row:
        stations = row.NO_STATIONS
        length = int(row.LENGTH_FT)
        stationRows = arcpy.InsertCursor(stationTable)
        newRow = stationRows.newRow()
        newRow.ID = row.ID
        newRow.STATION = length
        stationRows.insertRow(newRow)
        currentStation = 0

        while currentStation < stations:
            newRow = stationRows.newRow()
            newRow.ID = row.ID
            newRow.STATION = currentStation * interval
            stationRows.insertRow(newRow)
            currentStation = currentStation + 1

        row = rows.next()

        del stationRows
        del newRow
    del row
    del rows

    # Create Route(s) lyr and define events along each route
    AddMsgAndPrint("\nCreating Stations...",0)
    arcpy.CreateRoutes_lr(lineTemp, "ID", routes, "TWO_FIELDS", "FROM_PT", "LENGTH_FT", "UPPER_LEFT", "1", "0", "IGNORE", "INDEX")
    arcpy.MakeRouteEventLayer_lr(routes, "ID", stationTable, "ID POINT STATION", stationEvents, "", "NO_ERROR_FIELD", "NO_ANGLE_FIELD", "NORMAL", "ANGLE", "LEFT", "POINT")
    arcpy.AddField_management(stationEvents, "STATIONID", "TEXT", "", "", "25", "", "NULLABLE", "NON_REQUIRED", "")  
    #gp.CalculateField_management(stationEvents, "STATIONID", "[STATION] & \"_\" & [ID]", "VB", "")
    arcpy.CalculateField_management(stationEvents, "STATIONID", "str(!STATION!) + '_' + str(!ID!)", "PYTHON")
    arcpy.CopyFeatures_management(stationEvents, stationTemp, "", "0", "0", "0")
    arcpy.AddXY_management(stationTemp)
    arcpy.AddField_management(stationTemp, "POINT_Z", "DOUBLE", "", "", "", "", "NULLABLE", "NON_REQUIRED", "")  
    arcpy.MakeFeatureLayer_management(stationTemp, stationLyr, "", "", "")
    AddMsgAndPrint("\tSuccessfuly created a total of " + str(int(arcpy.GetCount_management(stationLyr).getOutput(0))) + " stations",0)
    AddMsgAndPrint("\tfor the " + str(int(arcpy.GetCount_management(lineTemp).getOutput(0))) + " line(s) provided\n",0)

    # --------------------------------------------------------------------- Retrieve Elevation values
    AddMsgAndPrint("\nRetrieving station elevations...",0)
    
    # Buffer the stations the width of one raster cell / unit
    if units == "Meters":
        bufferSize = str(cellSize) + " Meters"
    elif units == "Feet":
        bufferSize = str(cellSize) + " Feet"
    else:
        bufferSize = str(cellSize) + " Unknown"
        
    arcpy.Buffer_analysis(stationTemp, stationBuffer, bufferSize, "FULL", "ROUND", "NONE", "")
    arcpy.sa.ZonalStatisticsAsTable(stationBuffer, "STATIONID", DEM_aoi, stationElev, "NODATA", "ALL")
    arcpy.AddJoin_management(stationLyr, "StationID", stationElev, "StationID", "KEEP_ALL")
    expression = "round(!stationElev.MEAN! * " + str(Zfactor) + ",1)"
    arcpy.CalculateField_management(stationLyr, "stations.POINT_Z", expression, "PYTHON")
    arcpy.RemoveJoin_management(stationLyr, "stationElev")
    arcpy.DeleteField_management(stationTemp, "STATIONID; POINT_M")
    del expression
    
    # ---------------------------------------------------------------------- Create final output
    # Interpolate Line to 3d via Z factor
    arcpy.InterpolateShape_3d (DEM_aoi, lineTemp, outLine, "", Zfactor)

    # Copy Station Points
    arcpy.CopyFeatures_management(stationTemp, outPoints)

    # Copy output to tables folder
    arcpy.CopyRows_management(outPoints, pointsTable, "")
    #arcpy.CopyRows_management(stakeoutPoints, stakeoutTable, "")   # Redundant to the wascobStations script. Doesn't do anything here.

    # ------------------------------------------------------------------- Delete Temp Layers
    AddMsgAndPrint("\nDeleting temporary files...",0)
    layersToRemove = (lineTemp,routes,stationTable,stationEvents,stationTemp,stationLyr,stationBuffer,stationElev)    

    x = 0
    for layer in layersToRemove:
        if arcpy.exists(layer):
            if x == 0:
                x+=1
            try:
                arcpy.Delete_management(layer)
            except:
                pass

    del x, layersToRemove
    
    # ------------------------------------------------------------------------------------------------ Compact FGDB
    arcpy.Compact_management(watershedGDB_path)
    AddMsgAndPrint("Successfully Compacted FGDB: " + os.path.basename(watershedGDB_path) + "\n",0)

    # ---------------------------------------------------------------- Create Layers and apply symbology
        
    AddMsgAndPrint("\nAdding Layers to ArcMap",0)
    arcpy.SetParameterAsText(3, outLine)    
    arcpy.SetParameterAsText(4, outPoints)

    AddMsgAndPrint("\nProcessing Complete!",0)

    # ---------------------------------------------------------------------------- Cleanup
    arcpy.RefreshCatalog(watershedGDB_path)
        
except SystemExit:
    pass

except KeyboardInterrupt:
    AddMsgAndPrint("Interruption requested....exiting")

except:
    print_exception()
