## Wascob_Attributes.py
##
## Created by Peter Mead, Adolfo Diaz, USDA NRCS, 2013
## Updated by Chris Morse, USDA NRCS, 2020
##
## Update watershed attributes using ProjectDEM and create AOI land use and soils layers with intersect

## ================================================================================================================
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
    f.write("Executing \"Wascob Watershed Attributes\" tool\n")
    f.write("User Name: " + getpass.getuser() + "\n")
    f.write("Date Executed: " + time.ctime() + "\n")
    f.write("ArcGIS Version: " + str(arcpy.GetInstallInfo()['Version']) + "\n")
    f.write("User Parameters:\n")
    f.write("\tWorkspace: " + userWorkspace + "\n")
    f.write("\tInput Watershed: " + wsName + "\n")
    f.write("\tInput Soils: " + inSoils + "\n")
    f.write("\tInput Hydrologic Groups Field: " + inputField + "\n")
    if len(inCLU) > 0:
        f.write("\tInput CLU: " + inCLU + "\n")
    else:
        f.write("\tInput CLU: BLANK" + "\n")
        
    f.close
    del f

## ================================================================================================================
def splitThousands(someNumber):
# will determine where to put a thousands seperator if one is needed.
# Input is an integer.  Integer with or without thousands seperator is returned.

    try:
        return re.sub(r'(\d{3})(?=\d)', r'\1,', str(int(round(someNumber)))[::-1])[::-1]
    except:
        print_exception()
        return someNumber    

