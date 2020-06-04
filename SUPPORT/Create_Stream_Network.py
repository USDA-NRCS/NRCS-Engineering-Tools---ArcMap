## Create_Stream_Network.py
##
## Created by Peter Mead, Adolfo Diaz, USDA NRCS, 2013
## Updated by Chris Morse, USDA NRCS, 2020
##
## Create a stream network from DEM within AOI, with integration of cut lines

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
    f.write("Executing \"Create Stream Network\" tool\n")
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
    # This function will compute a geometric intersection of the project_AOI boundary and the culvert
    # layer to determine overlap.

    try:
        # Make a layer from the project_AOI
        if arcpy.Exists("AOI_lyr"):
            arcpy.Delete_management("AOI_lyr")

        arcpy.MakeFeatureLayer_management(projectAOI_path,"AOI_lyr")

        if arcpy.Exists("culvertsTempLyr"):
            arcpy.Delete_management("culvertsTempLyr")

        arcpy.MakeFeatureLayer_management(culvertLayer,"culvertsTempLyr")

        numOfCulverts = int((arcpy.GetCount_management(culvertLayer)).getOutput(0))

        # Select all culverts that are completely within the AOI polygon
        arcpy.SelectLayerByLocation_management("culvertsTempLyr", "completely_within", "AOI_lyr")
        numOfCulvertsWithinAOI = int((arcpy.GetCount_management("culvertsTempLyr")).getOutput(0))

        # There are no Culverts completely in AOI; may be some on the AOI boundary
        if numOfCulvertsWithinAOI == 0:

            arcpy.SelectLayerByAttribute_management("culvertsTempLyr", "CLEAR_SELECTION", "")
            arcpy.SelectLayerByLocation_management("culvertsTempLyr", "crossed_by_the_outline_of", "AOI_lyr")

            # Check for culverts on the AOI boundary
            numOfIntersectedCulverts = int((arcpy.GetCount_management("culvertsTempLyr")).getOutput(0))

            # No culverts within AOI or intersecting AOI
            if numOfIntersectedCulverts == 0:

                AddMsgAndPrint("\tAll Culverts are outside of your Area of Interest",0)
                AddMsgAndPrint("\tNo culverts will be used to hydro enforce " + os.path.basename(DEM_aoi),0)                
            
                arcpy.Delete_management("AOI_lyr")
                arcpy.Delete_management("culvertsTempLyr")
                del numOfCulverts, numOfCulvertsWithinAOI, numOfIntersectedCulverts
                
                return False

            # There are some culverts on AOI boundary but at least one culvert completely outside AOI
            else:            

                # All Culverts are intersecting the AOI
                if numOfCulverts == numOfIntersectedCulverts:
                    
                    AddMsgAndPrint("\tAll Culvert(s) are intersecting the AOI Boundary",0)
                    AddMsgAndPrint("\tCulverts will be clipped to AOI",0)

                 # Some Culverts intersecting AOI and some completely outside.
                else:

                    AddMsgAndPrint("\t" + str(numOfCulverts) + " Culverts digitized",0)
                    AddMsgAndPrint("\n\tThere is " + str(numOfCulverts - numOfIntersectedCulverts) + " culvert(s) completely outside the AOI Boundary",0)
                    AddMsgAndPrint("\tCulverts will be clipped to AOI",0)

                clippedCulverts = watershedGDB_path + os.sep + "Layers" + os.sep + projectName + "_clippedCulverts"
                arcpy.Clip_analysis(culvertLayer, projectAOI_path, clippedCulverts)

                arcpy.Delete_management("AOI_lyr")
                arcpy.Delete_management("culvertsTempLyr")
                del numOfCulverts, numOfCulvertsWithinAOI, numOfIntersectedCulverts

                arcpy.Delete_management(culverts)
                arcpy.Rename_management(clippedCulverts,culverts)

                AddMsgAndPrint("\n\t" + str(int(arcpy.GetCount_management(culverts).getOutput(0))) + " Culvert(s) will be used to hydro enforce " + os.path.basename(DEM_aoi),0)
                
                return True
        
        # all culverts are completely within AOI; Ideal scenario
        elif numOfCulvertsWithinAOI == numOfCulverts:

            AddMsgAndPrint("\n\t" + str(numOfCulverts) + " Culvert(s) will be used to hydro enforce " + os.path.basename(DEM_aoi),0)            
            
            arcpy.Delete_management("AOI_lyr")
            arcpy.Delete_management("culvertsTempLyr")
            del numOfCulverts, numOfCulvertsWithinAOI            
            
            return True

        # combination of scenarios.  Would require multiple culverts to have been digitized. A
        # will be required.
        else:

            arcpy.SelectLayerByAttribute_management("culvertsTempLyr", "CLEAR_SELECTION", "")
            arcpy.SelectLayerByLocation_management("culvertsTempLyr", "crossed_by_the_outline_of", "AOI_lyr")

            numOfIntersectedCulverts = int((arcpy.GetCount_management("culvertsTempLyr")).getOutput(0))            

            AddMsgAndPrint("\t" + str(numOfCulverts) + " Culverts digitized",0)

            # there are some culverts crossing the AOI boundary and some within.
            if numOfIntersectedCulverts > 0 and numOfCulvertsWithinAOI > 0:
                
                AddMsgAndPrint("\n\tThere is " + str(numOfIntersectedCulverts) + " culvert(s) intersecting the AOI Boundary",0)
                AddMsgAndPrint("\tCulverts will be clipped to AOI",0)

            # there are some culverts outside the AOI boundary and some within.
            elif numOfIntersectedCulverts == 0 and numOfCulvertsWithinAOI > 0:

                AddMsgAndPrint("\n\tThere is " + str(numOfCulverts - numOfCulvertsWithinAOI) + " culvert(s) completely outside the AOI Boundary",0)
                AddMsgAndPrint("\tCulverts(s) will be clipped to AOI",0)             

            # All culverts are intersecting the AOI boundary
            else:
                AddMsgAndPrint("\n\tAll Culverts intersect the AOI Boundary and will be clipped to AOI",0)      

            clippedCulverts = watershedGDB_path + os.sep + "Layers" + os.sep + projectName + "_clippedCulverts"
            arcpy.Clip_analysis(culvertLayer, projectAOI_path, clippedCulverts)

            arcpy.Delete_management("AOI_lyr")
            arcpy.Delete_management("culvertsTempLyr")
            del numOfCulverts, numOfCulvertsWithinAOI, numOfIntersectedCulverts            

            arcpy.Delete_management(culverts)
            arcpy.Rename_management(clippedCulverts,culverts)

            AddMsgAndPrint("\n\t" + str(int(arcpy.GetCount_management(culverts).getOutput(0))) + " Culvert(s) will be used to hydro enforce " + os.path.basename(DEM_aoi),0)            
            
            return True

    except:
        AddMsgAndPrint("\nFailed to determine overlap with " + projectAOI_path + ". (determineOverlap)",1)
        print_exception()
        AddMsgAndPrint("No culverts will be used to hydro enforce " + os.path.basename(DEM_aoi),1)
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

    # Script Parameters
    AOI = arcpy.GetParameterAsText(0)
    burnCulverts = arcpy.GetParameterAsText(1)  
    streamThreshold = arcpy.GetParameterAsText(2)

    # --------------------------------------------------------------------------------------------- Define Variables 
    projectAOI_path = arcpy.Describe(AOI).CatalogPath

    if projectAOI_path.find('.gdb') > 0 and projectAOI_path.find('_AOI') > 0:
        watershedGDB_path = projectAOI_path[:projectAOI_path.find('.gdb')+4]
    else:
        arcpy.AddError("\n\n" + AOI + " is an invalid project_AOI Feature")
        arcpy.AddError("Please run the Define Area of Interest tool!\n\n")
        sys.exit("")
        
    watershedGDB_name = os.path.basename(watershedGDB_path)
    userWorkspace = os.path.dirname(watershedGDB_path)
    projectName = arcpy.ValidateTableName(os.path.basename(userWorkspace).replace(" ","_"))

    # --------------------------------------------------------------- Datasets
    # ------------------------------ Permanent Datasets
    culverts = watershedGDB_path + os.sep + "Layers" + os.sep + projectName + "_Culverts"
    streams = watershedGDB_path + os.sep + "Layers" + os.sep + projectName + "_Streams"
    DEM_aoi = watershedGDB_path + os.sep + projectName + "_DEM"
    hydroDEM = watershedGDB_path + os.sep + "hydroDEM"
    Fill_hydroDEM = watershedGDB_path + os.sep + "Fill_hydroDEM"
    FlowAccum = watershedGDB_path + os.sep + "flowAccumulation"
    FlowDir = watershedGDB_path + os.sep + "flowDirection"

    # ----------------------------- Temporary Datasets
    culvertsTemp = watershedGDB_path + os.sep + "Layers" + os.sep + "culvertsTemp"
    culvertBuffered = watershedGDB_path + os.sep + "Layers" + os.sep + "Culverts_Buffered"
    culvertRaster = watershedGDB_path + os.sep + "culvertRaster"
    conFlowAccum = watershedGDB_path + os.sep + "conFlowAccum"
    streamLink = watershedGDB_path + os.sep + "streamLink"

    # check if culverts exist.  This is only needed b/c the script may be executed manually
    if burnCulverts == "#" or burnCulverts == "" or burnCulverts == False or int(arcpy.GetCount_management(burnCulverts).getOutput(0)) < 1 or len(burnCulverts) < 1:
        culvertsExist = False
    else:
        culvertsExist = True

    # Path of Log file
    textFilePath = userWorkspace + os.sep + projectName + "_EngTools.txt"

    # record basic user inputs and settings to log file for future purposes
    logBasicSettings()

    # ---------------------------------------------------------------------------------------------------------------------- Check Parameters
    # Make sure the FGDB and DEM_aoi exists from step 1
    if not arcpy.Exists(watershedGDB_path) or not arcpy.Exists(DEM_aoi):
        AddMsgAndPrint("\nThe \"" + str(projectName) + "_DEM\" raster file or the File Geodatabase from Define AOI was not found",2)
        AddMsgAndPrint("Please run the Define Area of Interest tool!\n\n",2)
        sys.exit(0)

    # ----------------------------------------------------------------------------------------------------------------------- Delete old datasets
    datasetsToRemove = (streams,Fill_hydroDEM,hydroDEM,FlowAccum,FlowDir,culvertsTemp,culvertBuffered,culvertRaster,conFlowAccum,streamLink)

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
    del dataset
    del datasetsToRemove
    del x
    
    # -------------------------------------------------------------------------------------------------------------------- Retrieve DEM Properties
    desc = arcpy.Describe(DEM_aoi)
    sr = desc.SpatialReference
    units = sr.LinearUnitName
    cellSize = desc.MeanCellWidth
        
    # ------------------------------------------------------------------------------------------------------------------------ Incorporate Culverts into DEM
    reuseCulverts = False
    # Culverts will be incorporated into the DEM_aoi if at least 1 culvert is provided.
    if culvertsExist:
        if int(arcpy.GetCount_management(burnCulverts).getOutput(0)) > 0:
            # if paths are not the same then assume culverts were manually digitized
            # or input is some from some other feature class/shapefile
            if not arcpy.Describe(burnCulverts).CatalogPath == culverts:
                # delete the culverts feature class; new one will be created   
                if arcpy.Exists(culverts):
                    try:
                        arcpy.Delete_management(culverts)
                        arcpy.CopyFeatures_management(burnCulverts, culverts)
                        AddMsgAndPrint("\nSuccessfully Recreated \"Culverts\" feature class.",0)
                    except:
                        print_exception()
                        arcpy.env.overwriteOutput = True
                else:
                    arcpy.CopyFeatures_management(burnCulverts, culverts)
                    AddMsgAndPrint("\nSuccessfully Created \"Culverts\" feature class",0)           

            # paths are the same therefore input was from within FGDB
            else:
                AddMsgAndPrint("\nUsing Existing \"Culverts\" feature class:",0)
                reuseCulverts = True

            # --------------------------------------------------------------------- determine overlap of culverts & AOI
            AddMsgAndPrint("\nChecking Placement of Culverts",0)
            proceed = False

            if determineOverlap(culverts):
                proceed = True

            # ------------------------------------------------------------------- Buffer Culverts
            if proceed:
                cellSize = arcpy.Describe(DEM_aoi).MeanCellWidth

                # determine linear units to set buffer value to the equivalent of 1 pixel
                if arcpy.Describe(DEM_aoi).SpatialReference.LinearUnitName == "Meter":
                    bufferSize = str(cellSize) + " Meters"
                    AddMsgAndPrint("\nBuffer size applied on Culverts: " + str(cellSize) + " Meter(s)",0)

                elif arcpy.Describe(DEM_aoi).SpatialReference.LinearUnitName == "Foot":
                    bufferSize = str(cellSize) + " Feet"
                    AddMsgAndPrint("\nBuffer size applied on Culverts: " + bufferSize,0)
                    
                elif arcpy.Describe(DEM_aoi).SpatialReference.LinearUnitName == "Foot_US":
                    bufferSize = str(cellSize) + " Feet"
                    AddMsgAndPrint("\nBuffer size applied on Culverts: " + bufferSize,0)
                    
                else:
                    bufferSize = str(cellSize) + " Unknown"
                    AddMsgAndPrint("\nBuffer size applied on Culverts: Equivalent of 1 pixel since linear units are unknown",0)
                    
                # Buffer the culverts to 1 pixel
                arcpy.Buffer_analysis(culverts, culvertBuffered, bufferSize, "FULL", "ROUND", "NONE", "")

                # Dummy field just to execute Zonal stats on each feature
                AddMsgAndPrint("\nApplying the minimum Zonal DEM Value to the Culverts",0)
                arcpy.AddField_management(culvertBuffered, "ZONE", "TEXT", "", "", "", "", "NULLABLE", "NON_REQUIRED", "")
                arcpy.CalculateField_management(culvertBuffered, "ZONE", "!OBJECTID!", "PYTHON_9.3")

                tempZones = arcpy.sa.ZonalStatistics(culvertBuffered, "ZONE", DEM_aoi, "MINIMUM", "NODATA")
                tempZones.save(culvertRaster)
                
                # Elevation cells that overlap the culverts will get the minimum elevation value
                AddMsgAndPrint("\nFusing Culverts and " + os.path.basename(DEM_aoi) + " to create " + os.path.basename(hydroDEM),0)
                mosaicList = DEM_aoi + ";" + culvertRaster
                arcpy.MosaicToNewRaster_management(mosaicList, watershedGDB_path, "hydroDEM", "#", "32_BIT_FLOAT", cellSize, "1", "LAST", "#")

                AddMsgAndPrint("\nFilling sinks...",0)
                #gp.Fill_sa(hydroDEM, Fill_hydroDEM)
                tempFill = arcpy.sa.Fill(hydroDEM)
                tempFill.save(Fill_hydroDEM)
                AddMsgAndPrint("\nSuccessfully filled sinks in " + os.path.basename(hydroDEM) + " to remove small imperfections",0)

                del bufferSize
                del mosaicList

                # Delete unwanted datasets
                arcpy.Delete_management(culvertBuffered)
                arcpy.Delete_management(culvertRaster)

            # No Culverts will be used due to no overlap or determining overlap error.
            else:
                AddMsgAndPrint("\nFilling sinks...",0)
                cellSize = arcpy.Describe(DEM_aoi).MeanCellWidth
                #gp.Fill_sa(DEM_aoi, Fill_hydroDEM)
                tempFill = arcpy.sa.Fill(DEM_aoi)
                tempFill.save(Fill_hydroDEM)
                AddMsgAndPrint("\nSuccessfully filled sinks in " + os.path.basename(hydroDEM) + " to remove small imperfections",0)

            del proceed
            
        # No culverts were detected.
        else:
            AddMsgAndPrint("\nNo Culverts detected!",0)
            AddMsgAndPrint("\nFilling sinks...",0)
            cellSize = arcpy.Describe(DEM_aoi).MeanCellWidth
            #gp.Fill_sa(DEM_aoi, Fill_hydroDEM)
            tempFill = arcpy.sa.Fill(DEM_aoi)
            tempFill.save(Fill_hydroDEM)
            AddMsgAndPrint("\nSuccessfully filled sinks in " + os.path.basename(DEM_aoi) + " to remove small imperfections",0)

    else:
        AddMsgAndPrint("\nNo Culverts detected!",0)
        AddMsgAndPrint("\nFilling sinks...",0)
        cellSize = arcpy.Describe(DEM_aoi).MeanCellWidth
        #gp.Fill_sa(DEM_aoi, Fill_hydroDEM)
        tempFill = arcpy.sa.Fill(DEM_aoi)
        tempFill.save(Fill_hydroDEM)
        AddMsgAndPrint("\nSuccessfully filled sinks in " + os.path.basename(DEM_aoi) + " to remove small imperfections",0)            

    # ---------------------------------------------------------------------------------------------- Create Stream Network
    # Create Flow Direction Grid...
    AddMsgAndPrint("\nCreating Flow Direciton...",0)
    #gp.FlowDirection_sa(Fill_hydroDEM, FlowDir, "NORMAL", "")
    tempFlow = arcpy.sa.FlowDirection(Fill_hydroDEM, "NORMAL", "")
    tempFlow.save(FlowDir)

    # Create Flow Accumulation Grid...
    AddMsgAndPrint("\nCreating Flow Accumulation...",0)
    #gp.FlowAccumulation_sa(FlowDir, FlowAccum, "", "INTEGER")
    tempAcc = arcpy.sa.FlowAccumulation(FlowDir, "", "INTEGER")
    tempAcc.save(FlowAccum)

    # Need to compute a histogram for the FlowAccumulation layer so that the full range of values is captured for subsequent stream generation
    # This tries to fix a bug of the primary channel not generating for large watersheds with high values in flow accumulation grid
    arcpy.CalculateStatistics_management(FlowAccum)

    AddMsgAndPrint("\nSuccessfully created Flow Direction and Flow Accumulation",0)

    # stream link will be created using pixels that have a flow accumulation greater than the
    # user-specified acre threshold
    AddMsgAndPrint("\nCreating Stream Link...",0)
    if streamThreshold > 0:

        # Calculating flow accumulation value for appropriate acre threshold
        if arcpy.Describe(DEM_aoi).SpatialReference.LinearUnitName == "Meter":
            acreThresholdVal = round((float(streamThreshold) * 4046.8564224)/(cellSize*cellSize))
            conExpression = "Value >= " + str(acreThresholdVal)

        elif arcpy.Describe(DEM_aoi).SpatialReference.LinearUnitName == "Foot":
            acreThresholdVal = round((float(streamThreshold) * 43560)/(cellSize*cellSize))
            conExpression = "Value >= " + str(acreThresholdVal)
            
        elif arcpy.Describe(DEM_aoi).SpatialReference.LinearUnitName == "Foot_US":
            acreThresholdVal = round((float(streamThreshold) * 43560)/(cellSize*cellSize))
            conExpression = "Value >= " + str(acreThresholdVal)

        else:
            acreThresholdVal = round(float(streamThreshold)/(cellSize*cellSize))
            conExpression = "Value >= " + str(acreThresholdVal)

        # Select all cells that are greater than conExpression
        #gp.Con_sa(FlowAccum, FlowAccum, conFlowAccum, "", conExpression)
        tempCon = arcpy.sa.Con(FlowAccum, FlowAccum, "", conExpression)
        tempCon.save(conFlowAccum)

        # Create Stream Link Works
        #gp.StreamLink_sa(conFlowAccum, FlowDir, streamLink)
        tempLink = arcpy.sa.StreamLink(conFlowAccum, FlowDir)
        tempLink.save(streamLink)
        del conExpression

    # All values in flowAccum will be used to create stream link
    else:
        acreThresholdVal = 0
        #gp.StreamLink_sa(FlowAccum, FlowDir, streamLink)
        tempLink = arcpy.sa.StreamLink(FlowAccum, FlowDir)
        tempLink.save(streamLink)
    AddMsgAndPrint("\nSuccessfully created Stream Link",0)

    # Converts a raster representing a linear network to features representing the linear network.
    # creates field grid_code
    AddMsgAndPrint("\nCreating Streams...",0)
    #gp.StreamToFeature_sa(streamLink, FlowDir, streams, "SIMPLIFY")
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
