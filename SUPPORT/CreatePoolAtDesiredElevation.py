## CreatePoolAtDesiredElevation.py
##
## Created by Peter Mead, Adolfo Diaz, USDA NRCS, 2013
## Updated by Chris Morse, USDA NRCS, 2020
## 
## Creates a pool polygon and calculates storage volume at a user provided elevation using a watershed or pool
## boundary to limit analysis extent.

## ================================================================================================================ 
def print_exception():
    
    tb = sys.exc_info()[2]
    l = traceback.format_tb(tb)
    l.reverse()
    tbinfo = "".join(l)
    AddMsgAndPrint(" \n----------ERROR Start------------------- \n",2)
    AddMsgAndPrint("Traceback Info:  \n" + tbinfo + "Error Info:  \n    " +  str(sys.exc_type)+ ": " + str(sys.exc_value) + "",2)
    AddMsgAndPrint("----------ERROR End--------------------  \n",2)

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
    f.write("Executing \"Create Pool at Desired Elevation\" Tool\n")
    f.write("User Name: " + getpass.getuser() + "\n")
    f.write("Date Executed: " + time.ctime() + "\n")
    f.write("ArcGIS Version: " + str(arcpy.GetInstallInfo()['Version']) + "\n")   
    f.write("User Parameters:\n")
    f.write("\tWorkspace: " + userWorkspace + "\n")
    f.write("\tInput Dem: " + arcpy.Describe(inputDEM).CatalogPath + "\n")
    f.write("\tElevation Z-units: " + zUnits + "\n")
    f.write("\tInput Watershed Mask: " + str(inPool) + "\n")
    f.write("\tPool Elevation: " + str(maxElev) + "\n")
    f.write("\tOutput Pool Polygon: " + str(outPool) + "\n")    

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
        
        poolExit = outPool        

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

        AddMsgAndPrint("\n\tCreated " + poolName + ":",0)
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

    #----------------------------------------------------------------------------------------- Input Parameters
    inputDEM = arcpy.GetParameterAsText(0)
    zUnits = arcpy.GetParameterAsText(1)
    inMask = arcpy.GetParameterAsText(2)                
    maxElev = float(arcpy.GetParameterAsText(3))
    
    # ---------------------------------------------------------------------------------------- Define Variables
    inPool = arcpy.Describe(inMask).CatalogPath
    if inPool.find('.gdb') > -1 or inPool.find('.mdb') > -1:
        watershedGDB_path = inPool[:inPool.find('.')+4]
    elif inPool.find('.shp')> -1:
        watershedGDB_path = os.path.dirname(inPool) + os.sep + os.path.basename(os.path.dirname(inPool)).replace(" ","_") + "_EngTools.gdb"
    else:
        arcpy.AddError("\nPool Polygon must either be a feature class or shapefile. Exiting...")
        sys.exit()

    watershedGDB_name = os.path.basename(watershedGDB_path)
    watershedFD = watershedGDB_path + os.sep + "Layers"
    poolName = os.path.basename(inPool) + "_Pool_" + str(maxElev).replace(".","_")
    userWorkspace = os.path.dirname(watershedGDB_path)
    
    # --------------------------------------------- Permanent Datasets
    outPool = watershedFD +os.sep + poolName
    # Must Have a unique name for pool -- Append a unique digit to watershed if required
    x = 1
    while x > 0:
        if arcpy.Exists(outPool):
            outPool = watershedFD + os.sep + os.path.basename(inMask) + "_Pool" + str(x) + "_" + str(maxElev).replace(".","_")
            x += 1
        else:
            x = 0
    del x
    
    storageTableView = "Pool_Storage_Table"

    # Storage CSV file
    storageCSV = userWorkspace + os.sep + poolName + "_storageCSV.txt"

    # --------------------------------------------- Temporary Datasets
    tempDEM = watershedGDB_path + os.sep + "tempDEM"
    storageTable = watershedGDB_path + os.sep + arcpy.ValidateTableName(poolName) + "_storageTable"

    # --------------------------------------------- Layers in ArcMap
    outPoolLyr = "" + os.path.basename(outPool) + ""
    
    # Set log file path and start logging
    textFilePath = userWorkspace + os.sep + os.path.basename(userWorkspace).replace(" ","_") + "_EngTools.txt" 
    logBasicSettings()

    # ---------------------------------------------------------------------------------------------- Check Parameters
    AddMsgAndPrint("\nChecking inputs...",0)
    # Exit if inPool has more than 1 polygon    
    if int(arcpy.GetCount_management(inPool).getOutput(0)) > 1:
        AddMsgAndPrint("\tOnly ONE Watershed or Pool Polygon can be submitted!",2)
        AddMsgAndPrint("\tEither export an individual polygon from your " + os.path.basename(inPool) + " layer,",2)
        AddMsgAndPrint("\tmake a single selection, or provide a different input. Exiting...",2)
        sys.exit()

    # Exit if inPool is not a Polygon geometry
    if arcpy.Describe(inPool).ShapeType != "Polygon":
        AddMsgAndPrint("\tYour Watershed or Pool Area must be a polygon layer! Exiting...",2)
        sys.exit()        

    # Exit if Elevation value is less than 1
    if maxElev < 1:
        AddMsgAndPrint("\tPool Elevation Value must be greater than 0! Exiting...",2)
        sys.exit()     

    #--------------------------------------------------------------------- Retrieve Spatial Reference and units from DEM
    desc = arcpy.Describe(inputDEM)
    sr = desc.SpatialReference
    cellSize = int(desc.MeanCellWidth)
    cellArea = desc.MeanCellWidth * desc.MeanCellHeight
    units = sr.LinearUnitName

    # Coordinate System must be a Projected type in order to continue.
    # XY & Z Units will determine Zfactor for Elevation and Volume Conversions.
    
    if sr.Type == "Projected":
        AddMsgAndPrint("\nInput DEM information: ",0)
        AddMsgAndPrint("\tProjection Name: " + sr.Name,0)
        AddMsgAndPrint("\tXY Linear Units: " + units,0)
        AddMsgAndPrint("\tElevation Values (Z): " + zUnits,0) 
        AddMsgAndPrint("\tCell Size: " + str(desc.MeanCellWidth) + " x " + str(desc.MeanCellHeight) + " " + units,0)

    else:
        AddMsgAndPrint("\t" + os.path.basename(inputDEM) + " is NOT in a Projected Coordinate System! Exiting...",2)
        sys.exit()

    # ----------------------------------------- Set Linear and Volume Conversion Factors
    # We need XY and Z units to map out all conversion factors.
    # First we have the z units, which came from now required parameter input by the user. Use it to set Zfactor for convering input pool elevation from feet to the DEM's z-units
    if zUnits == "Meters":
        Zfactor = 0.3048                    # Converts feet to meters
    if zUnits == "Centimeters":
        Zfactor = 30.48                     # Converts feet to centimeters
    if zUnits == "Feet":
        Zfactor = 1                         # Converts feet to feet
    if zUnits == "Inches":
        Zfactor = 12                        # Converts feet to inches

    # Convert Pool Elevation entered by user in feet to match the zUnits of the DEM specified by the user, using Zfactor
    demElev = maxElev * Zfactor

    # Now start setting factors based on xy and z unit combinations.
    if units == "Meter" or units == "Meters":
        units = "Meters"
        
        ftConversion = 0.09290304           # 0.092903 sq meters in 1 sq foot
        acreConversion = 4046.868564224     # 4046.86 sq meters in 1 acre
        
        if zUnits == "Meters":
            conversionFactor = 3.280839896      # For converting input units to feet. Convert meters to feet with times.
            volConversion = 1233.48184          # For computing Volume in Acre Feet from square meters by meters (from cubic meters).

        if zUnits == "Centimeters":
            conversionFactor = 0.03280839896    # For converting input units to feet. Convert centimeters to feet with times.
            volConversion = 123348.184          # For computing Volume in Acre Feet from square meters by centimeters.

        if zUnits == "Feet":
            conversionFactor = 1                # For converting input units to feet. 1 foot in 1 foot
            volConversion = 4046.868564224      # For computing Volume in Acre Feet from square meters by feet.

        if zUnits == "Inches":
            conversionFactor = 0.0833333        # For converting input units to feet. Convert inches to feet with times.
            volConversion = 48562.339425        # For computing Volume in Acre Feet from square meters by inches.

    elif units == "Foot" or units == "Foot_US" or units == "Feet":
        units = "Feet"

        ftConversion = 1            # 1 sq feet in 1 sq feet
        acreConversion = 43560      # 43560 sq feet in 1 acre

        if zUnits == "Meters":
            conversionFactor = 3.280839896      # For converting input units to feet. Convert feet to feet with times.
            volConversion = 13277.087996        # For computing Volume in Acre Feet from square feet by meters for output table.

        if zUnits == "Centimeters":
            conversionFactor = 0.03280839896    # For converting input units to feet. Convert centimeters to feet with times.
            volConversion = 1327708.799601      # For computing Volume in Acre Feet from square meters by centimeters for output table.

        if zUnits == "Feet":
            conversionFactor = 1                # For converting input units to feet. 1 foot in 1 foot
            volConversion = 43560               # For computing Volume in Acre Feet from square meters by feet for output table.

        if zUnits == "Inches":
            conversionFactor = 0.0833333        # For converting input units to feet. Convert inches to feet with times.
            volConversion = 522720.209088       # For computing Volume in Acre Feet from square meters by inches for output table.

    else:
        AddMsgAndPrint("\nLinear XY units of input DEM could not be determined. Confirm input DEM uses a projected coordinate system based on meters or feet. Exiting...",2)
        sys.exit()

    # ---------------------------------------------------------------------------------------------- Create FGDB, FeatureDataset
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
        
    # -------------------------------------------------------- Remove existing From ArcMap
    if arcpy.Exists(outPoolLyr):
        AddMsgAndPrint("\nRemoving previous layers from your ArcMap session...",0)
        AddMsgAndPrint("\tRemoving ..." + str(outPoolLyr) + "",0)
        arcpy.Delete_management(outPoolLyr)
        
    # ------------------------------------------------------------------------------------------------ Delete old data from gdb
    datasetsToRemove = (storageTable,tempDEM,storageCSV,storageTableView)
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

    if os.path.exists(storageCSV):
        os.remove(storageCSV)
            
    # ---------------------------------------------------- Clip DEM to Watershed & Setnull above Pool Elevation
    #gp.ExtractByMask_sa(inputDEM, inPool, tempDEM)
    tempMask = arcpy.sa.ExtractByMask(inputDEM, inPool)
    tempMask.save(tempDEM)

    # User specified max elevation value must be within min-max range of elevation values in clipped dem
    demTempMaxElev = round((float(arcpy.GetRasterProperties_management(tempDEM, "MAXIMUM").getOutput(0)) * conversionFactor),1)
    demTempMinElev = round((float(arcpy.GetRasterProperties_management(tempDEM, "MINIMUM").getOutput(0)) * conversionFactor),1)

    # Check to make sure specifies max elevation is within the range of elevation in clipped dem
    #if not demTempMinElev < demElev <= demTempMaxElev:
    if not demTempMinElev < maxElev <= demTempMaxElev:
        
        AddMsgAndPrint("\tThe Pool Elevation Specified is not within the range of elevations within your input watershed!",2)
        AddMsgAndPrint("\tPlease specify a value between " + str(demTempMinElev) + " and " + str(demTempMaxElev) + ". Exiting...",2)
        sys.exit()

    AddMsgAndPrint("\nCreating Pool at " + str(maxElev) + " feet",0)

    # --------------------------------------------------------------------------------- Set Elevations to calculate volume and surface area

    AddMsgAndPrint("\nCreating Pool at " + str(maxElev) + " FT")

    arcpy.SurfaceVolume_3d(tempDEM, storageCSV, "BELOW", demElev, "1")

    if not createPool(demElev,storageCSV):
        pass

    if arcpy.Exists(tempDEM):
        arcpy.Delete_management(tempDEM)

    #------------------------------------------------------------------------ Convert StorageCSV to FGDB Table and populate fields
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

    # ------------------------------------------------------------------------------------------------ Compact FGDB
    try:
        arcpy.Compact_management(watershedGDB_path)
        AddMsgAndPrint("\nSuccessfully Compacted FGDB: " + os.path.basename(watershedGDB_path),0)    
    except:
        pass

    # ------------------------------------------------------------------------------------------------ Prepare to Add to Arcmap
    arcpy.SetParameterAsText(4, outPool)

    # Create a table view from the storage table to add to Arcmap
    arcpy.MakeTableView_management(storageTable,storageTableView)

    #------------------------------------------------------------------------------------ Take care of a little housekeeping
    arcpy.RefreshCatalog(watershedGDB_path)

    if os.path.exists(storageCSV):
        try:
            os.path.remove(storageCSV)
        except:
            pass

except SystemExit:
    pass

except KeyboardInterrupt:
    AddMsgAndPrint("Interruption requested....exiting")

except:
    print_exception()
