## wascobAddPoints.py
##
## Created by Peter Mead, USDA NRCS, 2013
## Updated by Chris Morse, USDA NRCS, 2020
##
## Adds Points to WASCOB Tile Station Points
##
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
    f.write("Executing \"Wascob Add Points to Profile\" tool")
    f.write("User Name: " + getpass.getuser() + "\n")
    f.write("Date Executed: " + time.ctime() + "\n")
    f.write("ArcGIS Version: " + str(arcpy.GetInstallInfo()['Version']) + "\n")
    f.write("User Parameters:\n")
    f.write("\tWorkspace: " + userWorkspace + "\n")
    f.write("\tInput Stations: " + str(stationPoints) + "\n")
    
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

    #------------------------------------------------------------------ Input Parameters
    stationPoints = arcpy.GetParameterAsText(0)
    inPoints = arcpy.GetParameterAsText(1)

    # ----------------------------------------------------------------- Variables
    watershed_path = arcpy.Describe(stationPoints).CatalogPath
    watershedGDB_path = watershed_path[:watershed_path .find(".gdb")+4]
    watershedFD_path = watershedGDB_path + os.sep + "Layers"
    userWorkspace = os.path.dirname(watershedGDB_path)
    outputFolder = userWorkspace + os.sep + "gis_output"
    tables = outputFolder + os.sep + "tables"

    DEM_aoi = watershedGDB_path + os.sep + os.path.basename(userWorkspace).replace(" ","_") + "_Project_DEM"
    #DEM_aoi = watershedGDB_path + os.sep + "Project_DEM"
    tileLines = watershedFD_path + os.sep + "tileLines"

    # Set path to log file and start logging
    textFilePath = userWorkspace + os.sep + os.path.basename(userWorkspace).replace(" ","_") + "_EngTools.txt"
    logBasicSettings()
    
    if not arcpy.Exists(outputFolder):
        arcpy.CreateFolder_management(userWorkspace, "gis_output")
    if not arcpy.Exists(tables):
        arcpy.CreateFolder_management(outputFolder, "tables") 
    
    # ---------------------------------------------------------------- Permanent Datasets
    pointsTable = tables + os.sep + "stations.dbf"
    stations = watershedFD_path + os.sep + "stationPoints"

    # ---------------------------------------------------------------- Lyrs to ArcMap
    outPointsLyr = "StationPoints"
    
    # ---------------------------------------------------------------- Temporary Datasets
    pointsNear = watershedGDB_path + os.sep + "pointsNear"
    linesNear = watershedGDB_path + os.sep + "linesNear"   
    pointsTemp = watershedFD_path + os.sep + "pointsTemp"
    pointsLyr = "pointsLyr"
    stationTemp = watershedFD_path + os.sep + "stations"
    stationTable = watershedGDB_path + os.sep + "stationTable"
    routes = watershedFD_path + os.sep + "routes"
    stationEvents = watershedGDB_path + os.sep + "stationEvents"
    station_lyr = "stations"
    stationLyr = "stationLyr"
    stationBuffer = watershedFD_path + os.sep + "stationsBuffer"
    stationElev = watershedGDB_path + os.sep + "stationElev"
    outlets = watershedFD_path + os.sep + "tileOutlets"
    
    # -------------------------------------------------------------- Create Temp Point(s)
    arcpy.CopyFeatures_management(inPoints, pointsTemp, "", "0", "0", "0")
    
    AddMsgAndPrint("\nChecking inputs...",0)

    # Exit if no TileLines
    if not arcpy.Exists(tileLines):
        if arcpy.Exists("TileLines"):
            tileLines = "TileLines"
        else:
            AddMsgAndPrint("\tTile Lines Feature Class not found in same directory as Station Points ",2)
            AddMsgAndPrint("\tor in Current ArcMap Document. Unable to compute Stationing.",2)
            AddMsgAndPrint("\tCheck the source of your inputs and try again. Exiting...",2)
            sys.exit()
            
    # Exit if no Project DEM
    if not arcpy.Exists(DEM_aoi):
        AddMsgAndPrint("\tMissing Project_DEM from FGDB. Can not perform raster analysis.",2)
        AddMsgAndPrint("\tProject_DEM must be in the same geodatabase as your input watershed.",2)
        AddMsgAndPrint("\tCheck your the source of your provided watershed. Exiting...",2)
        sys.exit()
        
    # Exit if no points were digitized
    count = int(arcpy.GetCount_management(pointsTemp).getOutput(0))
    if count < 1:
        AddMsgAndPrint("\tNo points provided. You must use the Add Features tool to create",2)
        AddMsgAndPrint("\tat least one point to add to the stations. Exiting...",2)
        sys.exit()
    else:
        AddMsgAndPrint("\nAdding " + str(count) + " station(s) to existing station points...",0)

    # Add Fields as necessary
    if len(arcpy.ListFields(pointsTemp,"ID")) < 1:
        arcpy.AddField_management(pointsTemp, "ID", "LONG", "", "", "", "", "NULLABLE", "NON_REQUIRED", "")
    if len(arcpy.ListFields(pointsTemp,"STATION")) < 1:
        arcpy.AddField_management(pointsTemp, "STATION", "LONG", "", "", "", "", "NULLABLE", "NON_REQUIRED", "")
    if len(arcpy.ListFields(pointsTemp,"POINT_X")) < 1:
        arcpy.AddField_management(pointsTemp, "POINT_X", "DOUBLE", "", "", "", "", "NULLABLE", "NON_REQUIRED", "")
    if len(arcpy.ListFields(pointsTemp,"POINT_Y")) < 1:
        arcpy.AddField_management(pointsTemp, "POINT_Y", "DOUBLE", "", "", "", "", "NULLABLE", "NON_REQUIRED", "")    
    if len(arcpy.ListFields(pointsTemp,"POINT_Z")) < 1:
        arcpy.AddField_management(pointsTemp, "POINT_Z", "DOUBLE", "", "", "", "", "NULLABLE", "NON_REQUIRED", "")
    if len(arcpy.ListFields(pointsTemp,"STATIONID")) < 1:
        arcpy.AddField_management(pointsTemp, "STATIONID", "TEXT", "", "", "25", "", "NULLABLE", "NON_REQUIRED", "")

    # ---------------------------------- Retrieve Raster Properties
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
    
    # --------------------------------------------------------------- Find Nearest Tile Line
    AddMsgAndPrint("\nFinding Nearest Tile Line(s)...",0)
    arcpy.GenerateNearTable_analysis(pointsTemp, tileLines, linesNear, "", "NO_LOCATION", "NO_ANGLE", "ALL", "1")

    # Populate Tile ID in new Points
    rows = arcpy.SearchCursor(linesNear)
    row = rows.next()

    while row:
        pointID = row.IN_FID
        tileID = row.NEAR_FID
        whereclause = "OBJECTID = " + str(pointID)
        expression = "\"ID\" = " + str(tileID) + " AND \"STATION\" = 0"
        # Select each point corresponding "0utlet"
        arcpy.SelectLayerByAttribute_management(stationPoints, "NEW_SELECTION", expression)
        pointRows = arcpy.UpdateCursor(pointsTemp,whereclause)
        pointRow = pointRows.next()           

        # Pass the nearest Tile Line to temp points.
        while pointRow:
            pointRow.ID = tileID
            pointRows.updateRow(pointRow)

            break

        row = rows.next()        

        del pointID
        del tileID
        del whereclause
        del pointRows
        del pointRow

    del rows
    del row

    arcpy.Delete_management(linesNear)

    # -------------------------------------------------------------------- Find Distance from point "0" along each tile line
    # Clear any selected points 
    arcpy.SelectLayerByAttribute_management(stationPoints, "CLEAR_SELECTION", "")
    # Select each point "0"
    arcpy.SelectLayerByAttribute_management(stationPoints, "NEW_SELECTION", "\"STATION\" = 0")
    # Create layer from selection
    arcpy.MakeFeatureLayer_management(stationPoints, station_lyr, "", "", "")
    
    AddMsgAndPrint("\nCalculating station distance(s)...",0)    
    arcpy.GenerateNearTable_analysis(pointsTemp, station_lyr, pointsNear, "", "NO_LOCATION", "NO_ANGLE", "ALL", "1")
    arcpy.SelectLayerByAttribute_management(stationPoints, "CLEAR_SELECTION", "")

    # Calculate stations in new Points
    rows = arcpy.SearchCursor(pointsNear)
    row = rows.next()

    while row:
        pointID = row.IN_FID
        distance = row.NEAR_DIST
        if units == "Meters":
            station = int(distance * 3.280839896)
        else:
            station = int(distance)
            
        whereclause = "OBJECTID = " + str(pointID)
        pointRows = arcpy.UpdateCursor(pointsTemp,whereclause)
        pointRow = pointRows.next()           

        # Pass the station distance to temp points.
        while pointRow:
            pointRow.STATION = station
            pointRows.updateRow(pointRow)

            break

        row = rows.next()        

        del pointID, distance, station, whereclause, pointRows, pointRow

    del rows
    del row

    arcpy.Delete_management(pointsNear)

    arcpy.RefreshCatalog(watershedGDB_path)

    # ------------------- Append to Existing
    arcpy.Append_management(pointsTemp, stationPoints, "NO_TEST", "", "")
    arcpy.CopyRows_management(stationPoints, stationTable)
    arcpy.Delete_management(stationPoints)

    AddMsgAndPrint("\nCreating new stations...",0)
    arcpy.CreateRoutes_lr(tileLines, "ID", routes, "TWO_FIELDS", "FROM_PT", "LENGTH_FT", "UPPER_LEFT", "1", "0", "IGNORE", "INDEX")
    arcpy.MakeRouteEventLayer_lr(routes, "ID", stationTable, "ID POINT STATION", stationEvents, "", "NO_ERROR_FIELD", "NO_ANGLE_FIELD", "NORMAL", "ANGLE", "LEFT", "POINT")
    arcpy.AddField_management(stationEvents, "STATIONID", "TEXT", "", "", "25", "", "NULLABLE", "NON_REQUIRED", "")
    #gp.CalculateField_management(stationEvents, "STATIONID", "[STATION] & \"_\" & [ID]", "VB", "")
    arcpy.CalculateField_management(stationEvents, "STATIONID", "str(!STATION!) + '_' + str(!ID!)", "PYTHON")
    arcpy.CopyFeatures_management(stationEvents, stationTemp, "", "0", "0", "0")

    arcpy.Delete_management(stationTable)
    arcpy.Delete_management(routes)
    
    # ------------------------------ Add X/Y Cordinates
    arcpy.AddXY_management(stationTemp)
    arcpy.AddField_management(stationTemp, "POINT_Z", "DOUBLE", "", "", "", "", "NULLABLE", "NON_REQUIRED", "")  
    arcpy.MakeFeatureLayer_management(stationTemp, stationLyr, "", "", "")
    AddMsgAndPrint("\n\tSuccessfuly added a total of " + str(count) + " stations",0)
    del count

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
    expression = "round(!stationElev.MEAN!,1)"
    arcpy.CalculateField_management(stationLyr, "stations.POINT_Z", expression, "PYTHON")
    arcpy.RemoveJoin_management(stationLyr, "stationElev")
    arcpy.DeleteField_management(stationTemp, "STATIONID; POINT_M")
    del expression

    AddMsgAndPrint("\n\tSuccessfully added elevation values",0)    
    arcpy.Delete_management(stationElev)
    arcpy.Delete_management(stationBuffer)

    # --------------------------------------------------------------------------- Copy Station Output to FD
    if arcpy.Exists(stations):
        arcpy.Delete_management(stations)
    AddMsgAndPrint("\nSaving output...",0)
    arcpy.CopyFeatures_management(stationTemp, stations, "", "0", "0", "0")

    arcpy.Delete_management(stationTemp)
    arcpy.Delete_management(pointsTemp)

    # ----------------------------------------------------------------------------- Copy output to tables folder
    # Delete existing points Table
    AddMsgAndPrint("\nUpdating Station Table...",0)
    if arcpy.Exists(pointsTable):
        arcpy.Delete_management(pointsTable)
    # Copy output to dbf for import        
    arcpy.CopyRows_management(stations, pointsTable, "")
    
    # ------------------------------------------------------------------------------------------------ Compact FGDB
    arcpy.Compact_management(watershedGDB_path)
    AddMsgAndPrint("\nSuccessfully Compacted FGDB: " + os.path.basename(watershedGDB_path) + "\n",0)

    # ---------------------------------------------------------------- Create Layers and apply symbology
    AddMsgAndPrint("\nAdding Output to ArcMap",0)  
    arcpy.SetParameterAsText(2, stations)

    AddMsgAndPrint("\nProcessing Complete!\n",0)
    # ---------------------------------------------------------------------------- Cleanup
    arcpy.RefreshCatalog(watershedGDB_path)

except SystemExit:
    pass

except KeyboardInterrupt:
    AddMsgAndPrint("Interruption requested....exiting")

except:
    print_exception() 
    
