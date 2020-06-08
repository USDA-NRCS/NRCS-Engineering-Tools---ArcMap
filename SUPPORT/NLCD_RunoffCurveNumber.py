## NLCD_RunoffCurveNumber.py
##
## Created by Peter Mead, USDA NRCS, 2013
## Updated by Chris Mores, USDA NRCS, 2020
##
## Compute a runoff curve number for large watersheds using assumptions for soils data and landuse from NLCD

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
    f.write("\n################################################################################################################\n")
    f.write("Executing \"NLCD Runoff Curve Number\" tool\n")
    f.write("User Name: " + getpass.getuser() + "\n")
    f.write("Date Executed: " + time.ctime() + "\n")
    f.write("ArcGIS Version: " + str(arcpy.GetInstallInfo()['Version']) + "\n")
    f.write("User Parameters:\n")
    f.write("\tInput Watershed: " + inWatershed + "\n")
    f.write("\tInput NLCD Raster: " + inNLCD + "\n")
    f.write("\tInput Soils: " + inSoils + "\n")
    
    if createRCN:
        f.write("\tCreate RCN Grid: SELECTED\n")
        if len(snapRaster) > 0:
            f.write("\tRCN Grid Snap Raster: " + snapRaster + "\n")
            f.write("\tRCN Grid Cellsize: " + str(float(outCellSize)) + "\n")
            f.write("\tRCN Grid Coord Sys: " + str(outCoordSys) + "\n")
        else:
            f.write("\tRCN Grid Snap Raster: NOT SPECIFIED\n")
    else:
        f.write("\tCreate RCN Grid: NOT SELECTED\n")
    
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
    # Check out Spatial Analyst License        
    if arcpy.CheckExtension("Spatial") == "Available":
        arcpy.CheckOutExtension("Spatial")
    else:
        arcpy.AddError("Spatial Analyst Extension not enabled. Please enable Spatial analyst from the Tools/Extensions menu. Exiting...\n")
        sys.exit()
        
    # ---------------------------------------------------------------------- Input Parameters
    inWatershed = arcpy.GetParameterAsText(0)
    inNLCD = arcpy.GetParameterAsText(1)
    inSoils = arcpy.GetParameterAsText(2)
    inputField = arcpy.GetParameterAsText(3)
    curveNoGrid = arcpy.GetParameter(4)
    snapRaster = arcpy.GetParameterAsText(5)

    # Check for RCN Grid choice...
    if curveNoGrid == False:
        createRCN = False
    else:
        createRCN = True
        
    # If snap raster provided assign output cell size from snapRaster
    if len(snapRaster) > 0:
        if arcpy.Exists(snapRaster):
            desc = arcpy.Describe(snapRaster)
            sr = desc.SpatialReference
            outCellSize = desc.MeanCellWidth
            outCoordSys = sr
            del desc, sr
        else:
            AddMsgAndPrint("\n\nSpecified Snap Raster does not exist; please make another selection or verify the path. Exiting...",2)
            sys.exit()
        
    # --------------------------------------------------------------------------- Define Variables 
    inWatershed = arcpy.Describe(inWatershed).CatalogPath
    inSoils = arcpy.Describe(inSoils).CatalogPath

    # Manage the input watershed and integrate it to the Eng Tools workflow if it doesn't seem to originate from an Eng Tools workspace
    if inWatershed.find('.gdb') > -1 or inWatershed.find('.mdb') > -1:
        # inWatershed was created using 'Create Watershed Tool'
        if inWatershed.find('_EngTools'):
            watershedGDB_path = inWatershed[:inWatershed.find('.') + 4]
        # inWatershed is a fc from a DB not created using 'Create Watershed Tool'
        else:
            watershedGDB_path = os.path.dirname(inWatershed[:inWatershed.find('.')+4]) + os.sep + os.path.basename(inWatershed).replace(" ","_") + "_EngTools.gdb"
    elif inWatershed.find('.shp')> -1:
        watershedGDB_path = os.path.dirname(inWatershed[:inWatershed.find('.')+4]) + os.sep + os.path.basename(inWatershed).replace(".shp","").replace(" ","_") + "_EngTools.gdb"
    else:
        AddMsgAndPrint("\n\nWatershed Polygon must either be a feature class or shapefile!. Exiting...",2)
        sys.exit()

    # More variables now that watershedGDB path is set
    watershedFD = watershedGDB_path + os.sep + "Layers"
    watershedGDB_name = os.path.basename(watershedGDB_path)
    userWorkspace = os.path.dirname(watershedGDB_path)
    wsName = arcpy.ValidateTableName(os.path.splitext(os.path.basename(inWatershed))[0])

    # Set path to log file and start logging
    textFilePath = userWorkspace + os.sep + os.path.basename(userWorkspace).replace(" ","_") + "_EngTools.txt"   
    logBasicSettings()

    # ----------------------------------------------------------------------------- Datasets
    # --------------------------------------------------- Temporary Datasets
    LU_PLUS_SOILS = watershedGDB_path + os.sep + "LU_PLUS_SOILS"
    CULT_GRID = watershedGDB_path + os.sep + "CULT_GRID"
    CULT_POLY = watershedGDB_path + os.sep + "CULT_POLY"
    soilsLyr = "soilsLyr"
    SOILS_GRID = watershedGDB_path + os.sep + "SOILS"
    landuse = watershedGDB_path + os.sep + "NLCD"
    RCN_Stats = watershedGDB_path + os.sep + "RCN_Stats"
    RCN_Stats2 = watershedGDB_path + os.sep + "RCN_Stats2"
    
    # --------------------------------------------------- Permanent Datasets
    wsSoils = watershedFD + os.sep + wsName + "_Soils"
    watershed = watershedFD + os.sep + wsName
    RCN_GRID = watershedGDB_path + os.sep + wsName + "_RCN"
    RCN_TABLE = watershedGDB_path + os.sep + wsName + "_RCN_Summary_Table"
    
     # ----------------------------------------------------------- Lookup Tables
    NLCD_RCN_TABLE = os.path.join(os.path.dirname(sys.argv[0]), "Support.gdb" + os.sep + "NLCD_RCN_TABLE")
    
    # ----------------------------------------------------------------------------- Check Some Parameters
    AddMsgAndPrint("\nChecking inputs...",0)
    # Exit if any are true
    if not int(arcpy.GetCount_management(inWatershed).getOutput(0)) > 0:
        AddMsgAndPrint("\tWatershed Layer is empty. Exiting...",2)
        sys.exit()

    if int(arcpy.GetCount_management(inWatershed).getOutput(0)) > 1:
        AddMsgAndPrint("\tOnly ONE Watershed or Subbasin can be submitted!",2)
        AddMsgAndPrint("\tEither dissolve " + os.path.basename(inWatershed) + " layer, export an individual polygon, ",2)
        AddMsgAndPrint("\tmake a single selection, or provide a different input. Exiting...",2)
        sys.exit()
        
    if arcpy.Describe(inWatershed).ShapeType != "Polygon":
        AddMsgAndPrint("\tYour Watershed Layer must be a polygon layer! Exiting...",2)
        sys.exit()

    if arcpy.Describe(inSoils).ShapeType != "Polygon":
        AddMsgAndPrint("\tYour Soils Layer must be a polygon layer! Exiting...",2)
        sys.exit()

    if not len(arcpy.ListFields(inSoils,inputField)) > 0:
        AddMsgAndPrint("\tThe field specified for Hydro Groups does not exist in your soils data. Please specify another name and try again. Exiting...",2)
        sys.exit()

    if not len(arcpy.ListFields(inSoils,"MUNAME")) > 0:
        AddMsgAndPrint("\tMUNAME field does not exist in your soils data. Please correct and try again. Exiting...",2)
        sys.exit()

    if not arcpy.Exists(NLCD_RCN_TABLE):
        AddMsgAndPrint("\t\"NLCD_RCN_TABLE\" was not found! Make sure \"Support.gdb\" is located in the same location as this script. Exiting...",2)
        sys.exit()

    # --------------------------------------------------------------------------- Create FGDB, FeatureDataset
    # Boolean - Assume FGDB already exists
    FGDBexists = True

    # Create Watershed FGDB and feature dataset if it doesn't exist      
    if not arcpy.Exists(watershedGDB_path):
        desc = arcpy.Describe(inWatershed)
        sr = desc.SpatialReference

        arcpy.CreateFileGDB_management(userWorkspace, watershedGDB_name)
        arcpy.CreateFeatureDataset_management(watershedGDB_path, "Layers", sr)
        AddMsgAndPrint("\nSuccessfully created File Geodatabase: " + watershedGDB_name,0)
        FGDBexists = False
        del desc, sr

    # if GDB already existed but feature dataset doesn't
    if not arcpy.Exists(watershedFD):
        desc = arcpy.Describe(inWatershed)
        sr = desc.SpatialReference
        arcpy.CreateFeatureDataset_management(watershedGDB_path, "Layers", sr)
        del desc, sr

    # --------------------------------------------------------------------------- Remove domains from fields if they exist
    # If Watershed Runoff Curve Number Tools were previously used on specified watershed, domain will remain on fields
    vectorLanduse = watershedFD + os.sep + wsName + "_Landuse"
    desc = arcpy.Describe(watershedGDB_path)
    listOfDomains = []

    domains = desc.Domains

    for domain in domains:
        listOfDomains.append(domain)

    del desc, domains

    if "LandUse_Domain" in listOfDomains:
        try:
            arcpy.RemoveDomainFromField_management(vectorLanduse, "LANDUSE")
        except:
            pass
    if "Condition_Domain" in listOfDomains:
        try:
            arcpy.RemoveDomainFromField_management(vectorLanduse, "CONDITION")
        except:
            pass
    if "Hydro_Domain" in listOfDomains:
        try:
            arcpy.RemoveDomainFromField_management(wsSoils, "HYDGROUP")
        except:
            pass
        
    del listOfDomains
    
    # ------------------------------------- Delete previous layers from ArcMap if they exist
    # ------------------------------- Map Layers
    rcnOut = "" + wsName + "_RCN"
    soilsOut = "" + wsName + "_Soils"
    landuseOut = "" + wsName + "_Landuse"
    
    layersToRemove = (rcnOut,soilsOut,landuseOut)

    x = 0
    for layer in layersToRemove:
        if arcpy.Exists(layer):
            if x == 0:
                AddMsgAndPrint("\nRemoving previous layers from your ArcMap session...",0)
                x+=1
            try:
                arcpy.Delete_management(layer)
                AddMsgAndPrint("\tRemoving " + layer + "",0)
            except:
                pass

    del x, layersToRemove
    
    # -------------------------------------------------------------------------- Delete Previous Data if present 
    if FGDBexists:    
        layersToRemove = (wsSoils,landuse,vectorLanduse,LU_PLUS_SOILS,CULT_GRID,CULT_POLY,SOILS_GRID,RCN_GRID,RCN_Stats)
        x = 0        
        for layer in layersToRemove:
            if arcpy.Exists(layer):
                # strictly for formatting
                if x == 0:
                    AddMsgAndPrint("\nRemoving old files from FGDB: " + watershedGDB_name ,0)
                    x += 1
                try:
                    arcpy.Delete_management(layer)
                    AddMsgAndPrint("\tDeleting..." + os.path.basename(layer),0)
                except:
                    pass

        del x, layersToRemove

    # ----------------------------------------------------------------------------------------------- Create Watershed
    # if paths are not the same then assume AOI was manually digitized
    # or input is some from some other feature class/shapefile

    # True if watershed was not created from this Eng tools
    externalWshd = False
    if not arcpy.Describe(inWatershed).CatalogPath == watershed:       
        # delete the AOI feature class; new one will be created            
        if arcpy.Exists(watershed):
            try:
                arcpy.Delete_management(watershed)
                arcpy.CopyFeatures_management(inWatershed, watershed)
                AddMsgAndPrint("\nSuccessfully Overwrote existing Watershed",0)
            except:
                print_exception()
                arcpy.env.overwriteOutput = True
        else:
            arcpy.CopyFeatures_management(inWatershed, watershed)
            AddMsgAndPrint("\nSuccessfully Created Watershed " + os.path.basename(watershed) ,0)
        externalWshd = True

    # paths are the same therefore input IS projectAOI
    else:
        AddMsgAndPrint("\nUsing existing " + os.path.basename(watershed) + " feature class",0)

    if externalWshd:
        # Delete all fields in watershed layer except for obvious ones
        fields = arcpy.ListFields(watershed)
        for field in fields:
            fieldName = field.name
            if fieldName.find("Shape") < 0 and fieldName.find("OBJECTID") < 0 and fieldName.find("Subbasin") < 0:
                arcpy.DeleteField_management(watershed,fieldName)  
            del fieldName
        del fields

        if not len(arcpy.ListFields(watershed,"Subbasin")) > 0:
            arcpy.AddField_management(watershed, "Subbasin", "SHORT", "", "", "", "", "NULLABLE", "NON_REQUIRED", "")        
            arcpy.CalculateField_management(watershed, "Subbasin","!OBJECTID!","PYTHON")

        if not len(arcpy.ListFields(watershed,"Acres")) > 0:
            arcpy.AddField_management(watershed, "Acres", "DOUBLE", "", "", "", "", "NULLABLE", "NON_REQUIRED", "")
            arcpy.CalculateField_management(watershed, "Acres", "!shape.area@acres!", "PYTHON", "")

    # ------------------------------------------------------------------------------------------------ Prepare Landuse Raster(s)
    # ----------------------------------- Describe input NLCD Properties
    desc = arcpy.Describe(inNLCD)
    sr = desc.SpatialReference
    units = sr.LinearUnitName
    cellSize = desc.MeanCellWidth
    cellArea = cellSize * cellSize
    
    if units == "Meter" or units == "Meters":
        units = "Meters"
    elif units == "Foot" or units == "Feet" or units == "Foot_US":
        units = "Feet"
    else:
        AddMsgAndPrint("\nInput NLCD layer does not use meters or feet for linear units.",2)
        AddMsgAndPrint("\nPlease project your NLCD data to a projected coordinate system based in meters or feet. Exiting...",2)
        sys.exit()

    # ---------------------------------------------------------------------- Clip NLCD to watershed boundary
    AddMsgAndPrint("\nClipping " + str(os.path.basename(inNLCD)) + " to " + str(wsName) + " boundary...",0)
    #gp.ExtractByMask_sa(inNLCD, watershed, landuse)
    tempMask = arcpy.sa.ExtractByMask(inNLCD, watershed)
    tempMask.save(landuse)
    AddMsgAndPrint("\tSuccessful!",0)

    # Isolate Cultivated Cropland and export to poly for soils processing
    #gp.Con_sa(landuse, landuse, CULT_GRID, "", "\"VALUE\" = 81 OR \"VALUE\" = 82 OR \"VALUE\" = 83 OR \"VALUE\" = 84 OR \"VALUE\" = 85")
    tempCon = arcpy.sa.Con(landuse, landuse, "", "\"VALUE\" = 81 OR \"VALUE\" = 82 OR \"VALUE\" = 83 OR \"VALUE\" = 84 OR \"VALUE\" = 85")
    tempCon.save(CULT_GRID)
    
    # Convert to Polygon for selecting
    arcpy.RasterToPolygon_conversion(CULT_GRID,CULT_POLY,"SIMPLIFY","VALUE")

    # -------------------------------------------------------------------------------------- Clip and Process Soils Data          
    # Clip the soils to the watershed
    arcpy.Clip_analysis(inSoils,watershed,wsSoils)
    AddMsgAndPrint("\nSuccessfully clipped " + str(os.path.basename(inSoils)) + " soils layer",0)

    # If Input field name other than ssurgo default, add and calc proper field
    if inputField.upper() != "HYDGROUP":
        arcpy.AddField_management(wsSoils, "HYDGROUP", "TEXT", "", "", "20", "", "NULLABLE", "NON_REQUIRED", "")
    arcpy.CalculateField_management(wsSoils, "HYDGROUP", "!" + str(inputField) + "!", "PYTHON")

    # ADD HYD_CODE Field for lookup
    if len(arcpy.ListFields(wsSoils,"HYD_CODE")) < 1:
        arcpy.AddField_management(wsSoils, "HYD_CODE", "DOUBLE", "", "", "", "", "NULLABLE", "NON_REQUIRED", "")    
    arcpy.MakeFeatureLayer_management(wsSoils, soilsLyr)
    
    # Process soils to remove nulls in Water, Pits, or urban mapunits
    AddMsgAndPrint("\nProcessing soils data...",0)

    # Select and assign "W" value to any water type map units 
    arcpy.SelectLayerByAttribute_management(soilsLyr, "NEW_SELECTION", "\"MUNAME\" LIKE '%Water%'")
    count = int(arcpy.GetCount_management(soilsLyr).getOutput(0))
    if count > 0:
        AddMsgAndPrint("\tSelecting and converting 'Water' Mapunits...",0)
        arcpy.CalculateField_management(soilsLyr, "HYDGROUP", "\"W\"", "PYTHON")
    del count
        
    # Select and assign "P" value to any pit-like map units  
    arcpy.SelectLayerByAttribute_management(soilsLyr, "NEW_SELECTION", "\"MUNAME\" LIKE '%Pit%'")
    count = int(arcpy.GetCount_management(soilsLyr).getOutput(0))
    if count > 0:
        AddMsgAndPrint("\tSelecting and converting 'Pits' Mapunits...",0)
        arcpy.CalculateField_management(soilsLyr, "HYDGROUP", "\"P\"", "PYTHON")
    del count

    # Assign a "D" value to any unpopulated Urban mapunits   
    arcpy.SelectLayerByAttribute_management(soilsLyr, "NEW_SELECTION", "\"MUNAME\" LIKE 'Urban%'")
    count = int(arcpy.GetCount_management(soilsLyr).getOutput(0))
    if count > 0:
        AddMsgAndPrint("\t\tSelecting and converting Urban Mapunits",0) 
        arcpy.CalculateField_management(soilsLyr, "HYDGROUP", "\"D\"", "PYTHON")
    del count   
    
    # Select any Combined Hydro groups
    AddMsgAndPrint("\nChecking for combined hydrologic groups...",0)
    query = "\"HYDGROUP\" LIKE '%/%'"
    arcpy.SelectLayerByAttribute_management(soilsLyr, "NEW_SELECTION", query)
    del query
    count = int(arcpy.GetCount_management(soilsLyr).getOutput(0))
    if count > 0:
        AddMsgAndPrint("\tThere are " + str(count) + " soil map unit(s) with combined hydro groups.",0)
        arcpy.MakeFeatureLayer_management(soilsLyr, "combinedLyr")
    
        # Select Combined Classes that intersect cultivated cropland
        arcpy.SelectLayerByLocation_management("combinedLyr", "intersect", CULT_POLY, 0, "new_selection")
        count2 = int(arcpy.GetCount_management("combinedLyr").getOutput(0))
        if count2 > 0:
            AddMsgAndPrint("\tSetting " + str(count2) + " combined group(s) on cultivated land to drained state...",0)
            # Set selected polygons to drained state
            arcpy.CalculateField_management("combinedLyr", "HYDGROUP", "!HYDGROUP![0]", "PYTHON")
        del count2
        
        # Set remaining combined groups to natural state
        arcpy.SelectLayerByAttribute_management("combinedLyr", "SWITCH_SELECTION", "")
        count2 = int(arcpy.GetCount_management("combinedLyr").getOutput(0))
        if count2 > 0:
            AddMsgAndPrint("\tSetting "  + str(count2) + " non-cultivated combined group(s) to natural state...",0)
            arcpy.CalculateField_management("combinedLyr", "HYDGROUP", "\"D\"", "PYTHON")
        del count2
    del count
    
    # Set any possible remaing nulls to "W", which will assign a RCN of 99    
    query = "\"HYDGROUP\" Is Null"
    arcpy.SelectLayerByAttribute_management(soilsLyr, "NEW_SELECTION", query)
    count = int(arcpy.GetCount_management(soilsLyr).getOutput(0))
    del query
    if count > 0:
        AddMsgAndPrint("\tThere are " + str(count) + " null hydro group(s) remaining.",0)
        AddMsgAndPrint("\tA RCN value of 99 will be applied to these areas.",0)
        arcpy.CalculateField_management(soilsLyr, "HYDGROUP", "\"W\"", "PYTHON")
    del count

    # Clear any remaining selections
    arcpy.SelectLayerByAttribute_management(soilsLyr, "CLEAR_SELECTION", "")    
    
    # Join NLCD Lookup table to populate HYD_CODE field
    arcpy.AddJoin_management(soilsLyr, "HYDGROUP", NLCD_RCN_TABLE, "Soil", "KEEP_ALL")
    arcpy.CalculateField_management(soilsLyr, "" + str(os.path.basename(wsSoils)) + ".HYD_CODE", "!NLCD_RCN_TABLE.ID!", "PYTHON")
    arcpy.RemoveJoin_management(soilsLyr, "NLCD_RCN_TABLE")

    # ----------------------------------------------------------------------------------------------  Create Soils Raster
    # Set snap raster to clipped NLCD
    arcpy.env.snapRaster = landuse

    # Convert soils to raster using preset cellsize
    AddMsgAndPrint("\nCreating Hydro Groups Raster...",0)
    arcpy.PolygonToRaster_conversion(soilsLyr,"HYD_CODE",SOILS_GRID,"MAXIMUM_AREA","NONE","" + str(cellSize) + "")

    # ----------------------------------------------------------------------------------------------- Create Curve Number Grid
    # Combine Landuse and Soils
    #gp.Combine_sa(landuse + ";" + SOILS_GRID, LU_PLUS_SOILS)
    tempCombo = arcpy.sa.Combine(landuse + ";" + SOILS_GRID)
    tempCombo.save(LU_PLUS_SOILS)
    
    arcpy.BuildRasterAttributeTable_management(LU_PLUS_SOILS)

    # Add RCN field to raster attributes
    arcpy.AddField_management(LU_PLUS_SOILS, "HYD_CODE", "DOUBLE", "", "", "", "", "NULLABLE", "NON_REQUIRED", "")
    arcpy.CalculateField_management(LU_PLUS_SOILS, "HYD_CODE", "(!NLCD! * 100) + !SOILS!", "PYTHON")
    arcpy.AddField_management(LU_PLUS_SOILS, "LANDUSE", "TEXT", "", "", "255", "", "NULLABLE", "NON_REQUIRED", "")
    arcpy.AddField_management(LU_PLUS_SOILS, "HYD_GROUP", "TEXT", "", "", "", "", "NULLABLE", "NON_REQUIRED", "")
    arcpy.AddField_management(LU_PLUS_SOILS, "RCN", "DOUBLE", "", "", "", "", "NULLABLE", "NON_REQUIRED", "")
    arcpy.AddField_management(LU_PLUS_SOILS, "ACRES", "DOUBLE", "", "", "", "", "NULLABLE", "NON_REQUIRED", "")
    arcpy.AddField_management(LU_PLUS_SOILS, "WGT_RCN", "DOUBLE", "", "", "", "", "NULLABLE", "NON_REQUIRED", "")

    # Calculate area of each combined unit in acres
    if units == "Meters":
        arcpy.CalculateField_management(LU_PLUS_SOILS, "ACRES", "round(!COUNT! * (" + str(cellArea) + " / 4046.868564224),1)", "PYTHON")
    elif units == "Feet":
        arcpy.CalculateField_management(LU_PLUS_SOILS, "ACRES", "round(!COUNT! * (" + str(cellArea) + " / 43560),1)", "PYTHON")
    else:
        pass
    
    # Sum the count (equivalent to area) for each CN in watershed
    arcpy.Statistics_analysis(LU_PLUS_SOILS, RCN_Stats,"COUNT sum","")
    
    # Join NLCD Lookup table to retrieve RCN and desc values
    arcpy.MakeRasterLayer_management(LU_PLUS_SOILS, "LU_PLUS_SOILS_LYR")
    arcpy.AddJoin_management("LU_PLUS_SOILS_LYR", "HYD_CODE", NLCD_RCN_TABLE, "Join_", "KEEP_ALL")
    arcpy.CalculateField_management("LU_PLUS_SOILS_LYR", "VAT_LU_PLUS_SOILS.RCN", "!NLCD_RCN_TABLE.CN!", "PYTHON")
    arcpy.CalculateField_management("LU_PLUS_SOILS_LYR", "VAT_LU_PLUS_SOILS.LANDUSE", "!NLCD_RCN_TABLE.NRCS_LANDUSE!", "PYTHON")
    arcpy.CalculateField_management("LU_PLUS_SOILS_LYR", "VAT_LU_PLUS_SOILS.HYD_GROUP", "!NLCD_RCN_TABLE.Soil!", "PYTHON")

    # -------------------------------------------------------------------------------- Weight Curve Number    
    # Retrieve the total area (Watershed Area)
    rows = arcpy.SearchCursor(RCN_Stats)
    row = rows.next()
    wsArea = row.SUM_COUNT
    
    # Multiply CN by percent of area to weight
    arcpy.CalculateField_management(LU_PLUS_SOILS, "WGT_RCN", "!RCN! * (!COUNT! / " + str(float(wsArea)) + ")", "PYTHON")
    
    # Sum the weights to create weighted RCN
    arcpy.Statistics_analysis(LU_PLUS_SOILS, RCN_Stats2,"WGT_RCN sum","")
    wgtrows = arcpy.SearchCursor(RCN_Stats2)
    wgtrow = wgtrows.next()
    wgtRCN = wgtrow.SUM_WGT_RCN
    AddMsgAndPrint("\n\tWeighted Average Runoff Curve No. for " + str(wsName) + " is " + str(int(wgtRCN)),0)
    
    del wsArea
    del rows
    del row 
    del wgtrows
    del wgtrow
    
    # Export RCN Summary Table
    arcpy.CopyRows_management(LU_PLUS_SOILS, RCN_TABLE)
    
    # Delete un-necessary fields from summary table
    arcpy.DeleteField_management(RCN_TABLE, "VALUE;COUNT;SOILS;HYD_CODE;HYD_CODE;WGT_RCN")
    
    # ------------------------------------------------------------------ Pass results to user watershed
    AddMsgAndPrint("\nAdding RCN results to " + str(wsName) + "'s attributes",0)
    if not len(arcpy.ListFields(watershed,"RCN")) > 0:
        arcpy.AddField_management(watershed, "RCN", "LONG", "", "", "", "", "NULLABLE", "NON_REQUIRED", "")
    arcpy.CalculateField_management(watershed, "RCN", "" + str(wgtRCN) + "", "PYTHON")

    del wgtRCN
            
    # ------------------------------------------------------------------ Optional: Create Runoff Curve Number Grid
    if createRCN:
        AddMsgAndPrint("\nCreating Curve Number Raster...",0)
    
        # If user provided a snap raster, assign from input        
        if len(snapRaster) > 0:
            arcpy.env.snapRaster = snapRaster
            arcpy.env.outputCoordinateSystem = outCoordSys
            arcpy.env.cellSize = outCellSize
            del outCoordSys, outCellSize
        else:
            arcpy.env.snapRaster = landuse
            arcpy.env.cellSize = cellSize
            
        # Convert Combined Raster to Curve Number grid
        #gp.Lookup_sa(LU_PLUS_SOILS, "RCN", RCN_GRID)
        tempLU = arcpy.sa.Lookup(LU_PLUS_SOILS, "RCN")
        tempLU.save(RCN_GRID)
        
        AddMsgAndPrint("\nSuccessfully Created Runoff Curve Number Grid!",0)

    # ----------------------------------------------------- Delete Intermediate data
    layersToRemove = (LU_PLUS_SOILS,CULT_GRID,CULT_POLY,SOILS_GRID,RCN_Stats,RCN_Stats2,landuse)
    x = 0        
    for layer in layersToRemove:
        if arcpy.Exists(layer):
            # strictly for formatting
            if x == 0:
                AddMsgAndPrint("\nDeleting intermediate data...",0)
                x += 1
            try:
                arcpy.Delete_management(layer)
            except:
                pass
    del x, layersToRemove
    
    # ----------------------------------------------------------------------- Compact FGDB
    try:
        arcpy.Compact_management(watershedGDB_path)
        AddMsgAndPrint("\nSuccessfully Compacted FGDB: " + os.path.basename(watershedGDB_path),0)    
    except:
        pass
    
    # ------------------------------------------------------------ Prepare to Add to Arcmap
    AddMsgAndPrint("\nAdding Output to ArcMap...",0)
    
    if externalWshd:
        arcpy.SetParameterAsText(6, watershed)
    if createRCN:
        arcpy.SetParameterAsText(7, RCN_GRID)
    arcpy.SetParameterAsText(8, RCN_TABLE)
    
    arcpy.RefreshCatalog(watershedGDB_path)

except SystemExit:
    pass

except KeyboardInterrupt:
    AddMsgAndPrint("Interruption requested....exiting")

except:
    print_exception()    
