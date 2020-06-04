# Create_Watershed.py
##
## Created by Peter Mead, Adolfo Diaz, USDA NRCS, 2013
## Updated by Chris Morse, USDA, 2020
##
## Create watershed(s) from interactively input pour points (lines intersecting project's "streams")

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
    f.write("Executing \"Create Watershed\" tool\n")
    f.write("User Name: " + getpass.getuser() + "\n")
    f.write("Date Executed: " + time.ctime() + "\n")
    f.write("ArcGIS Version: " + str(arcpy.GetInstallInfo()['Version']) + "\n")
    f.write("User Parameters:\n")
    f.write("\tWorkspace: " + userWorkspace + "\n")
    f.write("\tStreams: " + streamsPath + "\n")
    
    if int(arcpy.GetCount_management(outlet).getOutput(0)) > 0:
        f.write("\tOutlets Digitized: " + str(arcpy.GetCount_management(outlet)) + "\n")
    else:
        f.write("\tOutlets Digitized: 0\n")
        
    f.write("\tWatershed Name: " + watershedOut + "\n")
    if calcLHL:    
        f.write("\tCreate flow paths: SELECTED\n")
    else:
        f.write("\tCreate flow paths: NOT SELECTED\n")
        
    f.close
    del f

## ================================================================================================================
def determineOverlap(outletsLayer):
    # This function will compute a geometric intersection of the project_AOI boundary and the outlet
    # layer to determine overlap.

    try:
        # Make a layer from the project_AOI
        if arcpy.Exists("AOI_lyr"):
            arcpy.Delete_management("AOI_lyr")

        arcpy.MakeFeatureLayer_management(projectAOI,"AOI_lyr")

        if arcpy.Exists("outletsTempLyr"):
            arcpy.Delete_management("outletsTempLyr")

        arcpy.MakeFeatureLayer_management(outletsLayer,"outletsTempLyr")

        numOfOutlets = int((arcpy.GetCount_management(outletsLayer)).getOutput(0))

        # Select all outlets that are completely within the AOI polygon
        arcpy.SelectLayerByLocation_management("outletsTempLyr", "completely_within", "AOI_lyr")
        numOfOutletsWithinAOI = int((arcpy.GetCount_management("outletsTempLyr")).getOutput(0))

        # There are no outlets completely within AOI; may be some on the AOI boundary
        if numOfOutletsWithinAOI == 0:

            arcpy.SelectLayerByAttribute_management("outletsTempLyr", "CLEAR_SELECTION", "")
            arcpy.SelectLayerByLocation_management("outletsTempLyr", "crossed_by_the_outline_of", "AOI_lyr")

            # Check for outlets on the AOI boundary
            numOfIntersectedOutlets = int((arcpy.GetCount_management("outletsTempLyr")).getOutput(0))

            # No outlets within AOI or intersecting AOI
            if numOfIntersectedOutlets == 0:

                AddMsgAndPrint("\tAll outlets are outside of your Area of Interest",2)
                AddMsgAndPrint("\tRedigitize your outlets so that they are within your Area of Interest. Exiting...\n",2)  
            
                arcpy.Delete_management("AOI_lyr")
                arcpy.Delete_management("outletsTempLyr")
                del numOfOutlets, numOfOutletsWithinAOI, numOfIntersectedOutlets
                
                return False

            # There are some outlets on AOI boundary but at least one outlet completely outside AOI
            else:

                # All outlets are intersecting the AOI boundary
                if numOfOutlets == numOfIntersectedOutlets:
                    
                    AddMsgAndPrint("\n\tAll Outlet(s) are intersecting the AOI Boundary",0)
                    AddMsgAndPrint("\tOutlets will be clipped to AOI",0)

                # Some outlets intersecting AOI and some completely outside.
                else:
                    
                    AddMsgAndPrint("\n\tThere are " + str(numOfOutlets - numOfOutletsWithinAOI) + " outlet(s) completely outside the AOI Boundary",0)
                    AddMsgAndPrint("\tOutlet(s) will be clipped to AOI",0)

                clippedOutlets = watershedGDB_path + os.sep + "Layers" + os.sep + projectName + "_clippedOutlets"
                arcpy.Clip_analysis(outletsLayer, projectAOI, clippedOutlets)

                arcpy.Delete_management("AOI_lyr")
                arcpy.Delete_management("outletsTempLyr")
                del numOfOutlets, numOfOutletsWithinAOI, numOfIntersectedOutlets

                arcpy.Delete_management(outletFC)
                arcpy.Rename_management(clippedOutlets,outletFC)

                AddMsgAndPrint("\n\t" + str(int(arcpy.GetCount_management(outletFC).getOutput(0))) + " Outlet(s) will be used to create watershed(s)",0) 
                
                return True
        
        # all outlets are completely within AOI; Ideal scenario
        elif numOfOutletsWithinAOI == numOfOutlets:

            AddMsgAndPrint("\n\t" + str(numOfOutlets) + " Outlet(s) will be used to create watershed(s)",0)            
            
            arcpy.Delete_management("AOI_lyr")
            arcpy.Delete_management("outletsTempLyr")
            del numOfOutlets, numOfOutletsWithinAOI            
            
            return True

        # combination of scenarios.  Would require multiple outlets to have been digitized. A
        # will be required.
        else:

            arcpy.SelectLayerByAttribute_management("outletsTempLyr", "CLEAR_SELECTION", "")
            arcpy.SelectLayerByLocation_management("outletsTempLyr", "crossed_by_the_outline_of", "AOI_lyr")

            numOfIntersectedOutlets = int((arcpy.GetCount_management("outletsTempLyr")).getOutput(0))

            AddMsgAndPrint("\t" + str(numOfOutlets) + " Outlets digitized",0)            

            # there are some outlets crossing the AOI boundary and some within.
            if numOfIntersectedOutlets > 0 and numOfOutletsWithinAOI > 0:

                AddMsgAndPrint("\n\tThere is " + str(numOfIntersectedOutlets) + " outlet(s) intersecting the AOI Boundary",0)
                AddMsgAndPrint("\tOutlet(s) will be clipped to AOI",0)

            # there are some outlets outside the AOI boundary and some within.
            elif numOfIntersectedOutlets == 0 and numOfOutletsWithinAOI > 0:

                AddMsgAndPrint("\n\tThere is " + str(numOfOutlets - numOfOutletsWithinAOI) + " outlet(s) completely outside the AOI Boundary",0)
                AddMsgAndPrint("\tOutlet(s) will be clipped to AOI",0)             

            # All outlets are are intersecting the AOI boundary
            else:
                AddMsgAndPrint("\n\tOutlet(s) is intersecting the AOI Boundary and will be clipped to AOI",0)

            clippedOutlets = watershedGDB_path + os.sep + "Layers" + os.sep + projectName + "_clippedOutlets"
            arcpy.Clip_analysis(outletsLayer, projectAOI, clippedOutlets)

            arcpy.Delete_management("AOI_lyr")
            arcpy.Delete_management("outletsTempLyr")
            del numOfOutlets, numOfOutletsWithinAOI, numOfIntersectedOutlets            

            arcpy.Delete_management(outletFC)
            arcpy.Rename_management(clippedOutlets,outletFC)

            AddMsgAndPrint("\n\t" + str(int(arcpy.GetCount_management(outletFC).getOutput(0))) + " Outlet(s) will be used to create watershed(s)",0)            
            
            return True

    except:
        AddMsgAndPrint("\nFailed to determine overlap between outlets and " + projectAOI + ". Exiting...",2)
        print_exception()
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
import arcpy, sys, os, string, traceback, re

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
    userWtshdName = arcpy.GetParameterAsText(2)
    createFlowPaths = arcpy.GetParameterAsText(3)

    if string.upper(createFlowPaths) <> "TRUE":
        calcLHL = False
    else:
        calcLHL = True
        
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
    DEM_aoi = watershedGDB_path + os.sep + projectName + "_DEM"
    DEMsmooth = watershedGDB_path + os.sep + "DEMsmooth"

    # Must Have a unique name for watershed -- userWtshdName gets validated, but that doesn't ensure a unique name
    # Append a unique digit to watershed if required -- This means that a watershed with same name will NOT be
    # overwritten.
    x = 1
    while x > 0:
        if arcpy.Exists(watershed):
            watershed = watershedFD + os.sep + (arcpy.ValidateTableName(userWtshdName, watershedFD)) + str(x)
            x += 1
        else:
            x = 0
    del x

    outletFC = watershedFD + os.sep + os.path.basename(watershed) + "_outlet"

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
    
    # Features in Arcmap
    watershedOut = "" + os.path.basename(watershed) + ""
    outletOut = "" + os.path.basename(outletFC) + ""

    # -----------------------------------------------------------------------------------------------  Path of Log file
    textFilePath = userWorkspace + os.sep + projectName + "_EngTools.txt"

    # record basic user inputs and settings to log file for future purposes
    logBasicSettings()

    # ---------------------------------------------------------------------------------------------- Check some parameters
    # If validated name becomes different than userWtshdName notify the user        
    if os.path.basename(watershed) != userWtshdName:
        AddMsgAndPrint("\nUser Watershed name: " + str(userWtshdName) + " is invalid or already exists in project geodatabase.",1)
        AddMsgAndPrint("\tRenamed output watershed to " + str(watershedOut),1)
        
    # Make sure the FGDB and streams exists from step 1 and 2
    if not arcpy.Exists(watershedGDB_path) or not arcpy.Exists(streamsPath):
        AddMsgAndPrint("\nThe \"Streams\" Feature Class or the File Geodatabase from Step 1 was not found!",2)
        AddMsgAndPrint("\nPlease run the Define AOI and the Create Stream Network tools.",2)
        AddMsgAndPrint("\nExiting...")
        sys.exit(0)

    # Must have one pour points manually digitized
    if not int(arcpy.GetCount_management(outlet).getOutput(0)) > 0:
        AddMsgAndPrint("\n\nAt least one pour point must be used! None detected. Exiting...\n",2)
        sys.exit(0)

    # Flow Accumulation grid must be present to proceed
    if not arcpy.Exists(FlowAccum):
        AddMsgAndPrint("\n\nFlow Accumulation Grid was not found in " + watershedGDB_path,2)
        AddMsgAndPrint("Please run the Create Stream Network tool. Exiting...\n",2)
        sys.exit(0)

    # Flow Direction grid must be present to proceed
    if not arcpy.Exists(FlowDir):
        AddMsgAndPrint("\n\nFlow Direction Grid was not found in " + watershedGDB_path,2)
        AddMsgAndPrint("Please run the Create Stream Network tool. Exiting...\n",2)
        sys.exit(0)

    # ---------------------------------------------------------------------------------------------- Delete old datasets
    datasetsToRemove = (outletBuffer,pourPointGrid,snapPourPoint,watershedGrid,watershedTemp,watershedDissolve,wtshdDEMsmooth,slopeGrid,slopeStats)

    x = 0
    for dataset in datasetsToRemove:
        if arcpy.Exists(dataset):
            if x < 1:
                AddMsgAndPrint("\nRemoving old datasets from FGDB: " + watershedGDB_name ,0)
                x += 1
            try:
                arcpy.Delete_management(dataset)
                AddMsgAndPrint("\tDeleting....." + os.path.basename(dataset),0)
            except:
                pass

    del datasetsToRemove
    del x
    
    # ----------------------------------------------------------------------------------------------- Create New Outlet
    # -------------------------------------------- Features reside on hard disk;
    #                                              No heads up digitizing was used.
    if (os.path.dirname(arcpy.Describe(outlet).CatalogPath)).find("memory") < 0:

        # if paths between outlet and outletFC are NOT the same
        if not arcpy.Describe(outlet).CatalogPath == outletFC:

            # delete the outlet feature class; new one will be created            
            if arcpy.Exists(outletFC):
                arcpy.Delete_management(outletFC)
                arcpy.CopyFeatures_management(outlet, outletFC)
                AddMsgAndPrint("\nSuccessfully Recreated " + str(outletOut) + " feature class from existing layer",0)                
                
            else:    
                arcpy.CopyFeatures_management(outlet, outletFC)
                AddMsgAndPrint("\nSuccessfully Created " + str(outletOut) + " feature class from existing layer",0)

        # paths are the same therefore input IS pour point
        else:
            AddMsgAndPrint("\nUsing Existing " + str(outletOut) + " feature class",0)

    # -------------------------------------------- Features reside in Memory;
    #                                              heads up digitizing was used.       
    else:
        if arcpy.Exists(outletFC):
            arcpy.Delete_management(outletFC)
            arcpy.CopyFeatures_management(outlet, outletFC)
            AddMsgAndPrint("\nSuccessfully Recreated " + str(outletOut) + " feature class from digitizing",0)

        else:
            arcpy.CopyFeatures_management(outlet, outletFC)
            AddMsgAndPrint("\nSuccessfully Created " + str(outletOut) + " feature class from digitizing",0)

    if arcpy.Describe(outletFC).ShapeType != "Polyline" and arcpy.Describe(outletFC).ShapeType != "Line":
        AddMsgAndPrint("\n\nYour Outlet must be a Line or Polyline layer! Exiting...",2)
        sys.exit()

    AddMsgAndPrint("\nChecking Placement of Outlet(s)...",0)
    if not determineOverlap(outletFC):
        arcpy.Delete_management(outletFC)
        sys.exit()

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
    
    # --------------------------------------------------------------------- Convert outlet Line Feature to Raster Pour Point.

    # Add dummy field for buffer dissolve and raster conversion using OBJECTID (which becomes subbasin ID)
    arcpy.AddField_management(outletFC, "IDENT", "DOUBLE", "", "", "", "", "NULLABLE", "NON_REQUIRED", "")
    arcpy.CalculateField_management(outletFC, "IDENT", "!OBJECTID!", "PYTHON_9.3")
    
    # Buffer outlet features by  raster cell size
    bufferDist = "" + str(cellSize) + " " + str(units) + ""    
    arcpy.Buffer_analysis(outletFC, outletBuffer, bufferDist, "FULL", "ROUND", "LIST", "IDENT")

    # Convert bufferd outlet to raster pour points    
    arcpy.MakeFeatureLayer_management(outletBuffer,"outletBufferLyr")
    arcpy.PolygonToRaster_conversion("outletBufferLyr","IDENT",pourPointGrid,"MAXIMUM_AREA","NONE",cellSize)

    # Delete intermediate data
    arcpy.Delete_management(outletBuffer)
    arcpy.Delete_management("outletBufferLyr")
    arcpy.DeleteField_management(outletFC, "IDENT")
    
    del bufferDist
    AddMsgAndPrint("\nDelineating Watershed(s)...",0)
    
    # ------------------------------------------------------------------ Create Watershed Raster using the raster pour point
    
    #gp.Watershed_sa(FlowDir,pourPointGrid,watershedGrid,"VALUE")
    arcpy.env.extent = "MAXOF"
    tempShed = arcpy.sa.Watershed(FlowDir,pourPointGrid,"VALUE")
    tempShed.save(watershedGrid)
    
    # ------------------------------------------------------------------- Convert results to simplified polygon
