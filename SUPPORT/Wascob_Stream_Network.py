## Wascob_Stream_Network.py
##
## Created by Peter Mead, Adolfo Diaz, USDA NRCS, 2013
## Updated by Chris Morse, USDA NRCS, 2020
##
## Create a stream network from DEM within AOI, with inegration of cut lines
## Uses original project AOI DEM for stream networking, and not Project_DEM that is based on 1/10th of a foot z values.
## WASCOB Stream Network will run on an aggregated DEM of 3m or 10 ft resolution if input DEM has a less coarse resolution.

## ================================================================================================================ 
def print_exception():
    
    tb = sys.exc_info()[2]
    l = traceback.format_tb(tb)
    l.reverse()
    tbinfo = "".join(l)
    AddMsgAndPrint("\n----------------------------------- ERROR Start -----------------------------------",2)
    AddMsgAndPrint("Traceback Info: \n" + tbinfo + "Error Info: \n    " +  str(sys.exc_type)+ ": " + str(sys.exc_value) + "",2)
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
    f.write("\n##################################################################\n")
    f.write("Executing \"Wascob Create Stream Network\" tool\n")
    f.write("User Name: " + getpass.getuser() + "\n")
    f.write("Date Executed: " + time.ctime() + "\n")
    f.write("ArcGIS Version: " + str(arcpy.GetInstallInfo()['Version']) + "\n")
    f.write("User Parameters:\n")
    f.write("\tWorkspace: " + userWorkspace + "\n")
    f.write("\tDem_AOI: " + DEM_aoi + "\n")
    if culvertsExist:
        if int(arcpy.GetCount_management(burnCulverts).getOutput(0)) > 1:
            f.write("\tCulverts Digitized: " + str(int(arcpy.GetCount_management(burnCulverts).getOutput(0))) + "\n")
        else:
            f.write("\tCulverts Digitized: 0\n")
    else:
        f.write("\tCulverts Digitized: 0\n")
    f.write("\tStream Threshold: " + str(streamThreshold) + "\n")
    
    f.close
    del f

## ================================================================================================================
def determineOverlap(culvertLayer):
    # This function will evaluate the input culverts vs the updated project culverts layer by comparing counts.
    # Returns true if there are culverts within the AOI, or false if there are not.

    try:
        numOfCulverts = int((arcpy.GetCount_management(burnCulverts)).getOutput(0))
        numOfCulvertsWithinAOI = int((arcpy.GetCount_management(culvertLayer)).getOutput(0))
        if numOfCulvertsWithinAOI > 0:
            if numOfCulverts == numOfCulvertsWithinAOI:
                AddMsgAndPrint("\tAll culverts are within the project area of interest.",0)
                AddMsgAndPrint("\tAll culverts will be used to hydro enforce the DEM.",0)
                return True
            else:
                AddMsgAndPrint("\tSome input culverts are within the project area of interest!",0)
                AddMsgAndPrint("\tCulverts that are within the area of interest will be used to hydro enforce the DEM!",0)
                return True
        else:
            AddMsgAndPrint("\tAll culverts are outside of the project area of interest!",1)
            AddMsgAndPrint("\tNo culverts will be used to hydro enforce the DEM!",1)
            return False
    except:
        AddMsgAndPrint("\nError in determineOverlap function.",1)
        return False
    
