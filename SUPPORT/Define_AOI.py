## Define_AOI.py
##
## Created by Peter Mead, Adolfo Diaz, USDA NRCS, 2013
## Updated by Chris Morse, USDA NRCS, 2020
##
## Define an area of interest for a watershed project

## ===============================================================================================================
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
    f.write("Executing \"Define Area of Interest\" tool\n")
    f.write("User Name: " + getpass.getuser() + "\n")
    f.write("Date Executed: " + time.ctime() + "\n")
    f.write("ArcGIS Version: " + str(arcpy.GetInstallInfo()['Version']) + "\n")
    f.write("User Parameters:\n")
    f.write("\tWorkspace: " + userWorkspace + "\n")
    f.write("\tInput DEM: " + inputDEM + "\n")
    f.write("\tInput DEM z-Units: " + zUnits + "\n")
    if len(interval) > 0:
        f.write("\tContour Interval: " + str(interval) + "\n")
    else:
        f.write("\tContour Interval: NOT SPECIFIED\n")
    
    f.close
    del f

## ================================================================================================================
def splitThousands(someNumber):
# will determine where to put a thousands seperator if one is needed.
# Input is an integer.  Integer with or without thousands seperator is returned.

    try:
        return re.sub(r'(\d{3})(?=\d)', r'\1,', str(someNumber)[::-1])[::-1]        

## --------------Use this code in case you want to preserve numbers after the decimal.  I decided to just round up
##        # Number is a floating number        
##        if str(someNumber).find("."):
##            
##            dropDecimals = int(someNumber)
##            numberStr = str(someNumber)
##
##            afterDecimal = str(numberStr[numberStr.find("."):numberStr.find(".")+2])
##            beforeDecimalCommas = re.sub(r'(\d{3})(?=\d)', r'\1,', str(dropDecimals)[::-1])[::-1]
##
##            return beforeDecimalCommas + afterDecimal
##
##        # Number is a whole number    
##        else:
##            return int(re.sub(r'(\d{3})(?=\d)', r'\1,', str(someNumber)[::-1])[::-1])
    
    except:
        print_exception()
        return someNumber