## ================================================================================================================
# Import system modules
import arcpy, sys, os, string, traceback, re, math

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

    # Script Parameters
    inWatershed = arcpy.GetParameterAsText(0)
    inSoils = arcpy.GetParameterAsText(1)  
    inputField = arcpy.GetParameterAsText(2)
    inCLU = arcpy.GetParameterAsText(3)

    # Determine if CLU is present
    if len(str(inCLU)) > 0:
        inCLU = arcpy.Describe(inCLU).CatalogPath
        splitLU = True
    else:
        splitLU = False 
    
    # ---------------------------------------------------------------------------- Define Variables 
    watershed_path = arcpy.Describe(inWatershed).CatalogPath
    watershedGDB_path = watershed_path[:watershed_path .find(".gdb")+4]
    watershedGDB_name = os.path.basename(watershedGDB_path)
    userWorkspace = os.path.dirname(watershedGDB_path)
    watershedFD = watershedGDB_path + os.sep + "Layers"
    projectName = arcpy.ValidateTableName(os.path.basename(userWorkspace).replace(" ","_"))
    projectAOI = watershedFD + os.sep + projectName + "_AOI"
    projectAOI_path = arcpy.Describe(projectAOI).CatalogPath
    wsName = os.path.splitext(os.path.basename(inWatershed))[0]
    outputFolder = userWorkspace + os.sep + "gis_output"
    tables = outputFolder + os.sep + "tables"
    
    if not arcpy.Exists(outputFolder):
        arcpy.CreateFolder_management(userWorkspace, "gis_output")
    if not arcpy.Exists(tables):
        arcpy.CreateFolder_management(outputFolder, "tables")    

    #ReferenceLine = "ReferenceLine"
    ReferenceLine = watershedFD + os.sep + "ReferenceLine"

    DEM_aoi = watershedGDB_path + os.sep + projectName + "_Raw_DEM"
    ProjectDEM = watershedGDB_path + os.sep + projectName + "_Project_DEM"
    DEMsmooth = watershedGDB_path + os.sep + projectName + "_DEMsmooth"

    # -------------------------------------------------------------------------- Permanent Datasets
    wsSoils = watershedFD + os.sep + wsName + "_Soils"
    landuse = watershedFD + os.sep + wsName + "_Landuse"
    storageTable = tables + os.sep + "storage.dbf"
    embankmentTable = tables + os.sep + "embankments.dbf"
    
    # -------------------------------------------------------------------------- Temporary Datasets
    cluClip = watershedFD + os.sep + "cluClip"
    watershedDissolve = watershedGDB_path + os.sep + "watershedDissolve"
    wtshdDEMsmooth = watershedGDB_path + os.sep + "wtshdDEMsmooth"
    slopeGrid = watershedGDB_path + os.sep + "slopeGrid"
    slopeStats = watershedGDB_path + os.sep + "slopeStats"
    outletBuffer = watershedGDB_path + os.sep + "Layers" + os.sep + "outletBuffer"
    outletStats = watershedGDB_path + os.sep + "outletStats"
    subMask = watershedFD + os.sep + "subbasin_mask"
    subGrid = watershedGDB_path + os.sep + "subElev"   
    #storageTemp = tables + os.sep + "storageTemp"
    storageTemp = watershedGDB_path + os.sep + "storageTemp"
    
    # -------------------------------------------------------------------------- Tables
    TR_55_LU_Lookup = os.path.join(os.path.dirname(sys.argv[0]), "Support.gdb" + os.sep + "TR_55_LU_Lookup")
    Hydro_Groups_Lookup = os.path.join(os.path.dirname(sys.argv[0]), "Support.gdb" + os.sep + "HydroGroups")
    Condition_Lookup = os.path.join(os.path.dirname(sys.argv[0]), "Support.gdb" + os.sep + "ConditionTable")    
    storageTemplate = os.path.join(os.path.dirname(sys.argv[0]), "storage.dbf")

    # ---------------------------------------------------- Feature Layers in Arcmap
    landuseOut = "Watershed_Landuse"
    soilsOut = "Watershed_Soils"
    
    # Set path of log file and start logging
    textFilePath = userWorkspace + os.sep + os.path.basename(userWorkspace).replace(" ","_") + "_EngTools.txt"    
    logBasicSettings()

    # ----------------------------------------------------------------------------- Check Some Parameters
    # Exit if any are true
    AddMsgAndPrint("\nChecking input data and project data...",0)
    
    if not int(arcpy.GetCount_management(inWatershed).getOutput(0)) > 0:
        AddMsgAndPrint("\tWatershed Layer is empty!",2)
        AddMsgAndPrint("\tExiting...",2)
        sys.exit()
        
    if arcpy.Describe(inWatershed).ShapeType != "Polygon":
        AddMsgAndPrint("\tWatershed Layer must be a polygon layer!",2)
        AddMsgAndPrint("\tExiting...",2)
        sys.exit()

    if arcpy.Describe(inSoils).ShapeType != "Polygon":
        AddMsgAndPrint("\tSoils Layer must be a polygon layer!",2)
        AddMsgAndPrint("\tExiting...",2)
        sys.exit()

    if splitLU:
        if arcpy.Describe(inCLU).ShapeType != "Polygon":
            AddMsgAndPrint("\tCLU Layer must be a polygon layer!",2)
            AddMsgAndPrint("\tExiting...",2)
            sys.exit()

    if not arcpy.Exists(ProjectDEM):
        AddMsgAndPrint("\tProject DEM was not found in " + watershedGDB_path,2)
        AddMsgAndPrint("\tPlease run the Define AOI and the Create Stream Network tools from the WASCOB toolset.",2)
        AddMsgAndPrint("\tExiting...",2)
        sys.exit(0)
        
    if not len(arcpy.ListFields(inSoils,inputField)) > 0:
        AddMsgAndPrint("\tThe field specified for Hydro Groups does not exist in your soils data.",2)
        AddMsgAndPrint("\tPlease specify another name and try again.",2)
        AddMsgAndPrint("\tExiting...",2)
        sys.exit()

    if not arcpy.Exists(TR_55_LU_Lookup):
        AddMsgAndPrint("\t\"TR_55_LU_Lookup\" was not found!",2)
        AddMsgAndPrint("\tMake sure \"Support.gdb\" is located within the same location as this script.",2)
        AddMsgAndPrint("\tExiting...",2)
        sys.exit()

    if not arcpy.Exists(Hydro_Groups_Lookup):
        AddMsgAndPrint("\t\"Hydro_Groups_Lookup\" was not found!",2)
        AddMsgAndPrint("\tMake sure \"Support.gdb\" is located within the same location as this script.",2)
        AddMsgAndPrint("\tExiting...",2)
        sys.exit()

    if not arcpy.Exists(Condition_Lookup):
        AddMsgAndPrint("\t\"Condition_Lookup\" was not found!",2)
        AddMsgAndPrint("\tMake sure \"Support.gdb\" is located within the same location as this script.",2)
        AddMsgAndPrint("\tExiting...",2)
        sys.exit()          

    # ------------------------------------- Remove domains from fields if they exist
    desc = arcpy.Describe(watershedGDB_path)
    listOfDomains = []
    domains = desc.Domains

    for domain in domains:
        listOfDomains.append(domain)

    del desc, domains

    if "LandUse_Domain" in listOfDomains:
        try:
            arcpy.RemoveDomainFromField(landuse, "LANDUSE")
        except:
            pass
    if "Condition_Domain" in listOfDomains:
        try:
            arcpy.RemoveDomainFromField(landuse, "CONDITION")
        except:
            pass
    if "Hydro_Domain" in listOfDomains:
        try:
            arcpy.RemoveDomainFromField(wsSoils, "HYDGROUP")
        except:
            pass
        
    del listOfDomains

    # ------------------------------------------------------------------------------- Remove existing layers from ArcMap
    layersToRemove = (landuseOut,soilsOut)

    x = 0
    for layer in layersToRemove:
        if arcpy.Exists(layer):
            if x == 0:
                AddMsgAndPrint("Removing layers from ArcMap...",0)
                x+=1
            try:
                arcpy.delete_management(layer)
                AddMsgAndPrint("Removing " + layer + "...",0)
            except:
                pass
    del x, layersToRemove

    # -------------------------------------------------------------------------- Delete Previous Data if present
    datasetsToRemove = (wsSoils,landuse,cluClip,wtshdDEMsmooth,slopeGrid,slopeStats,watershedDissolve,cluClip,storageTemp,subMask,subGrid,outletStats,outletBuffer)

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
    
    # ------------------------------------------------------------------ Update inWatershed Area in case of user edits
    AddMsgAndPrint("\nUpdating drainage area(s)",0)
    
    wsUnits = arcpy.Describe(inWatershed).SpatialReference.LinearUnitName
    if wsUnits == "Meter" or wsUnits == "Foot" or wsUnits == "Foot_US" or wsUnits == "Feet":
        AddMsgAndPrint("\tLinear Units: " + wsUnits,0)
    else:
        AddMsgAndPrint("\tWatershed layer's linear units are UNKNOWN. Computed drainage area and other values may not be correct!",1)
    
    if len(arcpy.ListFields(inWatershed, "Acres")) < 1:
        # Acres field does not exist, so create it.
        arcpy.AddField_management(inWatershed, "Acres", "DOUBLE", "", "", "", "", "NULLABLE", "NON_REQUIRED", "")

    # Acres field now exists either way, so update it
    try:
        expression = "!shape.area@acres!"
        arcpy.CalculateField_management(inWatershed, "Acres", expression, "PYTHON")
        del expression
        displayAreaInfo = True
        AddMsgAndPrint("\nSuccessfully updated drainage area(s) acres.",0)
    except:
        displayAreaInfo = False
        AddMsgAndPrint("\nUnable to update drainage acres... You must manually calculate acres in " + str(wsName) + "'s attribute table",1)
        
    # -------------------------- Get DEM Properties using ProjectDEM for WASCOB workflow
    desc = arcpy.Describe(ProjectDEM)
    sr = desc.SpatialReference
    cellSize = desc.MeanCellWidth
    units = sr.LinearUnitName

    # We need XY and Z units to map out all conversion factors.
    # First get z units.
