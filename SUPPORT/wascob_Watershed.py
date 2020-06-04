## Wascob_Watershed.py
##
## Created by Peter Mead, Adolfo Diaz, USDA NRCS, 2013
## Updated by Chris Morse, USDA, 2020
##
## Create watershed(s) for WASCOB basins

## ================================================================================================================ 
def print_exception():
    
    tb = sys.exc_info()[2]
    l = traceback.format_tb(tb)
    l.reverse()
    tbinfo = "".join(l)
    AddMsgAndPrint("\n----------------------------------- ERROR Start -----------------------------------",2)
    AddMsgAndPrint("Traceback Info:\n" + tbinfo + "Error Info:\n    " +  str(sys.exc_type)+ ": " + str(sys.exc_value) + "",2)
    AddMsgAndPrint("------------------------------------- ERROR End -----------------------------------\n",2)

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
        
        if severity == 0:
            arcpy.AddMessage(msg)
        elif severity == 1:
            arcpy.AddWarning(msg)
        elif severity == 2:
            arcpy.AddError(msg)
            
    except:
        pass

## ================================================================================================================
def logBasicSettings():    
    # record basic user inputs and settings to log file for future purposes

    import getpass, time

    f = open(textFilePath,'a+')
    f.write("\n################################################################################################################\n")
    f.write("Executing \"Wascob Create Watershed\" tool\n")
    f.write("User Name: " + getpass.getuser() + "\n")
    f.write("Date Executed: " + time.ctime() + "\n")
    f.write("ArcGIS Version: " + str(arcpy.GetInstallInfo()['Version']) + "\n")
    f.write("User Parameters:\n")
    f.write("\tWorkspace: " + userWorkspace + "\n")
    f.write("\tStreams: " + streamsPath + "\n")
    
    if int(arcpy.GetCount_management(outlet).getOutput(0)) > 0:
        f.write("\tReference Lines Digitized: " + str(arcpy.GetCount_management(outlet)) + "\n")
    else:
        f.write("\tReference Lines Digitized: 0\n")
        
    f.write("\tWatershed Name: " + watershedOut + "\n")
        
    f.close
    del f

## ================================================================================================================
def determineOverlap(outletsLayer):
    # This function will evaluate the input outlets vs the updated project outlets layer by comparing counts.
    # Returns true if there are outlets within the AOI, or false if there are not.

    try:
        numOfOutlets = int((arcpy.GetCount_management(outlet)).getOutput(0))
        numOfOutletsWithinAOI = int((arcpy.GetCount_management(outletsLayer)).getOutput(0))
        if numOfOutletsWithinAOI > 0:
            if numOfOutlets == numOfOutletsWithinAOI:
                AddMsgAndPrint("\tAll outlets are within the project area of interest.",0)
                AddMsgAndPrint("\tAll outlets will be used for processing.",0)
                return True
            else:
                AddMsgAndPrint("\tSome input outlets are within the project area of interest!",0)
                AddMsgAndPrint("\tOutlets that are within the area of interest will be used for processing!",0)
                return True
        else:
            AddMsgAndPrint("\tAll outlets are outside of the project area of interest!",1)
            AddMsgAndPrint("\tCannot complete Wascob Watershed Tool!",1)
            return False
    except:
        AddMsgAndPrint("\nError in determineOverlap function.",1)
        return False

## ================================================================================================================
def splitThousands(someNumber):
# will determine where to put a thousands seperator if one is needed.
# Input is an integer.  Integer with or without thousands seperator is returned.

    try:
        return re.sub(r'(\d{3})(?=\d)', r'\1,', str(someNumber)[::-1])[::-1]
    except:
        print_exception()
        return someNumber

## ================================================================================================================
##                                      Main Body
## ================================================================================================================
# Import system modules
import sys, os, string, traceback, re

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
        sys.exit("")

    # Script Parameters
    streams = arcpy.GetParameterAsText(0)
    outlet = arcpy.GetParameterAsText(1)
    userWtshdName = "Watershed"
##    createFlowPaths = arcpy.GetParameterAsText(3)