## ================================================================================================================
# Import system modules
import sys, os, arcpy, traceback, re

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
    userWorkspace = arcpy.GetParameterAsText(0)
    inputDEM = arcpy.GetParameterAsText(1)         #DEM
    zUnits = arcpy.GetParameterAsText(2)           # elevation z units of input DEM
    AOI = arcpy.GetParameterAsText(3)              # AOI that was drawn
    interval = arcpy.GetParameterAsText(4)         # user defined contour interval

    # --------------------------------------------------------------------------------------------- Define Variables
    projectName = arcpy.ValidateTableName(os.path.basename(userWorkspace).replace(" ","_"))
    textFilePath = userWorkspace + os.sep + projectName + "_EngTools.txt"

    watershedGDB_name = os.path.basename(userWorkspace).replace(" ","_") + "_EngTools.gdb"  # replace spaces for new FGDB name
    watershedGDB_path = userWorkspace + os.sep + watershedGDB_name
    watershedFD = watershedGDB_path + os.sep + "Layers"

    # ---------------------------------------------------------- Datasets
    # ------------------------------ Permanent Datasets
    projectAOI = watershedFD + os.sep + projectName + "_AOI"
    Contours = watershedFD + os.sep + projectName + "_Contours_" + str(interval.replace(".","_")) + "ft"
    DEM_aoi = watershedGDB_path + os.sep + projectName + "_DEM"
    Hillshade = watershedGDB_path + os.sep + projectName + "_Hillshade"
    depthGrid = watershedGDB_path + os.sep + projectName + "_DepthGrid"

    # ----------------------------- Temporary Datasets
    DEMsmooth = watershedGDB_path + os.sep + "DEMsmooth"
    aoiTemp = watershedFD + os.sep + "aoiTemp"
    ContoursTemp = watershedFD + os.sep + "ContoursTemp"
    Fill_DEMaoi = watershedGDB_path + os.sep + "Fill_DEMaoi"
    FilMinus = watershedGDB_path + os.sep + "FilMinus"

    # ------------------------------- Map Layers
    aoiOut = "" + projectName + "_AOI"
    contoursOut = "" + projectName + "_Contours"
    demOut = "" + projectName + "_DEM"
    hillshadeOut = "" + projectName + "_Hillshade"
    depthOut = "" + projectName + "_DepthGrid"    

    # record basic user inputs and settings to log file for future purposes
    logBasicSettings()

    # ---------------------------------------------------------------------------------------------- Count the number of features in AOI
    # Exit if AOI contains more than 1 digitized area.
    if int(arcpy.GetCount_management(AOI).getOutput(0)) > 1:
        AddMsgAndPrint("\n\nYou can only digitize 1 Area of interest! Please Try Again.",2)
        sys.exit()
        
    # ---------------------------------------------------------------------------------------------- Check DEM Coordinate System and Linear Units
    AddMsgAndPrint("\nGathering information about input DEM file: " + os.path.basename(inputDEM)+ ":",0)
    
    desc = arcpy.Describe(inputDEM)
    sr = desc.SpatialReference
    units = sr.LinearUnitName
    cellSize = desc.MeanCellWidth

    # Set units variable
    if units == "Meter":
        units = "Meters"
    elif units == "Foot":
        units = "Feet"
    elif units == "Foot_US":
        units = "Feet"
    else:
        AddMsgAndPrint("\nCould not determine linear units of DEM! Exiting...",2)
        sys.exit()

    # Coordinate System must be a Projected type in order to continue.
    # zUnits will determine Zfactor for the creation of foot contours.
    # if XY units differ from Z units then a Zfactor must be calculated to adjust
    # the z units by multiplying by the Zfactor

    if sr.Type == "Projected":
        if zUnits == "Meters":
            Zfactor = 3.280839896       # 3.28 feet in a meter

        elif zUnits == "Centimeters":   # 0.033 feet in a centimeter
            Zfactor = 0.03280839896

        elif zUnits == "Inches":        # 0.083 feet in an inch
            Zfactor = 0.0833333

        # z units and XY units are the same thus no conversion is required
        else:
            Zfactor = 1

        AddMsgAndPrint("\tProjection Name: " + sr.Name,0)
        AddMsgAndPrint("\tXY Linear Units: " + units,0)
        AddMsgAndPrint("\tElevation Values (Z): " + zUnits,0) 
        AddMsgAndPrint("\tCell Size: " + str(desc.MeanCellWidth) + " x " + str(desc.MeanCellHeight) + " " + units,0)

    else:
        AddMsgAndPrint("\n\n\t" + os.path.basename(inputDEM) + " is NOT in a projected Coordinate System. Exiting...",2)
        sys.exit()
        
    # ---------------------------------------------------------------------------------------------- Delete any project layers from ArcMap
    layersToRemove = (demOut,hillshadeOut,depthOut)#aoiOut,contoursOut,
    x = 0
    for layer in layersToRemove:
        if arcpy.Exists(layer):
            if x == 0:
                AddMsgAndPrint("\nRemoving previous layers from your ArcMap session " + watershedGDB_name ,0)
                x+=1
            try:
                arcpy.Delete_management(layer)
                AddMsgAndPrint("\tRemoving " + layer + "",0)
            except:
                pass
    del x
    del layer
    del layersToRemove
    
    # ------------------------------------------------------------------------ If project geodatabase exists remove any previous datasets 
    if arcpy.Exists(watershedGDB_path):
        datasetsToRemove = (DEM_aoi,Hillshade,depthGrid,DEMsmooth,ContoursTemp,Fill_DEMaoi,FilMinus)
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
        
        if not arcpy.Exists(watershedFD):
            arcpy.CreateFeatureDataset_management(watershedGDB_path, "Layers", sr)

    # ------------------------------------------------------------ If project geodatabase and feature dataset do not exist, create them.
    else:
        # Create project file geodatabase
        arcpy.CreateFileGDB_management(userWorkspace, watershedGDB_name)
        
        # Create Feature Dataset using spatial reference of input DEM
        arcpy.CreateFeatureDataset_management(watershedGDB_path, "Layers", sr)
        
        AddMsgAndPrint("\nSuccessfully created File Geodatabase: " + watershedGDB_name,0)
        
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

    # paths are the same therefore input IS projectAOI
    else:
        AddMsgAndPrint("\nUsing Existing \"" + str(projectName) + "_AOI\" feature class:",0)
        
        # Use temp lyr, delete from TOC and copy back to avoid refresh issues in arcmap
        arcpy.CopyFeatures_management(AOI, aoiTemp)
        
        if arcpy.Exists(aoiOut):
            arcpy.Delete_management(aoiOut)
        arcpy.CopyFeatures_management(aoiTemp, projectAOI)
        arcpy.Delete_management(aoiTemp)
        
    # -------------------------------------------------------------------------------------------- Exit if AOI was not a polygon    
    if arcpy.Describe(projectAOI).ShapeType != "Polygon":
        AddMsgAndPrint("\n\nYour Area of Interest must be a polygon layer!...Exiting!",2)
        sys.exit()
  
    # --------------------------------------------------------------------------------------------  Populate AOI with DEM Properties
    # Write input DEM name to AOI
    # Note: VB Expressions may need to be updated to Python to prepare for conversion to Pro
    if len(arcpy.ListFields(projectAOI,"INPUT_DEM")) < 1:
        arcpy.AddField_management(projectAOI, "INPUT_DEM", "TEXT", "", "", "", "", "NULLABLE", "NON_REQUIRED", "")
    #gp.CalculateField_management(projectAOI, "INPUT_DEM", "\"" + os.path.basename(inputDEM) +  "\"", "VB", "")
    expression = '"' + os.path.basename(inputDEM) + '"'
    arcpy.CalculateField_management(projectAOI, "INPUT_DEM", expression, "PYTHON_9.3")
    del expression
    
    # Write XY Units to AOI
    if len(arcpy.ListFields(projectAOI,"XY_UNITS")) < 1:
        arcpy.AddField_management(projectAOI, "XY_UNITS", "TEXT", "", "", "", "", "NULLABLE", "NON_REQUIRED", "")
    #gp.CalculateField_management(projectAOI, "XY_UNITS", "\"" + str(units) + "\"", "VB", "")
    expression = '"' + str(units) + '"'
    arcpy.CalculateField_management(projectAOI, "XY_UNITS", expression, "PYTHON_9.3")
    del expression
    
    # Write Z Units to AOI
    if len(arcpy.ListFields(projectAOI,"Z_UNITS")) < 1:
        arcpy.AddField_management(projectAOI, "Z_UNITS", "TEXT", "", "", "", "", "NULLABLE", "NON_REQUIRED", "")
    #gp.CalculateField_management(projectAOI, "Z_UNITS", "\"" + str(zUnits) + "\"", "VB", "")
    expression = '"' + str(zUnits) + '"'
    arcpy.CalculateField_management(projectAOI, "Z_UNITS", expression, "PYTHON_9.3")
    del expression

    # Delete unwanted "Id" remanant field
    if len(arcpy.ListFields(projectAOI,"Id")) > 0:
        try:
            arcpy.DeleteField_management(projectAOI,"Id")
        except:
            pass

    #--------------------------------------------------------------------- Add Acre field
    if not len(arcpy.ListFields(projectAOI,"Acres")) > 0:
        arcpy.AddField_management(projectAOI, "Acres", "DOUBLE", "", "", "", "", "NULLABLE", "NON_REQUIRED", "")

    #--------------------------------------------------------------------- Calculate Acres
    expression = "!Shape.Area@acres!"
    arcpy.CalculateField_management(projectAOI, "Acres", expression, "PYTHON_9.3")
    
    # Get the Shape Area to notify user of Area and Acres of AOI
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
            AddMsgAndPrint("\tCould not calculate Acres for AOI ID: " + str(row.OBJECTID),2)
        del area
        del acres
        row = rows.next()
    del rows
    del row

    # ------------------------------------------------------------------------------------------------- Clip inputDEM
    maskedDEM = arcpy.sa.ExtractByMask(inputDEM, projectAOI)
    maskedDEM.save(DEM_aoi)
    AddMsgAndPrint("\nSuccessully Clipped " + os.path.basename(inputDEM) + " using " + os.path.basename(projectAOI),0)

    # ------------------------------------------------------------------------------------------------ Create Smoothed Contours
    createContours = False
    if len(interval) > 0:
        if interval > 0:
            createContours = True
            try:
                float(interval)
            except:
                AddMsgAndPrint("\n\tContour Interval Must be a Number. Contours will NOT be created!",0)
                createContours = False
    else:
        createContours = False
        AddMsgAndPrint("\nContours will not be created since interval was not specified or set to 0",0)

    if createContours:
        # Run Focal Statistics on the DEM_aoi for the purpose of generating smooth contours
        outFocalStats = arcpy.sa.FocalStatistics(DEM_aoi, "RECTANGLE 3 3 CELL","MEAN","DATA")
        outFocalStats.save(DEMsmooth)
        AddMsgAndPrint("\nSuccessully Smoothed " + os.path.basename(DEM_aoi),0)
        
        arcpy.sa.Contour(DEMsmooth, ContoursTemp, interval, "0", Zfactor)
        AddMsgAndPrint("\nSuccessfully Created " + str(interval) + " foot Contours using a Z-factor of " + str(Zfactor),0)
        
        arcpy.AddField_management(ContoursTemp, "Index", "DOUBLE", "", "", "", "", "NULLABLE", "NON_REQUIRED", "")
        if arcpy.Exists("ContourLYR"):
            try:
                arcpy.Delete_management("ContourLYR")
            except:
                pass
            
        arcpy.MakeFeatureLayer_management(ContoursTemp,"ContourLYR","","","")

        # Every 5th contour will be indexed to 1
        expression = "MOD( \"CONTOUR\"," + str(float(interval) * 5) + ") = 0"
        arcpy.SelectLayerByAttribute_management("ContourLYR", "NEW_SELECTION", expression)
        del expression
        
        indexValue = 1
        #gp.CalculateField_management("ContourLYR", "Index", indexValue, "VB","")
        arcpy.CalculateField_management("ContourLYR", "Index", indexValue, "PYTHON_9.3")
        del indexValue

        # All othe contours will be indexed to 0
        arcpy.SelectLayerByAttribute_management("ContourLYR", "SWITCH_SELECTION", "")
        indexValue = 0
        #gp.CalculateField_management("ContourLYR", "Index", indexValue, "VB","")
        arcpy.CalculateField_management("ContourLYR", "Index", indexValue, "PYTHON_9.3")
        del indexValue

        # Clear selection and write all contours to a new feature class        
        arcpy.SelectLayerByAttribute_management("ContourLYR","CLEAR_SELECTION","")      
        arcpy.CopyFeatures_management("ContourLYR", Contours)

        # Delete unwanted "Id" remanant field
        if len(arcpy.ListFields(Contours,"Id")) > 0:
            try:
                arcpy.DeleteField_management(Contours,"Id")
            except:
                pass

    # ---------------------------------------------------------------------------------------------- Create Hillshade and Depth Grid
    # Process: Creating Hillshade from DEM_aoi
    # This section needs a different Zfactor than just the contours conversion multiplier!
    # Update Zfactor for use with hillshade

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

    outHill = arcpy.sa.Hillshade(DEM_aoi, "315", "45", "#", Zfactor)
    outHill.save(Hillshade)
    AddMsgAndPrint("\nSuccessfully Created Hillshade from " + os.path.basename(DEM_aoi),0)

    
    fill = False
    try:
        # Fills sinks in DEM_aoi to remove small imperfections in the data.
        outFill = arcpy.sa.Fill(DEM_aoi, "")
        #gp.Fill_sa(DEM_aoi, Fill_DEMaoi, "")
        AddMsgAndPrint("\nSuccessfully filled sinks in " + os.path.basename(DEM_aoi) + " to create Depth Grid",0)
        fill = True

    except:
        AddMsgAndPrint("\nError encountered while filling sinks on " + os.path.basename(DEM_aoi) + "\n",1)
        AddMsgAndPrint("\nDepth Grid will not be created\n",1)

    if fill:
        # DEM_aoi - Fill_DEMaoi = FilMinus
        FilMinus = arcpy.sa.Minus(outFill, DEM_aoi)
        #gp.Minus_sa(Fill_DEMaoi, DEM_aoi, FilMinus)
        # Create a Depth Grid; Any pixel where there is a difference write it out
        tempDepths = arcpy.sa.Con(FilMinus, FilMinus, "", "VALUE > 0")
        #gp.Con_sa(FilMinus, FilMinus, depthGrid, "", "VALUE > 0")
        tempDepths.save(depthGrid)
        
        AddMsgAndPrint("\nSuccessfully Created a Depth Grid",0)

    # ---------------------------------------------------------------------------------------------- Delete Intermediate data
    datasetsToRemove = (DEMsmooth,ContoursTemp,"ContourLYR", FilMinus)
    x = 0
    for dataset in datasetsToRemove:
        if arcpy.Exists(dataset):
            # Strictly Formatting
            if x < 1:
                x += 1
            try:
                arcpy.Delete_management(dataset)
            except:
                pass
    del datasetsToRemove
    del x

    # ------------------------------------------------------------------------------------------------ Compact FGDB
    try:
        arcpy.Compact_management(watershedGDB_path)
        AddMsgAndPrint("\nSuccessfully Compacted FGDB: " + os.path.basename(watershedGDB_path),0)    
    except:
        pass      

    # ------------------------------------------------------------------------------------------------ Prepare to Add to Arcmap
    if createContours:
        arcpy.SetParameterAsText(5, Contours)
        
    arcpy.SetParameterAsText(6, projectAOI)
    arcpy.SetParameterAsText(7, DEM_aoi)
    arcpy.SetParameterAsText(8, Hillshade)
    arcpy.SetParameterAsText(9, depthGrid)

    AddMsgAndPrint("\nAdding Layers to ArcMap",0)
    AddMsgAndPrint("\n",0)

    # ------------------------------------------------------------------------------------------------ Clean up Time!
    arcpy.RefreshCatalog(watershedGDB_path)
    

except SystemExit:
    pass

except KeyboardInterrupt:
    AddMsgAndPrint("Interruption requested....exiting")

except:
    print_exception()
