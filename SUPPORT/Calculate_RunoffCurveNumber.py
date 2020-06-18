## Calculate_RunoffCurveNumber.py
##
## Created by Peter Mead, Adolfo Diaz, USDA NRCS, 2013
## Updated by Chris Morse, USDA NRCS, 2020
##
## Compute a runoff curve number for input watershed(s)

#---------------------------------------------------------------------------------------------------------
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
    f.write("\n##################################################################\n")
    f.write("Executing \"Calculate Runoff Curve Number\" tool \n")
    f.write("User Name: " + getpass.getuser() + "\n")
    f.write("Date Executed: " + time.ctime() + "\n")
    f.write("ArcGIS Version: " + str(arcpy.GetInstallInfo()['Version']) + "\n")
    f.write("User Parameters:\n")
    f.write("\tinWatershed: " + inWatershed + "\n")
    
    f.close
    del f

## ================================================================================================================
# Import system modules
import arcpy, sys, os, string, traceback

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
    # Script Parameters
    inWatershed = arcpy.GetParameterAsText(0)

    # ---------------------------------------------------------------------------- Define Variables
    # inWatershed can ONLY be a feature class
    watershed_path = arcpy.Describe(inWatershed).CatalogPath

    arcpy.AddMessage("Checking input watershed...")
    
    if watershed_path.find('.gdb') > 0:
        watershedGDB_path = watershed_path[:watershed_path.find('.gdb')+4]
        
    else:
        arcpy.AddError("Watershed layer must be from an NRCS engineering tools project!")
        arcpy.AddError("Exiting...")
        sys.exit()    

    # Check for an edit session on the database before continuing. Users likely were editing just prior to running this script.
    workspace = watershedGDB_path
    edit = arcpy.da.Editor(workspace)
    edit.startEditing(True, False)
    try:
        edit.stopEditing(False)
    except:
        del workspace, edit
        arcpy.AddError("\nYou have an active edit session. Please stop editing and run this script again. Exiting...")
        sys.exit()
    del workspace, edit

    # Continue defining variables
    watershedFD_path = watershedGDB_path + os.sep + "Layers"
    watershedGDB_name = os.path.basename(watershedGDB_path)
    userWorkspace = os.path.dirname(watershedGDB_path)
    wsName = os.path.basename(inWatershed)

    inLanduse = watershedFD_path + os.sep + wsName + "_Landuse"
    inSoils = watershedFD_path + os.sep + wsName + "_Soils"

    # -------------------------------------------------------------------------- Permanent Datasets
    rcn = watershedFD_path + os.sep + wsName + "_RCN"

    # Set log file path and start logging
    textFilePath = userWorkspace + os.sep + os.path.basename(userWorkspace).replace(" ","_") + "_EngTools.txt"
    logBasicSettings()    

    # -------------------------------------------------------------------------- Temporary Datasets
    luLayer = "landuseLyr"
    soilsLyr = "soilsLyr"
    watershedLanduseInt = watershedFD_path + os.sep + "watershedLanduseInt"
    wtshdLanduseSoilsIntersect = watershedFD_path + os.sep + "wtshdLanduseSoilsIntersect"
    wtshdLanduseSoilsIntersect_Layer = "soils_lu_lyr"
    wtshdLanduseSoils_dissolve = watershedFD_path + os.sep + "wtshdLanduseSoils_dissolve"
    rcn_stats = watershedGDB_path + os.sep + "rcn_stats"
    rcnLayer = "rcnLayer"

    # ---------------------------------------------------- Map Layers   
    rcnOut = "" + str(wsName) + "_RCN"

    # -------------------------------------------------------------------------- Lookup Tables
    HYD_GRP_Lookup_Table = os.path.join(os.path.dirname(sys.argv[0]), "Support.gdb" + os.sep + "HYD_GRP_Lookup")
    TR_55_RCN_Lookup = os.path.join(os.path.dirname(sys.argv[0]), "Support.gdb" + os.sep + "TR_55_RCN_Lookup")
    
    # ---------------------------------------------------- Reports
    reportPDF = userWorkspace + os.sep + inWatershed + " RCN Reports.pdf"
    sb_PDF = userWorkspace + os.sep + "Sub-Basin Report.pdf"
    dr_PDF = userWorkspace + os.sep + "Detailed RCN Report.pdf"
    sb_rlf = os.path.join(os.path.dirname(sys.argv[0]), "subbasin_rcn_report.rlf")
    dr_rlf = os.path.join(os.path.dirname(sys.argv[0]), "detailed_rcn_report.rlf")
    sb_title = "Sub-Basin RCN Report"
    dr_title = "Detailed RCN Report"
    sb_table = "sb_report_table"
    dr_table = "dr_report_table"

    # Make sure reports, if they exist, are closed/able to be overwritten before we get going
    if arcpy.Exists(reportPDF):
        try:
            arcpy.Delete_management(reportPDF)
        except:
            AddMsgAndPrint("\nThe RCN Reports PDF file for the input watershed is open and cannot be updated.",2)
            AddMsgAndPrint("\nPlease close the RCN Reports PDF file for this watershed and run the tool again.",2)
            AddMsgAndPrint("\nExiting...",2)
            sys.exit()

    # Check for and delete the temp reports in case of interrupt on previous execution of the tool
    if arcpy.Exists(sb_PDF):
        arcpy.Delete_management(sb_PDF)
    if arcpy.Exists(dr_PDF):
        arcpy.Delete_management(dr_PDF)

    # -------------------------------------------------------------------------- Check Soils / Landuse Inputs
    # Exit if input watershed is landuse or soils layer
    AddMsgAndPrint("\nChecking inputs and project data...",0)
    
    if inWatershed.find("_Landuse") > 0 or inWatershed.find("_Soils") > 0:
        AddMsgAndPrint("\tLanduse or Soils were set as the input layer. Enter the watershed layer as input to this tool.",2)
        AddMsgAndPrint("\tExiting...",2)
        sys.exit()
        
    # Exit if "Subbasin" field not found in watershed layer
    if not len(arcpy.ListFields(inWatershed,"Subbasin")) > 0:
        AddMsgAndPrint("\tSubbasin field was not found in " + os.path.basename(inWatershed) + "layer.",2)
        AddMsgAndPrint("\tConfirm the input watershed is from an engineering tools project.",2)
        AddMsgAndPrint("\tConfirm that the Prepare Soils and Landuse tool for watersheds or Update Watershed Attributes tool for WASCOBs has been run with this watershed.",2)
        AddMsgAndPrint("\tExiting...",2)
        sys.exit()

    # Exit if Soils fc not found in FD        
    if not arcpy.Exists(inSoils):
        AddMsgAndPrint("\tSoils data not found in " + str(watershedFD_path) + ".",2)
        AddMsgAndPrint("\tRun Prepare Soils and Landuse tool for watersheds or Update Watershed Attributes for WASCOBs and review soils for any required edits.",2)
        AddMsgAndPrint("\tExiting...",2)
        sys.exit()

    # Exit if landuse fc not found in FD
    if not arcpy.Exists(inLanduse):
        AddMsgAndPrint("\tLanduse data not present in " + str(watershedFD_path) +".\n",2)
        AddMsgAndPrint("\tRun Prepare Soils and Landuse tool for watersheds or Update Watershed Attributes for WASCOBs and review landuse for any required edits.",2)
        AddMsgAndPrint("\tExiting...",2)
        sys.exit()        

    # Exit if Hydro group lookup table is missing
    if not arcpy.Exists(HYD_GRP_Lookup_Table):
        AddMsgAndPrint("\tHYD_GRP_Lookup_Table was not found! Make sure Support.gdb is located within the same location as this script.",2)
        AddMsgAndPrint("\tExiting...",2)
        sys.exit()

    # Exit if TR 55 lookup table is missing
    if not arcpy.Exists(TR_55_RCN_Lookup):
        AddMsgAndPrint("\tTR_55_RCN_Lookup was not found! Make sure Support.gdb is located within the same location as this script.",2)
        AddMsgAndPrint("\tExiting...",2)
        sys.exit()

    # ---------------------------------------------------------------------------------------------- Check for RCN Grid:
    # If NLCD Curve Number tool was executed on specified watershed and a curve number grid was created, overwrite error
    # will result as rcn output feature class in feature dataset will have same name as existing FGDB raster. 
    rcnGrid = watershedGDB_path + os.sep + wsName + "_RCN"
    rcnGridLyr = "" + wsName + "_RCN"
    renameGrid = watershedGDB_path + os.sep + wsName + "_RCN_Grid"
    x = 1
    # Check for Watershed RCN Grid in TOC
    if arcpy.Exists(rcnGridLyr):
        # Remove if present
        arcpy.Delete_management(rcnGridLyr)
    # Check for RCN Grid in FGDB
    if arcpy.Exists(rcnGrid):
        while x > 0:
            # Make sure renameGrid has a unique name
            if arcpy.Exists(renameGrid):
                renameGrid = watershedGDB_path + os.sep + wsName + "_RCN_Grid" + str(x)
                x += 1
            else:
                x = 0
        # rename RCN Grid if present
        arcpy.Rename_management(rcnGrid,renameGrid)
        AddMsgAndPrint("\nIt appears you have previously created a RCN Grid for " + wsName,0)
        AddMsgAndPrint("\n\t" + wsName+ "'s RCN Grid has been renamed to " + str(os.path.basename(renameGrid)),0)
        AddMsgAndPrint("\tto avoid any overwrite errors",0)

    del rcnGrid, renameGrid, rcnGridLyr, x
    arcpy.RefreshCatalog(watershedGDB_path)
    
    # ------------------------------------------------------------------------------------------------ Check for Null Values in Landuse Field
    AddMsgAndPrint("\nChecking Values in landuse layer...",0)
    arcpy.MakeFeatureLayer_management(inLanduse, luLayer, "", "", "")

    # Landuse Field MUST be populated.  It is acceptable to have Condition field unpopulated.
    query = "\"LANDUSE\" LIKE '%Select%' OR \"LANDUSE\" Is Null"
    arcpy.SelectLayerByAttribute_management(luLayer, "NEW_SELECTION", query)

    nullFeatures = int(arcpy.GetCount_management(luLayer).getOutput(0))
    
    if  nullFeatures > 0:
        AddMsgAndPrint("\tThere are " + str(nullFeatures) + " NULL or un-populated values in the LANDUSE or CONDITION Field of your landuse layer.",2)
        AddMsgAndPrint("\tMake sure all rows are attributed in an edit session, save your edits, stop editing and re-run this tool.",2)
        arcpy.Delete_management(luLayer)
        sys.exit()

    arcpy.Delete_management(luLayer)
        
    del query, nullFeatures

    # ------------------------------------------------------------------------------------------------ Check for Combined Classes in Soils Layer...
    AddMsgAndPrint("\nChecking Values in soils layer...",0)
    arcpy.MakeFeatureLayer_management(inSoils, soilsLyr, "", "", "")

    query = "\"HYDGROUP\" LIKE '%/%' OR \"HYDGROUP\" Is Null"
    arcpy.SelectLayerByAttribute_management(soilsLyr, "NEW_SELECTION", query)
    
    combClasses = int(arcpy.GetCount_management(soilsLyr).getOutput(0))
    arcpy.SelectLayerByAttribute_management(soilsLyr, "CLEAR_SELECTION", "")

    if combClasses > 0:
        AddMsgAndPrint("\tThere are " + str(combClasses) + " Combined or un-populated classes in the HYDGROUP Field of your watershed soils layer.",2)
        AddMsgAndPrint("\tYou will need to make sure all rows are attributed with a single class in an edit session,",2)
        AddMsgAndPrint("\tsave your edits, stop editing and re-run this tool.\n",2)
        arcpy.Delete_management(soilsLyr)
        sys.exit()

    arcpy.Delete_management(soilsLyr)

    del combClasses, query   

    # -------------------------------------------------------------------------- Delete Previous Map Layer if present
    if arcpy.Exists(rcnOut):
        AddMsgAndPrint("\nRemoving previous layers from your ArcMap session...",0)
        AddMsgAndPrint("\tRemoving..." + str(wsName) + "_RCN",0)
        arcpy.Delete_management(rcnOut)

    # -------------------------------------------------------------------------- Delete Previous Data if present 
    datasetsToRemove = (rcn,watershedLanduseInt,wtshdLanduseSoilsIntersect_Layer,wtshdLanduseSoils_dissolve,rcn_stats,luLayer,soilsLyr,rcnLayer)

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

    # ------------------------------------------------------------------------------------------------ Intersect Soils, Landuse and Subbasins.
    if not len(arcpy.ListFields(inWatershed,"RCN")) > 0:
        arcpy.AddField_management(inWatershed, "RCN", "LONG", "", "", "", "", "NULLABLE", "NON_REQUIRED", "")

    if not len(arcpy.ListFields(inWatershed,"Acres")) > 0:
        arcpy.AddField_management(inWatershed, "Acres", "DOUBLE", "", "", "", "", "NULLABLE", "NON_REQUIRED", "")
        
    arcpy.CalculateField_management(inWatershed, "Acres", "!shape.area@acres!", "PYTHON")

    arcpy.Intersect_analysis(inWatershed + "; " + inLanduse + ";" + inSoils, wtshdLanduseSoilsIntersect, "NO_FID", "", "INPUT")
    #gp.Intersect_analysis(watershedLanduseInt + "; " + inSoils, wtshdLanduseSoilsIntersect, "NO_FID", "", "INPUT")
        
    arcpy.AddField_management(wtshdLanduseSoilsIntersect, "LUDESC", "TEXT", "255", "", "", "", "NULLABLE", "NON_REQUIRED", "")
    arcpy.AddField_management(wtshdLanduseSoilsIntersect, "LU_CODE", "DOUBLE", "", "", "", "", "NULLABLE", "NON_REQUIRED", "")
    arcpy.AddField_management(wtshdLanduseSoilsIntersect, "HYDROL_ID", "DOUBLE", "", "", "", "", "NULLABLE", "NON_REQUIRED", "")
    arcpy.AddField_management(wtshdLanduseSoilsIntersect, "HYD_CODE", "DOUBLE", "", "", "", "", "NULLABLE", "NON_REQUIRED", "")
    arcpy.AddField_management(wtshdLanduseSoilsIntersect, "RCN_ACRES", "DOUBLE", "", "", "", "", "NULLABLE", "NON_REQUIRED", "")
    arcpy.AddField_management(wtshdLanduseSoilsIntersect, "WGTRCN", "DOUBLE", "", "", "", "", "NULLABLE", "NON_REQUIRED", "")
    arcpy.AddField_management(wtshdLanduseSoilsIntersect, "IDENT", "TEXT", "", "", "", "", "NULLABLE", "NON_REQUIRED", "")

    #arcpy.Delete_management(watershedLanduseInt)

    AddMsgAndPrint("\nSuccessfully intersected Hydrologic Groups, Landuse, and Subbasin Boundaries",0)    
    
    # ------------------------------------------------------------------------------------------------ Perform Checks on Landuse and Condition Attributes
    # Make all edits to feature layer; delete intersect fc.
    arcpy.MakeFeatureLayer_management(wtshdLanduseSoilsIntersect, wtshdLanduseSoilsIntersect_Layer, "", "", "")
    
    AddMsgAndPrint("\nChecking Landuse and Condition Values in intersected data",0)
    assumptions = 0

    #+++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
    # Check #1: Set the condition of the following landuses to NULL
    query = "\"LANDUSE\" = 'Fallow Bare Soil' OR \"LANDUSE\" = 'Farmstead' OR \"LANDUSE\" LIKE 'Roads%' OR \"LANDUSE\" LIKE 'Paved%' OR \"LANDUSE\" LIKE '%Districts%' OR \"LANDUSE\" LIKE 'Newly Graded%' OR \"LANDUSE\" LIKE 'Surface Water%' OR \"LANDUSE\" LIKE 'Wetland%'"
    arcpy.SelectLayerByAttribute_management(wtshdLanduseSoilsIntersect_Layer, "NEW_SELECTION", query)
    count = int(arcpy.GetCount_management(wtshdLanduseSoilsIntersect_Layer).getOutput(0))
    if count > 0:    
        arcpy.CalculateField_management(wtshdLanduseSoilsIntersect_Layer, "CONDITION", "\"\"", "PYTHON")
    arcpy.SelectLayerByAttribute_management(wtshdLanduseSoilsIntersect_Layer, "CLEAR_SELECTION", "")
    del query, count

    #+++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
    # Check #2: Convert All 'N/A' Conditions to 'Good'
    arcpy.SelectLayerByAttribute_management(wtshdLanduseSoilsIntersect_Layer, "NEW_SELECTION", "\"CONDITION\" = 'N/A'")                                        
    count = int(arcpy.GetCount_management(wtshdLanduseSoilsIntersect_Layer).getOutput(0))
    if count > 0:
        AddMsgAndPrint("\n\tThere were " + str(count) + " Landuse polygons with CONDITION 'N/A' that require a condition of Poor, Fair, or Good.",0)
        AddMsgAndPrint("\tCondition for these areas will be assumed to be 'Good'.",0)
        arcpy.CalculateField_management(wtshdLanduseSoilsIntersect_Layer, "CONDITION", '"Good"', "PYTHON")
        assumptions = assumptions + 1
    arcpy.SelectLayerByAttribute_management(wtshdLanduseSoilsIntersect_Layer, "CLEAR_SELECTION", "")
    del count
    
    #++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
    # Check #3: "Open Space Grass Cover 50 to 75 percent" should have a condition of "Fair"
    query = "\"LANDUSE\" = 'Open Space Grass Cover 50 to 75 percent' AND \"CONDITION\" <> 'Fair'"
    arcpy.SelectLayerByAttribute_management(wtshdLanduseSoilsIntersect_Layer, "NEW_SELECTION", query)
    count = int(arcpy.GetCount_management(wtshdLanduseSoilsIntersect_Layer).getOutput(0))
    if count > 0:
        AddMsgAndPrint("\n\tThere were " + str(count) + " 'Open Space Grass Cover 50 to 75 percent' polygons with a condition other than fair.",0)
        AddMsgAndPrint("\tA condition of fair will be assigned to these polygons.",0)
        arcpy.CalculateField_management(wtshdLanduseSoilsIntersect_Layer, "CONDITION", '"Fair"', "PYTHON")
        assumptions = assumptions + 1
    arcpy.SelectLayerByAttribute_management(wtshdLanduseSoilsIntersect_Layer, "CLEAR_SELECTION", "")
    del query, count
    
    #++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
    # Check #4: "Open Space Grass Cover greater than 75 percent" should have a condition of "Good"
    query = "\"LANDUSE\" = 'Open Space Grass Cover greater than 75 percent' AND \"CONDITION\" <> 'Good'"
    arcpy.SelectLayerByAttribute_management(wtshdLanduseSoilsIntersect_Layer, "NEW_SELECTION", query)
    count = int(arcpy.GetCount_management(wtshdLanduseSoilsIntersect_Layer).getOutput(0))
    if count > 0:
        AddMsgAndPrint("\n\tThere were " + str(count) + " 'Open Space Grass Cover greater than 75 percent' polygons with a condition other than Good. Greater than 75 percent cover assumes a condition of 'Good'..\n",0)
        AddMsgAndPrint("\tA condition of Good will be assigned to these polygons.\n",0)
        arcpy.CalculateField_management(wtshdLanduseSoilsIntersect_Layer, "CONDITION", '"Good"', "PYTHON")
        assumptions = assumptions + 1
    arcpy.SelectLayerByAttribute_management(wtshdLanduseSoilsIntersect_Layer, "CLEAR_SELECTION", "")
    del query, count        

    #++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
    # Check #5: "Open Space, Grass Cover less than 50 percent" should have a condition of "Poor"
    query = "\"LANDUSE\" = 'Open Space, Grass Cover less than 50 percent' AND  \"CONDITION\" <> 'Poor'"
    arcpy.SelectLayerByAttribute_management(wtshdLanduseSoilsIntersect_Layer, "NEW_SELECTION", query)
    count = int(arcpy.GetCount_management(wtshdLanduseSoilsIntersect_Layer).getOutput(0))
    if count > 0:
        AddMsgAndPrint("\n\n\tThere were " + str(count) + " 'Open Space, Grass Cover less than 50 percent' polygons with a condition other than Poor. Less than 50 percent cover assumes a condition of 'Poor'..\n",0)
        AddMsgAndPrint("\tA condition of Poor will be assigned to these polygons.\n",0)
        arcpy.CalculateField_management(wtshdLanduseSoilsIntersect_Layer, "CONDITION", '"Poor"', "PYTHON")
        assumptions = assumptions + 1
    arcpy.SelectLayerByAttribute_management(wtshdLanduseSoilsIntersect_Layer, "CLEAR_SELECTION", "")
    del query, count

    #++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
    # Check #6: "Meadow or Continuous Grass Not Grazed Generally Hayed" should have a condition of "Good"
    query = "\"LANDUSE\" = 'Meadow or Continuous Grass Not Grazed Generally Hayed' AND  \"CONDITION\" <> 'Good'"
    arcpy.SelectLayerByAttribute_management(wtshdLanduseSoilsIntersect_Layer, "NEW_SELECTION", query)
    count = int(arcpy.GetCount_management(wtshdLanduseSoilsIntersect_Layer).getOutput(0))
    if count > 0:
        AddMsgAndPrint("\n\n\tThere were " + str(count) + " 'Meadow or Continuous Grass Not Grazed Generally Hayed' polygons with a condition other than Good.",0)
        AddMsgAndPrint("\tA condition of Good will be assigned to these polygons.\n",0)
        arcpy.CalculateField_management(wtshdLanduseSoilsIntersect_Layer, "CONDITION", '"Good"', "PYTHON")
        assumptions = assumptions + 1
    arcpy.SelectLayerByAttribute_management(wtshdLanduseSoilsIntersect_Layer, "CLEAR_SELECTION", "")
    del query, count

    #++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
    # Check #7: "Woods Grazed Not Burned Some forest Litter" should have a condition of "Fair"
    query = "\"LANDUSE\" = 'Woods Grazed Not Burned Some forest Litter' AND \"CONDITION\" <> 'Fair'"
    arcpy.SelectLayerByAttribute_management(wtshdLanduseSoilsIntersect_Layer, "NEW_SELECTION", query)
    count = int(arcpy.GetCount_management(wtshdLanduseSoilsIntersect_Layer).getOutput(0))
    if count > 0:
        AddMsgAndPrint("\n\n\tThere were " + str(count) + " 'Woods Grazed Not Burned Some forest Litter' polygons with a condition other than fair.",0)
        AddMsgAndPrint("\tA condition of fair will be assigned to these polygons.\n",0)
        arcpy.CalculateField_management(wtshdLanduseSoilsIntersect_Layer, "CONDITION", '"Fair"', "PYTHON")
        assumptions = assumptions + 1
    arcpy.SelectLayerByAttribute_management(wtshdLanduseSoilsIntersect_Layer, "CLEAR_SELECTION", "")
    del query, count

    #++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
    # Check #8: "Woods Not Grazed Adequate litter and brush" should have a condition of "Good"
    query = "\"LANDUSE\" = 'Woods Not Grazed Adequate litter and brush' AND  \"CONDITION\" <> 'Good'"
    arcpy.SelectLayerByAttribute_management(wtshdLanduseSoilsIntersect_Layer, "NEW_SELECTION", query)
    count = int(arcpy.GetCount_management(wtshdLanduseSoilsIntersect_Layer).getOutput(0))
    if count > 0:
        AddMsgAndPrint("\n\n\tThere were " + str(count) + " 'Woods Not Grazed Adequate litter and brush' polygons with a condition other than Good.",0)
        AddMsgAndPrint("\tA condition of Good will be assigned to these polygons.\n",0)
        arcpy.CalculateField_management(wtshdLanduseSoilsIntersect_Layer, "CONDITION", '"Good"', "PYTHON")
        assumptions = assumptions + 1
    arcpy.SelectLayerByAttribute_management(wtshdLanduseSoilsIntersect_Layer, "CLEAR_SELECTION", "")
    del query, count        

    #++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
    # Check #9: "Woods Heavily Grazed or Burned" should have a condition of "Poor"
    query = "\"LANDUSE\" = 'Woods Heavily Grazed or Burned' AND  \"CONDITION\" <> 'Poor'"
    arcpy.SelectLayerByAttribute_management(wtshdLanduseSoilsIntersect_Layer, "NEW_SELECTION", query)
    count = int(arcpy.GetCount_management(wtshdLanduseSoilsIntersect_Layer).getOutput(0))
    if count > 0:
        AddMsgAndPrint("\n\tThere were " + str(count) + " 'Woods Heavily Grazed or Burned' polygons with a condition other than Poor.",0)
        AddMsgAndPrint("\tA condition of Poor will be assigned to these polygons.\n",0)
        arcpy.CalculateField_management(wtshdLanduseSoilsIntersect_Layer, "CONDITION", '"Poor"', "PYTHON")
        assumptions = assumptions + 1
    arcpy.SelectLayerByAttribute_management(wtshdLanduseSoilsIntersect_Layer, "CLEAR_SELECTION", "")
    del query, count          

    #++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
    # Check #10: Fallow crops, Row crops, Small Grains or closed seed should have a condition of 'Good' or 'Poor' - default to Good
    query = "\"LANDUSE\" LIKE 'Fallow Crop%' AND \"CONDITION\" = 'Fair' OR \"LANDUSE\" LIKE 'Row Crops%' AND \"CONDITION\" = 'Fair' OR \"LANDUSE\" LIKE 'Small Grain%' AND \"CONDITION\" = 'Fair' OR \"LANDUSE\" LIKE 'Close Seeded%' AND \"CONDITION\" = 'Fair'"
    arcpy.SelectLayerByAttribute_management(wtshdLanduseSoilsIntersect_Layer, "NEW_SELECTION", query)
    count = int(arcpy.GetCount_management(wtshdLanduseSoilsIntersect_Layer).getOutput(0))
    if count > 0:
        AddMsgAndPrint("\n\tThere were " + str(count) + " Cropland related polygons with a 'Fair' condition listed. This Landuse assumes a condition of 'Good' or 'Poor'..\n",0)
        AddMsgAndPrint("\tA condition of Good will be assumed and assigned to these polygons.\n",0)
        arcpy.CalculateField_management(wtshdLanduseSoilsIntersect_Layer, "CONDITION", '"Good"', "PYTHON")
        assumptions = assumptions + 1
    arcpy.SelectLayerByAttribute_management(wtshdLanduseSoilsIntersect_Layer, "CLEAR_SELECTION", "")
    del query, count
    
    if assumptions == 0:
        AddMsgAndPrint("\n\tAll populated correctly!",0)

    # ------------------------------------------------------------------------------------------------ Join LU Descriptions and assign codes for RCN Lookup
    # Select Landuse categories that arent assigned a condition (these dont need to be concatenated)
    query = "\"CONDITION\" = ''"
    arcpy.SelectLayerByAttribute_management(wtshdLanduseSoilsIntersect_Layer, "NEW_SELECTION", query)
    count = int(arcpy.GetCount_management(wtshdLanduseSoilsIntersect_Layer).getOutput(0))
    if count > 0:
        arcpy.CalculateField_management(wtshdLanduseSoilsIntersect_Layer, "LUDESC", "!LANDUSE!", "PYTHON")

    # Concatenate Landuse and Condition fields together
    arcpy.SelectLayerByAttribute_management(wtshdLanduseSoilsIntersect_Layer, "SWITCH_SELECTION", "")
    arcpy.CalculateField_management(wtshdLanduseSoilsIntersect_Layer, "LUDESC", "!LANDUSE!" + "' '" +  "!CONDITION!", "PYTHON")  
    arcpy.SelectLayerByAttribute_management(wtshdLanduseSoilsIntersect_Layer, "CLEAR_SELECTION", "")
    del query, count
    
    # Join Layer and TR_55_RCN_Lookup table to get LUCODE
    arcpy.AddJoin_management(wtshdLanduseSoilsIntersect_Layer, "LUDESC", TR_55_RCN_Lookup, "LandUseDes", "KEEP_ALL")
    arcpy.CalculateField_management(wtshdLanduseSoilsIntersect_Layer, "wtshdLanduseSoilsIntersect.LU_CODE", "!TR_55_RCN_Lookup.LU_CODE!", "PYTHON")
    arcpy.RemoveJoin_management(wtshdLanduseSoilsIntersect_Layer, "TR_55_RCN_Lookup")
    AddMsgAndPrint("\nSuccesfully Joined to TR_55_RCN Lookup table to assign Land Use Codes",0)

    # Join Layer and HYD_GRP_Lookup table to get HYDCODE
    arcpy.AddJoin_management(wtshdLanduseSoilsIntersect_Layer, "HYDGROUP", HYD_GRP_Lookup_Table, "HYDGRP", "KEEP_ALL")
    arcpy.CalculateField_management(wtshdLanduseSoilsIntersect_Layer, "wtshdLanduseSoilsIntersect.HYDROL_ID", "!HYD_GRP_Lookup.HYDCODE!", "PYTHON")
    arcpy.RemoveJoin_management(wtshdLanduseSoilsIntersect_Layer, "HYD_GRP_Lookup")
    AddMsgAndPrint("\nSuccesfully Joined to HYD_GRP_Lookup table to assign Hydro Codes",0)

    # ------------------------------------------------------------------------------------------------ Join and Populate RCN Values        
    # Concatenate LU Code and Hydrol ID to create HYD_CODE for RCN Lookup
    exp = "''.join([str(int(!LU_CODE!)),str(int(!HYDROL_ID!))])"
    arcpy.CalculateField_management(wtshdLanduseSoilsIntersect_Layer, "HYD_CODE", exp,"PYTHON")
    #arcpy.CalculateField_management(wtshdLanduseSoilsIntersect_Layer, "HYD_CODE", "str(int(!LU_CODE!)) + str(int(!HYDROL_ID!))", "PYTHON")

    # Join Layer and TR_55_RCN_Lookup to get RCN value
    arcpy.AddJoin_management(wtshdLanduseSoilsIntersect_Layer, "HYD_CODE", TR_55_RCN_Lookup, "HYD_CODE", "KEEP_ALL")
    arcpy.CalculateField_management(wtshdLanduseSoilsIntersect_Layer, "wtshdLanduseSoilsIntersect.RCN", "!TR_55_RCN_Lookup.RCN!", "PYTHON")
    arcpy.RemoveJoin_management(wtshdLanduseSoilsIntersect_Layer, "TR_55_RCN_Lookup")
    AddMsgAndPrint("\nSuccesfully Joined to TR_55_RCN Lookup table to assign Curve Numbers for Unique Combinations",0)
    
    # ------------------------------------------------------------------------------------------------ Calculate Weighted RCN For Each Subbasin
    # Update acres for each new polygon
    arcpy.CalculateField_management(wtshdLanduseSoilsIntersect_Layer, "RCN_ACRES", "!shape.area@acres!", "PYTHON")

    # Get weighted acres
    arcpy.CalculateField_management(wtshdLanduseSoilsIntersect_Layer, "WGTRCN", "(!RCN_ACRES! / !ACRES!) * !RCN!", "PYTHON")

    arcpy.Statistics_analysis(wtshdLanduseSoilsIntersect_Layer, rcn_stats, "WGTRCN SUM", "Subbasin")
    AddMsgAndPrint("\nSuccessfully Calculated Weighted Runoff Curve Number for each SubBasin",0)

    # ------------------------------------------------------------------------------------------------ Put the results in Watershed Attribute Table
    #AddMsgAndPrint("\nUpdating RCN values on " + os.path.basename(inWatershed) + " layer",1)
    # go through each weighted record and pull out the Mean value
    rows = arcpy.SearchCursor(rcn_stats)
    row = rows.next()

    while row:
        subbasinNum = row.Subbasin
        RCNvalue = row.SUM_WGTRCN
        
        wtshdRows = arcpy.UpdateCursor(inWatershed)
        wtshdRow = wtshdRows.next()

        while wtshdRow:
            watershedSubbasin = wtshdRow.Subbasin

            if watershedSubbasin == subbasinNum:
                wtshdRow.RCN = RCNvalue
                wtshdRows.updateRow(wtshdRow)

                AddMsgAndPrint("\n\tSubbasin ID: " + str(watershedSubbasin),0)
                AddMsgAndPrint("\t\tWeighted Average RCN Value: " + str(round(RCNvalue,0)),0)

                del watershedSubbasin
                break

            else:
                wtshdRow = wtshdRows.next()

        del subbasinNum, RCNvalue, wtshdRows, wtshdRow
        
        row = rows.next()

    del rows, row        

    # ------------------------------------------------------------------------------------------------ Create fresh new RCN Layer
    AddMsgAndPrint("\nAdding unique identifier to each subbasin's soil and landuse combinations",0)
    
    arcpy.CalculateField_management(wtshdLanduseSoilsIntersect_Layer, "IDENT", "str(!HYD_CODE!) + str(!Subbasin!)", "PYTHON")
    
    arcpy.Dissolve_management(wtshdLanduseSoilsIntersect_Layer, wtshdLanduseSoils_dissolve, "Subbasin;HYD_CODE", "", "MULTI_PART", "DISSOLVE_LINES")
    
    arcpy.AddField_management(wtshdLanduseSoils_dissolve, "IDENT", "TEXT", "", "", "", "", "NULLABLE", "NON_REQUIRED", "") #done
    arcpy.AddField_management(wtshdLanduseSoils_dissolve, "SUB_BASIN", "LONG", "", "", "", "", "NULLABLE", "NON_REQUIRED", "") #done
    arcpy.AddField_management(wtshdLanduseSoils_dissolve, "LANDUSE", "TEXT", "", "", "", "", "NULLABLE", "NON_REQUIRED", "")
    arcpy.AddField_management(wtshdLanduseSoils_dissolve, "CONDITION", "TEXT", "", "", "", "", "NULLABLE", "NON_REQUIRED", "")
    arcpy.AddField_management(wtshdLanduseSoils_dissolve, "HYDROLGROUP", "TEXT", "", "", "", "", "NULLABLE", "NON_REQUIRED", "")
    arcpy.AddField_management(wtshdLanduseSoils_dissolve, "RCN", "LONG", "", "", "", "", "NULLABLE", "NON_REQUIRED", "")
    arcpy.AddField_management(wtshdLanduseSoils_dissolve, "ACRES", "DOUBLE", "5", "1", "", "", "NULLABLE", "NON_REQUIRED", "") #done

    arcpy.CalculateField_management(wtshdLanduseSoils_dissolve, "IDENT", "str(!HYD_CODE!) + str(!Subbasin!)", "PYTHON")
    arcpy.CalculateField_management(wtshdLanduseSoils_dissolve, "ACRES", "!shape.area@acres!", "PYTHON")
    arcpy.CalculateField_management(wtshdLanduseSoils_dissolve, "SUB_BASIN", "!Subbasin!", "PYTHON")

    # Just for the purpose of joining and transfering attributes    
    arcpy.MakeFeatureLayer_management(wtshdLanduseSoils_dissolve, rcnLayer, "", "", "")
    arcpy.AddJoin_management(rcnLayer, "IDENT", wtshdLanduseSoilsIntersect_Layer, "IDENT", "KEEP_ALL")

    arcpy.CalculateField_management(rcnLayer, "wtshdLanduseSoils_dissolve.LANDUSE", "!wtshdLanduseSoilsIntersect.LANDUSE!", "PYTHON")
    arcpy.CalculateField_management(rcnLayer, "wtshdLanduseSoils_dissolve.CONDITION", "!wtshdLanduseSoilsIntersect.CONDITION!", "PYTHON")
    arcpy.CalculateField_management(rcnLayer, "wtshdLanduseSoils_dissolve.HYDROLGROUP", "!wtshdLanduseSoilsIntersect.HYDGROUP!", "PYTHON")
    arcpy.CalculateField_management(rcnLayer, "wtshdLanduseSoils_dissolve.RCN", "!wtshdLanduseSoilsIntersect.RCN!", "PYTHON")

    arcpy.RemoveJoin_management(rcnLayer, "wtshdLanduseSoilsIntersect")
    arcpy.DeleteField_management(rcnLayer, "Subbasin;IDENT;HYD_CODE")

    # Create final RCN feature class
    arcpy.CopyFeatures_management(rcnLayer,rcn)

    arcpy.Delete_management(rcn_stats)
    arcpy.Delete_management(wtshdLanduseSoilsIntersect)
    arcpy.Delete_management(wtshdLanduseSoilsIntersect_Layer)
    arcpy.Delete_management(wtshdLanduseSoils_dissolve)
    arcpy.Delete_management(rcnLayer)

    AddMsgAndPrint("\nSuccessfully created RCN Layer: " + str(os.path.basename(rcn)),0)

    # ----------------------------------------------------------- Generate PDF Reports of RCN Data in user workspace
    AddMsgAndPrint("\nCreating RCN PDF reports...",0)

    reportPDF = arcpy.mapping.PDFDocumentCreate(reportPDF)
    
    # Subbasin RCN Report
    arcpy.MakeTableView_management(inWatershed, sb_table)
    tbl = arcpy.mapping.TableView(sb_table)
    arcpy.mapping.ExportReport(tbl, sb_rlf, sb_PDF, "ALL", sb_title)

    # Detailed RCN Report
    arcpy.MakeTableView_management(rcn, dr_table)
    tbl = arcpy.mapping.TableView(dr_table)
    arcpy.mapping.ExportReport(tbl, dr_rlf, dr_PDF, "ALL", dr_title)

    # Assemble the final PDF report
    reportPDF.appendPages(sb_PDF)
    reportPDF.appendPages(dr_PDF)

    # Save and Close the report
    reportPDF.saveAndClose()

    # Delete the temporary tables and files
    arcpy.Delete_management(sb_table)
    arcpy.Delete_management(dr_table)
    arcpy.Delete_management(sb_PDF)
    arcpy.Delete_management(dr_PDF)

    AddMsgAndPrint("\tDone!",0)
    
    # ---------------------------------------------------------------------------------------------------------------------------- Compact FGDB
    try:
        arcpy.Compact_management(watershedGDB_path)
        AddMsgAndPrint("\nSuccessfully Compacted FGDB: " + os.path.basename(watershedGDB_path),0)    
    except:
        pass

    # --------------------------------------------------------------------------------------------------------------------------- Prepare to Add to Arcmap
    arcpy.SetParameterAsText(1, rcn)    
    AddMsgAndPrint("\nAdding Layers to ArcMap",0)

    # ----------------------------------------------------------------------------------------------------- Cleanup
    arcpy.RefreshCatalog(watershedGDB_path)
    
except SystemExit:
    pass

except KeyboardInterrupt:
    AddMsgAndPrint("Interruption requested....exiting")

except:
    print_exception()