##    if arcpy.Exists(projectAOI):
##        rows = arcpy.SearchCursor(projectAOI)
##        row = rows.next()
##        zUnits = row.Z_UNITS
##        if not zUnits == "Meters" or zUnits == "Feet" or zUnits == "Inches" or zUnits == "Centimeters":
##            AddMsgAndPrint("\nProject or Input DEM has unknown vertical elevation (z) units. Cannot compute slope and volumes. Exiting...",2)
##            sys.exit()
##    else:
##        AddMsgAndPrint("\nProject AOI does not exist. This tool must be run on a project created with this toolbox which has an AOI. Exiting...",2)
##        sys.exit()
    #In this case we are using the ProjectDEM which has been converted to z units of feet, so we know the zUnits are feet.
    zUnits = "Feet"
    
    if units == "Meter" or units == "Meters":
        units = "Meters"

        # Area units in the Area_2D column output of the SurfaceVolume tool are always based on the XY of the input DEM, regardless of Z.
        ftConversion = 0.092903     # 0.092903 sq meters in 1 sq foot
        acreConversion = 4046.86    # 4046.86 sq meters in 1 acre

        # Zfactor varies by Z units and is for use with the Slope tool
        # Conversion factor varies by Z units and is always targeted at producting feet for the output values/reports.
        # Volume conversion varies by Z units and is dependent on the combination of XY units and Z units and is always aiming to create a calculation to get acre feet
##        if zUnits = "Meters":
##            Zfactor = 1                         # For Slope tool
##            conversionFactor = 3.280839896      # For computing Plane Height in Feet for output table. Convert meters to feet with times.
##            volConversion = 1233.48184          # For computing Volume in Acre Feet from square meters by meters (from cubic meters) for output table.
##
##        if zUnits = "Centimeters":
##            Zfactor = 0.01                      # For Slope tool
##            conversionFactor = 0.03280839896    # For computing Plane Height in Feet for output table. Convert centimeters to feet with times.
##            volConversion = 123348.184          # For computing Volume in Acre Feet from square meters by centimeters for output table.

        if zUnits == "Feet":
            Zfactor = 0.3048                    # For Slope tool
            conversionFactor = 1                # For computing Plane Height in Feet for output table. 1 foot in 1 foot
            volConversion = 4046.86             # For computing Volume in Acre Feet from square meters by feet for output table.