##    if ArcGIS10:
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

##    # Do the following for ArcGIS 9.3
##    else:                
##
##        try:
##            # Convert to watershed grid to a polygon feature class
##            gp.RasterToPolygon_conversion(watershedGrid,watershedTemp,"SIMPLIFY","VALUE")
##
##        except:
##            if gp.exists(watershedTemp):
##                
##                if int(gp.GetCount_management(watershedTemp).getOutput(0)) > 0:
##                    AddMsgAndPrint("",1)
##                else:
##                    AddMsgAndPrint("\n" + gp.GetMessages(2),2)
##                    sys.exit()                
##            else:
##                AddMsgAndPrint("\n" + gp.GetMessages(2),2)
##                sys.exit()
##
##        # Dissolve watershedTemp by GRIDCODE or grid_code 
##        if len(gp.ListFields(watershedTemp,"GRIDCODE")) > 0:
##            gp.Dissolve_management(watershedTemp, watershedDissolve, "GRIDCODE", "", "MULTI_PART", "DISSOLVE_LINES")
##        else:
##            gp.Dissolve_management(watershedTemp, watershedDissolve, "grid_code", "", "MULTI_PART", "DISSOLVE_LINES")
##
##        gp.delete_management(watershedTemp)


    # Copy Results to watershedFD
    arcpy.CopyFeatures_management(watershedDissolve, watershed)    
    AddMsgAndPrint("\n\tSuccessfully Created " + str(int(arcpy.GetCount_management(watershed).getOutput(0))) + " Watershed(s) from " + str(outletOut),0)

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
        arcpy.CalculateField_management(watershed, "Subbasin", "!GRIDCODE!", "PYTHON_9.3")
        arcpy.DeleteField_management(watershed, "GRIDCODE")
        
    else:
        arcpy.CalculateField_management(watershed, "Subbasin", "!grid_code!", "PYTHON_9.3")
        arcpy.DeleteField_management(watershed, "grid_code")

    # Add Acres Field in watershed and calculate them and notify the user
    displayAreaInfo = False

    arcpy.AddField_management(watershed, "Acres", "DOUBLE", "", "", "", "", "NULLABLE", "NON_REQUIRED", "")
    expression = "!shape.area@acres!"
    arcpy.CalculateField_management(watershed, "Acres", expression, "PYTHON_9.3")
    displayAreaInfo = True

