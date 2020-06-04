## Wascob_AOI.py
##
## Created by Peter Mead (see below) and Adolfo Diaz
## Updated by Chris Morse, USDA NRCS, 2020
##
## See functionality described below
##
# ===============================================================================================================
# ===============================================================================================================
#
#                 WASCOB_AOI.py for LiDAR Based Design of Water and Sediment Control Basins
#
#                 Author:   Originally Scripted by Peter Mead, MN USDA-NRCS with assistance 
#                           from Adolfo Diaz, WI NRCS. 
#
#                           Graciously updated and maintained by Peter Mead, under GeoGurus Group.
#
#                 Contact: peter.mead@geogurus.com
#
#                 Notes:
#                           Rescripted in arcpy 12/2013.
#
#                           3/2014 - removed of "Relative Survey" as default.
#                           Added option of creating "Relative Survey" or using MSL (Mean Sea Level) elevations.
#
# ===============================================================================================================
# ===============================================================================================================
#
# Checks a user supplied workspace's file structure and creates 
# directories as necessary for 638 Tool Workflow.
#
# Determines input DEM's Native Resolution, Spatial Reference, and Elevation format to 
# apply proper conversion factors and projection where necessary throughout the workflow.
#  
# Clips a user supplied DEM to a User defined area of interest, Saving a clipped 
# "AOI DEM", Polygon Mask, and Hillshade of the Area of interest.
#
# Converts (if necessary) Clipped Input to Feet, and creates "Project DEM" --  with 
# elevations rounded to nearest 1/10th ft for the area of interest. Option to use MSL elevations
# or create " Relative Survey". Relative survey is useful when projects will be staked in
# field using a laser vs. msl when using a vrs system.
#
# The Project DEM is "smoothed" using focal mean within a 3 cell x 3 cell window, 
# and indexed contour lines are generated at the user defined interval.
#
# A "Depth Grid" is also created to show area of the DEM where water would theoretically 
# pool due to either legitimate sinks or "digital dams" existing in the raster data.
#
# All Derived Layers are added to the Current MXD's table of contents upon successful execution
#
# ===============================================================================================================
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
    f.write("\n##################################################################\n")
    f.write("Executing \"WASCOB: Define Area of Interest\" tool\n")
    f.write("User Name: " + getpass.getuser() + "\n")
    f.write("Date Executed: " + time.ctime() + "\n")
    f.write("ArcGIS Version: " + str(arcpy.GetInstallInfo()['Version']) + "\n")
    f.write("User Parameters:\n")
    f.write("\tWorkspace: " + userWorkspace + "\n")
    f.write("\tInput Dem: " + arcpy.Describe(inputDEM).CatalogPath + "\n")
    f.write("\tElevation Z-units: " + zUnits + "\n")
    f.write("\tContour Interval: " + str(interval) + "\n")
    
    f.close
    del f

## ================================================================================================================
def splitThousands(someNumber):
# will determine where to put a thousands seperator if one is needed.
# Input is an integer.  Integer with or without thousands seperator is returned.

    try:
        return re.sub(r'(\d{3})(?=\d)', r'\1,', str(someNumber)[::-1])[::-1]        

## --------------Use this code in case you want to preserve numbers after the decimal.  I decided to just round up
        # Number is a floating number        
        if str(someNumber).find("."):
            
            dropDecimals = int(someNumber)
            numberStr = str(someNumber)

            afterDecimal = str(numberStr[numberStr.find("."):numberStr.find(".")+2])
            beforeDecimalCommas = re.sub(r'(\d{3})(?=\d)', r'\1,', str(dropDecimals)[::-1])[::-1]

            return beforeDecimalCommas + afterDecimal

        # Number is a whole number    
        else:
            return int(re.sub(r'(\d{3})(?=\d)', r'\1,', str(someNumber)[::-1])[::-1])
    
    except:
        print_exception()
        return someNumber

## ================================================================================================================
# Import system modules
import sys, os, arcpy, string, traceback, re

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