##        if zUnits = "Inches":
##            Zfactor = 0.0254                    # For Slope tool
##            conversionFactor = 0.0833333        # For computing Plane Height in Feet for output table. Convert inches to feet with times.
##            volConversion = 48562.339425        # For computing Volume in Acre Feet from square meters by inches for output table.

    elif units == "Foot" or units == "Foot_US" or units == "Feet":
        units = "Feet"

        # Area units in the Area_2D column output of the SurfaceVolume tool are always based on the XY of the input DEM, regardless of Z.
        ftConversion = 1            # 1 sq feet in 1 sq feet
        acreConversion = 43560      # 43560 sq feet in 1 acre

        # Zfactor varies by Z units and is for use with the Slope tool
        # Conversion factor varies by Z units and is always targeted at producting feet for the output values/reports.
        # Volume conversion varies by Z units and is dependent on the combination of XY units and Z units and is always aiming to create a calculation to get acre feet
##        if zUnits = "Meters":
##            Zfactor = 3.280839896               # For Slope tool
##            conversionFactor = 3.280839896      # For computing Plane Height in Feet for output table. Convert feet to feet with times.
##            volConversion = 13277.087996        # For computing Volume in Acre Feet from square feet by meters for output table.
##
##        if zUnits = "Centimeters":
##            Zfactor = 0.03280839896             # For Slope tool
##            conversionFactor = 0.03280839896    # For computing Plane Height in Feet for output table. Convert centimeters to feet with times.
##            volConversion = 1327708.799601      # For computing Volume in Acre Feet from square meters by centimeters for output table.

        if zUnits == "Feet":
            Zfactor = 1                         # For Slope tool
            conversionFactor = 1                # For computing Plane Height in Feet for output table. 1 foot in 1 foot
            volConversion = 43560               # For computing Volume in Acre Feet from square meters by feet for output table.

