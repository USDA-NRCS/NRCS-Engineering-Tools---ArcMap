## wascobWorksheet.py
##
## Created by Peter Mead, USDA NRCS, 2013
## Updated by Chris Morse, USDA NRCS, 2020
##
## <Pending>

#----------------------------------------------------------------------------
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
    f.write("Executing \"6. Wascob Design Worksheet\" tool\n")
    f.write("User Name: " + getpass.getuser() + "\n")
    f.write("Date Executed: " + time.ctime() + "\n")
    f.write("ArcGIS Version: " + str(arcpy.GetInstallInfo()['Version']) + "\n")
    f.write("User Parameters:\n")
    f.write("\tWorkspace: " + userWorkspace + "\n")
    f.write("\tInput Watershed: " + inWatershed + "\n")
        
    f.close
    del f   

## ================================================================================================================
# Import system modules
import arcpy, sys, os, traceback, subprocess, time, shutil

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
    # ---------------------------------------------- Input Parameters
    inWatershed = arcpy.GetParameterAsText(0)

    # ---------------------------------------------- Variables
    watershed_path = arcpy.Describe(inWatershed).CatalogPath
    watershedGDB_path = watershed_path[:watershed_path .find(".gdb")+4]
    watershedFD_path = watershedGDB_path + os.sep + "Layers"
    watershedGDB_name = os.path.basename(watershedGDB_path)
    userWorkspace = os.path.dirname(watershedGDB_path)
    wsName = os.path.basename(inWatershed)
    outputFolder = userWorkspace + os.sep + "gis_output"
    tables = outputFolder + os.sep + "tables"
    Documents = userWorkspace + os.sep + "Documents"
    
    # Set path to log file and start logging
    textFilePath = userWorkspace + os.sep + os.path.basename(userWorkspace).replace(" ","_") + "_EngTools.txt"    
    logBasicSettings()
    
    # ------------------------------------------------ Existing Data
    inWorksheet = os.path.join(os.path.dirname(sys.argv[0]), "LiDAR_WASCOB.xlsm")
    rcn = watershedFD_path + os.sep + wsName + "_RCN"

    # ------------------------------------------------ Permanent Datasets
    stakeoutPoints = watershedFD_path + os.sep + "stakeoutPoints"
    rcnTable = tables + os.sep + "RCNsummary.dbf"
    watershedTable = tables + os.sep + "watershed.dbf"

    # ---------------------------- Layers in ArcMap
    outPoints = "StakeoutPoints"

    # Check inputs and workspace
    AddMsgAndPrint("\nChecking inputs...",0)
    
    # Make sure RCN layer was created
    if not arcpy.Exists(rcn):
        AddMsgAndPrint("\t" + str(os.path.basename(rcn)) + " not found in " + str(watershedGDB_name),2)
        AddMsgAndPrint("\tYou must run Tool #5: \"Calculate Runoff Curve Number\" before executing this tool. Exiting...",2)
        sys.exit()
        
    # Make Sure RCN Field is in the Watershed
    if not len(arcpy.ListFields(inWatershed,"RCN")) > 0:
        AddMsgAndPrint("\tRCN Field not found in " + str(wsName),2)
        AddMsgAndPrint("\tYou must run Tool #5: \"Calculate Runoff Curve Number\" before executing this tool. Exiting...",2)
        sys.exit()        

    # Make Sure RCN Field has valid value(s)
    rows = arcpy.SearchCursor(inWatershed)
    row = rows.next()
    invalidValue = 0
    
    while row:
        rcnValue = str(row.RCN)
        if not len(rcnValue) > 0:  # NULL Value
            invalidValue += 1            
        row = rows.next()
    del rows, row
    
    if invalidValue > 0:
        AddMsgAndPrint("\tRCN Field in " + str(wsName) + " contains invalid or Null values!",2)
        AddMsgAndPrint("\tRe-run Tool #5: \"Calculate Runoff Curve Number\" or manually correct RCN value(s). Exiting...",2)
        sys.exit()
        
    del invalidValue
    
    # Make sure Wacob Worksheet template exists
    if not arcpy.Exists(inWorksheet):
        AddMsgAndPrint("\tLiDAR_WASCOB.xlsm Worksheet template not found in " + str(os.path.dirname(sys.argv[0])),2)
        AddMsgAndPrint("\tPlease Check the Support Folder and replace the file if necessary. Exiting...",2)
        sys.exit()
        
    # Check Addnt'l directories
    if not arpcy.Exists(outputFolder):
        arcpy.CreateFolder_management(userWorkspace, "gis_output")
    if not arcpy.Exists(tables):
        arcpy.CreateFolder_management(outputFolder, "tables")
        
    # If Documents folder not present, create and copy required files to it
    if not arcpy.Exists(Documents):
        arcpy.CreateFolder_management(userWorkspace, "Documents")
        DocumentsFolder =  os.path.join(os.path.dirname(sys.argv[0]), "Documents")
        if arcpy.Exists(DocumentsFolder):
            arcpy.Copy_management(DocumentsFolder, Documents, "Folder")
        del DocumentsFolder
    
    # Copy User Watershed and RCN Layer tables for spreadsheet import
    AddMsgAndPrint("\nCopying results to tables...\n",0)
    arcpy.CopyRows_management(inWatershed, watershedTable, "")
    arcpy.CopyRows_management(rcn, rcnTable, "")
        
    # ------------------------------------------------------------------ Create Wascob Worksheet
    #os.path.basename(userWorkspace).replace(" ","_") + "_Wascob.gdb" 
    outWorksheet = Documents + os.sep + os.path.basename(userWorkspace).replace(" ","_") + "_WASCOB.xlsm"
    x = 1
    while x > 0:
        if arcpy.Exists(outWorksheet):
            outWorksheet = Documents + os.sep + os.path.basename(userWorkspace).replace(" ","_") + "_WASCOB" + str(x) + ".xlsm"
            x += 1
        else:
            x = 0
    del x

    # Copy template and save as defined
    shutil.copyfile(inWorksheet, outWorksheet)
                    
    # --------------------------------------------------------------------------- Create Stakeout Points FC    
    if not arcpy.Exists(outPoints):
    
        arcpy.CreateFeatureclass_management(watershedFD_path, "stakeoutPoints", "POINT", "", "DISABLED", "DISABLED", "", "", "0", "0", "0")
        arcpy.AddField_management(stakeoutPoints, "ID", "LONG", "", "", "", "", "NULLABLE", "NON_REQUIRED", "")
        arcpy.AddField_management(stakeoutPoints, "Subbasin", "LONG", "", "", "", "", "NULLABLE", "NON_REQUIRED", "")
        arcpy.AddField_management(stakeoutPoints, "Elev", "DOUBLE", "", "", "", "", "NULLABLE", "NON_REQUIRED", "")
        arcpy.AddField_management(stakeoutPoints, "Notes", "TEXT", "", "", "50", "", "NULLABLE", "NON_REQUIRED", "")

        # ------------------------------------------------------------------------------------------------ Compact FGDB
        try:
            arcpy.Compact_management(watershedGDB_path)
        except:
            pass
        
        # ------------------------------------------------------------------------------------------------ add to ArcMap
        AddMsgAndPrint("\nAdding Stakeout Points to ArcMap Session\n",0)    
        arcpy.SetParameterAsText(1, stakeoutPoints)       
   

    # ----------------------------------------------------------------------- Launch Wascob Spreadsheet
    AddMsgAndPrint("\n===============================================================",0)
    AddMsgAndPrint("\tThe LiDAR_WASCOB Spreadsheet will open in Microsoft Excel",0)
    AddMsgAndPrint("\tand has been saved to " + str(userWorkspace)+ " \Documents.",0)
    AddMsgAndPrint("\tIf the file doesn't open automatically, navigate to the above ",0)
    AddMsgAndPrint("\tlocation and open it manually.",0)
    AddMsgAndPrint("\tOnce Excel is open, enable macros (if not already enabled),",0)
    AddMsgAndPrint("\tand set the path to your project folder to import your gis data.",0)
    AddMsgAndPrint("\tOnce you have completed the Wascob Design Sheet(s) you can return ",0)
    AddMsgAndPrint("\tto ArcMap and complete the degign height and tile layout steps.",0)
    AddMsgAndPrint("\n===============================================================",0)

    try:
        os.startfile(outWorksheet)
    except:
        AddMsgAndPrint("\tCould not open the Excel Worksheet. Please open it manually.",0)
        
    AddMsgAndPrint("\nProcessing Finished\n",0)
    
except SystemExit:
    pass

except KeyboardInterrupt:
    AddMsgAndPrint("Interruption requested. Exiting...")

except:
    print_exception()

