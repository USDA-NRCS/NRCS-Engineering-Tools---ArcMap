## PrepareSoilsLanduse.py
##
## Created by Peter Mead, Adolfo Diaz, USDA NRCS, 2013
## Updated by Chris Morse, USDA NRCS, 2020
##
## Create soil layer and land use layer in formats usable by tools and to make ready for editing, in watershed extent
##
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
    f.write("Executing \"Prepare Soils and Landuse\" tool\n")
    f.write("User Name: " + getpass.getuser() + "\n")
    f.write("Date Executed: " + time.ctime() + "\n")
    f.write("ArcGIS Version: " + str(arcpy.GetInstallInfo()['Version']) + "\n")
    f.write("User Parameters:\n")
    f.write("\tWorkspace: " + userWorkspace + "\n")
    f.write("\tInput Soils Data: " + inSoils + "\n")
    f.write("\tInput Hydrologic Groups Field: " + inputField + "\n")
    if splitLU:    
        f.write("\tInput CLU Layer: " + inCLU + " \n")
    else:
        f.write("\tInput CLU Layer: BLANK" + " \n")
    
    f.close
    del f

## ================================================================================================================
# Import system modules
import arcpy, sys, os, string, traceback

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
    # Script Parameters
    inWatershed = arcpy.GetParameterAsText(0)
    inSoils = arcpy.GetParameterAsText(1)
    inputField = arcpy.GetParameterAsText(2)
    inCLU = arcpy.GetParameterAsText(3)

    # --------------------------------------------------------------------------- Define Variables 
    inWatershed = arcpy.Describe(inWatershed).CatalogPath
    inSoils = arcpy.Describe(inSoils).CatalogPath

    if inWatershed.find('.gdb') > -1 or inWatershed.find('.mdb') > -1:
        # inWatershed was created using 'Create Watershed Tool'
        if inWatershed.find('_EngTools'):
            watershedGDB_path = inWatershed[:inWatershed.find('.') + 4]
        # inWatershed is a fc from a DB not created using 'Create Watershed Tool'
        else:
            watershedGDB_path = os.path.dirname(inWatershed[:inWatershed.find('.')+4]) + os.sep + os.path.basename(inWatershed).replace(" ","_") + "_EngTools.gdb"
    # inWatershed is a shapefile
    elif inWatershed.find('.shp')> -1:
        watershedGDB_path = os.path.dirname(inWatershed[:inWatershed.find('.')+4]) + os.sep + os.path.basename(inWatershed).replace(".shp","").replace(" ","_") + "_EngTools.gdb"
    else:
        arcpy.AddError("\nWatershed Polygon must either be a feature class or shapefile! Exiting...")
        sys.exit()

    watershedFD = watershedGDB_path + os.sep + "Layers"
    watershedGDB_name = os.path.basename(watershedGDB_path)
    userWorkspace = os.path.dirname(watershedGDB_path)
    wsName = os.path.splitext(os.path.basename(inWatershed))[0]

    # Determine if CLU is present
    if len(str(inCLU)) > 0:
        inCLU = arcpy.Describe(inCLU).CatalogPath
        splitLU = True
        
    else:
        splitLU = False
        
    # Set log file path and start logging
    textFilePath = userWorkspace + os.sep + os.path.basename(userWorkspace).replace(" ","_") + "_EngTools.txt"
    logBasicSettings()

    # ----------------------------------------------------------------------------- Datasets    
    # --------------------------------------------------- Permanent Datasets
    wsSoils = watershedFD + os.sep + wsName + "_Soils"
    landuse = watershedFD + os.sep + wsName + "_Landuse"
    watershed = watershedFD + os.sep + wsName

    # ---------------------------------------------------- Temporary Datasets
    cluClip = watershedFD + os.sep + "cluClip"
    watershedDissolve = watershedFD + os.sep + "watershedDissolve"
    luUnion = watershedFD + os.sep + "luUnion"

    # ----------------------------------------------------------- Lookup Tables
    TR_55_LU_Lookup = os.path.join(os.path.dirname(sys.argv[0]), "Support.gdb" + os.sep + "TR_55_LU_Lookup")
    Hydro_Groups_Lookup = os.path.join(os.path.dirname(sys.argv[0]), "Support.gdb" + os.sep + "HydroGroups")
    Condition_Lookup = os.path.join(os.path.dirname(sys.argv[0]), "Support.gdb" + os.sep + "ConditionTable")    

    # ----------------------------------------------------------------------------- Check Some Parameters
    # Exit if any are true
    AddMsgAndPrint("\nChecking inputs and project data...",0)
    if not int(arcpy.GetCount_management(inWatershed).getOutput(0)) > 0:
        AddMsgAndPrint("\tWatershed Layer is empty. Exiting...",2)
        sys.exit()

    # Exit if wathershed layer not a polygon        
    if arcpy.Describe(inWatershed).ShapeType != "Polygon":
        AddMsgAndPrint("\tInput Watershed Layer must be a polygon layer. Exiting...",2)
        sys.exit()

    # Exit if soils layer not a polygon
    if arcpy.Describe(inSoils).ShapeType != "Polygon":
        AddMsgAndPrint("\tInput Soils Layer must be a polygon layer. Exiting...",2)
        sys.exit()

    # Exit if CLU layer not a polygon
    if splitLU:
        if arcpy.Describe(inCLU).ShapeType != "Polygon":
            AddMsgAndPrint("\tInput CLU Layer must be a polygon layer. Exiting...",2)
            sys.exit()

    # Exit if Hydro Group field not present
    if not len(arcpy.ListFields(inSoils,inputField)) > 0:
        AddMsgAndPrint("\tThe field specified for Hydrologic Groups does not exist in your soils data. Please check the input layer and field and try again. Exiting...",2)
        sys.exit()

    # Exit if TR55 table not found in directory.
    if not arcpy.Exists(TR_55_LU_Lookup):
        AddMsgAndPrint("\tTR_55_LU_Lookup table was not found! Make sure Support.gdb is located in the same folder as this script. Exiting...",2)
        sys.exit("")

    # Exit if Hydro Groups Lookup table not found in directory
    if not arcpy.Exists(Hydro_Groups_Lookup):
        AddMsgAndPrint("\tHydro_Groups_Lookup table was not found! Make sure Support.gdb is located in the same folder as this script. Exiting...",2)
        sys.exit()

    # Exit if Condition lookup table not found in directory
    if not arcpy.Exists(Condition_Lookup):
        AddMsgAndPrint("\tCondition_Lookup table was not found! Make sure Support.gdb is located in the same folder as this script. Exiting...",2)
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
    desc = arcpy.Describe(watershedGDB_path)
    listOfDomains = []
    domains = desc.Domains
    for domain in domains:
        listOfDomains.append(domain)
    del desc, domains

    if "LandUse_Domain" in listOfDomains:
        arcpy.RemoveDomainFromField_management(landuse, "LANDUSE")
    if "Condition_Domain" in listOfDomains:
        arcpy.RemoveDomainFromField_management(landuse, "CONDITION")
    if "Hydro_Domain" in listOfDomains:
        arcpy.RemoveDomainFromField_management(wsSoils, inputField)
        
    del listOfDomains

    # ---------------------------------------------------------------------------------------------- Delete any project layers from ArcMap        
    # ------------------------------- Map Layers
    landuseOut = "" + wsName + "_Landuse"
    soilsOut = "" + wsName + "_Soils"
    
    # ------------------------------------- Delete previous layers from ArcMap if they exist
    layersToRemove = (landuseOut,soilsOut)

    x = 0
    for layer in layersToRemove:
        if arcpy.Exists(layer):
            if x == 0:
                AddMsgAndPrint("\nRemoving previous layers from your ArcMap session... " + watershedGDB_name ,1)
                x+=1
            try:
                arcpy.Delete_management(layer)
                AddMsgAndPrint("\tRemoving... " + layer + "",0)
            except:
                pass
    del x, layersToRemove
    
    # -------------------------------------------------------------------------- Delete Previous Data if present
    if FGDBexists:    
        layersToRemove = (wsSoils,landuse,cluClip,watershedDissolve,luUnion)
        x = 0        
        for layer in layersToRemove:
            if arcpy.Exists(layer):
                # strictly for formatting
                if x == 0:
                    AddMsgAndPrint("\nRemoving old files from FGDB: " + watershedGDB_name ,1)
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
            arcpy.Delete_management(watershed)
            arcpy.CopyFeatures_management(inWatershed, watershed)
            AddMsgAndPrint("\nSuccessfully overwrote existing watershed.",0)
        else:
            arcpy.CopyFeatures_management(inWatershed, watershed)
            AddMsgAndPrint("\nSuccessfully created watershed layer: " + os.path.basename(watershed) ,0)
        externalWshd = True

    # paths are the same therefore input IS projectAOI
    else:
        AddMsgAndPrint("\nUsing existing " + os.path.basename(watershed) + " watershed layer",0)
    if externalWshd:
        # Delete all fields in watershed layer except for obvious ones
        fields = arcpy.ListFields(watershed)
        for field in fields:
            fieldName = field.name
            if fieldName.find("Shape") < 0 and fieldName.find("OBJECTID") < 0 and fieldName.find("Subbasin") < 0:
                arcpy.Deletefield_management(watershed,fieldName)
            del fieldName
        del fields

        if not len(arcpy.ListFields(watershed,"Subbasin")) > 0:
            arcpy.AddField_management(watershed, "Subbasin", "SHORT", "", "", "", "", "NULLABLE", "NON_REQUIRED", "")        
            arcpy.CalculateField_management(watershed, "Subbasin","!OBJECTID!","PYTHON")

        if not len(arcpy.ListFields(watershed,"Acres")) > 0:
            arcpy.AddField_management(watershed, "Acres", "DOUBLE", "", "", "", "", "NULLABLE", "NON_REQUIRED", "")
            arcpy.CalculateField_management(watershed, "Acres", "!shape.area@acres!", "PYTHON")

    # ------------------------------------------------------------------------------------------------ Create Landuse Layer
    if splitLU:
        AddMsgAndPrint("\nIncorporating CLU layer...",0)
        # Dissolve in case the watershed has multiple polygons        
        arcpy.Dissolve_management(inWatershed, watershedDissolve, "", "", "MULTI_PART", "DISSOLVE_LINES")

        # Clip the CLU layer to the dissolved watershed layer
        arcpy.Clip_analysis(inCLU, watershedDissolve, cluClip, "")
        AddMsgAndPrint("\nSuccessfully clipped the CLU to your watershed layer.",0)

        # Union the CLU and dissolve watershed layer simply to fill in gaps
        arcpy.Union_analysis(cluClip +";" + watershedDissolve, landuse, "ONLY_FID", "", "GAPS")
        AddMsgAndPrint("\nSuccessfully filled in any CLU gaps and created Landuse Layer: " + os.path.basename(landuse),0)

        # Delete FID field
        fields = arcpy.ListFields(landuse,"FID*")
        for field in fields:
            arcpy.Deletefield_management(landuse,field.name)
        del fields

        arcpy.Delete_management(watershedDissolve)
        arcpy.Delete_management(cluClip)

    else:
        AddMsgAndPrint("\nNo CLU Layer Detected.",0)
        AddMsgAndPrint("\nProcessing data...",0)

        arcpy.Dissolve_management(inWatershed, landuse, "", "", "MULTI_PART", "DISSOLVE_LINES")
        AddMsgAndPrint("\nSuccessfully created Watershed Landuse layer: " + os.path.basename(landuse),0)

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

    AddMsgAndPrint("\nSuccessufully added \"LANDUSE\" and \"CONDITION\" fields to Landuse Layer and associated Domains.",0)

    # ---------------------------------------------------------------------------------------------------------------------------------- Work with soils
    
    # --------------------------------------------------------------------------------------- Clip Soils           
    # Clip the soils to the dissolved (and possibly unioned) watershed
    arcpy.Clip_analysis(inSoils,landuse,wsSoils)

    AddMsgAndPrint("\nSuccessfully clipped soils layer to Landuse layer and removed unnecessary fields.",0)  
    
    # --------------------------------------------------------------------------------------- check the soils input Field to make
    # --------------------------------------------------------------------------------------- sure they are valid Hydrologic Group values
    AddMsgAndPrint("\nChecking Hydrologic Group Attributes in Soil Layer...",0)
                   
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
                AddMsgAndPrint("\t\t" + "\"" + hydValue + "\" is not a valid Hydrologic Group attribute.",0)
            if hydValue in valuesToConvert:
                valuesToConvertCount += 1
                #AddMsgAndPrint("\t" + "\"" + hydValue + "\" needs to be converted -------- " + str(valuesToConvertCount),1)
        else: # NULL Value
            emptyValues += 1          
        row = rows.next()
    del rows, row        

    # ------------------------------------------------------------------------------------------- Inform the user of Hydgroup Attributes
    if invalidHydValues > 0:
        AddMsgAndPrint("\tThere are " + str(invalidHydValues) + " invalid attribute(s) found in your Soil's " + "\"" + inputField + "\"" + " Field",1)

    if valuesToConvertCount > 0:
        AddMsgAndPrint("\tThere are " + str(valuesToConvertCount) + " attribute(s) that need to be converted to a single class i.e. \"B/D\" to \"B\"",0)

    if emptyValues > 0:
        AddMsgAndPrint("\tThere are " + str(emptyValues) + " NULL polygon(s) that need to be attributed with a Hydrologic Group",1)

    if emptyValues == int(arcpy.GetCount_management(inSoils).getOutput(0)):
        AddMsgAndPrint("\t" + "\"" + inputField + "\"" + "Field is blank.  It must be populated before using this tool!",1)
        missingValues = 1
        
    del validHydroValues, valuesToConvert, invalidHydValues

    # ------------------------------------------------------------------------------------------- Compare Input Field to SSURGO HydroGroup field name
    if inputField.upper() != "HYDGROUP":
        arcpy.AddField_management(wsSoils, "HYDGROUP", "TEXT", "", "", "20", "", "NULLABLE", "NON_REQUIRED", "")

        if missingValues == 0:
            arcpy.CalculateField_management(wsSoils, "HYDGROUP", "!" + str(inputField) + "!", "PYTHON")
        else:
            AddMsgAndPrint("\n\tAdded " + "\"HYDGROUP\" to soils layer.  Please Populate the Hydrologic Group Values manually for this field",1)

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

    arcpy.SetParameterAsText(4, landuse)
    arcpy.SetParameterAsText(5, wsSoils)
    
    if externalWshd:
        arcpy.SetParameterAsText(6, watershed)       

    AddMsgAndPrint("\nAdding Layers to ArcMap",0)
    AddMsgAndPrint("\n\t=========================================================================",0)
    AddMsgAndPrint("\tBEFORE CALCULATING THE RUNOFF CURVE NUMBER FOR YOUR WATERSHED MAKE SURE TO",0)
    AddMsgAndPrint("\tATTRIBUTE THE \"LANDUSE\" AND \"CONDITION\" FIELDS IN " + os.path.basename(landuse) + " LAYER",0)
    
    if valuesToConvertCount > 0:
        AddMsgAndPrint("\tAND CONVERT THE " + str(valuesToConvertCount) + " COMBINED HYDROLOGIC GROUPS IN " + os.path.basename(wsSoils) + " LAYER",0)
        
    if emptyValues > 0:
        AddMsgAndPrint("\tAS WELL AS POPULATE VALUES FOR THE " + str(emptyValues) + " NULL POLYGONS IN " + os.path.basename(wsSoils) + " LAYER",0)
        
    AddMsgAndPrint("\t=========================================================================\n",0)

    del valuesToConvertCount, emptyValues

    # -------------------------------------------------------------------------------- Clean Up
    arcpy.RefreshCatalog(watershedGDB_path)

except SystemExit:
    pass

except KeyboardInterrupt:
    AddMsgAndPrint("Interruption requested....exiting")

except:
    print_exception()
