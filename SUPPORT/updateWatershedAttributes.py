## UpdateWatershedAttributes.py
##
## Created by Peter Mead, Adolfo Diaz, USDA NRCS, 2013
## Updated by Chris Morse, USDA, 2020
##
## Update Drainage Area, Slope, Flow Length for an existing selected watershed layer

## ================================================================================================================ 
def print_exception():
    
    tb = sys.exc_info()[2]
    l = traceback.format_tb(tb)
    l.reverse()
    tbinfo = "".join(l)
    AddMsgAndPrint("\n----------ERROR Start-------------------\n",2)
    AddMsgAndPrint("Traceback Info:\n" + tbinfo + "Error Info:\n    " +  str(sys.exc_type)+ ": " + str(sys.exc_value) + "",2)
    AddMsgAndPrint("----------ERROR End--------------------\n",2)

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
    f.write("Executing \"Update Watershed Attributess\" tool\n")
    f.write("User Name: " + getpass.getuser() + "\n")
    f.write("Date Executed: " + time.ctime() + "\n")
    f.write("ArcGIS Version: " + str(arcpy.GetInstallInfo()['Version']) + "\n")
    f.write("User Parameters:\n")
    f.write("\tInput Watershed: " + watershed + "\n")
    
    f.close
    del f
    
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
import arcpy, sys, os, traceback, string, re

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
        sys.exit("")
        
    # Script Parameters
    watershed = arcpy.GetParameterAsText(0)

    # --------------------------------------------------------------------- Variables
    watershedPath = arcpy.Describe(watershed).CatalogPath
    watershedGDB_path = watershedPath[:watershedPath.find('.gdb')+4]
    watershedGDB_name = os.path.basename(watershedGDB_path)
    userWorkspace = os.path.dirname(watershedGDB_path)
    watershedFD = watershedGDB_path + os.sep + "Layers"
    wsName = os.path.basename(watershed)
    projectName = arcpy.ValidateTableName(os.path.basename(userWorkspace).replace(" ","_"))
    projectAOI = watershedFD + os.sep + projectName + "_AOI"
    Flow_Length = watershedFD + os.sep + wsName + "_FlowPaths"
    
    # log File Path
    textFilePath = userWorkspace + os.sep + projectName + "_EngTools.txt"   
    
    # record basic user inputs and settings to log file for future purposes
    logBasicSettings()
    
    if arcpy.Exists(Flow_Length):
        updateFlowLength = True
    else:
        updateFlowLength = False
        
    # --------------------------------------------------------------------- Permanent Datasets
    DEM_aoi = watershedGDB_path + os.sep + projectName + "_DEM"
    DEMsmooth = watershedGDB_path + os.sep + "DEMsmooth"

    # --------------------------------------------------------------------- Temporary Datasets
    wtshdDEMsmooth = watershedGDB_path + os.sep + "wtshdDEMsmooth"
    slopeGrid = watershedGDB_path + os.sep + "slopeGrid"
    slopeStats = watershedGDB_path + os.sep + "slopeStats"

    # --------------------------------------------------------------------- Get XY Units
    desc = arcpy.Describe(DEM_aoi)
    sr = desc.SpatialReference
    units = sr.LinearUnitName
    cellSize = desc.MeanCellWidth
    
    if units == "Meter":
        units = "Meters"
    elif units == "Foot":
        units = "Feet"
    elif units == "Foot_US":
        units = "Feet"
        