# Main - wrap everything in a try statement
try:
    # Check out Spatial Analyst License        
    if arcpy.CheckExtension("Spatial") == "Available":
        arcpy.CheckOutExtension("Spatial")
    else:
        arcpy.AddError("Spatial Analyst Extension not enabled. Please enable Spatial analyst from the Tools/Extensions menu. Exiting...\n")
        sys.exit()
        
    # --------------------------------------------------------------------------------------------- Input Parameters
    # Comment following six lines to run from pythonWin
    userWorkspace = arcpy.GetParameterAsText(0)     # User Defined Workspace Folder
    inputDEM = arcpy.GetParameterAsText(1)          # Input DEM Raster
    zUnits = arcpy.GetParameterAsText(2)            # Elevation z units of input DEM
    AOI = arcpy.GetParameterAsText(3)               # AOI that was drawn
    interval = arcpy.GetParameterAsText(4)          # user defined contour interval           
    relSurvey = arcpy.GetParameterAsText(5)         # Optional - Create Relative Survey

    # If user selected relative survey, set boolean to create relative dem surface.
    if string.upper(relSurvey) <> "TRUE":
        relativeSurvey = False
    else:
        relativeSurvey = True
        
    # --------------------------------------------------------------------------------------------- Define Variables
    projectName = arcpy.ValidateTableName(os.path.basename(userWorkspace).replace(" ","_"))
    watershedGDB_name = os.path.basename(userWorkspace).replace(" ","_") + "_Wascob.gdb"  # replace spaces for new FGDB name
    watershedGDB_path = userWorkspace + os.sep + watershedGDB_name
    watershedFD = watershedGDB_path + os.sep + "Layers"

    # WASCOB Project Folders:
    DocumentsFolder =  os.path.join(os.path.dirname(sys.argv[0]), "Documents")
    Documents = userWorkspace + os.sep + "Documents"
    gis_output = userWorkspace + os.sep + "gis_output"

    # ---------------------------------------------------------- Datasets
    # ------------------------------ Permanent Datasets
    projectAOI = watershedFD + os.sep + projectName + "_AOI"
    Contours = watershedFD + os.sep + projectName + "_Contours_" + str(interval.replace(".","_")) + "_ft"
    DEM_aoi = watershedGDB_path + os.sep + projectName + "_Raw_DEM"
    Hillshade = watershedGDB_path + os.sep + projectName + "_Hillshade"
    depthGrid = watershedGDB_path + os.sep + projectName + "_DepthGrid"
    projectDEM = watershedGDB_path + os.sep + projectName + "_Project_DEM"
    DEMsmooth = watershedGDB_path + os.sep + projectName + "_DEMsmooth"
    
    # ----------------------------- Temporary Datasets
    ContoursTemp = watershedFD + os.sep + "ContoursTemp"
    Fill_DEMaoi = watershedGDB_path + os.sep + "Fill_DEMaoi"
    FilMinus = watershedGDB_path + os.sep + "FilMinus"
    DEMft = watershedGDB_path + os.sep + "DEMft"
    MinDEM = watershedGDB_path + os.sep + "min"
    MinusDEM = watershedGDB_path + os.sep + "minus"
    TimesDEM = watershedGDB_path + os.sep + "times"
    intDEM = watershedGDB_path + os.sep + "DEMint"
    
    # record basic user inputs and settings to log file for future purposes
    textFilePath = userWorkspace + os.sep + projectName + "_EngTools.txt"
    logBasicSettings()

    # ---------------------------------------------------------------------------------------------- Count the number of features in AOI
    # Exit if AOI contains more than 1 digitized area.
    if int(arcpy.GetCount_management(AOI).getOutput(0)) > 1:
        AddMsgAndPrint(" \n\nYou can only digitize 1 Area of interest! Please Try Again. Exiting...",2)
        sys.exit()
        
    # ---------------------------------------------------------------------------------------------- Check DEM Coordinate System and Linear Units
    AddMsgAndPrint(" \nGathering information about DEM: " + os.path.basename(inputDEM),0)
    
    desc = arcpy.Describe(inputDEM)
    sr = desc.SpatialReference
    units = sr.LinearUnitName
    cellSize = desc.MeanCellWidth
    
    if not sr.Type == "Projected":
        AddMsgAndPrint("\n" + os.path.basename(inputDEM) + " is not in a Projected Coordinate System. Exiting...",2)
        sys.exit()
        
    # Standardize the units variable
    if units == "Meter":
        units = "Meters"
    elif units == "Foot":
        units = "Feet"
    elif units == "Foot_US":
        units = "Feet"
    else:
        AddMsgAndPrint("\nCould not determine linear units of " + os.path.basename(inputDEM) + "! Exiting...",2)
        sys.exit()

    # Coordinate System must be a Projected type in order to continue.
    # zUnits will determine Zfactor for converting elevations to feet

    if zUnits == "Meters":
        Zfactor = 3.280839896       # 3.28 feet in a meter
    elif zUnits == "Centimeters":
        Zfactor = 0.03280839896     # 0.033 feet in a centimeter
    elif zUnits == "Inches":
        Zfactor = 0.0833333         # 0.083 feet in an inch
    elif zUnits == "Feet":
        Zfactor = 1
    else:
        AddMsgAndPrint("\nSpecified Elevation Units (z) for " + os.path.basename(inputDEM) + " are not a valid choice! Exiting...",2)
        sys.exit()

    AddMsgAndPrint("\tProjection Name: " + sr.Name,0)
    AddMsgAndPrint("\tXY Linear Units: " + units,0)
    AddMsgAndPrint("\tElevation Values (Z): " + zUnits,0) 
    AddMsgAndPrint("\tCell Size: " + str(desc.MeanCellWidth) + " x " + str(desc.MeanCellHeight) + " " + units,0)
    
    # ---------------------------------------------------------------------------------------------- Delete old datasets
    if arcpy.Exists(watershedGDB_path):
        datasetsToRemove = (DEM_aoi,Hillshade,depthGrid,DEMsmooth,ContoursTemp,Fill_DEMaoi,FilMinus,projectDEM,DEMft,intDEM)
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

        # If FGDB Exists but FD not present, create it.
        if not arcpy.Exists(watershedFD):
            arcpy.CreateFeatureDataset_management(watershedGDB_path, "Layers", sr)

    # Otherwise FGDB does not exist, create it.
    else:
        arcpy.CreateFileGDB_management(userWorkspace, watershedGDB_name)
        arcpy.CreateFeatureDataset_management(watershedGDB_path, "Layers", sr)
        AddMsgAndPrint("\nSuccessfully created File Geodatabase: " + watershedGDB_name,0)
    
    # If Documents folder not present, create and copy required files to it
    if not arcpy.Exists(Documents):
        arcpy.CreateFolder_management(userWorkspace, "Documents")
        if arcpy.Exists(DocumentsFolder):
            arcpy.Copy_management(DocumentsFolder, Documents, "Folder")
        
    # Create gis_output folder if not present 
    if not arcpy.Exists(gis_output):
        arcpy.CreateFolder_management(userWorkspace, "gis_output")

    # ----------------------------------------------------------------------------------------------- Create New AOI
    # if AOI path and  projectAOI path are not the same then assume AOI was manually digitized
    # or input is some from some other feature class/shapefile
    if not arcpy.Describe(AOI).CatalogPath == projectAOI:       
        # delete the existing projectAOI feature class and recreate it.
        if arcpy.Exists(projectAOI):
            try:
                arcpy.Delete_management(projectAOI)
                arcpy.CopyFeatures_management(AOI, projectAOI)
                AddMsgAndPrint("\nSuccessfully Recreated \"" + str(projectName) + "_AOI\" feature class",0)
            except:
                print_exception()
                arcpy.env.overwriteOutput = True
        else:
            arcpy.CopyFeatures_management(AOI, projectAOI)
            AddMsgAndPrint("\nSuccessfully Created \"" + str(projectName) + "_AOI\" feature class",0)

    # paths are the same therefore AOI is projectAOI
    else:
        AddMsgAndPrint("\nUsing Existing \"" + str(projectName) + "_AOI\" feature class:",0)
      
    # -------------------------------------------------------------------------------------------- Exit if AOI was not a polygon
    if arcpy.Describe(projectAOI).ShapeType != "Polygon":
        AddMsgAndPrint("\n\nYour Area of Interest must be a polygon layer! Exiting...",2)
        sys.exit()
        
    # --------------------------------------------------------------------------------------------  Populate AOI with DEM Properties
    # Write input DEM name to AOI 
    if len(arcpy.ListFields(projectAOI,"INPUT_DEM")) < 1:
        arcpy.AddField_management(projectAOI, "INPUT_DEM", "TEXT", "", "", "", "", "NULLABLE", "NON_REQUIRED", "")
    expression = '"' + os.path.basename(inputDEM) + '"'
    arcpy.CalculateField_management(projectAOI, "INPUT_DEM", expression, "PYTHON")
    del expression
    
    # Write XY Units to AOI
    if len(arcpy.ListFields(projectAOI,"XY_UNITS")) < 1:
        arcpy.AddField_management(projectAOI, "XY_UNITS", "TEXT", "", "", "", "", "NULLABLE", "NON_REQUIRED", "")
    expression = '"' + str(units) + '"'
    arcpy.CalculateField_management(projectAOI, "XY_UNITS", expression, "PYTHON")
    del expression
    
    # Write Z Units to AOI
    if len(arcpy.ListFields(projectAOI,"Z_UNITS")) < 1:
        arcpy.AddField_management(projectAOI, "Z_UNITS", "TEXT", "", "", "", "", "NULLABLE", "NON_REQUIRED", "")
    expression = '"' + str(zUnits) + '"'
    arcpy.CalculateField_management(projectAOI, "Z_UNITS", expression, "PYTHON")
    del expression

    # Add and update Acres field
    if len(arcpy.ListFields(projectAOI,"Acres")) < 1:
        arcpy.AddField_management(projectAOI, "Acres", "DOUBLE", "", "", "", "", "NULLABLE", "NON_REQUIRED", "")
    expression = "!Shape.Area@acres!"
    arcpy.CalculateField_management(projectAOI, "Acres", expression, "PYTHON")
    
    # Delete unwanted "Id" remanant field
    if len(arcpy.ListFields(projectAOI,"Id")) > 0:
        try:
            arcpy.DeleteField_management(projectAOI,"Id")
        except:
            pass

    # Get the Shape Area to notify user of Square Units and Acres of AOI
    rows = arcpy.SearchCursor(projectAOI)
    row = rows.next()
    area = ""
    while row:
        area = row.SHAPE_Area
        acres = row.Acres
        if area != 0:
            AddMsgAndPrint("\n\tArea of Interest: " + str(os.path.basename(projectAOI)),0)
            AddMsgAndPrint("\t\tArea:  " + str(splitThousands(round(area,2))) + " Sq. " + units,0)
            AddMsgAndPrint("\t\tAcres: " + str(splitThousands(round(acres,2))) + " Acres",0)
        else:
            AddMsgAndPrint("\tCould not calculate Acres for AOI ID: " + str(row.OBJECTID),1)
        row = rows.next()
        
        break

    # ------------------------------------------------------------------------------------------------- Clip inputDEM
    AddMsgAndPrint("\nClipping "+ os.path.basename(inputDEM) +" using " + os.path.basename(projectAOI) + "...",0)
    maskedDEM = arcpy.sa.ExtractByMask(inputDEM, projectAOI)
    maskedDEM.save(DEM_aoi)
    AddMsgAndPrint("\tSuccessully created: " + os.path.basename(DEM_aoi),0)
     
    # --------------------------------------------------------------- Round Elevation Values to nearest 10th
    if not relativeSurvey:
        AddMsgAndPrint("\nCreating Project DEM using Mean Sea Level Elevations...",0)
    else:
        AddMsgAndPrint("\nCreating Project DEM using Relative Elevations (0 ft. to Maximum rise)...",0)
    
    # Convert to feet if necessary
    if not zUnits == "Feet":
        AddMsgAndPrint("\tConverting elevations to feet...",0)
        tempTimes = arcpy.sa.Times(DEM_aoi, Zfactor)
        tempTimes.save(DEMft)
        DEM_aoi = DEMft
        
    if relativeSurvey:
        AddMsgAndPrint("\tDetermining relative elevations...",0)
        # Get Minimum Elevation in AOI
        AddMsgAndPrint("\tRetrieving minimum elevation...",0)
        tempMin = arcpy.sa.ZonalStatistics(projectAOI, "OBJECTID", DEM_aoi, "MINIMUM", "DATA")
        tempMin.save(MinDEM)
        
        # Subtract Minimum Elevation from all cells in AOI
        AddMsgAndPrint("\tDetermining maximum rise...",0)
        tempMinus = arcpy.sa.Minus(DEM_aoi, MinDEM)
        tempMinus.save(MinusDEM)

        AddMsgAndPrint("\tSuccessful!",0)
        DEM_aoi = MinusDEM

    AddMsgAndPrint("\tRounding to nearest 1/10th ft...",0)
    # Multiply DEM by 10 for rounding...
    tempTimes2 = arcpy.sa.Times(DEM_aoi, 10)
    tempTimes2.save(TimesDEM)
    
    # Create integer raster and add 0.5..
    #Expression1 = "Int(\""+str(TimesDEM)+"\" + 0.5)"
    #arcpy.gp.RasterCalculator_sa(Expression1, intDEM)
    tempPlus = arcpy.sa.Plus(TimesDEM, 0.5)
    tempInt = arcpy.sa.Int(tempPlus)
    tempInt.save(intDEM)

    # Restore the decimal point for 1/10th foot. 
    # This becomes "Project DEM", a raster surface in 1/10th foot values
    #Expression2 = "Float(\""+str(intDEM)+"\" * 0.1)"
    #arcpy.gp.RasterCalculator_sa(Expression2, projectDEM)
    tempTimes3 = arcpy.sa.Times(intDEM, 0.1)
    tempTimes3.save(projectDEM)

    AddMsgAndPrint("\tSuccessfully created Project DEM!",0)

    # Delete intermediate rasters
    datasetsToRemove = (intDEM,DEMft,TimesDEM,MinDEM,MinusDEM,tempPlus)
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

    # ------------------------------------------------------------------------------------------------ Create Contours 
    AddMsgAndPrint("\nCreating " + str(interval) + "-foot contours...",0)
 
    # Run Focal Statistics on the Project DEM to generate smooth contours
    tempFocal = arcpy.sa.FocalStatistics(projectDEM, "RECTANGLE 3 3 CELL","MEAN","DATA")
    tempFocal.save(DEMsmooth)

    # Create Contours from DEMsmooth if user-defined interval is greater than 0
    if interval > 0:
        #Z factor to use here is 1 because vertical values of the input DEM have been forced to be feet.        
        arcpy.sa.Contour(DEMsmooth, ContoursTemp, interval, "0", 1)
        AddMsgAndPrint(" \tSuccessfully Created Contours from " + os.path.basename(projectDEM),0)
        
        arcpy.AddField_management(ContoursTemp, "Index", "DOUBLE", "", "", "", "", "NULLABLE", "NON_REQUIRED", "")
        if arcpy.Exists("ContourLYR"):
            try:
                arcpy.Delete_management("ContourLYR")
            except:
                pass
            
        arcpy.MakeFeatureLayer_management(ContoursTemp,"ContourLYR","","","")

        # Every 5th contour will be indexed to 1
        AddMsgAndPrint("\tIndexing every 5th Contour line...",0)
        expression = "MOD( \"CONTOUR\"," + str(float(interval) * 5) + ") = 0"
        arcpy.SelectLayerByAttribute_management("ContourLYR", "NEW_SELECTION", expression)
        del expression
        
        indexValue = 1
        arcpy.CalculateField_management("ContourLYR", "Index", indexValue, "PYTHON")
        del indexValue

        # All other contours will be indexed to 0
        arcpy.SelectLayerByAttribute_management("ContourLYR", "SWITCH_SELECTION", "")
        indexValue = 0
        arcpy.CalculateField_management("ContourLYR", "Index", indexValue, "PYTHON")
        del indexValue

        AddMsgAndPrint(" \tSuccessfully indexed Contour lines",0)
        
        # Clear selection and write all contours to a new feature class        
        arcpy.SelectLayerByAttribute_management("ContourLYR","CLEAR_SELECTION","")      
        arcpy.CopyFeatures_management("ContourLYR", Contours)

        # Delete unwanted datasets
        arcpy.Delete_management(ContoursTemp)
        arcpy.Delete_management("ContourLYR")
        arcpy.Delete_management(DEMsmooth)
        
    else:
        AddMsgAndPrint("\nContours will not be created because interval was set to 0",1)

    # ---------------------------------------------------------------------------------------------- Create Hillshade and Depth Grid
    # Process: Creating Hillshade from DEM_aoi
    # This section needs a different Zfactor than just the feet conversion multiplier used earlier!
    # Update Zfactor for use with hillshade. This is because the hillshade is created with the original DEM, prior to conversion to vertical feet.

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
    elif zUnits == "Inches":
        if units == "Feet":
            Zfactor = 0.0833333
        if units == "Meters":
            Zfactor = 0.0254
            
    AddMsgAndPrint("\nCreating Hillshade for AOI...",0)
    DEM_aoi = watershedGDB_path + os.sep + projectName + "_Raw_DEM"
    outHill = arcpy.sa.Hillshade(DEM_aoi, "315", "45", "#", Zfactor)
    outHill.save(Hillshade)
    AddMsgAndPrint("\tSuccessfully Created Hillshade",0)
    
    AddMsgAndPrint(" \nFilling sinks to create depth grid...",0)
    try:
        # Fills sinks in DEM_aoi to create depth grid.
        outFill = arcpy.sa.Fill(DEM_aoi, "")
        outFill.save(Fill_DEMaoi)
        AddMsgAndPrint("\tSuccessfully filled sinks",0)
        fill = True

    except:
        fill = False
        AddMsgAndPrint("\tFailed filling sinks on " + os.path.basename(DEM_aoi) + ".",1)
        AddMsgAndPrint("\tDepth Grid will not be created!",1)

    if fill:
        AddMsgAndPrint("\nCreating depth grid...",0)
        # DEM_aoi - Fill_DEMaoi = FilMinus
        #arcpy.gp.Minus_sa(Fill_DEMaoi, DEM_aoi, FilMinus)
        FilMinus = arcpy.sa.Minus(Fill_DEMaoi, DEM_aoi)
        # Create a Depth Grid; Any pixel where there is a difference write it out
        #arcpy.gp.Con_sa(FilMinus, FilMinus, depthGrid, "", "VALUE > 0")
        tempDepths = arcpy.sa.Con(FilMinus, FilMinus, "", "VALUE > 0")
        tempDepths.save(depthGrid)
        
        # Delete unwanted rasters
        arcpy.Delete_management(Fill_DEMaoi)
        arcpy.Delete_management(FilMinus)
        
        AddMsgAndPrint("\tSuccessfully Created a Depth Grid!",0)
          
    # ------------------------------------------------------------------------------------------------ Prepare to Add to Arcmap
    AddMsgAndPrint("\nAdding Layers to ArcMap",0)
    AddMsgAndPrint("\t...Contours",0)
    arcpy.SetParameterAsText(6, Contours)
    AddMsgAndPrint("\t...Area of Interest",0)
    arcpy.SetParameterAsText(7, projectAOI)
    AddMsgAndPrint("\t...Project DEM",0)
    arcpy.SetParameterAsText(8, projectDEM)
    AddMsgAndPrint("\t...Hillshade",0)
    arcpy.SetParameterAsText(9, Hillshade)
    AddMsgAndPrint("\t...Depth Grid",0)
    arcpy.SetParameterAsText(10, depthGrid)
    arcpy.RefreshActiveView()
    
    # ------------------------------------------------------------------------------------------------ Compact FGDB
    try:
        AddMsgAndPrint("\n\nCompacting FGDB: " + os.path.basename(watershedGDB_path) + "...",0)
        arcpy.Compact_management(watershedGDB_path)
    except:
        pass
    # ------------------------------------------------------------------------------------------------ Refresh Catalog
    arcpy.RefreshCatalog(watershedGDB_path)

    AddMsgAndPrint("\nProcessing Complete!",0)
    
except SystemExit:
    pass

except KeyboardInterrupt:
    AddMsgAndPrint("Interruption requested....exiting")

except:
    print_exception()