##    if string.upper(createFlowPaths) <> "TRUE":
##        calcLHL = False
##    else:
##        calcLHL = True
        
    # --------------------------------------------------------------------------------------------- Define Variables
    streamsPath = arcpy.Describe(streams).CatalogPath

    if streamsPath.find('.gdb') > 0 and streamsPath.find('_Streams') > 0:
        watershedGDB_path = streamsPath[:streamsPath.find(".gdb")+4]
    else:
        arcpy.AddError("\n\n" + streams + " is an invalid Stream Network project layer")
        arcpy.AddError("Please run the Create Stream Network tool.\n\n")
        sys.exit("")
    
    userWorkspace = os.path.dirname(watershedGDB_path)
    watershedGDB_name = os.path.basename(watershedGDB_path)
    watershedFD = watershedGDB_path + os.sep + "Layers"
    projectName = arcpy.ValidateTableName(os.path.basename(userWorkspace).replace(" ","_"))
    projectAOI = watershedFD + os.sep + projectName + "_AOI"

    # --------------------------------------------------------------- Datasets
    # ------------------------------ Permanent Datasets
    watershed = watershedFD + os.sep + (arcpy.ValidateTableName(userWtshdName, watershedFD))
    FlowAccum = watershedGDB_path + os.sep + "flowAccumulation"
    FlowDir = watershedGDB_path + os.sep + "flowDirection"
    DEM_aoi = watershedGDB_path + os.sep + projectName + "_Raw_DEM"
    DEMsmooth = watershedGDB_path + os.sep + "_DEMsmooth"
    ProjectDEM = watershedGDB_path + os.sep + projectName + "_Project_DEM"
    outletFC = watershedFD + os.sep + "ReferenceLine"

    # ---------------------------------------------------------------------------------------------- Temporary Datasets
    outletBuffer = watershedGDB_path + os.sep + "Layers" + os.sep + "outletBuffer"
    pourPointGrid = watershedGDB_path + os.sep + "PourPoint"
    snapPourPoint = watershedGDB_path + os.sep + "snapPourPoint"
    watershedGrid = watershedGDB_path + os.sep + "watershedGrid"
    watershedTemp = watershedGDB_path + os.sep + "watershedTemp"
    watershedDissolve = watershedGDB_path + os.sep + "watershedDissolve"
    wtshdDEMsmooth = watershedGDB_path + os.sep + "wtshdDEMsmooth"
    slopeGrid = watershedGDB_path + os.sep + "slopeGrid"
    slopeStats = watershedGDB_path + os.sep + "slopeStats"
    # Wascob Additions
    outletStats = watershedGDB_path + os.sep + "outletStats"
    clippedOutlets = watershedGDB_path + os.sep + "Layers" + os.sep + projectName + "_clippedOutlets"
    # Features in Arcmap
    watershedOut = "" + os.path.basename(watershed) + ""
    outletOut = "" + os.path.basename(outletFC) + ""

    # Set path of log file and start logging
    textFilePath = userWorkspace + os.sep + projectName + "_EngTools.txt"
    logBasicSettings()

    # ---------------------------------------------------------------------------------------------- Check some parameters
    AddMsgAndPrint("\nChecking inputs and project data...",0)
    # Make sure the FGDB and streams exists from step 1 and 2
    if not arcpy.Exists(watershedGDB_path) or not arcpy.Exists(streamsPath):
        AddMsgAndPrint("\tThe \"Streams\" Feature Class or the File Geodatabase from Step 1 was not found!",2)
        AddMsgAndPrint("\tPlease run the Define AOI and the Create Stream Network tools in the WASCOB toolset.",2)
        AddMsgAndPrint("\tExiting...",2)
        sys.exit(0)

    # Must have one pour points manually digitized
    if not int(arcpy.GetCount_management(outlet).getOutput(0)) > 0:
        AddMsgAndPrint("\tAt least one pour point must be used! None detected.",2)
        AddMsgAndPrint("\tExiting...",2)
        sys.exit(0)
    else:
        outletsExist = True

    # Outlets must be polyline or line
    if arcpy.Describe(outlet).ShapeType != "Polyline":
        if arcpy.Describe(outlet).ShapeType != "Line":
            AddMsgAndPrint("\tOutlets must be a Line or Polyline layer!",2)
            AddMsgAndPrint("\tExiting...",2)
            sys.exit()

    # Project DEM must be present to proceed
    if not arcpy.Exists(ProjectDEM):
        AddMsgAndPrint("\tProject DEM was not found in " + watershedGDB_path,2)
        AddMsgAndPrint("\tPlease run the Define AOI and the Create Stream Network tools from the WASCOB toolset.",2)
        AddMsgAndPrint("\tExiting...",2)
        sys.exit(0)

    # Flow Accumulation grid must be present to proceed
    if not arcpy.Exists(FlowAccum):
        AddMsgAndPrint("\tFlow Accumulation Grid was not found in " + watershedGDB_path,2)
        AddMsgAndPrint("\tPlease run the Create Stream Network tool.",2)
        AddMsgAndPrint("\tExiting...",2)
        sys.exit(0)

    # Flow Direction grid must be present to proceed
    if not arcpy.Exists(FlowDir):
        AddMsgAndPrint("\tFlow Direction Grid was not found in " + watershedGDB_path,2)
        AddMsgAndPrint("\tPlease run the Create Stream Network tool.",2)
        AddMsgAndPrint("\tExiting...",2)
        sys.exit(0)

    # -------------------------------------------- Update Outlets
    # Determine if outlets overlap AOI, checking for previous outlets and new outlets
    if outletsExist:
        AddMsgAndPrint("\nProcessing input outlets data...",0)
        # if paths are not the same then the outlets are new input
        if not arcpy.Describe(outlet).CatalogPath == outletFC:
            AddMsgAndPrint("\tInput outlets data is new. Updating outlets project data...",0)
            # delete the outlet feature class; new one will be created            
            if arcpy.Exists(outletFC):
                try:
                    arcpy.Delete_management(outletFC)
                    #arcpy.CopyFeatures_management(outlet, outletFC)
                    AddMsgAndPrint("\nRemoved previous outlets project data.",0)                
                except:
                    print_exception()
            # Create new updated outlets layer from new input by clipping to AOI (instead of copying)
            arcpy.Clip_analysis(outlet, projectAOI, outletFC)
            AddMsgAndPrint("\tSuccessfully created new outlets data for project.",0)
        # paths are the same therefore input IS pour point
        else:
            AddMsgAndPrint("\tUsing existing outlets project data...",0)
            # Clip existing outlets in case the AOI was redone and moved in the same project folder.
            arcpy.Clip_analysis(outlet, projectAOI, clippedOutlets)
            arcpy.Delete_management(outletFC)
            arcpy.Rename_management(clippedOutlets, outletFC)
            AddMsgAndPrint("\tSuccessfully re-created outlets data for project.",0)

    AddMsgAndPrint("\nChecking Placement of Reference Line(s)...",0)
    proceed = False
    if determineOverlap(outletFC):
        proceed = True
    else:
        arcpy.Delete_management(outletFC)
        AddMsgAndPrint("\tNo outlets exist within the project AOI.",2)
        AddMsgAndPrint("\tPlease digitize or use an outlets layer that is within the AOI.",2)
        AddMsgAndPrint("\tExiting...",2)
        sys.exit()
        
    # ------------------------------------- Delete previous layers from ArcMap if they exist
    layersToRemove = (watershedOut,outletOut)

    x = 0
    for layer in layersToRemove:
        if arcpy.Exists(layer):
            if x == 0:
                AddMsgAndPrint("\nRemoving previous layers from your ArcMap session " + watershedGDB_name ,0)
                x+=1
            try:
                arcpy.Delete_management(layer)
                AddMsgAndPrint("\tRemoving " + layer + "",0)
            except:
                pass
    del layersToRemove, x
    
    # ---------------------------------------------------------------------------------------------- Delete old datasets
    # dropped outletFC from the remove list on 1/11/2018. It would cause problems with the Create New Outlet sequence
    datasetsToRemove = (watershed,outletBuffer,pourPointGrid,snapPourPoint,watershedGrid,watershedTemp,wtshdDEMsmooth,slopeGrid,slopeStats,outletStats)

    x = 0
    for dataset in datasetsToRemove:
        if arcpy.Exists(dataset):
            if x < 1:
                AddMsgAndPrint("\nRemoving old datasets from FGDB: " + watershedGDB_name ,0)
                x += 1
            try:
                arcpy.Delete_management(dataset)
                AddMsgAndPrint("\tDeleting..." + os.path.basename(dataset),0)
            except:
                pass
    del datasetsToRemove, x

    # ---------------------------------------------------------------------------------------------- Create Watershed
    # ---------------------------------- Retrieve Raster Properties
    desc = arcpy.Describe(FlowDir)
    sr = desc.SpatialReference
    units = sr.LinearUnitName
    cellSize = desc.MeanCellWidth
    
    if units == "Meter":
        units = "Meters"
    elif units == "Foot":
        units = "Feet"
    elif units == "Foot_US":
        units = "Feet"

    # --------------------------------------------------------------------- Attribute Embankement(s)        
    # Add Attribute Fields to Reference Line(s)
    if len(arcpy.ListFields(outletFC,"Subbasin")) < 1:
        arcpy.AddField_management(outletFC, "Subbasin", "LONG", "", "", "", "", "NULLABLE", "NON_REQUIRED", "")
    if len(arcpy.ListFields(outletFC,"MaxElev")) < 1:
        arcpy.AddField_management(outletFC, "MaxElev", "DOUBLE", "", "", "", "", "NULLABLE", "NON_REQUIRED", "")
    if len(arcpy.ListFields(outletFC,"MinElev")) < 1:
        arcpy.AddField_management(outletFC, "MinElev", "DOUBLE", "", "", "", "", "NULLABLE", "NON_REQUIRED", "")    
    if len(arcpy.ListFields(outletFC,"MeanElev")) < 1:
        arcpy.AddField_management(outletFC, "MeanElev", "DOUBLE", "", "", "", "", "NULLABLE", "NON_REQUIRED", "")
    if len(arcpy.ListFields(outletFC,"LengthFt")) < 1:
        arcpy.AddField_management(outletFC, "LengthFt", "DOUBLE", "", "", "", "", "NULLABLE", "NON_REQUIRED", "")

    # Populate Subbasin Field and Calculate embankment length       
    arcpy.CalculateField_management(outletFC, "Subbasin","!OBJECTID!", "PYTHON")
    arcpy.CalculateField_management(outletFC, "LengthFt","!shape.length@feet!", "PYTHON")
    
    # Buffer outlet features by  raster cell size - dissolving by Subbasin ID
    bufferSize = cellSize * 2
    bufferDist = "" + str(bufferSize) + " " + str(units) + ""    
    arcpy.Buffer_analysis(outletFC, outletBuffer, bufferDist, "FULL", "ROUND", "LIST", "Subbasin")
    del bufferSize, bufferDist

    # Get Reference Line Elevation Properties (Uses ProjectDEM, which is vertical feet by 1/10ths)
    AddMsgAndPrint("\nCalculating Reference Line Attributes...",0)
    arcpy.sa.ZonalStatisticsAsTable(outletBuffer, "Subbasin", ProjectDEM, outletStats, "DATA")
    
    rows = arcpy.SearchCursor(outletStats)
    row = rows.next()

    while row:
        wtshdID = row.OBJECTID

        # zonal stats doesnt generate "Value" with the 9.3 geoprocessor
        if len(arcpy.ListFields(outletStats,"Value")) > 0:
            zonalValue = row.VALUE
        else:
            zonalValue = row.SUBBASIN

        zonalMaxValue = row.MAX   
        zonalMeanValue = row.MEAN
        zonalMinValue = row.MIN

        whereclause = "Subbasin = " + str(zonalValue)
        refRows = arcpy.UpdateCursor(outletFC,whereclause)
        refRow = refRows.next()           

        # Pass the elevation Data to Reference Line FC.
        while refRow:
            refRow.MaxElev = zonalMaxValue
            refRow.MinElev = zonalMinValue
            refRow.MeanElev = round(zonalMeanValue,1)
            refRows.updateRow(refRow)
            
            break

        row = rows.next()        

        del wtshdID
        del zonalValue
        del zonalMeanValue
        del zonalMaxValue
        del zonalMinValue
        del whereclause
        del refRows
        del refRow

    del rows
    del row

    arcpy.Delete_management(outletStats)

    # --------------------------------------------------------------------- Delineate Watershed(s) from Reference Lines
    # Convert buffered outlet Feature to Raster Pour Point.
    arcpy.MakeFeatureLayer_management(outletBuffer,"outletBufferLyr")       # <--- Is this step actually needed?
    arcpy.PolygonToRaster_conversion("outletBufferLyr","Subbasin",pourPointGrid,"MAXIMUM_AREA","NONE",cellSize)
    # Delete intermediate data
    arcpy.Delete_management(outletBuffer)
    arcpy.Delete_management("outletBufferLyr")
    
    # ------------------------------------------------------------------ Create Watershed Raster using the raster pour point
    AddMsgAndPrint("\nDelineating watershed(s)...",0)
    # Update extent environment prior to delineation so watersheds actually create correctly
    arcpy.env.extent = "MAXOF"
    tempShed = arcpy.sa.Watershed(FlowDir,pourPointGrid,"VALUE")
    tempShed.save(watershedGrid)
    
    # ------------------------------------------------------------------- Convert results to simplified polygon
    try:
        # --------------------------------------------- Convert to watershed grid to a polygon feature class
        arcpy.RasterToPolygon_conversion(watershedGrid,watershedTemp,"SIMPLIFY","VALUE")
    except:
        if arcpy.Exists(watershedTemp):
            try:
                arcpy.MakeFeatureLayer_management(watershedTemp,"wtshdTempLyr")
            except:
                print_exception
        else:
            AddMsgAndPrint("\n" + arcpy.GetMessages(2),2)
            sys.exit()
            
    # -------------------------------------------------  Dissolve watershedTemp by GRIDCODE or grid_code
    if len(arcpy.ListFields(watershedTemp,"GRIDCODE")) > 0:
        arcpy.Dissolve_management(watershedTemp, watershedDissolve, "GRIDCODE", "", "MULTI_PART", "DISSOLVE_LINES")
    else:
        arcpy.Dissolve_management(watershedTemp, watershedDissolve, "grid_code", "", "MULTI_PART", "DISSOLVE_LINES")

    # Copy Results to watershedFD
    arcpy.CopyFeatures_management(watershedDissolve, watershed)    
    AddMsgAndPrint("\tSuccessfully Created " + str(int(arcpy.GetCount_management(watershed).getOutput(0))) + " Watershed(s) from " + str(outletOut),0)

    # Delete unwanted datasets
    if arcpy.Exists(watershedTemp):
        arcpy.Delete_management(watershedTemp)
    arcpy.Delete_management(watershedDissolve)    
    arcpy.Delete_management(pourPointGrid)
    arcpy.Delete_management(watershedGrid)

    # -------------------------------------------------------------------------------------------------- Add and Calculate fields
    # Add Subbasin Field in watershed and calculate it to be the same as GRIDCODE
    arcpy.AddField_management(watershed, "Subbasin", "LONG", "", "", "", "", "NULLABLE", "NON_REQUIRED", "")

    if len(arcpy.ListFields(watershed,"GRIDCODE")) > 0:
        arcpy.CalculateField_management(watershed, "Subbasin", "!GRIDCODE!", "PYTHON")
        arcpy.DeleteField_management(watershed, "GRIDCODE")
    else:
        arcpy.CalculateField_management(watershed, "Subbasin", "!grid_code!", "PYTHON")
        arcpy.DeleteField_management(watershed, "grid_code")
    
    # Add Acres Field in watershed and calculate them and notify the user
    displayAreaInfo = False

    arcpy.AddField_management(watershed, "Acres", "DOUBLE", "", "", "", "", "NULLABLE", "NON_REQUIRED", "")
    expression = "!shape.area@acres!"
    arcpy.CalculateField_management(watershed, "Acres", expression, "PYTHON")
    displayAreaInfo = True

    # ----------------------------------------------------------------------------------------------- Calculate Average Slope
    calcAvgSlope = False

    # zUnits are feet because we are using the ProjectDEM in this practice workflow path for WASCOBs   
    if units == "Feet":
        Zfactor = 1
    if units == "Meters":
        Zfactor = 0.3048                  
        
    # ------------------------------------------------------- Add slope attributes to watershed basins
    AddMsgAndPrint("\nCalculating average slope...",0)

    # Always re-create DEMsmooth in case people jumped from Watershed workflow to WASCOB workflow somehow and base on ProjectDEM in this WASCOB toolset
    arcpy.Delete_management(DEMsmooth)
        
    # Run Focal Statistics on the ProjectDEM for the purpose of generating smoothed results.
    tempFocal = arcpy.sa.FocalStatistics(ProjectDEM, "RECTANGLE 3 3 CELL","MEAN","DATA")
    tempFocal.save(DEMsmooth)
        
    # Add Avg_Slope field to watershed layer
    arcpy.AddField_management(watershed, "Avg_Slope", "DOUBLE", "", "", "", "", "NULLABLE", "NON_REQUIRED", "")

    # Extract area for slope from DEMSmooth and compute statistics for it
    tempWtshDEM = arcpy.sa.ExtractByMask(DEMsmooth, watershed)
    tempWtshDEM.save(wtshdDEMsmooth)
    
    tempSlope = arcpy.sa.Slope(wtshdDEMsmooth, "PERCENT_RISE", Zfactor)
    tempSlope.save(slopeGrid)
    
    arcpy.sa.ZonalStatisticsAsTable(watershed, "Subbasin", slopeGrid, slopeStats, "DATA")
    calcAvgSlope = True

    # Delete unwanted rasters
    arcpy.Delete_management(DEMsmooth)
    arcpy.Delete_management(wtshdDEMsmooth)
    arcpy.Delete_management(slopeGrid)

    # -------------------------------------------------------------------------------------- Update Watershed FC with Average Slope
    if calcAvgSlope:
        
        # go through each zonal Stat record and pull out the Mean value
        rows = arcpy.SearchCursor(slopeStats)
        row = rows.next()

        AddMsgAndPrint("\nSuccessfully Calculated Average Slope",0)

        AddMsgAndPrint("\n===================================================",0)
        AddMsgAndPrint("\tUser Watershed: " + str(watershedOut),0)
        
        while row:
            wtshdID = row.OBJECTID

            # zonal stats doesnt generate "Value" with the 9.3 geoprocessor in 10
            if len(arcpy.ListFields(slopeStats,"Value")) > 0:
                zonalValue = row.VALUE
            else:
                zonalValue = row.SUBBASIN
                
            zonalMeanValue = row.MEAN

            whereclause = "Subbasin = " + str(zonalValue)
            wtshdRows = arcpy.UpdateCursor(watershed,whereclause)
            wtshdRow = wtshdRows.next()           

            # Pass the Mean value from the zonalStat table to the watershed FC.
            while wtshdRow:
                wtshdRow.Avg_Slope = zonalMeanValue
                wtshdRows.updateRow(wtshdRow)

                # Inform the user of Watershed Acres, area and avg. slope
                if displayAreaInfo:
                    
                    # Inform the user of Watershed Acres, area and avg. slope
                    AddMsgAndPrint("\n\tSubbasin: " + str(wtshdRow.OBJECTID),0)
                    AddMsgAndPrint("\t\tAcres: " + str(splitThousands(round(wtshdRow.Acres,2))),0)
                    AddMsgAndPrint("\t\tArea: " + str(splitThousands(round(wtshdRow.Shape_Area,2))) + " Sq. " + units,0)
                    AddMsgAndPrint("\t\tAvg. Slope: " + str(round(zonalMeanValue,2)),0)
                    if wtshdRow.Acres > 40:
                        AddMsgAndPrint("\t\tSubbasin " + str(wtshdRow.OBJECTID) + " is greater than the 40 acre 638 standard.",1)
                        AddMsgAndPrint("\t\tConsider re-delineating to split basins or move upstream.",1)

                else:
                    AddMsgAndPrint("\tSubbasin " + str(wtshdRow.OBJECTID) + " Avg. Slope: " + str(zonalMeanValue) + "%",0)
                    
                break

            row = rows.next()        

            del wtshdID
            del zonalValue
            del zonalMeanValue
            del whereclause
            del wtshdRows
            del wtshdRow

        del rows
        del row
        AddMsgAndPrint("\n===================================================",0)
        arcpy.Delete_management(slopeStats)
    
    # ------------------------------------------------------------------------------------------------ Compact FGDB
    try:
        arcpy.Compact_management(watershedGDB_path)
        AddMsgAndPrint("\nCompacted FGDB: " + os.path.basename(watershedGDB_path),0)    
    except:
        pass

    # ------------------------------------------------------------------------------------------------ Prepare to Add to Arcmap
    # Set paths for derived layers
    arcpy.SetParameterAsText(2, outletFC)
    arcpy.SetParameterAsText(3, watershed)

    AddMsgAndPrint("\nAdding Layers to ArcMap",0)

    # --------------------------------------------------------------------------------------------------- Cleanup
    arcpy.RefreshCatalog(watershedGDB_path)
    
except SystemExit:
    pass

except KeyboardInterrupt:
    AddMsgAndPrint("Interruption requested....exiting")

except:
    print_exception()