##    # ------------------------------------ Capture default environments
##    tempExtent = gp.Extent
##    tempMask = gp.mask
##    tempSnapRaster = gp.SnapRaster
##    tempCellSize = gp.CellSize
##    tempCoordSys = gp.OutputCoordinateSystem
##
##    # ----------------------------------- Set Environment Settings
##    gp.Extent = "MINOF"
##    gp.CellSize = cellSize
##    gp.mask = ""
##    gp.SnapRaster = DEM_aoi
##    gp.OutputCoordinateSystem = sr
    
    # ---------------------------------------------------------------------- Update Drainage Area(s)
    AddMsgAndPrint("\nUpdating drainage area(s) acres...",0)
    if len(arcpy.ListFields(watershed,"Acres")) < 1:
        # Acres field doesn't exist, so create it
        arcpy.AddField_management(watershed, "Acres", "DOUBLE")
        
    # Acres field now exists either way, so update it
    try:
        expression = "!shape.area@acres!"
        arcpy.CalculateField_management(watershed, "Acres", expression, "PYTHON_9.3")
        del expression
        displayAreaInfo = True
        AddMsgAndPrint("\nSuccessfully updated drainage area(s) acres.",0)
    except:
        displayAreaInfo = False
        AddMsgAndPrint("\nUnable to update drainage acres... You must manually calculate acres in " + str(wsName) + "'s attribute table",1)

    # ---------------------------------------------------------------------- Update Flow Path Length (if present)
    if updateFlowLength:
        AddMsgAndPrint("\nUpdating flow path lengths...",0)
        if len(arcpy.ListFields(Flow_Length,"Length_ft")) < 1:
            # Length_ft field doesn't exist, so create it
            arcpy.AddField_management(Flow_Length, "Length_ft", "DOUBLE")
        else:
            # Length_ft field exists, so update it
            try:
                expression = "!shape.length@feet!"
                arcpy.CalculateField_management(Flow_Length, "Length_ft", expression, "PYTHON_9.3")
                del expression
                AddMsgAndPrint("\nSuccessfully updated flow path length(s).",0)
            except:
                AddMsgAndPrint("\nUnable to update flow length(s)...  You must manually calculate length in " + str(os.path.basename(Flow_Length)) + "'s attribute table",1)        
             
    # ----------------------------------------------------------------------- Update Average Slope
    calcAvgSlope = False

    # ----------------------------- Retrieve Z Units from AOI    
    if arcpy.Exists(projectAOI):
        
        rows = arcpy.SearchCursor(projectAOI)
        row = rows.next()
        zUnits = row.Z_UNITS

        del rows
        del row
        
        # Assign proper Z factor
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

        # zUnits must be inches; no more choices                
        else:
            if units == "Feet":
                Zfactor = 0.0833333
            if units == "Meters":
                Zfactor = 0.0254
    else:
        Zfactor = 0 # trapped for below so if Project AOI not present slope isnt calculated
        
    # --------------------------------------------------------------------------------------------------------
    if Zfactor > 0:
        AddMsgAndPrint("\nCalculating average slope...",0)
        
        if arcpy.Exists(DEMsmooth):
            
            # Use smoothed DEM to calculate slope to remove extraneous values
            if len(arcpy.ListFields(watershed, "Avg_Slope")) < 1:
                arcpy.AddField_management(watershed, "Avg_Slope", "DOUBLE", "", "", "", "", "NULLABLE", "NON_REQUIRED", "")

            #gp.ExtractByMask_sa(DEMsmooth, watershed, wtshdDEMsmooth)
            tempWtshDEM = arcpy.sa.ExtractByMask(DEMsmooth, watershed)
            tempWtshDEM.save(wtshdDEMsmooth)
            
            #gp.Slope_sa(wtshdDEMsmooth, slopeGrid, "PERCENT_RISE", Zfactor)
            tempSlope = arcpy.sa.Slope(wtshdDEMsmooth, "PERCENT_RISE", Zfactor)
            tempSlope.save(slopeGrid)
            
            #gp.ZonalStatisticsAsTable_sa(watershed, "Subbasin", slopeGrid, slopeStats, "DATA")
            arcpy.sa.ZonalStatisticsAsTable(watershed, "Subbasin", slopeGrid, slopeStats, "DATA")
            calcAvgSlope = True

            # Delete unwanted rasters
            arcpy.Delete_management(DEMsmooth)
            arcpy.Delete_management(wtshdDEMsmooth)
            arcpy.Delete_management(slopeGrid)

        elif arcpy.Exists(DEM_aoi):
           
            # Run Focal Statistics on the DEM_aoi to remove exteraneous values
            #gp.focalstatistics_sa(DEM_aoi, DEMsmooth,"RECTANGLE 3 3 CELL","MEAN","DATA")
            tempFocal = arcpy.sa.FocalStatistics(DEM_aoi, "RECTANGLE 3 3 CELL","MEAN","DATA")
            tempFocal.save(DEMsmooth)

            arcpy.AddField_management(watershed, "Avg_Slope", "DOUBLE", "", "", "", "", "NULLABLE", "NON_REQUIRED", "")

            #gp.ExtractByMask_sa(DEMsmooth, watershed, wtshdDEMsmooth)
            tempWtshDEM = arcpy.sa.ExtractByMask(DEMsmooth, watershed)
            tempWtshDEM.save(wtshdDEMsmooth)
            
            #gp.Slope_sa(wtshdDEMsmooth, slopeGrid, "PERCENT_RISE", Zfactor)
            tempSlope = arcpy.sa.Slope(wtshdDEMsmooth, "PERCENT_RISE", Zfactor)
            tempSlope.save(slopeGrid)
            
            #gp.ZonalStatisticsAsTable_sa(watershed, "Subbasin", slopeGrid, slopeStats, "DATA")
            arcpy.sa.ZonalStatisticsAsTable(watershed, "Subbasin", slopeGrid, slopeStats, "DATA")
            calcAvgSlope = True

            # Delete unwanted rasters
            arcpy.Delete_management(DEMsmooth)
            arcpy.Delete_management(wtshdDEMsmooth)
            arcpy.Delete_management(slopeGrid)   

        else:
            AddMsgAndPrint("\nMissing DEMsmooth and DEM_aoi from FGDB. Could not Calculate Average Slope",1)
    else:
        AddMsgAndPrint("\nMissing Project AOI from FGDB. Could not retrieve Z Factor to Calculate Average Slope",1)

    # -------------------------------------------------------------------------------------- Update Watershed FC with Average Slope
    if calcAvgSlope:
        
        # go through each zonal Stat record and pull out the Mean value
        rows = arcpy.SearchCursor(slopeStats)
        row = rows.next()

        AddMsgAndPrint("\nSuccessfully re-calculated average slope",0)

        AddMsgAndPrint("\n===================================================",0)
        AddMsgAndPrint("\tUser Watershed: " + str(wsName),0)
        
        while row:
            wtshdID = row.OBJECTID

            # zonal stats doesnt generate "Value" with the 9.3 geoprocessor
            if len(arcpy.ListFields(slopeStats,"Value")) > 0:
                zonalValue = row.VALUE
                
            else:
                zonalValue = row.SUBBASIN
                
            zonalMeanValue = row.MEAN

            whereclause = "Subbasin = " + str(zonalValue)
            wtshdRows = arcpy.UpdateCursor(watershed,whereclause)
            wtshdRow = wtshdRows.next()           

            # Pass the Mean value from the zonalStat table to the watershed FC.
            while wtshdRow:
                wtshdRow.Avg_Slope = zonalMeanValue
                wtshdRows.updateRow(wtshdRow)

                # Inform the user of Watershed Acres, area and avg. slope
                if displayAreaInfo:
                    
                    # Inform the user of Watershed Acres, area and avg. slope
                    AddMsgAndPrint("\n\tSubbasin: " + str(wtshdRow.OBJECTID),0)
                    AddMsgAndPrint("\t\tAcres: " + str(splitThousands(round(wtshdRow.Acres,2))),0)
                    AddMsgAndPrint("\t\tArea: " + str(splitThousands(round(wtshdRow.Shape_Area,2))) + " Sq. " + units,0)
                    AddMsgAndPrint("\t\tAvg. Slope: " + str(round(zonalMeanValue,2)),0)

                else:
                    AddMsgAndPrint("\tSubbasin " + str(wtshdRow.OBJECTID) + " Avg. Slope: " + str(zonalMeanValue) + "%",0)
                                   
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
        AddMsgAndPrint("\n===================================================",0)
        arcpy.Delete_management(slopeStats)

    ## ????????
    import time
    time.sleep(5)
    
    # ------------------------------------------------------------------------------------------------ Compact FGDB
    try:
        arcpy.Compact_management(watershedGDB_path)
        AddMsgAndPrint("\nSuccessfully Compacted FGDB: " + os.path.basename(watershedGDB_path),0)    
    except:
        pass

    # ------------------------------------------------------------------------------------------------ Cleanup
##    # Restore original environments
##    gp.extent = tempExtent
##    gp.mask = tempMask
##    gp.SnapRaster = tempSnapRaster
##    gp.CellSize = tempCellSize
##    gp.OutputCoordinateSystem = tempCoordSys
    
    
except SystemExit:
    pass

except KeyboardInterrupt:
    AddMsgAndPrint("Interruption requested....exiting")

except:
    print_exception()    
