## CalculateStageStorageVolume.py
##
## Created by Peter Mead, Adolfo Diaz, USDA NRCS, 2013
## Updated by Chris Morse, USDA NRCS, 2020
##
## Calculates and returns the storage volume and surface area within a watershed or pool area at a user specified interval.
## Optionally creates pools at each elevation.

## ================================================================================================================ 
def print_exception():
    
    tb = sys.exc_info()[2]
    l = traceback.format_tb(tb)
    l.reverse()
    tbinfo = "".join(l)
    AddMsgAndPrint("\n----------ERROR Start-------------------",2)
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
    f.write("Executing \"Calculate Stage Storage Volume\" tool\n")
    f.write("User Name: " + getpass.getuser() + "\n")
    f.write("Date Executed: " + time.ctime() + "\n")
    f.write("ArcGIS Version: " + str(arcpy.GetInstallInfo()['Version']) + "\n")
    f.write("User Parameters:\n")
    f.write("\tWorkspace: " + userWorkspace + "\n")
    f.write("\tInput Dem: " + arcpy.Describe(inputDEM).CatalogPath + "\n")
    f.write("\tElevation Z-units: " + zUnits + "\n")
    f.write("\tInput Watershed or Pool Mask: " + str(inPool) + "\n")
    f.write("\tMaximum Elevation: " + str(maxElev) + " Feet\n")
    f.write("\tAnalysis Increment: " + str(userIncrement) + " Feet\n")
    if b_createPools:
        f.write("\tCreate Pool Polygons: YES\n")  
    else:
        f.write("\tCreate Pool Polygons: NO\n")
    
    f.close
    del f