##        if zUnits = "Inches":
##            Zfactor = 0.0833333                 # For Slope tool
##            conversionFactor = 0.0833333        # For computing Plane Height in Feet for output table. Convert inches to feet with times.
##            volConversion = 522720.209088       # For computing Volume in Acre Feet from square meters by inches for output table.

    else:
        AddMsgAndPrint("\nLinear XY units of ProjectDEM could not be determined. Confirm input DEM in Define AOI step uses a projected coordinate system based on meters or feet. Exiting...",2)
        sys.exit()

    # ----------------------------------------------------------------------- Calculate Average Slope        
    calcAvgSlope = False
    AddMsgAndPrint("\nUpdating average slope",0)

    # Always re-create DEMsmooth in case people jumped from Watershed workflow to WASCOB workflow somehow and base on ProjectDEM in this WASCOB toolset
    arcpy.Delete_management(DEMsmooth)

    # Run Focal Statistics on the ProjectDEM for the purpose of generating smoothed results.
    tempFocal = arcpy.sa.FocalStatistics(ProjectDEM, "RECTANGLE 3 3 CELL","MEAN","DATA")
    tempFocal.save(DEMsmooth)
    
    # Extract area for slope from DEMSmooth and compute statistics for it
    tempExtract = arcpy.sa.ExtractByMask(DEMsmooth, inWatershed)
    tempExtract.save(wtshdDEMsmooth)
        
    tempSlope = arcpy.sa.Slope(wtshdDEMsmooth, "PERCENT_RISE", Zfactor)
    tempSlope.save(slopeGrid)
        
    arcpy.sa.ZonalStatisticsAsTable(inWatershed, "Subbasin", slopeGrid, slopeStats, "DATA")
    calcAvgSlope = True

    # Delete unwanted rasters
    arcpy.Delete_management(DEMsmooth)
    arcpy.Delete_management(wtshdDEMsmooth)
    arcpy.Delete_management(slopeGrid)   

    # -------------------------------------------------------------------------------------- Update inWatershed FC with Average Slope
    if calcAvgSlope:
        
        # go through each zonal Stat record and pull out the Mean value
        rows = arcpy.SearchCursor(slopeStats)
        row = rows.next()

        AddMsgAndPrint("\n\tSuccessfully re-calculated average slope",0)

        while row:
            wtshdID = row.OBJECTID
            
            # zonal stats doesnt generate "Value" with the 9.3 geoprocessor in 10
            if len(arcpy.ListFields(slopeStats,"Value")) > 0:
                zonalValue = row.VALUE
            else:
                zonalValue = row.SUBBASIN
   
            zonalMeanValue = row.MEAN

            whereclause = "Subbasin = " + str(zonalValue)
            wtshdRows = arcpy.UpdateCursor(inWatershed,whereclause)
            wtshdRow = wtshdRows.next()           

            # Pass the Mean value from the zonalStat table to the watershed FC.
            while wtshdRow:
                wtshdRow.Avg_Slope = zonalMeanValue
                wtshdRows.updateRow(wtshdRow)

                # Inform the user of Watershed Acres, area and avg. slope
                if displayAreaInfo:
                    
                    # Inform the user of Watershed Acres, area and avg. slope                    
                    AddMsgAndPrint("\n\tSubbasin ID: " + str(wtshdRow.OBJECTID),0)
                    AddMsgAndPrint("\t\tAcres: " + str(splitThousands(round(wtshdRow.Acres,2))),0)
                    AddMsgAndPrint("\t\tArea: " + str(splitThousands(round(wtshdRow.Shape_Area,2))) + " Sq. " + units,0)
                    AddMsgAndPrint("\t\tAvg. Slope: " + str(round(zonalMeanValue,2)),0)
                    if wtshdRow.Acres > 40:
                        AddMsgAndPrint("\t\tSubbasin " + str(wtshdRow.OBJECTID) + " is greater than the 40 acre 638 standard.",1)
                        AddMsgAndPrint("\t\tConsider re-delineating to split basins or move upstream.",1)

                else:
                    AddMsgAndPrint("\tWatershed ID: " + str(wtshdRow.OBJECTID) + " is " + str(zonalMeanValue),0)
                                   
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
        
        arcpy.Delete_management(slopeStats)
    
    # ------------------------------------------------------------------------ Update reference line / Perform storage calculations                          
    calcSurfaceVol = False

    if arcpy.Exists(ReferenceLine):
        calcSurfaceVol = True

    else:
        AddMsgAndPrint("\nReference Line not found in table of contents or in the workspace of your input watershed,",1)
        AddMsgAndPrint("\nUnable to update attributes to perform surface volume calculations.",1)
        AddMsgAndPrint("\nYou will have to either correct the workspace issue or manually derive surface / volume calculations for " + str(wsName),1)
            
    # -------------------------------------------------------------------------- Update Reference Line Attributes
    if calcSurfaceVol:
        AddMsgAndPrint("\nUpdating Reference Line Attributes...",0)
        arcpy.CalculateField_management(ReferenceLine, "LengthFt","!shape.length@feet!", "PYTHON")
        
        # Buffer outlet features by raster cell size * 2; and dissolve by Subbasin ID
        bufferSize = cellSize * 2
        bufferDist = "" + str(bufferSize) + " " + str(units) + ""
        arcpy.Buffer_analysis(ReferenceLine, outletBuffer, bufferDist, "FULL", "ROUND", "LIST", "Subbasin")
        del bufferSize, bufferDist

        # Get Reference Line Elevation Properties
        arcpy.sa.ZonalStatisticsAsTable(outletBuffer, "Subbasin", ProjectDEM, outletStats, "DATA")
        
        rows = arcpy.SearchCursor(outletStats)
        row = rows.next()

        while row:
            wtshdID = row.OBJECTID

            # zonal stats doesnt generate "Value" with the 9.3 geoprocessor in 10
            if len(arcpy.ListFields(outletStats,"Value")) > 0:
                zonalValue = row.VALUE
            else:
                zonalValue = row.SUBBASIN

            zonalMaxValue = row.MAX   
            zonalMeanValue = row.MEAN
            zonalMinValue = row.MIN

            whereclause = "Subbasin = " + str(zonalValue)
            refRows = arcpy.UpdateCursor(ReferenceLine,whereclause)
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

        AddMsgAndPrint("\n\tSuccessfully updated Reference Line attributes.",0)
        arcpy.Delete_management(outletStats)
        arcpy.Delete_management(outletBuffer)
    
        # --------------------------------------------------------------------- Begin Subbasin Stage Storage Calcs
        AddMsgAndPrint("\nBeginning subbasin storage calculations...",0)
        arcpy.CopyRows_management(storageTemplate, storageTable, "")
        rows = arcpy.UpdateCursor(ReferenceLine)
        row = rows.next()
        while row:
            value = row.Subbasin
            query = "Subbasin"+" = " +str(value)
            arcpy.SelectLayerByAttribute_management(inWatershed, "NEW_SELECTION", query)
            arcpy.CopyFeatures_management(inWatershed, subMask)
            tempExtract2 = arcpy.sa.ExtractByMask(ProjectDEM, subMask)
            tempExtract2.save(subGrid)
            
            AddMsgAndPrint("\n\tRetrieving Minumum Elevation for subbasin "+ str(value) + "\n",0)
            maxValue = row.MaxElev
            MinElev = round(float(arcpy.GetRasterProperties_management(subGrid, "MINIMUM").getOutput(0)),1)
            totalElev = round(float(maxValue - MinElev),1)
            roundElev = math.floor(totalElev)
            remainder = totalElev - roundElev
            
            Reference_Plane = "BELOW"
            plnHgt = MinElev + remainder
            outputText = tables + os.sep + "subbasin" + str(value) +".txt"

            f = open(outputText, "w")
            f.write("Dataset, Plane_heig, Reference, Z_Factor, Area_2D, Area_3D, Volume, Subbasin\n")
            f.close()
            
            while plnHgt <= maxValue:
                Plane_Height = plnHgt
                AddMsgAndPrint("\tCalculating storage at elevation " + str(round(plnHgt,1)),0)
                arcpy.SurfaceVolume_3d(subGrid, outputText, Reference_Plane, Plane_Height, 1)
                plnHgt = 1 + plnHgt

            AddMsgAndPrint("\n\t\t\t\tConverting results...",0)
            arcpy.CopyRows_management(outputText, storageTemp, "")
            arcpy.CalculateField_management(storageTemp, "Subbasin", value, "PYTHON")

            arcpy.Append_management(storageTemp, storageTable, "NO_TEST", "", "")
            arcpy.Delete_management(storageTemp)
            
            rows.updateRow(row)
            row = rows.next()
            
        del rows
        del maxValue
        del MinElev
        del totalElev
        del roundElev
        del remainder
        del Reference_Plane
        del plnHgt
        del outputText
        
        arcpy.SelectLayerByAttribute_management(inWatershed, "CLEAR_SELECTION", "")

        arcpy.AddField_management(storageTable, "ELEV_FEET", "DOUBLE", "5", "1", "", "", "NULLABLE", "NON_REQUIRED", "")
        arcpy.AddField_management(storageTable, "POOL_SQFT", "DOUBLE", "", "", "", "", "NULLABLE", "NON_REQUIRED", "")
        arcpy.AddField_management(storageTable, "POOL_ACRES", "DOUBLE", "", "", "", "", "NULLABLE", "NON_REQUIRED", "")
        arcpy.AddField_management(storageTable, "ACRE_FOOT", "DOUBLE", "", "", "", "", "NULLABLE", "NON_REQUIRED", "")

        # Convert area sq feet and volume to cu ft (as necessary)
        elevFeetCalc = "round(!Plane_heig! *" + str(conversionFactor) + ",1)"
        pool2dSqftCalc = "round(!Area_2D! /" + str(ftConversion) + ",1)"
        pool2dAcCalc = "round(!Area_2D! /" + str(acreConversion) + ",1)"
        #pool3dSqftCalc = "round([Area_3D] /" + str(ftConversion) + ",1)"
        cuFootCalc = "round(!Volume! /" + str(volConversion) + ",1)"
                
        arcpy.CalculateField_management(storageTable, "Subbasin", "'Subbasin' + !Subbasin!", "PYTHON")
        arcpy.CalculateField_management(storageTable, "ELEV_FEET", elevFeetCalc, "PYTHON")
        arcpy.CalculateField_management(storageTable, "POOL_SQFT", pool2dSqftCalc, "PYTHON")
        arcpy.CalculateField_management(storageTable, "POOL_ACRES", pool2dAcCalc, "PYTHON")
        #gp.CalculateField_management(storageTable, "Area_3D", pool3dSqftCalc, "VB")
        arcpy.CalculateField_management(storageTable, "ACRE_FOOT", cuFootCalc, "PYTHON")
        
        AddMsgAndPrint("\n\tSurface volume and area calculations completed",0)

        arcpy.Delete_management(subMask)
        arcpy.Delete_management(subGrid)
        
    # -------------------------------------------------------------------------- Process Soils and Landuse Data
    
    AddMsgAndPrint("\nProcessing Soils and Landuse for " + str(wsName) + "...",0)
    
    # -------------------------------------------------------------------------- Create Landuse Layer
    if splitLU:

        # Dissolve in case the watershed has multiple polygons        
        arcpy.Dissolve_management(inWatershed, watershedDissolve, "", "", "MULTI_PART", "DISSOLVE_LINES")

        # Clip the CLU layer to the dissolved watershed layer
        arcpy.Clip_analysis(inCLU, watershedDissolve, cluClip, "")
        AddMsgAndPrint("\n\tSuccessfully clipped the CLU to your Watershed Layer",0)

        # Union the CLU and dissolve watershed layer simply to fill in gaps
        arcpy.Union_analysis(cluClip +";" + watershedDissolve, landuse, "ONLY_FID", "", "GAPS")
        AddMsgAndPrint("\tSuccessfully filled in any CLU gaps and created Landuse Layer: " + os.path.basename(landuse),0)

        # Delete FID field
        fields = arcpy.ListFields(landuse,"FID*")

        for field in fields:
            arcpy.DeleteField_management(landuse,field.Name)

        del fields

        arcpy.Delete_management(watershedDissolve)
        arcpy.Delete_management(cluClip)

    else:
        AddMsgAndPrint("\nNo CLU Layer Detected",0)

        arcpy.Dissolve_management(inWatershed, landuse, "", "", "MULTI_PART", "DISSOLVE_LINES")
        AddMsgAndPrint("\n\tSuccessfully created Watershed Landuse layer: " + os.path.basename(landuse),0)

    arcpy.AddField_management(landuse, "LANDUSE", "TEXT", "", "", "254", "", "NULLABLE", "NON_REQUIRED", "")
    arcpy.CalculateField_management(landuse, "LANDUSE", "\"- Select Land Use -\"", "PYTHON")
    
    arcpy.AddField_management(landuse, "CONDITION", "TEXT", "", "", "25", "", "NULLABLE", "NON_REQUIRED", "")    
    arcpy.CalculateField_management(landuse, "CONDITION", "\"- Select Condition -\"", "PYTHON")

    # ---------------------------------------------------------------------------------------------- Set up Domains
    desc = arcpy.Describe(watershedGDB_path)
    listOfDomains = []

    domains = desc.Domains

    for domain in domains:
        listOfDomains.append(domain)

    del desc, domains

    if not "LandUse_Domain" in listOfDomains:
        arcpy.TableToDomain_management(TR_55_LU_Lookup, "LandUseDesc", "LandUseDesc", watershedGDB_path, "LandUse_Domain", "LandUse_Domain", "REPLACE")

    if not "Hydro_Domain" in listOfDomains:
        arcpy.TableToDomain_management(Hydro_Groups_Lookup, "HydrolGRP", "HydrolGRP", watershedGDB_path, "Hydro_Domain", "Hydro_Domain", "REPLACE")

    if not "Condition_Domain" in listOfDomains:
        arcpy.TableToDomain_management(Condition_Lookup, "CONDITION", "CONDITION", watershedGDB_path, "Condition_Domain", "Condition_Domain", "REPLACE")

    del listOfDomains

    # Assign Domain To Landuse Fields for User Edits...
    arcpy.AssignDomainToField_management(landuse, "LANDUSE", "LandUse_Domain", "")
    arcpy.AssignDomainToField_management(landuse, "CONDITION", "Condition_Domain", "")

    AddMsgAndPrint("\tSuccessfully added \"LANDUSE\" and \"CONDITION\" fields to Landuse Layer and associated Domains",0)

    # ---------------------------------------------------------------------------------------------------------------------------------- Work with soils
    
    # --------------------------------------------------------------------------------------- Clip Soils           
    # Clip the soils to the dissolved (and possibly unioned) watershed
    arcpy.Clip_analysis(inSoils,landuse,wsSoils)

    AddMsgAndPrint("\nSuccessfully clipped soils layer to Landuse layer and removed unnecessary fields",0)  
    
    # --------------------------------------------------------------------------------------- check the soils input Field to make
    # --------------------------------------------------------------------------------------- sure they are valid Hydrologic Group values
    AddMsgAndPrint("\nChecking Hydrologic Group Attributes in Soil Layer.....",0)
                   
    validHydroValues = ['A','B','C','D','A/D','B/D','C/D','W']
    valuesToConvert = ['A/D','B/D','C/D','W']
    
    rows = arcpy.SearchCursor(wsSoils)
    row = rows.next()
    
    invalidHydValues = 0
    valuesToConvertCount = 0
    emptyValues = 0
    missingValues = 0
    
    while row:
        hydValue = str(row.getValue(inputField))
        if len(hydValue) > 0:  # Not NULL Value
            if not hydValue in validHydroValues:
                invalidHydValues += 1
                AddMsgAndPrint("\t\t" + "\"" + hydValue + "\" is not a valid Hydrologic Group Attribute",0)
            if hydValue in valuesToConvert:
                valuesToConvertCount += 1
                #AddMsgAndPrint("\t" + "\"" + hydValue + "\" needs to be converted -------- " + str(valuesToConvertCount),1)
        else: # NULL Value
            emptyValues += 1
        row = rows.next()
    del rows, row        

    # ------------------------------------------------------------------------------------------- Inform the user of Hydgroup Attributes
    if invalidHydValues > 0:
        AddMsgAndPrint("\t\tThere are " + str(invalidHydValues) + " invalid attributes found in your Soil's " + "\"" + inputField + "\"" + " Field",0)

    if valuesToConvertCount > 0:
        AddMsgAndPrint("\t\tThere are " + str(valuesToConvertCount) + " attributes that need to be converted to a single class i.e. \"B/D\" to \"B\"",0)

    if emptyValues > 0:
        AddMsgAndPrint("\t\tThere are " + str(emptyValues) + " NULL polygon(s) that need to be attributed with a Hydrologic Group",0)

    if emptyValues == int(arcpy.GetCount_management(inSoils).getOutput(0)):
        AddMsgAndPrint("\t\t" + "\"" + inputField + "\"" + "Field is blank.  It must be populated before using this tool!",0)
        missingValues = 1
        
    del validHydroValues, valuesToConvert, invalidHydValues

    # ------------------------------------------------------------------------------------------- Compare Input Field to SSURGO HydroGroup field name
    if inputField.upper() != "HYDGROUP":
        arcpy.AddField_management(wsSoils, "HYDGROUP", "TEXT", "", "", "20", "", "NULLABLE", "NON_REQUIRED", "")

        if missingValues == 0:
            arcpy.CalculateField_management(wsSoils, "HYDGROUP", "!" + str(inputField) + "!", "PYTHON")

        else:
            AddMsgAndPrint("\n\tAdded " + "\"HYDGROUP\" to soils layer.  Please Populate the Hydrologic Group Values manually for this field",0)

    # Delete any field not in the following list
    fieldsToKeep = ["MUNAME","MUKEY","HYDGROUP","MUSYM","OBJECTID"]

    fields = arcpy.ListFields(wsSoils)

    for field in fields:
        fieldName = field.name
        if not fieldName.upper() in fieldsToKeep and fieldName.find("Shape") < 0:
            arcpy.DeleteField_management(wsSoils,fieldName)

    del fields, fieldsToKeep, missingValues

    arcpy.AssignDomainToField_management(wsSoils, "HYDGROUP", "Hydro_Domain", "")


    # ---------------------------------------------------------------------------------------------------------------------------- Compact FGDB
    try:
        arcpy.Compact_management(watershedGDB_path)
        AddMsgAndPrint("\nSuccessfully Compacted FGDB: " + os.path.basename(watershedGDB_path),0)
    except:
        pass
    # --------------------------------------------------------------------------------------------------------------------------- Prepare to Add to Arcmap
    
    arcpy.SetParameterAsText(4, wsSoils)
    arcpy.SetParameterAsText(5, landuse)

    # Copy refernce line to embankment table
    arcpy.CopyRows_management(ReferenceLine, embankmentTable, "")
    
    AddMsgAndPrint("\nAdding Layers to ArcMap",0)

    AddMsgAndPrint("\n\t=========================================================================",0)
    AddMsgAndPrint("\tBEFORE CALCULATING THE RUNOFF CURVE NUMBER FOR YOUR WATERSHED MAKE SURE TO",0)
    AddMsgAndPrint("\tATTRIBUTE THE \"LANDUSE\" AND \"CONDITION\" FIELDS IN " + os.path.basename(landuse) + " LAYER",0)
    
    if valuesToConvertCount > 0:
        AddMsgAndPrint("\tAND CONVERT THE " + str(valuesToConvertCount) + " COMBINED HYDROLOGIC GROUPS IN " + os.path.basename(wsSoils) + " LAYER",0)
        
    if emptyValues > 0:
        AddMsgAndPrint("\tAS WELL AS POPULATE VALUES FOR THE " + str(emptyValues) + " NULL POLYGONS IN " + os.path.basename(wsSoils) + " LAYER",0)
        
    AddMsgAndPrint("\t=========================================================================\n",0)   

    # -------------------------------------
    arcpy.RefreshCatalog(watershedGDB_path)
    
except SystemExit:
    pass

except KeyboardInterrupt:
    AddMsgAndPrint("Interruption requested....exiting")

except:
    print_exception()