## ================================================================================================================
# Import system modules
import arcpy, sys, os, traceback

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
    # Check out Spatial Analyst License        
    if arcpy.CheckExtension("Spatial") == "Available":
        arcpy.CheckOutExtension("Spatial")
    else:
        arcpy.AddError("Spatial Analyst Extension not enabled. Please enable Spatial analyst from the Tools/Extensions menu. Exiting...\n")
        sys.exit()

    #  ------------------------------ Script Parameters
    AOI = arcpy.GetParameterAsText(0)
    burnCulverts = arcpy.GetParameterAsText(1)  
    streamThreshold = arcpy.GetParameterAsText(2)

    # ------------------------------ Define Variables 
    projectAOI_path = arcpy.Describe(AOI).CatalogPath

    if projectAOI_path.find('.gdb') > 0 and projectAOI_path.find('_AOI') > 0:
        watershedGDB_path = projectAOI_path[:projectAOI_path.find('.gdb')+4]
    else:
        arcpy.AddError("\n" + AOI + " is an invalid project AOI feature!")
        arcpy.AddError("Please run the Define Area of Interest tool!")
        sys.exit()
        
    watershedGDB_name = os.path.basename(watershedGDB_path)
    userWorkspace = os.path.dirname(watershedGDB_path)
    projectName = arcpy.ValidateTableName(os.path.basename(userWorkspace).replace(" ","_"))

    # ------------------------------ Permanent Datasets
    culverts = watershedGDB_path + os.sep + "Layers" + os.sep + projectName + "_Culverts"
    streams = watershedGDB_path + os.sep + "Layers" + os.sep + projectName + "_Streams"
    DEM_aoi = watershedGDB_path + os.sep + projectName + "_Raw_DEM"
    hydroDEM = watershedGDB_path + os.sep + "hydroDEM"
    Fill_hydroDEM = watershedGDB_path + os.sep + "Fill_hydroDEM"
    FlowAccum = watershedGDB_path + os.sep + "flowAccumulation"
    FlowDir = watershedGDB_path + os.sep + "flowDirection"

    # ----------------------------- Temporary Datasets
    aggregatedDEM = watershedGDB_path + os.sep + "agrDEM"
    clippedCulverts = watershedGDB_path + os.sep + "Layers" + os.sep + projectName + "_clippedCulverts"
    culvertsTemp = watershedGDB_path + os.sep + "Layers" + os.sep + "culvertsTemp"
    culvertBuffered = watershedGDB_path + os.sep + "Layers" + os.sep + "Culverts_Buffered"
    culvertRaster = watershedGDB_path + os.sep + "culvertRaster"
    conFlowAccum = watershedGDB_path + os.sep + "conFlowAccum"
    streamLink = watershedGDB_path + os.sep + "streamLink"

    # Check if input culverts were submitted because it is an optional parameter
    if burnCulverts == "#" or burnCulverts == "" or burnCulverts == False or int(arcpy.GetCount_management(burnCulverts).getOutput(0)) < 1 or len(burnCulverts) < 1:
        culvertsExist = False
    else:
        culvertsExist = True

    # Set path of log file and start logging
    textFilePath = userWorkspace + os.sep + projectName + "_EngTools.txt"
    logBasicSettings()

    # ---------------------------------------------------------------------------------------------------------------------- Check Parameters
    # Make sure the FGDB and DEM_aoi exist from step 1
    if not arcpy.Exists(watershedGDB_path) or not arcpy.Exists(DEM_aoi):
        AddMsgAndPrint("\nThe \"" + str(projectName) + "_DEM\" raster file or the File Geodatabase from Define AOI was not found!",2)
        AddMsgAndPrint("Please run the Define Area of Interest tool! Exiting...",2)
        sys.exit(0)

    # ----------------------------------------------------------------------------------------------------------------------- Delete old datasets
    datasetsToRemove = (streams,Fill_hydroDEM,hydroDEM,FlowAccum,FlowDir,culvertsTemp,culvertBuffered,culvertRaster,conFlowAccum,streamLink,aggregatedDEM)

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
    
    # -------------------------------------------------------------------------------------------------------------------- Retrieve DEM Properties
    desc = arcpy.Describe(DEM_aoi)
    sr = desc.SpatialReference
    units = sr.LinearUnitName
    cellSize = desc.MeanCellWidth

    # If Cellsize was less than 3 meter or 10 foot resolution create aggregated DEM
    aggregate = False
    
    if units == "Meter":
        units = "Meters"
    elif units == "Foot":
        units = "Feet"
    elif units == "Foot_US":
        units = "Feet"
    else:
        AddMsgAndPrint("\nHorizontal linear units for project DEM data are not in meters or feet. Exiting...",2)
        sys.exit()
    
    if units == "Feet":
        if cellSize < 10:
            cellSize = 10
            aggregate = True

    if units == "Meters":
        if cellSize < 3:
            cellSize = 3
            aggregate = True

    if aggregate:
        AddMsgAndPrint("\nResampling DEM resolution...",0)
        arcpy.Resample_management(DEM_aoi, aggregatedDEM, cellSize, "BILINEAR")
        DEM_aoi = aggregatedDEM
        AddMsgAndPrint("\tResampling successful!",0)
    
    # ------------------------------------------------------------------------------------------------------------------------ Incorporate Culverts into DEM
    reuseCulverts = False
    # Culverts will be incorporated into the DEM_aoi if at least 1 culvert is provided.
    if culvertsExist:
        AddMsgAndPrint("\nProcessing input culverts data...",0)
        if int(arcpy.GetCount_management(burnCulverts).getOutput(0)) > 0:
            # if paths are not the same then the culverts are new input
            if not arcpy.Describe(burnCulverts).CatalogPath == culverts:
                AddMsgAndPrint("\tInput culverts data is new. Updating culverts project data...",0)
                # delete the culverts feature class; new one will be created
                if arcpy.Exists(culverts):
                    try:
                        arcpy.Delete_management(culverts)
                        AddMsgAndPrint("\tRemoved previous culverts project data.",0)
                    except:
                        print_exception()
                # Create new updated culverts layer from new input by clipping to AOI (instead of copying) in case input dataset is very large
                #arcpy.CopyFeatures_management(burnCulverts, culverts)
                arcpy.Clip_analysis(burnCulverts, projectAOI_path, culverts)
                AddMsgAndPrint("\tSuccessfully created new culverts data for project.",0)     
            # paths are the same therefore input was from within the project's FGDB
            else:
                AddMsgAndPrint("\tUsing existing culverts project data...",0)
                # Clip existing culverts in case the AOI was redone and moved in the same project folder.
                arcpy.Clip_analysis(burnCulverts, projectAOI_path, clippedCulverts)
                arcpy.Delete_management(culverts)
                arcpy.Rename_management(clippedCulverts, culverts)
                AddMsgAndPrint("\tSuccessfully re-created culverts data for project.",0)
                reuseCulverts = True

            # --------------------------------------------------------------------- determine overlap of culverts & AOI
            proceed = False
            if determineOverlap(culverts):
                proceed = True
                
            # ------------------------------------------------------------------- Buffer Culverts
            if proceed:
                AddMsgAndPrint("\nAppying hydro-enforcement at culvert locations...",0)
                # Set buffer value for 1 pixel
                if units == "Meters":
                    bufferSize = str(cellSize) + " Meters"
                elif units == "Feet":
                    bufferSize = str(cellSize) + " Feet"
                else:
                    bufferSize = str(cellSize) + " Unknown"
                AddMsgAndPrint("\nBuffer size applied on culverts: " + bufferSize,0)
                    
                # Buffer the culverts to 1 pixel
                arcpy.Buffer_analysis(culverts, culvertBuffered, bufferSize, "FULL", "ROUND", "NONE", "")

                # Dummy field just to execute Zonal stats on each feature
                AddMsgAndPrint("\nApplying the minimum Zonal DEM Value to the Culverts...",0)
                arcpy.AddField_management(culvertBuffered, "ZONE", "TEXT", "", "", "", "", "NULLABLE", "NON_REQUIRED", "")
                arcpy.CalculateField_management(culvertBuffered, "ZONE", "!OBJECTID!", "PYTHON")
                tempZones = arcpy.sa.ZonalStatistics(culvertBuffered, "ZONE", DEM_aoi, "MINIMUM", "NODATA")
                tempZones.save(culvertRaster)

                # Elevation cells that overlap the culverts will get the minimum elevation value
                AddMsgAndPrint("\nFusing Culverts and " + os.path.basename(DEM_aoi) + " to create " + os.path.basename(hydroDEM),0)
                mosaicList = DEM_aoi + ";" + culvertRaster
                arcpy.MosaicToNewRaster_management(mosaicList, watershedGDB_path, "hydroDEM", "#", "32_BIT_FLOAT", cellSize, "1", "LAST", "#")

                AddMsgAndPrint("\nFilling sinks...",0)
                tempFill = arcpy.sa.Fill(hydroDEM)
                tempFill.save(Fill_hydroDEM)
                AddMsgAndPrint("\nSuccessfully filled sinks in " + os.path.basename(hydroDEM) + " to remove small imperfections.",0)

                # Delete unwanted datasets
                arcpy.Delete_management(culvertBuffered)
                arcpy.Delete_management(culvertRaster)

            # No Culverts will be used due to no overlap or determining overlap error.
            else:
                AddMsgAndPrint("\nNo Culverts overlap project area.",0)
                AddMsgAndPrint("\nFilling sinks...",0)
                cellSize = arcpy.Describe(DEM_aoi).MeanCellWidth
                tempFill = arcpy.sa.Fill(DEM_aoi)
                tempFill.save(Fill_hydroDEM)
                AddMsgAndPrint("\nSuccessfully filled sinks in " + os.path.basename(hydroDEM) + " to remove small imperfections.",0)

            del proceed
            
        # No culverts were detected.
        else:
            AddMsgAndPrint("\nNo new culverts were input.",0)
            AddMsgAndPrint("\nFilling sinks...",0)
            cellSize = arcpy.Describe(DEM_aoi).MeanCellWidth
            tempFill = arcpy.sa.Fill(DEM_aoi)
            tempFill.save(Fill_hydroDEM)
            AddMsgAndPrint("\nSuccessfully filled sinks in " + os.path.basename(DEM_aoi) + " to remove small imperfections.",0)

    else:
        AddMsgAndPrint("\nNo culverts input or existing in project data.",0)
        AddMsgAndPrint("\nFilling sinks...",0)
        cellSize = arcpy.Describe(DEM_aoi).MeanCellWidth
        tempFill = arcpy.sa.Fill(DEM_aoi)
        tempFill.save(Fill_hydroDEM)
        AddMsgAndPrint("\nSuccessfully filled sinks in " + os.path.basename(DEM_aoi) + " to remove small imperfections.",0)            

    # ---------------------------------------------------------------------------------------------- Create Stream Network
    # Create Flow Direction Grid...
    AddMsgAndPrint("\nCreating Flow Direciton...",0)
    tempFlow = arcpy.sa.FlowDirection(Fill_hydroDEM, "NORMAL", "")
    tempFlow.save(FlowDir)

    # Create Flow Accumulation Grid...
    AddMsgAndPrint("\nCreating Flow Accumulation...",0)
    tempAcc = arcpy.sa.FlowAccumulation(FlowDir, "", "INTEGER")
    tempAcc.save(FlowAccum)

    # Need to compute a histogram for the FlowAccumulation layer so that the full range of values is captured for subsequent stream generation
    # This tries to fix a bug of the primary channel not generating for large watersheds with high values in flow accumulation grid
    arcpy.CalculateStatistics_management(FlowAccum)

    AddMsgAndPrint("\nSuccessfully created Flow Direction and Flow Accumulation",0)

    # Create stream link using a flow accumulation greater than the user-specified acre threshold, expressed as pixels
    AddMsgAndPrint("\nCreating Stream Link...",0)
    if streamThreshold > 0:
        # Calculating flow accumulation value for appropriate acre threshold
        if units == "Meters":
            acreThresholdVal = round((float(streamThreshold) * 4046.8564224)/(cellSize*cellSize))
            conExpression = "Value >= " + str(acreThresholdVal)

        elif units == "Feet":
            acreThresholdVal = round((float(streamThreshold) * 43560)/(cellSize*cellSize))
            conExpression = "Value >= " + str(acreThresholdVal)

        else:
            acreThresholdVal = round(float(streamThreshold)/(cellSize*cellSize))
            conExpression = "Value >= " + str(acreThresholdVal)

        # Select all cells that are greater than conExpression
        tempCon = arcpy.sa.Con(FlowAccum, FlowAccum, "", conExpression)
        tempCon.save(conFlowAccum)

        # Create Stream Link Works
        tempLink = arcpy.sa.StreamLink(conFlowAccum, FlowDir)
        tempLink.save(streamLink)

    # All values in flowAccum will be used to create sream link
    else:
        acreThresholdVal = 0
        tempLink = arcpy.sa.StreamLink(FlowAccum, FlowDir)
        tempLink.save(streamLink)
    AddMsgAndPrint("\nSuccessfully created Stream Link!",0)
    
    # Converts a raster representing a linear network to features representing the linear network.
    # creates field grid_code
    AddMsgAndPrint("\nCreating Streams...",0)
    arcpy.sa.StreamToFeature(streamLink, FlowDir, streams, "SIMPLIFY")
    AddMsgAndPrint("\nSuccessfully created stream linear network using a flow accumulation value >= " + str(acreThresholdVal),0)

    # ------------------------------------------------------------------------------------------------ Delete unwanted datasets
    arcpy.Delete_management(Fill_hydroDEM)
    arcpy.Delete_management(conFlowAccum)
    arcpy.Delete_management(streamLink)

    # ------------------------------------------------------------------------------------------------ Compact FGDB
    try:
        arcpy.Compact_management(watershedGDB_path)
        AddMsgAndPrint("\nSuccessfully Compacted FGDB: " + os.path.basename(watershedGDB_path),0)    
    except:
        pass

    # ------------------------------------------------------------------------------------------------ Prepare to Add to Arcmap    

    arcpy.SetParameterAsText(3, streams)
    
    if not reuseCulverts:
        arcpy.SetParameterAsText(4, culverts)
    
    AddMsgAndPrint("\nAdding Layers to ArcMap",0)

    # ------------------------------------------------------------------------------------------------ Clean up Time!
    arcpy.RefreshCatalog(watershedGDB_path)

except SystemExit:
    pass

except KeyboardInterrupt:
    AddMsgAndPrint("Interruption requested....exiting")

except:
    print_exception()    