## ================================================================================================================
def createPool(elevationValue,storageTxtFile):
    try:
        global conversionFactor,acreConversion,ftConversion,volConversion

        tempDEM2 = watershedGDB_path + os.sep + "tempDEM2"
        tempDEM3 = watershedGDB_path + os.sep + "tempDEM3"
        tempDEM4 = watershedGDB_path + os.sep + "tempDEM4"
        poolTemp = watershedFD + os.sep + "poolTemp"
        poolTempLayer = os.path.dirname(watershedGDB_path) + os.sep + "poolTemp.shp"

        # Just in case they exist Remove them
        layersToRemove = (tempDEM2,tempDEM3,tempDEM4,poolTemp,poolTempLayer)
           
        for layer in layersToRemove:
            if arcpy.Exists(layer):
                try:
                    arcpy.Delete_management(layer)
                except:
                    pass

        fcName =  ("Pool_" + str(round((elevationValue * conversionFactor),1))).replace(".","_")
        
        poolExit = watershedFD + os.sep + fcName        

        # Create new raster of only values below an elevation value
        conStatement = "Value > " + str(elevationValue)
        #gp.SetNull_sa(tempDEM, tempDEM, tempDEM2, conStatement)
        tempNull = arcpy.sa.SetNull(tempDEM, tempDEM, conStatement)
        tempNull.save(tempDEM2)

        # Multiply every pixel by 0 and convert to integer for vectorizing
        # with geoprocessor 9.3 you need to have 0 w/out quotes.
        #gp.Times_sa(tempDEM2, 0, tempDEM3)
        tempTimes = arcpy.sa.Times(tempDEM2, 0)
        tempTimes.save(tempDEM3)
        
        #gp.Int_sa(tempDEM3, tempDEM4)
        tempInt = arcpy.sa.Int(tempDEM3)
        tempInt.save(tempDEM4)

        # Convert to polygon and dissolve
        # This continuously fails despite changing env settings.  Works fine from python win
        # but always fails from arcgis 10 not 9.3.  Some reason ArcGIS 10 thinks that the
        # output of RasterToPolygon is empty?
        try:
            arcpy.RasterToPolygon_conversion(tempDEM4, poolTemp, "NO_SIMPLIFY", "VALUE")
            
        except:
            if arcpy.Exists(poolTemp):
                pass
                 #AddMsgAndPrint(" ",0)
            else:
                AddMsgAndPrint("\n" + arcpy.GetMessages(2) + "\n",2)
                sys.exit()

        arcpy.CopyFeatures_management(poolTemp,poolTempLayer)
        arcpy.Dissolve_management(poolTempLayer, poolExit, "", "", "MULTI_PART", "DISSOLVE_LINES")
      
        arcpy.AddField_management(poolExit, "ELEV_FEET", "DOUBLE", "", "", "", "", "NULLABLE", "NON_REQUIRED", "")
        arcpy.AddField_management(poolExit, "POOL_ACRES", "DOUBLE", "", "", "", "", "NULLABLE", "NON_REQUIRED", "")
        arcpy.AddField_management(poolExit, "POOL_SQFT", "DOUBLE", "", "", "", "", "NULLABLE", "NON_REQUIRED", "")
        arcpy.AddField_management(poolExit, "ACRE_FOOT", "DOUBLE", "", "", "", "", "NULLABLE", "NON_REQUIRED", "")

        # open storageCSV file and read the last line which should represent the last pool
        file = open(storageTxtFile)
        lines = file.readlines()
        file.close()    

        area2D = float(lines[len(lines)-1].split(',')[4])
        volume = float(lines[len(lines)-1].split(',')[6])

        elevFeetCalc = round(elevationValue * conversionFactor,1)
        poolAcresCalc = round(area2D / acreConversion,1)
        poolSqftCalc = round(area2D / ftConversion,1)
        acreFootCalc = round(volume / volConversion,1)
     
        arcpy.CalculateField_management(poolExit, "ELEV_FEET", elevFeetCalc, "PYTHON")
        arcpy.CalculateField_management(poolExit, "POOL_ACRES", poolAcresCalc, "PYTHON")
        arcpy.CalculateField_management(poolExit, "POOL_SQFT", poolSqftCalc, "PYTHON")
        arcpy.CalculateField_management(poolExit, "ACRE_FOOT", acreFootCalc, "PYTHON")

        AddMsgAndPrint("\n\tCreated " + fcName + ":",0)
        AddMsgAndPrint("\t\tArea:   " + str(splitThousands(round(poolSqftCalc,1))) + " Sq.Feet",0)
        AddMsgAndPrint("\t\tAcres:  " + str(splitThousands(round(poolAcresCalc,1))),0)
        AddMsgAndPrint("\t\tVolume: " + str(splitThousands(round(acreFootCalc,1))) + " Ac. Foot",0)

        #------------------------------------------------------------------------------------ Delete Temp Layers
        layersToRemove = (tempDEM2,tempDEM3,tempDEM4,poolTemp,poolTempLayer)
     
        for layer in layersToRemove:
            if arcpy.Exists(layer):
                try:
                    arcpy.Delete_management(layer)
                except:
                    pass

    except:
        AddMsgAndPrint("\nFailed to Create Pool Polygon for elevation value: " + str(elevationValue),1)
        print_exception()
        sys.exit()
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
        sys.exit()

    # Check out 3D Analyst License        
    if arcpy.CheckExtension("3D") == "Available":
        arcpy.CheckOutExtension("3D")
    else:
        arcpy.AddError("3D Analyst Extension not enabled. Please enable 3D Analyst from the Tools/Extensions menu. Exiting...\n")
        sys.exit()

    #----------------------------------------------------------------------------------------- Input Parameters
    inputDEM = arcpy.GetParameterAsText(0)
    zUnits = arcpy.GetParameterAsText(1)
    inPool = arcpy.GetParameterAsText(2)
    maxElev = float(arcpy.GetParameterAsText(3))
    userIncrement = float(arcpy.GetParameterAsText(4))
    b_createPools = arcpy.GetParameter(5)
    
    # ---------------------------------------------------------------------------------------- Define Variables
    inPool = arcpy.Describe(inPool).CatalogPath
    if inPool.find('.gdb') > -1 or inPool.find('.mdb') > -1:
        watershedGDB_path = inPool[:inPool.find('.')+4]
    elif inPool.find('.shp')> -1:
        watershedGDB_path = os.path.dirname(inPool) + os.sep + os.path.basename(os.path.dirname(inPool)).replace(" ","_") + "_EngTools.gdb"
    else:
        arcpy.AddError("\nPool Polygon must either be a feature class or shapefile. Exiting...")
        sys.exit()

    watershedGDB_name = os.path.basename(watershedGDB_path)
    watershedFD = watershedGDB_path + os.sep + "Layers"
    poolName = os.path.splitext(os.path.basename(inPool))[0]
    userWorkspace = os.path.dirname(watershedGDB_path)

    # ------------------------------------------- Layers in Arcmap
    poolMergeOut = "" + arcpy.ValidateTableName(poolName) + "_All_Pools"
    storageTableView = "Stage_Storage_Table"

    # Storage CSV file
    storageCSV = userWorkspace + os.sep + poolName + "_storageCSV.txt"

    # ---------------------------------------------------------------------- Datasets
    tempDEM = watershedGDB_path + os.sep + "tempDEM"
    storageTable = watershedGDB_path + os.sep + arcpy.ValidateTableName(poolName) + "_storageTable"
    PoolMerge = watershedFD + os.sep + arcpy.ValidateTableName(poolName) + "_All_Pools"

    # Set log file path and start logging
    textFilePath = userWorkspace + os.sep + os.path.basename(userWorkspace).replace(" ","_") + "_EngTools.txt"
    logBasicSettings()
    
    # ---------------------------------------------------------------------------------------------- Check Parameters
    AddMsgAndPrint("\nChecking inputs...",0)
    # Exit if inPool has more than 1 polygon    
    if int(arcpy.GetCount_management(inPool).getOutput(0)) > 1:
        AddMsgAndPrint("\tOnly ONE Watershed or Pool Polygon can be submitted.",2)
        AddMsgAndPrint("\tEither export an individual polygon from your " + os.path.basename(inPool) + " layer, ",2)
        AddMsgAndPrint("\tmake a single selection, or provide a different input. Exiting...",2)
        sys.exit()

    # Exit if inPool is not a Polygon geometry
    if arcpy.Describe(inPool).ShapeType != "Polygon":
        AddMsgAndPrint("\tYour watershed or pool area must be a polygon layer! Exiting...",2)
        sys.exit()        

    # Exit if Elevation value is less than 1
    if maxElev < 1:
        AddMsgAndPrint("\tMaximum Elevation Value must be greater than 0! Exiting...",2)
        sys.exit()

    # Exit if elevation increment is not greater than 0
    if userIncrement < 0.5:
        AddMsgAndPrint("\tAnalysis Increment Value must be greater than or equal to 0.5! Exiting...",2)
        sys.exit()        
    
    # ---------------------------------------------------------------------------------------------- Check DEM Coordinate System and Linear Units
    desc = arcpy.Describe(inputDEM)
    sr = desc.SpatialReference
    cellSize = desc.MeanCellWidth
    units = sr.LinearUnitName

    # Coordinate System must be a Projected type in order to continue.       
    if not sr.Type == "Projected":
        AddMsgAndPrint("\n" + os.path.basename(inputDEM) + " is NOT in a projected Coordinate System! Exiting...",2)
        sys.exit()
        
    # ----------------------------------------- Set Linear and Volume Conversion Factors
    # We need XY and Z units to map out all conversion factors.
    # First we have the z units, which came from now required parameter input by the user. Use it to set Zfactor for convering input max elevation from feet to the DEM's z-units
    if zUnits == "Meters":
        Zfactor = 0.3048                    # Converts feet to meters
    if zUnits == "Centimeters":
        Zfactor = 30.48                     # Converts feet to centimeters
    if zUnits == "Feet":
        Zfactor = 1                         # Converts feet to feet
    if zUnits == "Inches":
        Zfactor = 12                        # Converts feet to inches
    
    # Now start setting factors based on xy and z unit combinations.
    if units == "Meter" or units == "Meters":
        units = "Meters"

        # Area units in the Area_2D column output of the SurfaceVolume tool are always based on the XY of the input DEM, regardless of Z.
        ftConversion = 0.09290304           # 0.092903 sq meters in 1 sq foot
        acreConversion = 4046.868564224     # 4046.86 sq meters in 1 acre

        # Zfactor varies by Z units and is for converting the input maxElev (which is always in Feet) to the DEM's actual Z units
        # Conversion factor varies by Z units and is always targeted at producting feet for the output values/reports.
        # Volume conversion varies by Z units and is dependent on the combination of XY units and Z units and is always aiming to create a calculation to get acre feet
        if zUnits == "Meters":
            conversionFactor = 3.280839896      # For computing Plane Height in Feet for output table. Convert meters to feet with times.
            volConversion = 1233.48184          # For computing Volume in Acre Feet from square meters by meters (from cubic meters).

        if zUnits == "Centimeters":
            conversionFactor = 0.03280839896    # For computing Plane Height in Feet for output table. Convert centimeters to feet with times.
            volConversion = 123348.184          # For computing Volume in Acre Feet from square meters by centimeters.

        if zUnits == "Feet":
            conversionFactor = 1                # For computing Plane Height in Feet for output table. 1 foot in 1 foot
            volConversion = 4046.868564224      # For computing Volume in Acre Feet from square meters by feet.

        if zUnits == "Inches":
            conversionFactor = 0.0833333        # For computing Plane Height in Feet for output table. Convert inches to feet with times.
            volConversion = 48562.339425        # For computing Volume in Acre Feet from square meters by inches.

    elif units == "Foot" or units == "Foot_US" or units == "Feet":
        units = "Feet"

        # Area units in the Area_2D column output of the SurfaceVolume tool are always based on the XY of the input DEM, regardless of Z.
        ftConversion = 1            # 1 sq feet in 1 sq feet
        acreConversion = 43560      # 43560 sq feet in 1 acre

        if zUnits == "Meters":
            conversionFactor = 3.280839896      # For computing Plane Height in Feet for output table. Convert feet to feet with times.
            volConversion = 13277.087996        # For computing Volume in Acre Feet from square feet by meters for output table.

        if zUnits == "Centimeters":
            conversionFactor = 0.03280839896    # For computing Plane Height in Feet for output table. Convert centimeters to feet with times.
            volConversion = 1327708.799601      # For computing Volume in Acre Feet from square meters by centimeters for output table.

        if zUnits == "Feet":
            conversionFactor = 1                # For computing Plane Height in Feet for output table. 1 foot in 1 foot
            volConversion = 43560               # For computing Volume in Acre Feet from square meters by feet for output table.

        if zUnits == "Inches":
            conversionFactor = 0.0833333        # For computing Plane Height in Feet for output table. Convert inches to feet with times.
            volConversion = 522720.209088       # For computing Volume in Acre Feet from square meters by inches for output table.

    else:
        AddMsgAndPrint("\nLinear XY units of input DEM could not be determined. Confirm input DEM uses a projected coordinate system based on meters or feet. Exiting...",2)
        sys.exit()
        
