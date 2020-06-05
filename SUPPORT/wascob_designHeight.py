## wascob_designHeight.py
##
## Created by Peter Mead, USDA NRCS, 2013
## Updated by Chris Morse, USDA NRCS, 2020
##
## Creates embankment points for stakeout, Allows user input of intake location.
## Appends results to "StakeoutPoints" Layer in Table of contents.

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
    f.write("Executing \"7. Wascob Design Height & Intake Location\" tool\n")
    f.write("User Name: " + getpass.getuser() + "\n")
    f.write("Date Executed: " + time.ctime() + "\n")
    f.write("ArcGIS Version: " + str(arcpy.GetInstallInfo()['Version']) + "\n")
    f.write("User Parameters:\n")
    f.write("\tInput Watershed: " + inWatershed + "\n")
    f.write("\tWorkspace: " + userWorkspace + "\n")
    f.write("\tSelected Subbasin: " + Subbasin + "\n")
    f.write("\tDesign Elevation: " + DesignElev + "\n") 
    f.write("\tIntake Elevation: " + IntakeElev + "\n")    
        
    f.close
    del f   

## ================================================================================================================
# Import system modules
import arcpy, sys, os, traceback, string

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
        
    # ---------------------------------------------- Input Parameters
    inWatershed = arcpy.GetParameterAsText(0)
    Subbasin = arcpy.GetParameterAsText(1)
    DesignElev = arcpy.GetParameterAsText(2)
    IntakeElev = arcpy.GetParameterAsText(3)
    IntakeLocation = arcpy.GetParameterAsText(4)

    # ---------------------------------------------------------------------------- Define Variables 
    watershed_path = arcpy.Describe(inWatershed).CatalogPath
    watershedGDB_path = watershed_path[:watershed_path .find(".gdb")+4]
    watershedGDB_name = os.path.basename(watershedGDB_path)
    watershedFD_path = watershedGDB_path + os.sep + "Layers"
    userWorkspace = os.path.dirname(watershedGDB_path)
    wsName = os.path.basename(inWatershed)
    
    # ---------------------------------------------------------------------------- Existing Datasets
    stakeoutPoints = watershedFD_path + os.sep + "stakeoutPoints"
    DEM_aoi = watershedGDB_path + os.sep + os.path.basename(userWorkspace).replace(" ","_") + "_Project_DEM"
    #DEM_aoi = watershedGDB_path + os.sep + "Project_DEM"

    # ------------- Layers in ArcMap
    stakeoutPoints = "stakeoutPoints"
    ReferenceLine = "ReferenceLine"

    # --------------------------------------------------------------------------- Temporary Datasets
    RefLineLyr = "ReferenceLineLyr"
    stakeoutPointsLyr ="stakeoutPointsLyr"
    pointsSelection = "pointsSelection"
    refLineSelection = "refLineSelection"
    refTemp = watershedFD_path + os.sep + "refTemp"
    intake = watershedFD_path + os.sep + "intake"
    refTempClip = watershedFD_path + os.sep + "refTemp_Clip"
    refPoints = watershedFD_path + os.sep + "refPoints"
    WSmask = watershedFD_path + os.sep + "WSmask"
    DA_Dem = watershedGDB_path + os.sep + "da_dem"
    DA_sn = watershedGDB_path + os.sep + "da_sn"
    DAint = watershedGDB_path + os.sep + "daint"
    DAx0 = watershedGDB_path + os.sep + "dax0"
    DA_snPoly = watershedGDB_path + os.sep + "DA_snPoly"

    # Set path to log file and start logging
    textFilePath = userWorkspace + os.sep + os.path.basename(userWorkspace).replace(" ","_") + "_EngTools.txt"
    logBasicSettings()
   
    # ---------------------------------------------------------------------------- Check inputs
    AddMsgAndPrint("\nChecking inputs and workspace...",0)
    if not arcpy.Exists(DEM_aoi):
        AddMsgAndPrint("\tMissing Project_DEM from FGDB. Can not perform raster analysis.",2)
        AddMsgAndPrint("\tProject_DEM must be in the same geodatabase as your input watershed.",2)
        AddMsgAndPrint("\tCheck your the source of your provided watershed. Exiting...",2)
        sys.exit()
            
    if not arcpy.Exists(ReferenceLine):
        AddMsgAndPrint("\tReference Line not found in table of contents or in the workspace of your input watershed",2)
        AddMsgAndPrint("\tDouble check your inputs and workspace. Exiting...",2)
        sys.exit()
            
    if int(arcpy.GetCount_management(IntakeLocation).getOutput(0)) > 1:
        # Exit if user input more than one intake
        AddMsgAndPrint("\tYou provided more than one inlet location",2)
        AddMsgAndPrint("\tEach subbasin must be completed individually,",2)
        AddMsgAndPrint("\twith one intake provided each time you run this tool.",2)
        AddMsgAndPrint("\tTry again with only one intake loacation. Exiting...",2)
        sys.exit()
        
    if int(arcpy.GetCount_management(IntakeLocation).getOutput(0)) < 1:
        # Exit if no intake point was provided
        AddMsgAndPrint("\tYou did not provide a point for your intake loaction",2)
        AddMsgAndPrint("\tYou must create a point at the proposed inlet location by using",2)
        AddMsgAndPrint("\tthe Add Features tool in the Design Height tool dialog box. Exiting...",2)
        sys.exit()

    if not arcpy.Exists(stakeoutPoints):
        arcpy.CreateFeatureclass_management(watershedFD_path, "stakeoutPoints", "POINT", "", "DISABLED", "DISABLED", "", "", "0", "0", "0")
        arcpy.AddField_management(stakeoutPoints, "ID", "LONG", "", "", "", "", "NULLABLE", "NON_REQUIRED", "")
        arcpy.AddField_management(stakeoutPoints, "Subbasin", "LONG", "", "", "", "", "NULLABLE", "NON_REQUIRED", "")
        arcpy.AddField_management(stakeoutPoints, "Elev", "DOUBLE", "", "", "", "", "NULLABLE", "NON_REQUIRED", "")
        arcpy.AddField_management(stakeoutPoints, "Notes", "TEXT", "", "", "50", "", "NULLABLE", "NON_REQUIRED", "")
    
    # ---------------------------------- Retrieve Raster Properties
    desc = arcpy.Describe(DEM_aoi)
    sr = desc.SpatialReference
    cellSize = desc.MeanCellWidth    
    
    # ----------------------------------------------------- Select reference line for specified Subbasin
    arcpy.MakeFeatureLayer_management(ReferenceLine, RefLineLyr)
    exp = "\"Subbasin\" = " + str(Subbasin) + ""
    AddMsgAndPrint("\nSelecting Reference Line for subbasin " + str(Subbasin),0)
    arcpy.SelectLayerByAttribute_management(RefLineLyr, "NEW_SELECTION", exp)
    arcpy.MakeFeatureLayer_management(RefLineLyr, refLineSelection)
    
    if not int(arcpy.GetCount_management(refLineSelection).getOutput(0)) > 0:
        # Exit if no corresponding subbasin id found in reference line
        AddMsgAndPrint("\tNo reference line features were found for subbasin " + str(Subbasin),2)
        AddMsgAndPrint("\tDouble check your inputs and specify a different subbasin ID. Exiting...",2)
        sys.exit()
        
    arcpy.CopyFeatures_management(refLineSelection, refTemp, "", "0", "0", "0")
    arcpy.SelectLayerByAttribute_management(RefLineLyr, "CLEAR_SELECTION", "")

    # Select any existing Reference points for specified basin and delete
    arcpy.MakeFeatureLayer_management(stakeoutPoints, stakeoutPointsLyr)
    arcpy.SelectLayerByAttribute_management(stakeoutPointsLyr, "NEW_SELECTION", exp)
    arcpy.MakeFeatureLayer_management(stakeoutPointsLyr, pointsSelection)
    if int(arcpy.GetCount_management(pointsSelection).getOutput(0)) > 0:
        arcpy.DeleteFeatures_management(pointsSelection)
    arcpy.SelectLayerByAttribute_management(stakeoutPointsLyr, "CLEAR_SELECTION", "")
    
    # Create Intake from user input and append to Stakeout Points
    AddMsgAndPrint("\nCreating Intake Reference Point...",0)
    arcpy.CopyFeatures_management(IntakeLocation, intake, "", "0", "0", "0")
    arcpy.CalculateField_management(intake, "Id", "" + str(Subbasin)+ "", "PYTHON")
    arcpy.CalculateField_management(intake, "Subbasin", "" + str(Subbasin)+ "", "PYTHON")
    arcpy.CalculateField_management(intake, "Elev", "" + str(IntakeElev)+ "", "PYTHON")
    arcpy.CalculateField_management(intake, "Notes", "\"Intake\"", "PYTHON")
    AddMsgAndPrint("\tSuccessfully created intake for subbasin " + str(Subbasin) + " at " + str(IntakeElev) + " feet",0)
    AddMsgAndPrint("\tAppending results to Stakeout Points...",0)
    arcpy.Append_management(intake, stakeoutPoints, "NO_TEST", "", "")
    
    # Use DEM to determine intersection of Reference Line and Plane @ Design Elevation
    AddMsgAndPrint("\nCalculating Pool Extent...",0)
    arcpy.SelectLayerByAttribute_management(inWatershed, "NEW_SELECTION", exp)
    arcpy.CopyFeatures_management(inWatershed, WSmask, "", "0", "0", "0")
    arcpy.SelectLayerByAttribute_management(inWatershed, "CLEAR_SELECTION", "")

    #gp.ExtractByMask_sa(DEM_aoi, WSmask, DA_Dem)
    tempMask = arcpy.sa.ExtractByMask(DEM_aoi, WSmask)
    tempMask.save(DA_Dem)
    
    #gp.SetNull_sa(DA_Dem, DA_Dem, DA_sn, "VALUE > " + str(DesignElev))
    tempNull = arcpy.sa.SetNull(DA_Dem, DA_Dem, "VALUE > " + str(DesignElev))
    tempNull.save(DA_sn)

    #gp.Times_sa(DA_sn, "0", DAx0)
    tempTimes = arcpy.sa.Times(DA_sn, 0)
    tempTimes.save(DAx0)

    #gp.Int_sa(DAx0, DAint)
    tempInt = arcpy.sa.Int(DAx0)
    tempInt.save(DAint)

    arcpy.RasterToPolygon_conversion(DAint, DA_snPoly, "NO_SIMPLIFY", "VALUE")

    AddMsgAndPrint("\nCreating Embankment Reference Points...",0)
    arcpy.Clip_analysis(refTemp, DA_snPoly, refTempClip, "")
    arcpy.FeatureVerticesToPoints_management(refTempClip, refPoints, "BOTH_ENDS")
    AddMsgAndPrint("\tSuccessfully created " +  str(int(arcpy.GetCount_management(refPoints).getOutput(0))) + " reference points at " + str(DesignElev) + " feet",0)
    arcpy.AddField_management(refPoints, "Id", "LONG", "", "", "", "", "NULLABLE", "NON_REQUIRED", "")
    arcpy.CalculateField_management(refPoints, "Id", "" + str(Subbasin)+ "", "PYTHON")
    arcpy.AddField_management(refPoints, "Elev", "DOUBLE", "", "", "", "", "NULLABLE", "NON_REQUIRED", "")
    arcpy.CalculateField_management(refPoints, "Elev", "" + str(DesignElev)+ "", "PYTHON")
    arcpy.AddField_management(refPoints, "Notes", "TEXT", "", "", "50", "", "NULLABLE", "NON_REQUIRED", "")
    arcpy.CalculateField_management(refPoints, "Notes", "\"Embankment\"", "PYTHON")
    AddMsgAndPrint("\tAppending Results to Stakeout Points...",0)
    arcpy.Append_management(refPoints, stakeoutPoints, "NO_TEST", "", "")

    # Add XY Coordinates to Stakeout Points
    AddMsgAndPrint("\nAdding XY Coordinates to Stakeout Points...",0)
    arcpy.AddXY_management(stakeoutPoints)

    # -------------------------------------------------------------- Delete Intermediate Files
    datasetsToRemove = (stakeoutPointsLyr,RefLineLyr,pointsSelection,refLineSelection,refTemp,intake,refTempClip,refPoints,WSmask,DA_Dem,DA_sn,DAint,DAx0,DA_snPoly)

    x = 0
    for dataset in datasetsToRemove:
        if arcpy.Exists(dataset):
            if x < 1:
                AddMsgAndPrint("\nDeleting temporary data..." ,0)
                x += 1
            try:
                arcpy.Delete_management(dataset)
            except:
                pass
            
    del datasetsToRemove, x
    
    # ------------------------------------------------------------------------------------------------ Compact FGDB
    try:
        arcpy.Compact_management(watershedGDB_path)
        AddMsgAndPrint(" \nSuccessfully Compacted FGDB: " + os.path.basename(watershedGDB_path),0)
    except:
        pass

    # ------------------------------------------------------------------------------------------------ add to ArcMap
    AddMsgAndPrint("\nAdding Results to ArcMap",0)

    arcpy.SetParameterAsText(5, stakeoutPoints)
    
    AddMsgAndPrint("\nProcessing Finished!\n",0)

    # -------------------------------------------------------------- Cleanup
    arcpy.RefreshCatalog(watershedGDB_path)
    
except SystemExit:
    pass

except KeyboardInterrupt:
    AddMsgAndPrint("Interruption requested....exiting")

except:
    print_exception()