##    if units == "Meters":
##        arcpy.AddField_management(watershed, "Acres", "DOUBLE", "", "", "", "", "NULLABLE", "NON_REQUIRED", "")
##        arcpy.CalculateField_management(watershed, "Acres", "[Shape_Area]/4046.86", "VB", "")
##        displayAreaInfo = True
##        
##    elif units == "Feet":
##        gp.AddField_management(watershed, "Acres", "DOUBLE", "", "", "", "", "NULLABLE", "NON_REQUIRED", "")
##        gp.CalculateField_management(watershed, "Acres", "[Shape_Area]/43560", "VB", "")
##        displayAreaInfo = True
##
##    else:
##        displayAreaInfo = False

    # ---------------------------------------------------------------------------- If user opts to calculate watershed flow paths
    if calcLHL:
        try:

            # ----------------------------------------- Temporary Datasets (Yes, there's a bunch)
            UP_GRID = watershedGDB_path + os.sep + "upgrid"
            DOWN_GRID = watershedGDB_path + os.sep + "downgrid"
            PLUS_GRID = watershedGDB_path + os.sep + "plusgrid"
            MAX_GRID = watershedGDB_path + os.sep + "maxgrid"
            MINUS_GRID = watershedGDB_path + os.sep + "minusgrid"
            LONGPATH = watershedGDB_path + os.sep + "longpath"
            LP_Extract = watershedGDB_path + os.sep + "lpExt"
            LongpathTemp = watershedGDB_path + os.sep + "lpTemp"
            LongpathTemp1 = watershedGDB_path + os.sep + "lpTemp1"
            LongpathTemp2 = watershedGDB_path + os.sep + "lpTemp2"
            LP_Smooth = watershedGDB_path + os.sep + "lpSmooth"
            
            # ------------------------------------------- Permanent Datasets (...and yes, it took 13 other ones to get here)
            Flow_Length = watershedFD + os.sep + os.path.basename(watershed) + "_FlowPaths"
            FlowLengthName = os.path.basename(Flow_Length)

            # ------------------------------------------- Derive Longest flow path for each subbasin
            # Create Longest Path Feature Class
            arcpy.CreateFeatureclass_management(watershedFD, FlowLengthName, "POLYLINE") 
            arcpy.AddField_management(Flow_Length, "Subbasin", "LONG", "", "", "", "", "NULLABLE", "NON_REQUIRED", "")
            arcpy.AddField_management(Flow_Length, "Reach", "LONG", "", "", "", "", "NULLABLE", "NON_REQUIRED", "")
            arcpy.AddField_management(Flow_Length, "Type", "TEXT", "", "", "", "", "NULLABLE", "NON_REQUIRED", "")
            arcpy.AddField_management(Flow_Length, "Length_ft", "DOUBLE", "", "", "", "", "NULLABLE", "NON_REQUIRED", "")

            AddMsgAndPrint("\nCalculating watershed flow path(s)...",0)
            
            # -------------------------------------------- Raster Flow Length Analysis
            # Set mask to watershed to limit calculations
            arcpy.env.mask = watershed

            # Calculate total upstream flow length on FlowDir grid
            AddMsgAndPrint("\tCalculating upstream flow...",0)
            #gp.FlowLength_sa(FlowDir, UP_GRID, "UPSTREAM", "")
            tempUp = arcpy.sa.FlowLength(FlowDir, "UPSTREAM", "")
            tempUp.save(UP_GRID)
            
            # Calculate total downsteam flow length on FlowDir grid
            AddMsgAndPrint("\tCalculating downstream flow...",0)
            #gp.FlowLength_sa(FlowDir, DOWN_GRID, "DOWNSTREAM", "")
            tempDown = arcpy.sa.FlowLength(FlowDir, "DOWNSTREAM", "")
            tempDown.save(DOWN_GRID)            
            
            # Sum total upstream and downstream flow lengths
            AddMsgAndPrint("\tCombining upstream and downstream flow...",0)
            #gp.Plus_sa(UP_GRID, DOWN_GRID, PLUS_GRID)
            tempSum = arcpy.sa.Plus(UP_GRID, DOWN_GRID)
            tempSum.save(PLUS_GRID)
            
            # Get Maximum downstream flow length in each subbasin
            AddMsgAndPrint("\tExtracting maximum flow values...",0)
            #gp.ZonalStatistics_sa(watershed, "Subbasin", DOWN_GRID, MAX_GRID, "MAXIMUM", "DATA")
            tempZones = arcpy.sa.ZonalStatistics(watershed, "Subbasin", DOWN_GRID, "MAXIMUM", "DATA")
            tempZones.save(MAX_GRID)
            
            # Subtract tolerance from Maximum flow length -- where do you get tolerance from?
            AddMsgAndPrint("\tAdjusting maximum flows for tolerance level...",0)
            #gp.Minus_sa(MAX_GRID, "0.3", MINUS_GRID)
            tempMinus = arcpy.sa.Minus(MAX_GRID, 0.3)
            tempMinus.save(MINUS_GRID)
            
            # Extract cells with positive difference to isolate longest flow path(s)
            AddMsgAndPrint("\tExtracting Longest Flow Path...",0)
            #gp.GreaterThan_sa(PLUS_GRID, MINUS_GRID, LONGPATH)
            tempGTR = arcpy.sa.GreaterThan(PLUS_GRID, MINUS_GRID)
            tempGTR.save(LONGPATH)
            #gp.Con_sa(LONGPATH, LONGPATH, LP_Extract, "", "\"VALUE\" = 1")
            tempLPE = arcpy.sa.Con(LONGPATH, LONGPATH, "", "\"VALUE\" = 1")
            tempLPE.save(LP_Extract)

    ##            # -------------------------------------------- Convert to Polyline features
    ##            # Convert raster flow path to polyline (DOES NOT RUN IN ARCGIS 10.5.0 Base Install)
    ##            gp.RasterToPolyline_conversion(LP_Extract, LongpathTemp, "ZERO", "", "NO_SIMPLIFY", "VALUE")
    ##            
    ####################################################################################################################################
            # Try to use Stream to Feature process to convert the raster Con result to a line (DUE TO 10.5.0 BUG)
            AddMsgAndPrint("\tConverting Raster flow path to a line...",0)
            LFP_StreamLink = watershedGDB_path + os.sep + "lfplink"
            #gp.StreamLink_sa(LP_Extract, FlowDir, LFP_StreamLink)
            tempLink = arcpy.sa.StreamLink(LP_Extract, FlowDir)
            tempLink.save(LFP_StreamLink)
            arcpy.sa.StreamToFeature(LFP_StreamLink, FlowDir, LongpathTemp, "NO_SIMPLIFY")
    ####################################################################################################################################
            
            # Smooth and Dissolve results
            arcpy.SmoothLine_cartography(LongpathTemp, LP_Smooth, "PAEK", "100 Feet", "FIXED_CLOSED_ENDPOINT", "NO_CHECK")

            # Intersect with watershed to get subbasin ID
            arcpy.Intersect_analysis(LP_Smooth + "; " + watershed, LongpathTemp1, "ALL", "", "INPUT")
            
            # Dissolve to create single lines for each subbasin
            arcpy.Dissolve_management(LongpathTemp1, LongpathTemp2, "Subbasin", "", "MULTI_PART", "DISSOLVE_LINES")
            
            # Add Fields / attributes & calculate length in feet
            AddMsgAndPrint("\tUpdating longest flow path attributes...",0)
            arcpy.AddField_management(LongpathTemp2, "Reach", "SHORT", "", "", "", "", "NULLABLE", "NON_REQUIRED", "")
            arcpy.CalculateField_management(LongpathTemp2, "Reach", "!OBJECTID!", "PYTHON_9.3")
            arcpy.AddField_management(LongpathTemp2, "Type", "TEXT", "", "", "", "", "NULLABLE", "NON_REQUIRED", "")
            arcpy.CalculateField_management(LongpathTemp2, "Type", "'Natural Watercourse'", "PYTHON_9.3")
            arcpy.AddField_management(LongpathTemp2, "Length_ft", "DOUBLE", "", "", "", "", "NULLABLE", "NON_REQUIRED", "")
            expression = "!shape.length@feet!"
            arcpy.CalculateField_management(LongpathTemp2, "Length_ft", expression, "PYTHON_9.3")
            
    ##            if units == "Meters":
    ##                gp.CalculateField_management(LongpathTemp2, "Length_ft", "[shape_length] * 3.28084", "VB", "")
    ##            else:
    ##                gp.CalculateField_management(LongpathTemp2, "Length_ft", "[shape_length]", "VB", "")
                
            # Append Results to Flow Length FC
            arcpy.Append_management(LongpathTemp2, Flow_Length, "NO_TEST")

            # Delete Intermediate Data            
            datasetsToRemove = (UP_GRID,DOWN_GRID,PLUS_GRID,MAX_GRID,MINUS_GRID,LONGPATH,LP_Extract,LongpathTemp,LongpathTemp1,LongpathTemp2,LP_Smooth, LFP_StreamLink)
            x = 0
            for dataset in datasetsToRemove:
                if arcpy.Exists(dataset):
                    if x < 1:
                        x += 1
                    try:
                        arcpy.Delete_management(dataset)
                    except:
                        pass
            del datasetsToRemove, x
        
            # ---------------------------------------------------------------------------------------------- Set up Domains
            # Apply domains to watershed geodatabase and Flow Length fields to aid in user editing
            AddMsgAndPrint("\tConfiguring attribute domains to prepare for editing...",0)
            domainTables = True
            ID_Table = os.path.join(os.path.dirname(sys.argv[0]), "Support.gdb" + os.sep + "ID_TABLE")
            Reach_Table = os.path.join(os.path.dirname(sys.argv[0]), "Support.gdb" + os.sep + "REACH_TYPE")

            # If support tables not present skip domains -- user is on their own.
            if not arcpy.Exists(ID_Table):
                domainTables = False
                
            if not arcpy.Exists(Reach_Table):
                domainTables = False

            if domainTables:
                # describe present domains, estrablish and apply if needed
                desc = arcpy.Describe(watershedGDB_path)
                listOfDomains = []

                domains = desc.Domains

                for domain in domains:
                    listOfDomains.append(domain)

                del desc, domains

                if not "Reach_Domain" in listOfDomains:
                    arcpy.TableToDomain_management(ID_Table, "IDENT", "ID_DESC", watershedGDB_path, "Reach_Domain", "Reach_Domain", "REPLACE")

                if not "Type_Domain" in listOfDomains:
                    arcpy.TableToDomain_management(Reach_Table, "TYPE", "TYPE", watershedGDB_path, "Type_Domain", "Type_Domain", "REPLACE")

                del listOfDomains, ID_Table, Reach_Table, domainTables

                # Assign domain to flow length fields for User Edits...
                arcpy.AssignDomainToField_management(Flow_Length, "Reach", "Reach_Domain", "")
                arcpy.AssignDomainToField_management(Flow_Length, "TYPE", "Type_Domain", "")

            else:
                AddMsgAndPrint("\tCould not create attribute domains! Continuing...",1)

            #---------------------------------------------------------------------- Flow Path Calculations complete
            AddMsgAndPrint("\nSuccessfully extracted watershed flow path(s)",0)
            
        except:
            # If Calc LHL fails prompt user to delineate manually and continue...  ...capture error for reference
            AddMsgAndPrint("\nUnable to Calculate Flow Path(s). You will have to trace your stream network to create them manually.",1)
            AddMsgAndPrint("\nContinuing...",1)
            
    # ----------------------------------------------------------------------------------------------- Calculate Average Slope
    calcAvgSlope = False

    # ----------------------------- Retrieve Z Units from AOI    
    if arcpy.Exists(projectAOI):
        
        rows = arcpy.SearchCursor(projectAOI)
        row = rows.next()
        zUnits = row.Z_UNITS
        
        del rows
        del row
        
        # Assign proper Z factor
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

        # zUnits must be inches; no more choices                
        else:
            if units == "Feet":
                Zfactor = 0.0833333
            if units == "Meters":
                Zfactor = 0.0254
    else:
        Zfactor = 0 # trapped for below so if Project AOI not present slope isn't calculated
        
    # --------------------------------------------------------------------------------------------------------
    if Zfactor > 0:
        AddMsgAndPrint("\nCalculating average slope...",0)
        
        if arcpy.Exists(DEMsmooth):
            
            # Use smoothed DEM to calculate slope to remove exteraneous values
            arcpy.AddField_management(watershed, "Avg_Slope", "DOUBLE", "", "", "", "", "NULLABLE", "NON_REQUIRED", "")

            #gp.ExtractByMask_sa(DEMsmooth, watershed, wtshdDEMsmooth)
            tempWtshDEM = arcpy.sa.ExtractByMask(DEMsmooth, watershed)
            tempWtshDEM.save(wtshdDEMsmooth)
            
            #gp.Slope_sa(wtshdDEMsmooth, slopeGrid, "PERCENT_RISE", Zfactor)
            tempSlope = arcpy.sa.Slope(wtshdDEMsmooth, "PERCENT_RISE", Zfactor)
            tempSlope.save(slopeGrid)
            
            #gp.ZonalStatisticsAsTable_sa(watershed, "Subbasin", slopeGrid, slopeStats, "DATA")
            arcpy.sa.ZonalStatisticsAsTable(watershed, "Subbasin", slopeGrid, slopeStats, "DATA")
            calcAvgSlope = True

            # Delete unwanted rasters
            arcpy.Delete_management(DEMsmooth)
            arcpy.Delete_management(wtshdDEMsmooth)
            arcpy.Delete_management(slopeGrid)

        elif arcpy.Exists(DEM_aoi):
            
            # Run Focal Statistics on the DEM_aoi to remove exteraneous values
            #gp.focalstatistics_sa(DEM_aoi, DEMsmooth,"RECTANGLE 3 3 CELL","MEAN","DATA")
            tempFocal = arcpy.sa.FocalStatistics(DEM_aoi, "RECTANGLE 3 3 CELL","MEAN","DATA")
            tempFocal.save(DEMsmooth)

            arcpy.AddField_management(watershed, "Avg_Slope", "DOUBLE", "", "", "", "", "NULLABLE", "NON_REQUIRED", "")

            #gp.ExtractByMask_sa(DEMsmooth, watershed, wtshdDEMsmooth)
            tempWtshDEM = arcpy.sa.ExtractByMask(DEMsmooth, watershed)
            tempWtshDEM.save(wtshdDEMsmooth)
            
            #gp.Slope_sa(wtshdDEMsmooth, slopeGrid, "PERCENT_RISE", Zfactor)
            tempSlope = arcpy.sa.Slope(wtshdDEMsmooth, "PERCENT_RISE", Zfactor)
            tempSlope.save(slopeGrid)
            
            #gp.ZonalStatisticsAsTable_sa(watershed, "Subbasin", slopeGrid, slopeStats, "DATA")
            arcpy.sa.ZonalStatisticsAsTable(watershed, "Subbasin", slopeGrid, slopeStats, "DATA")
            calcAvgSlope = True

            # Delete unwanted rasters
            arcpy.Delete_management(DEMsmooth)
            arcpy.Delete_management(wtshdDEMsmooth)
            arcpy.Delete_management(slopeGrid)   

        else:
            AddMsgAndPrint("\nMissing DEMsmooth or DEM_aoi from FGDB. Could not Calculate Average Slope",1)
            
    else:
        AddMsgAndPrint("\nMissing Project AOI from FGDB. Could not retrieve Z Factor to Calculate Average Slope",1)

    # -------------------------------------------------------------------------------------- Update Watershed FC with Average Slope
    if calcAvgSlope:
        
        # go through each zonal Stat record and pull out the Mean value
        rows = arcpy.SearchCursor(slopeStats)
        row = rows.next()

        AddMsgAndPrint("\n\tSuccessfully Calculated Average Slope",0)

        AddMsgAndPrint("\nCreate Watershed Results:",0)
        AddMsgAndPrint("\n===================================================",0)
        AddMsgAndPrint("\tUser Watershed: " + str(watershedOut),0)
        
        while row:
            wtshdID = row.OBJECTID

            # zonal stats doesnt generate "Value" with the 9.3 geoprocessor
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

    ## ????????
    import time
    time.sleep(5)
    
    # ------------------------------------------------------------------------------------------------ Compact FGDB
    try:
        arcpy.Compact_management(watershedGDB_path)
        AddMsgAndPrint("\nSuccessfully Compacted FGDB: " + os.path.basename(watershedGDB_path),0)    
    except:
        pass

    # ------------------------------------------------------------------------------------------------ Prepare to Add to Arcmap
    # Set paths for derived layers
    arcpy.SetParameterAsText(4, outletFC)
    arcpy.SetParameterAsText(5, watershed)
    
    if calcLHL:
        arcpy.SetParameterAsText(6, Flow_Length)
        del Flow_Length

    AddMsgAndPrint("\nAdding Layers to ArcMap",0)

    arcpy.RefreshCatalog(watershedGDB_path)

##    # Restore original environments
##    gp.extent = tempExtent
##    gp.mask = tempMask
##    gp.SnapRaster = tempSnapRaster
##    gp.CellSize = tempCellSize
##    gp.OutputCoordinateSystem = tempCoordSys
    
except SystemExit:
    pass

except KeyboardInterrupt:
    AddMsgAndPrint("Interruption requested....exiting")

except:
    print_exception()