##    #Old Unit conversions, seems to be based on an assumption that zUnits of input DEM are always feet (not the case in the toolbox, yet)
##    if units == "Meter":
##        units = "Meters"
##        acreConversion = 4046.86    # 4046 sq meters in an acre
##        ftConversion = 0.092903     # 0.093 sq meters in 1 sq foot
##        volConversion = 1233.48184  # 1233 cubic meters in 1 acre @ 1FT depth
##
##    elif units == "Foot":
##        units = "Feet"
##        acreConversion = 43560      # 43560 sq feet in an acre
##        ftConversion = 1            # no conversion necessary
##        volConversion = 43560       # 43560 cu feet in 1 acre @ 1FT depth
##
##    elif units == "Foot_US":
##        units = "Feet"
##        acreConversion = 43560      # 43560 sq feet in an acre
##        ftConversion = 1            # no conversion necessary
##        volConversion = 43560       # 43560 cu feet in 1 acre @ 1FT depth
##    else:
##        AddMsgAndPrint("\nCould not determine linear units of DEM....Exiting!",2)
##        sys.exit()

    # ----------------------------------------- Output messages to user about DEM info
    AddMsgAndPrint("\nInput DEM information: ",0)
    AddMsgAndPrint("\tProjection Name: " + sr.Name,0)
    AddMsgAndPrint("\tXY Linear Units: " + units,0)
    AddMsgAndPrint("\tElevation Values (Z): " + zUnits,0) 
    AddMsgAndPrint("\tCell Size: " + str(desc.MeanCellWidth) + " x " + str(desc.MeanCellHeight) + " " + units,0)

    # --------------------------------------------------------------------------- Create FGDB, FeatureDataset
    # Boolean - Assume FGDB already exists
    FGDBexists = True
                      
    # Create Watershed FGDB and feature dataset if it doesn't exist
    if not arcpy.Exists(watershedGDB_path):
        arcpy.CreateFileGDB_management(userWorkspace, watershedGDB_name)
        arcpy.CreateFeatureDataset_management(watershedGDB_path, "Layers", sr)
        AddMsgAndPrint("\nSuccessfully created File Geodatabase: " + watershedGDB_name,0)
        FGDBexists = False
    # if GDB already existed but feature dataset doesn't
    if not arcpy.Exists(watershedFD):
        arcpy.CreateFeatureDataset_management(watershedGDB_path, "Layers", sr)

    # --------------------------------------------------------------------- Clean old files if FGDB already existed.
    if FGDBexists:    
        layersToRemove = (PoolMerge,storageTable,tempDEM,storageCSV)
        x = 0        
        for layer in layersToRemove:
            if arcpy.Exists(layer):
                # strictly for formatting
                if x == 0:
                    AddMsgAndPrint("\nRemoving old files from FGDB..." + watershedGDB_name ,0)
                    x += 1
                try:
                    arcpy.Delete_management(layer)
                    AddMsgAndPrint("\tDeleting..." + os.path.basename(layer),0)
                except:
                    pass
                
        arcpy.env.workspace = watershedFD
        
        poolFCs = arcpy.ListFeatureClasses("Pool_*")
        
        for poolFC in poolFCs:
            if arcpy.Exists(poolFC):
                arcpy.Delete_management(poolFC)
                AddMsgAndPrint("\tDeleting..." + poolFC,0)               

        if os.path.exists(storageCSV):
            os.remove(storageCSV)
            
        del x,layersToRemove,poolFCs

    if os.path.exists(storageCSV):
        os.remove(storageCSV)
        AddMsgAndPrint("\tDeleting..." + storageCSV,0)
        
    # ------------------------------------- Remove layers from ArcMap if they exist
    layersToRemove = (poolMergeOut,storageTableView)
    x = 0
    for layer in layersToRemove:
        if arcpy.Exists(layer):
            if x == 0:
                AddMsgAndPrint("",0)
                x+=1
            try:
                arcpy.Delete_management(layer)
                AddMsgAndPrint("Removing previous " + layer + " from your ArcMap Session...",0)
            except:
                pass

    del x, layersToRemove
    
    # --------------------------------------------------------------------------------- ClipDEM to User's Pool or Watershed
    tempMask = arcpy.sa.ExtractByMask(inputDEM, inPool)
    tempMask.save(tempDEM)

    # User specified max elevation value must be within min-max elevation range of clipped dem
    demTempMaxElev = round(float(arcpy.GetRasterProperties_management(tempDEM, "MAXIMUM").getOutput(0)),1)
    demTempMinElev = round(float(arcpy.GetRasterProperties_management(tempDEM, "MINIMUM").getOutput(0)),1)

    # convert max elev value and increment(FT) to match the native Z-units of input DEM
    maxElevConverted = maxElev * Zfactor
    increment = userIncrement * Zfactor

    # if maxElevConverted is not within elevation range exit.    
    if not demTempMinElev < maxElevConverted <= demTempMaxElev:

        AddMsgAndPrint("\nThe Max Elevation value specified is not within the elevation range of your watershed-pool area",2)
        AddMsgAndPrint("\tThe Elevation Range of your watershed-pool polygon is:",2)
        AddMsgAndPrint("\tMaximum Elevation: " + str(demTempMaxElev) + " " + zUnits + " ---- " + str(round(float(demTempMaxElev*conversionFactor),1)) + " Feet",0)
        AddMsgAndPrint("\tMinimum Elevation: " + str(demTempMinElev) + " " + zUnits + " ---- " + str(round(float(demTempMinElev*conversionFactor),1)) + " Feet",0)
        AddMsgAndPrint("\tPlease enter an elevation value within this range. Exiting...",2)
        sys.exit()

    else:
        AddMsgAndPrint("\nSuccessfully clipped DEM to " + os.path.basename(inPool),0)

    # --------------------------------------------------------------------------------- Set Elevations to calculate volume and surface area                   
    try:
        i = 1    
        while maxElevConverted > demTempMinElev:

            if i == 1:
                AddMsgAndPrint("\nDeriving Surface Volume for elevation values between " + str(round(demTempMinElev * conversionFactor,1)) + " and " + str(maxElev) + " FT every " + str(userIncrement) + " FT" ,0)
                numOfPoolsToCreate = str(int(round((maxElevConverted - demTempMinElev)/increment)))
                AddMsgAndPrint(numOfPoolsToCreate + " Pool Feature Classes will be created",0)
                i+=1

            arcpy.SurfaceVolume_3d(tempDEM, storageCSV, "BELOW", maxElevConverted, "1")

            if b_createPools:
                if not createPool(maxElevConverted,storageCSV):
                    pass
            maxElevConverted = maxElevConverted - increment
        del i            
  
    except:
        print_exception()
        sys.exit()

    if arcpy.Exists(tempDEM):
        arcpy.Delete_management(tempDEM)
        
    #------------------------------------------------------------------------ Convert StorageCSV to FGDB Table and populate fields.
    arcpy.CopyRows_management(storageCSV, storageTable, "")
    arcpy.AddField_management(storageTable, "ELEV_FEET", "DOUBLE", "5", "1", "", "", "NULLABLE", "NON_REQUIRED", "")
    arcpy.AddField_management(storageTable, "POOL_ACRES", "DOUBLE", "", "", "", "", "NULLABLE", "NON_REQUIRED", "")
    arcpy.AddField_management(storageTable, "POOL_SQFT", "DOUBLE", "", "", "", "", "NULLABLE", "NON_REQUIRED", "")
    arcpy.AddField_management(storageTable, "ACRE_FOOT", "DOUBLE", "", "", "", "", "NULLABLE", "NON_REQUIRED", "")

    elevFeetCalc = "round(!Plane_Height! *" + str(conversionFactor) + ",1)"
    poolAcresCalc = "round(!Area_2D! /" + str(acreConversion) + ",1)"
    poolSqftCalc = "round(!Area_2D! /" + str(ftConversion) + ",1)"
    acreFootCalc = "round(!Volume! /" + str(volConversion) + ",1)"
    
    arcpy.CalculateField_management(storageTable, "ELEV_FEET", elevFeetCalc, "PYTHON")
    arcpy.CalculateField_management(storageTable, "POOL_ACRES", poolAcresCalc, "PYTHON")
    arcpy.CalculateField_management(storageTable, "POOL_SQFT", poolSqftCalc, "PYTHON")
    arcpy.CalculateField_management(storageTable, "ACRE_FOOT", acreFootCalc, "PYTHON")

    del elevFeetCalc,poolAcresCalc,poolSqftCalc,acreFootCalc

    AddMsgAndPrint("\nSuccessfully Created " + os.path.basename(storageTable),0)

    #------------------------------------------------------------------------ Append all Pool Polygons together
    if b_createPools:
        mergeList = ""
        i = 1
        arcpy.env.workspace = watershedFD
        poolFCs = arcpy.ListFeatureClasses("Pool_*")

        for poolFC in poolFCs:
            if i == 1:
                mergeList = arcpy.Describe(poolFC).CatalogPath + ";"
            else:
                mergeList = mergeList + ";" + arcpy.Describe(poolFC).CatalogPath
            i+=1

        arcpy.Merge_management(mergeList,PoolMerge)
                
        AddMsgAndPrint("\nSuccessfully Merged Pools into " + os.path.basename(PoolMerge),0)

        del mergeList,poolFCs,i

    # ------------------------------------------------------------------------------------------------ Compact FGDB
    try:
        arcpy.Compact_management(watershedGDB_path)
        AddMsgAndPrint("\nSuccessfully Compacted FGDB: " + os.path.basename(watershedGDB_path),0)    
    except:
        pass

    # ------------------------------------------------------------------------------------------------ Prepare to Add to Arcmap

    if b_createPools:
        arcpy.SetParameterAsText(7, PoolMerge)
        
    # Create a table view from the storage table to add to Arcmap
    arcpy.MakeTableView_management(storageTable,storageTableView)

    #------------------------------------------------------------------------------------ Take care of a little housekeeping
    arcpy.RefreshCatalog(watershedGDB_path)

    if os.path.exists(storageCSV):
        try:
            os.path.remove(storageCSV)
        except:
            pass

    del storageCSV        
    
except SystemExit:
    pass

except KeyboardInterrupt:
    AddMsgAndPrint("Interruption requested....exiting")

except:
    print_exception()
