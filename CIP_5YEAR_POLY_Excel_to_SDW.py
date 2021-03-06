#-------------------------------------------------------------------------------
# Name:        CIP_5YEAR_POLY_Excel_to_SDW.py
"""
Purpose:
  To update the CIP_5YEAR_POLY feature class on the Blue Workspace (SDW) using
  a constrained Excel spreadsheet that CIP maintains.  The spreadsheet has had
  a number of modifications and constraints put on it so that any alterations
  CIP makes to the spreadsheet, the spreadsheet will always be able to be used
  to update the SDW feature class.

  This script:
    1) Imports the Excel file to a FGDB table.
       FUNCTION: Excel_To_Table()

    2) Validates for correct data (ERRORS result if script needs to stop,
       WARNINGS result if there is potentially missing data).  These messages
       are delivered at the end of the script.
       FUNCTION: Validate_Table()

    3) Processes the data (if valid).  i.e. change all values in [NAME] to be
       all uppercase if there are any lowercase characters. And change the string
       values in the Excel sheet in [TYPE] to the corresponding numeric values
       that are used in the actual SDW FC.
       FUNCTION: Process_Table()

    4) Joins the imported FGDB table to the SDW CIP_5YEAR_POLY feature class,
       FUNCTION: Join_2_Objects()

    5) Calculates the fields from the imported table to the SDW FC (essentially
       overwriting the attributes in the SDW with the attributes from the
       imported table).
       FUNCTION: Update_Fields()
"""
# Author:      mgrue
#
# Created:     12/05/2017
# Copyright:   (c) mgrue 2017
# Licence:     <your licence>
#-------------------------------------------------------------------------------

import arcpy, os, ConfigParser
arcpy.env.overwriteOutput = True

def main():
    #---------------------------------------------------------------------------
    #                 Find and read the ini file to get some variables
    localPath = sys.path[0]
    settingsFile = os.path.join(localPath, "Settings_Excel_to_SDW.ini")

    if os.path.isfile(settingsFile):
        config = ConfigParser.ConfigParser()
        config.read(settingsFile)
    else:
        print("INI file not found. \nMake sure a valid '.ini' file exists in the same directory as this script.")
        sys.exit()

    #---------------------------------------------------------------------------
    #                              Set variables
    #---------------------------------------------------------------------------

    # FGDB to import the Excel table info, user must create FGDB, this is a wkg directory,
    # ***NOT the directory of the Feature Class to update
    wkg_FGDB = config.get('FGDB', 'wkg_FGDB')                                           # Get from INI file


    # Excel file info
    excel_file        = config.get('Excel', 'EXCEL_FILE')                               # Get from INI file
    sheet_to_import   = 'CIP_5YEAR_POLY'  # Sheet name                                  # Should be constant
    join_field        = 'PROJECT_ID'      # Field used to join (primary key)            # Should be constant


    # SDW connection info, this is the FC and budget table to be updated (can be pointed to FGDB to update a FGDB)
    sdw_connection          = config.get('SDW', 'CONNECTION')                             # Get from INI file

    sdw_cip_fds_name   = config.get('SDW', 'FEATURE_DATA_SET')                            # Get from INI file
    sdw_cip_fc_name    = config.get('SDW', 'FEATURE_CLASS')                               # Get from INI file
    sdw_cip_fc_path    = os.path.join(sdw_connection, sdw_cip_fds_name, sdw_cip_fc_name)  # Should be constant

    sdw_cip_budget_tbl_name = config.get('SDW', 'BUDGET_TABLE')                           # Get from INI file
    sdw_cip_budget_tbl_path = os.path.join(sdw_connection, sdw_cip_budget_tbl_name)       # Should be constant


    # List of Fields to update in SDW Feature Class
    # 'PROJECT_ID' not in below list since that is the field used to join
    sdw_field_ls =   ['NAME', 'TYPE', 'PROJECT_STATUS', 'DETAIL_WK_PROG',
                      'FIVE_YR_PLAN', 'EST_START', 'EST_COMPLT',
                      'EST_PR_CST', 'FUNDING_STATUS', 'FUNDING', 'LENGTH',
                      'PLANNING_GROUP', 'SUPERVISOR_DISTRICT', 'THOMAS_BROTHERS',
                      'PROJECT_MANAGER', 'PM_EMAIL', 'PM_PHONE', 'ORACLE_NUMBER',
                      'DESCRIPTION', 'URL_LINK']


    # Dictionary of [TYPE] domains.
    #The left side is the text in Excel : The right side is the numerical value the [TYPE] field expects in SDW
    type_dict = {
    'Road Reconstruction':'1',
    'Community Development Block Grant':'2',
    'Bike Lanes/Pathways':'3',
    'Traffic Signals':'4',
    'Intersection Improvements':'5',
    'Sidewalks':'6',
    'Drainage Improvements':'7',
    'Bridge':'8',
    'Wastewater':'9.1',
    'Airports':'9.2',
    'Utility Undergrounding Districts':'9.3',
    'Watersheds':'9.4'
    }

    #---------------------------------------------------------------------------
    #                       Start running script
    #---------------------------------------------------------------------------

    # Make sure there is an excel_file to import
    if not os.path.isfile(excel_file):
        print '***ERROR! there is no file: {} ***'.format(excel_file)
        print '   Please save the Excel file you wish to use to update SDW to the above path/name.'
        quit()

    # Get DateTime to append to the imported Excel table
    dt_to_append = Get_DT_To_Append()

    # Import Excel to FGDB Table
    imported_table = os.path.join(wkg_FGDB, sheet_to_import + '_' + dt_to_append)
    Excel_To_Table(excel_file, imported_table, sheet_to_import)

    # Validate the imported table data (make sure it has the correct fields)
    # Get a boolean (True/False) if valid:  valid_table
    # Get list of the project id's that were in SDW, but not in import table:  ids_not_in_imprt_tbl
    # Get list of the project id's that were in import table, but not in SDW:  ids_not_in_sdw
    # Get list of the project id's that had a NAME value in the import table that does not match the SDW value:  ids_w_NAME_not_match
    # Get list of the project names that are in SDW:  NAME_in_SDW
    # Get list of the project names that are in the imported table:  NAME_in_imprt_tbl
    valid_table, ids_not_in_imprt_tbl, ids_not_in_sdw, ids_w_NAME_not_match, NAME_in_SDW, NAME_in_imprt_tbl = Validate_Table(sdw_field_ls, imported_table, sdw_cip_fc_path)

    if valid_table == True:
        # If import table was valid, Process the imported_table
        Process_Table(imported_table, type_dict)

        #-----------------------------------------------------------------------
        #        Update fields from imported table to SDW Feature Class
        print '\n--------------------------------------------------------------'
        print 'Update CIP_5YEAR_POLY\n'
        Update_Fields(sdw_cip_fc_path, join_field, imported_table, sdw_field_ls)

        #-----------------------------------------------------------------------
        #         Update fields from imported_table to SDW Budget Table

        # Get a list of fields from the imported_table that need to be updated
        fields_to_analyze = arcpy.ListFields(imported_table)  # List of all fields in the imported table
        fields_to_update = []  # Container for fields that should be updated
        for field in fields_to_analyze:
            fld_name = field.name
            if fld_name.startswith('FY'):  # All budget fields to update start with 'FY'
                fields_to_update.append(fld_name)
                ##print 'Will update: "{}"'.format(fld_name)  # Only needed for testing
            else:
                pass

        print '\n--------------------------------------------------------------'
        print 'Update CIP_5YR_BUDGET_LUT\n'
        Update_Fields(sdw_cip_budget_tbl_path, join_field, imported_table, fields_to_update)

        #-----------------------------------------------------------------------
        #               Append dt_to_append to the end of excel_file
        new_name = os.path.dirname(excel_file) + '\\' + (os.path.basename(excel_file.split('.')[0])) + '_' + dt_to_append + '.xlsx'
        print '\n--------------------------------------------------------------'
        print 'Renaming: {}\n      To: {}'.format(excel_file, new_name)
        os.rename(excel_file, new_name)

    #---------------------------------------------------------------------------
    #---------------------------------------------------------------------------
    #                          End of script reporting

    print '--------------------------------------------------------------------'
    print '                    End of script reporting\n'

    # Let user know that they need to review the data and update the LUEG_UPDATES table
    # in order for Blue SDE can be updated
    if valid_table == True:
        print '***Updated the data in BLUE SDW, but you are NOT DONE YET! To continue process please:***'
        print '  TO UPDATE AGOL Feature Service:'
        print '    1) Review the updated Feature Class at: {}'.format(sdw_cip_fc_path)
        print '    1) Double click on script CIP_5YEAR_POLY_SDW_to_AGOL.py to update.'
        print '    2) Confirm that the script updated the feature service on AGOL.'
        print '    3) If errors, first confirm that SDW_to_AGOL_settings.ini has correct settings.\n'
        print '  TO UPDATE BLUE SDE:'
        print '    1) Review the updated Feature Class at: {}'.format(sdw_cip_fc_path)
        print '    2) Review the updated Table at:         {}'.format(sdw_cip_budget_tbl_path)
        print '    2) Then, update the date for: CIP_5YEAR_POLY, and CIP_5YR_PLAN_BUDGET_LUT, in the SDW.PDS.LUEG_UPDATES table.'
        print '    3) In a few days, check to confirm that the changes from BLUE SDE have replicated to County SDEP.\n'

    # If there were any projects in SDW, but not in import table warn user
    if (len(ids_not_in_imprt_tbl) != 0):
        print '*** WARNING!  The below PROJECT_ID(s) is/are in the SDW FC, but not in the import table: ***'
        for proj in ids_not_in_imprt_tbl:
            print '  {}'.format(proj)
        print '  Any project in SDW should have a project in the import table.  Please inform CIP that their "Excel sheet may be missing these projects,'
        print '  and that these project still exist in their database, but they will not be updated if they are not in the Excel sheet."\n'

    # If there were any projects in import table, but not SDW warn user
    if (len(ids_not_in_sdw) != 0):
        print '*** WARNING! The below PROJECT_ID(s) is/are in the import table, but NOT in the SDW FC: ***'
        for proj in ids_not_in_sdw:
            print '  {}'.format(proj)
        print '  This means there is no feature in SDW to update attributes.  Contact CIP for project footprint.'
        print '  Please create a polygon in SDW with the above project number and run this script again to update the new project with the Excel\'s attributes.\n'

    # If there were any projects with mismatched NAMEs, warn user that those projects' attributes were not updated by the script
    if (len(ids_w_NAME_not_match) != 0):
        count = 0
        print '*** WARNING! The below PROJECT_ID(s) have mismacthing NAMEs: ***'
        for proj in ids_w_NAME_not_match:
            print '  PROJECT_ID: "{}" has a value in SDW of: "{}" and a value in the imported table of: "{}"'.format(proj, NAME_in_SDW[count], NAME_in_imprt_tbl[count])
            count += 1

        print '\n  The above projects did not have their attributes updated in SDW by the imported table because of an error.'
        print '  This error happens when a project NAME has been changed in the Excel sheet.'
        print '  Please find out if:'
        print '    A) The NAME was legitemately and intentionally changed by CIP for the specific project, then:'
        print '      1) You should make the changes in SDW and run this script again.'
        print '    B) If the original project was deleted in the Excel sheet and the PROJECT_ID was reused for a new project, then:'
        print '      1) The attribute information from the deleted project SDW should be entered back into the import table for the correct PROJECT_ID.'
        print '      2) The new project that was in Excel that is reusing the original PROJECT_ID, should be reassigned a new and unused PROJECT_ID.'
        print '      3) Inform CIP that they cannot delete projects from the Excel spreadsheet and that PROJECT_IDs need to remain unique.'

    # If the import table was not valid, have this error the last item in the report
    if valid_table == False:
        print '*** ERROR! The update cannot be completed. ***'
        print '  Validate_Table function has found missing / incorrect info.  Please see above for *** ERROR! *** messages.'
        print '  No features in SDW have been updated.'

    raw_input('Press ENTER to finish.')

#-------------------------------------------------------------------------------
#*******************************************************************************
#-------------------------------------------------------------------------------
#                          Start defining FUNCTIONS
#-------------------------------------------------------------------------------
#*******************************************************************************
#-------------------------------------------------------------------------------
#                         FUNCTION: Get dt_to_append
def Get_DT_To_Append():
    """
    PARAMETERS:
        none

    RETURNS:
        dt_to_append (str): Which is in the format 'YYYY_M_D__H_M_S'

    FUNCTION:
        To get a formatted datetime string that can be used to append to files
        to keep them unique.
    """

    print 'Starting Get_DT_To_Append()...'

    start_time = datetime.datetime.now()

    date = '%s_%s_%s' % (start_time.year, start_time.month, start_time.day)
    time = '%s_%s_%s' % (start_time.hour, start_time.minute, start_time.second)

    dt_to_append = '%s__%s' % (date, time)

    print '  DateTime to append: {}'.format(dt_to_append)

    print 'Finished Get_DT_To_Append()\n'
    return dt_to_append

#-------------------------------------------------------------------------------
#-------------------------------------------------------------------------------
#                       FUNCTION Excel_To_Table()
def Excel_To_Table(input_excel_file, out_table, sheet):
    """
    PARAMETERS:
        input_excel_file (str): The full path to the Excel file to import.

        out_table (str): The full path to the FGDB and NAME of the table in the FGDB.

        sheet (str): The name of the sheet to import.

    RETURNS:
        none

    FUNCTION:
        To import an Excel sheet into a FGDB.
    """

    print 'Starting Excel_To_Table()...'

    print '  Importing Excel sheet: {}\{}\n  To: {}'.format(input_excel_file, sheet, out_table)

    # Perform conversion
    arcpy.ExcelToTable_conversion(input_excel_file, out_table, sheet)

    print 'Finished Excel_To_Table()\n'

#-------------------------------------------------------------------------------
#-------------------------------------------------------------------------------
#                          FUNCTION: Validate_Table()
def Validate_Table(sdw_field_ls, imported_table, sdw_cip_fc_path):
    """
    PARAMETERS:
      sdw_field_ls (list of str): The list of fields that we defined in main()
        that are in SDW FC that we want to update with the imported table.

      imported_table (str): The full path of the imported_table generated from
        Excel_To_Table()

      sdw_cip_fc_path (str): The full path of the SDW CIP Feature Class.

    RETURNS:
      valid_table (Boolean): A Boolean variable that is 'False' if there were ERRORS,
        but is 'True' if there were NO errors or if there were only WARNINGS.
        if valid_table = 'False' we can stop the script in main() so we do not
        copy over bad/incomplete data to SDW.

      proj_ids_not_in_imprt_tbl (list of str): Project ID's that are in SDW, but
        are not found in the import table.

      proj_ids_not_in_sdw (list of str): Project ID's that are in the import table,
        but are not found in SDW.

    FUNCTION:
        To validate the newly imported FGDB table from the Excel table.  This
        function:
          1) Checks for any "Blank Projects" and deletes them.
             Blank projects are not really CIP projects,
             they exist only because there are values embedded in the PROJECT_ID
             field to minimize the amount of editing GIS needs to do on
             CIP's Excel sheet.  For example, project 20000 exists in the PROJECT_ID
             field, but this is a blank project until CIP enteres a project name
             in the NAME field.

          2) Validates that the fields which need to be updated in SDW are found
             in the import table.
             "valid_table = False" if not.

          3.1) Validates that all PROJECT_ID's in SDW are also in the import table,
               warns user of ID's in SDW, but not in import table.
               "valid_table = True" regardless of this validation result.

          3.2) Validates that all PROJECT_ID's in the import table are also in SDW,
               "valid_table = True" regardless of this validation result.

          4) Validates that every project has both a PROJECT_ID and a NAME.
             "valid_table = False" if any project is missing one of these.

          5) Validate that every project NAME in SDW is the same as in the import
             table.
             "valid_table = True" regardless of this validation result.
    """

    print 'Starting Validate_Table()...\n'

    valid_table = True  # Will change to 'False' if we want to stop script

    #---------------------------------------------------------------------------
    #                    1) Delete any blank projects
    # 'Blank projects' have a PROJECT_ID from the Excel table, but they don't
    # have any other attributes.  The Excel sheet has preset PROJECT_ID's for
    # our workflow to reduce the amount of editing needed by GIS in the Excel sheet.
    # Script checks both the NAME and TYPE fields.  If both are blank, then that row
    # is deleted.

    print '  Checking for "Blank Projects"'

    # Get new selection in the imported table and return the layer with the selection
    lyr_w_selection = Select_Object(imported_table, 'NEW_SELECTION', "NAME = '' and TYPE = '' ")

    # Get the count of the number of selected records
    count = Get_Count_Selected(lyr_w_selection)

    print '    There are {} blank projects to delete'.format(count)

    # Only delete the rows if there is at least one selected feature
    if count != 0:
        print '    Deleting...'
        arcpy.DeleteRows_management(lyr_w_selection)

    print '  Done checking for "Blank Projects"\n'

    #---------------------------------------------------------------------------
    #       2) Validate that the fields we need in SDW are in the import table
    print '  ------------------------------------------------------------------'
    print '  Validating the field names in import table:'

    # Get a list of the names of the fields in the imported table
    imported_fields = arcpy.ListFields(imported_table)
    imported_field_names = []
    for field in imported_fields:
        imported_field_names.append(field.name)

    # list to contain any fields in sdw_field_ls that is not in the imported table
    fields_not_in_imprt_tbl = []

    # For each SDW field in the sdw_field_ls, pass if the imported table has the same named field
    for sdw_field in sdw_field_ls:
        if sdw_field in imported_field_names:
            pass

    # If there is a field in our sdw_field_ls that is NOT in the imported table,
    # Stop the function and return 'valid_table = False' so we do not copy incomplete data
        else:
            fields_not_in_imprt_tbl.append(sdw_field)

    # If there were any fields in sdw_field_ls, but not in import table
    if (len(fields_not_in_imprt_tbl) != 0):
        print '*** ERROR! The below FIELD(s) is/are NOT in the imported table. ***'
        for field in fields_not_in_imprt_tbl:
            print '        "{}"'.format(field)
        print '      Please see why these fields are not in the import table.'
        print '      valid_table = False'
        valid_table = False

    print '  Done validating the field names in import table\n'

    #---------------------------------------------------------------------------
    #---------------------------------------------------------------------------
    #            3)Validate that PROJECT_ID's exist in both datasets

    # Get list of PROJECT_ID's in SDW FC
    sdw_project_ids = []
    with arcpy.da.SearchCursor(sdw_cip_fc_path, ['PROJECT_ID']) as cursor:
        for row in cursor:
            sdw_project_ids.append(row[0])

    # Get lists of PROJECT_ID's in imported table
    imprt_tbl_project_ids = []
    with arcpy.da.SearchCursor(imported_table, ['PROJECT_ID']) as cursor:
        for row in cursor:
            imprt_tbl_project_ids.append(row[0])

    # Sort the lists
    sdw_project_ids.sort()
    imprt_tbl_project_ids.sort()

    #---------------------------------------------------------------------------
    #      3.1) If a PROJECT_ID exists in SDW that is not in the import table,
    # warn user but do not change valid_table
    print '  ------------------------------------------------------------------'
    print '  Validating PROJECT_ID in SDW is also in import table:'

    # List to contain any PROJECT_ID'S that are in SDW but not in the import table
    proj_ids_not_in_imprt_tbl = []

    for project_id in sdw_project_ids:
        if project_id in imprt_tbl_project_ids:
            # Don't do anything if the SDW project_id is also in the import table
            pass

        # There is a project that is in SDW but not in import table.  This could
        # happen if CIP deleted a project in their Excel file.
        # Add this project_id to list
        else:
            proj_ids_not_in_imprt_tbl.append(project_id)

    print '    There are {} projects that are in SDW, but not in the import table.'.format(len(proj_ids_not_in_imprt_tbl))

    print '  Done validating PROJECT_ID in SDW\n'

    #---------------------------------------------------------------------------
    #        3.2) Make sure that every PROJECT_ID in the import table also
    # exists in SDW warn user but do not change valid_table
    print '  ------------------------------------------------------------------'
    print '  Validating PROJECT_ID in import table is also in SDW:'

    # list to contain any PROJECT_ID's that are in import table, but not in SDW
    proj_ids_not_in_sdw = []

    for project_id in imprt_tbl_project_ids:
        if project_id in sdw_project_ids:
            # Don't do anything if the import table project_id is also in SDW
            pass

        # There is a project that is in the import table but not SDW.  This could happen
        # if CIP added a project, but GIS has not added the project footprint in SDW.
        # Add this project_id to list
        else:
            proj_ids_not_in_sdw.append(project_id)

    print '    There are {} projects that are in the import table, but not in SDW.'.format(len(proj_ids_not_in_sdw))

    print '  Done validating PROJECT_IDs in import table\n'

    #---------------------------------------------------------------------------
    #        4) Make sure that every project has a PROJECT_ID and a NAME
    print '  ------------------------------------------------------------------'
    print '  Validating that every project has a PROJECT_ID and a NAME'

    # Where clause to select only the invalid rows
    num_errors = 0  # Counter of this type of error
    where_clause = "PROJECT_ID IS NULL OR NAME = ''"
    with arcpy.da.SearchCursor(imported_table, ['PROJECT_ID', 'NAME'], where_clause) as cursor:
        for row in cursor:
            print '*** ERROR! The below project is missing PROJECT_ID / NAME (or both), both are needed for a valid table. ***'
            print '    PROJECT_ID: "{}"      NAME: "{}"'.format(row[0], row[1])
            valid_table = False
            num_errors += 1

    print '    There are: {} projects that are missing either a PROJECT_ID or a NAME'.format(num_errors)

    print '  Done Validating PROJECT_ID and NAME\n'

    #---------------------------------------------------------------------------
    #         5) Validate that every project NAME in SDW is the same as in
    #            the import table
    print '  ------------------------------------------------------------------'
    print '  Validating that every project NAME in SDW matches the project NAME in the imported table'

    # Join the SDW FC and the imported table on PROJECT_ID to compare the NAME fields
    sdw_cip_join_imprt_tbl = Join_2_Objects(sdw_cip_fc_path, 'PROJECT_ID',
                                               imported_table, 'PROJECT_ID', 'KEEP_COMMON')

    # Get the basename of the imported table, i.e. "CIP_5YEAR_POLY_2017_5_15__9_38_50"
    # Will be used in 'where_clause' below
    import_table_name = os.path.basename(imported_table)

    # Get the basename of the sdw_cip_fc_path i.e. 'CIP_5YEAR_POLY'
    # Will be used in the 'where_clause' and 'SearchCursor' below
    sdw_cip_fc_name = os.path.basename(sdw_cip_fc_path)

    # Lists to hold report info
    ids_w_NAME_not_match = []
    NAME_in_SDW = []
    NAME_in_imprt_tbl = []
    num_errors = 0

    # Create SearchCursor
    where_clause = '{}.NAME <> {}.NAME'.format(sdw_cip_fc_name, import_table_name)

    with arcpy.da.SearchCursor(sdw_cip_join_imprt_tbl,
                               ['{}.PROJECT_ID'.format(sdw_cip_fc_name), '{}.NAME'.format(sdw_cip_fc_name), '{}.NAME'.format(import_table_name)],
                               where_clause) as cursor:
        for row in cursor:
            # Append row value to lists
            ids_w_NAME_not_match.append(row[0])
            NAME_in_SDW.append(row[1])
            NAME_in_imprt_tbl.append(row[2])

            # Increment error counter
            num_errors += 1

    print '    There are: {} projects that have mismatching values in the NAME field'.format(num_errors)

    # If there were projects with mismatching NAME values, change the PROJECT_ID
    # value in the imported table to change_value so that it will not be joined
    # in Update_Fields() and will not overwrite any SDW attributes
    if num_errors != 0:
        change_value = -99
        print '    Changing these {} PROJECT_IDs in imported table with mismatching values to: {}'.format(num_errors, change_value)

        # Create UpdateCursor for imported table
        with arcpy.da.UpdateCursor(imported_table, ['PROJECT_ID']) as cursor:
            for row in cursor:
                if row[0] in ids_w_NAME_not_match:
                    row[0] = change_value
                    cursor.updateRow(row)

    # Delete the layer/view between the SDW FC and the imported table so there
    #   is no 'holdover' when creating the next joined layer/view
    print '\n  Deleting layer/view with the join'
    arcpy.Delete_management(sdw_cip_join_imprt_tbl)

    print '  Done Validating project NAME matches SDW and imported table\n'
    #---------------------------------------------------------------------------
    print '  ------------------------------------------------------------------'
    print '  valid_table = {}\n'.format(valid_table)
    print 'Finished Validating Table\n'

    return valid_table, proj_ids_not_in_imprt_tbl, proj_ids_not_in_sdw, ids_w_NAME_not_match, NAME_in_SDW, NAME_in_imprt_tbl

#-------------------------------------------------------------------------------
#-------------------------------------------------------------------------------
#                         FUNCTION: Process_Table()

def Process_Table(imported_table, type_dict):
    """
    PARAMETERS:
      imported_table (str): The full path of the imported_table generated from
        Excel_To_Table()

      type_dict (dictionary): The dictionary defined in main() that has the
        string and code values of all the types in the domain CIP_TYPE.

    RETURNS:
      none

    FUNCTION:
      To process any data in the imported_table before joining to the SDW FC.
      This function:
        1) Makes sure that all values in [NAME] are all uppercase.
        2) Changes the string values in the Excel sheet in [TYPE] to the
           corresponding numeric values that are used in the actual SDW FC.
    """

    print 'Starting Process_Table()...'
    print '  Processing "{}"\n'.format(imported_table)

    #---------------------------------------------------------------------------
    # 1)  Calculate field [NAME] to have all upper case letters for consistency
    field_to_calc = 'NAME'
    expression    = '!NAME!.upper()'

    print '  Calculating field: "{}" to equal: "{}"'.format(field_to_calc, expression)
    arcpy.CalculateField_management(imported_table, field_to_calc, expression, 'PYTHON_9.3')

    #---------------------------------------------------------------------------
    # 2) Calculate the values in [TYPE] to equal the values in the domain CIP_TYPE
    # not the string values found in the Excel table
    print '\n  Calculating [TYPE] based off of CIP_TYPE domain:'
    for typ in type_dict:

        where_clause = "TYPE = '{}'".format(typ)
        # Perform a selection based on the where_clause
        lyr_w_selection = Select_Object(imported_table, 'NEW_SELECTION', where_clause)

        # Get the count of the number of selected rows
        count_selected = Get_Count_Selected(lyr_w_selection)

        # If there were selected rows, calculate those rows based on the dictionary value
        if count_selected != 0:
            domain_value = type_dict[typ]
            print '    Calculating field: "TYPE" to equal: {}\n'.format(domain_value)
            arcpy.CalculateField_management(lyr_w_selection, 'TYPE', domain_value)

        else:
            print '*** WARNING, no records selected.  Field not calculated. ***'

    print 'Finished Processing Table\n'


#-------------------------------------------------------------------------------
#-------------------------------------------------------------------------------
#                         FUNCTION: Update_Fields()

def Update_Fields(target_obj, join_field, obj_to_join, fields_to_update):
    """
    PARAMETERS:
      target_obj (str): The full path of the SDW CIP Feature Class.

      join_field (str): The name of the field used to join two objects.

      obj_to_join (str): The full path of the obj_to_join generated from
        Excel_To_Table()

      fields_to_update (list): List of the fields that will be updated.

    RETURNS:
      none

    FUNCTION:
      To calculate the fields in 'fields_to_update' list from the obj_to_join
      to the target_obj

    NOTE:
      This Function needs access to Join_2_Objects() function in order to work.
    """

    print 'Starting Update_Fields()...'

    joined_obj = Join_2_Objects(target_obj, join_field, obj_to_join, join_field, 'KEEP_COMMON')

    # Get the basename of the imported table, i.e. "CIP_5YEAR_POLY_2017_5_15__9_38_50"
    # Will be used in 'expression' below
    obj_to_join_name = os.path.basename(obj_to_join)

    # Get the basename of the target_obj i.e. 'CIP_5YEAR_POLY'
    # Will be used in the 'where_clause' and 'SearchCursor' below
    target_obj_name = os.path.basename(target_obj)

    for field in fields_to_update:

        field_to_calc = '{}.{}'.format(target_obj_name, field)
        expression    = '!{}.{}!'.format(obj_to_join_name, field)

        print '  In joined_fc, calculating field: "{}", to equal: "{}"'.format(field_to_calc, expression)
        arcpy.CalculateField_management(joined_obj, field_to_calc, expression, 'PYTHON_9.3')

    # Delete the layer/view between the SDW FC and the imported table so there
    #   is no 'holdover' when creating the next joined layer/view
    print '\n  Deleting layer/view with the join'
    arcpy.Delete_management(joined_obj)

    print 'Finished Updating Fields\n'

#-------------------------------------------------------------------------------
#-------------------------------------------------------------------------------
#                          FUNCTION Join 2 Objects

def Join_2_Objects(target_obj, target_join_field, to_join_obj, to_join_field, join_type):
    """
    PARAMETERS:
      target_obj (str): The full path to the FC or Table that you want to have
        another object join to.

      target_join_field (str): The field name in the target_obj to be used as the
        primary key.

      to_join_obj (str): The full path to the FC or Table that you want to join
        to the target_obj.

      to_join_field (str): The field name in the to_join_obj to be used as the
        foreign key.

      join_type (str): Specifies what will be done with records in the input
        that match a record in the join table. Valid values:
          KEEP_ALL
          KEEP_COMMON

    RETURNS:
      target_obj (lyr): Return the layer/view of the joined object so that
        it can be processed.

    FUNCTION:
      To join two different objects via a primary key field and a foreign key
      field by:
        1) Creating a layer or table view for each object ('target_obj', 'to_join_obj')
        2) Joining the layer(s) / view(s) via the 'target_join_field' and the
           'to_join_field'

    NOTE:
      This function returns a layer/view of the joined object, remember to delete
      the joined object (arcpy.Delete_management(target_obj)) if performing
      multiple joins in one script.
    """

    print '\n    Starting Join_2_Objects()...'

    # Create the layer or view for the target_obj using try/except
    try:
        arcpy.MakeFeatureLayer_management(target_obj, 'target_obj')
        print '      Made FEATURE LAYER for: {}'.format(target_obj)
    except:
        arcpy.MakeTableView_management(target_obj, 'target_obj')
        print '      Made TABLE VIEW for: {}'.format(target_obj)

    # Create the layer or view for the to_join_obj using try/except
    try:
        arcpy.MakeFeatureLayer_management(to_join_obj, 'to_join_obj')
        print '      Made FEATURE LAYER for: {}'.format(to_join_obj)
    except:
        arcpy.MakeTableView_management(to_join_obj, 'to_join_obj')
        print '      Made TABLE VIEW for: {}'.format(to_join_obj)

    # Join the layers
    print '      Joining "{}"\n         With "{}"\n           On "{}"\n         Type "{}"\n'.format(target_obj, to_join_obj, to_join_field, join_type)
    arcpy.AddJoin_management('target_obj', target_join_field, 'to_join_obj', to_join_field, join_type)

    # Print the fields (only really needed during testing)
    ##fields = arcpy.ListFields('target_obj')
    ##print '  Fields in joined layer:'
    ##for field in fields:
    ##    print '    ' + field.name

    print '    Finished Join_2_Objects()\n'

    # Return the layer/view of the joined object so it can be processed
    return 'target_obj'

#-------------------------------------------------------------------------------
#-------------------------------------------------------------------------------
#                       FUNCTION Select_Object()
def Select_Object(path_to_obj, selection_type, where_clause):
    """
    PARAMETERS:
      path_to_obj (str): Full path to the object (Feature Layer or Table) that
        is to be selected.

      selection_type (str): Selection type.  Valid values are:
        NEW_SELECTION
        ADD_TO_SELECTION
        REMOVE_FROM_SELECTION
        SUBSET_SELECTION
        SWITCH_SELECTION
        CLEAR_SELECTION

      where_clause (str): The SQL where clause.

    RETURNS:
      'lyr' (lyr): The layer/view with the selection on it.

    FUNCTION:
      To perform a selection on the object.
    """

##    print '    Starting Select_Object()...'

    # Make a feature layer or a table view
    # Use try/except to handle either object type (Feature Layer / Table)
    try:
        arcpy.MakeFeatureLayer_management(path_to_obj, 'lyr')
    except:
        arcpy.MakeTableView_management(path_to_obj, 'lyr')

    # Select layer by Attribute
    print '      Selecting "lyr" with a selection type: {}, where: "{}"'.format(selection_type, where_clause)
    arcpy.SelectLayerByAttribute_management('lyr', selection_type, where_clause)

##    print '    Finished Select_Object()'
    return 'lyr'

#-------------------------------------------------------------------------------
#-------------------------------------------------------------------------------
#                        FUNCTION Get_Count_Selected()
def Get_Count_Selected(lyr):
    """
    PARAMETERS:
      lyr (lyr): The layer that should have a selection on it that we want to test.

    RETURNS:
      count_selected (int): The number of selected records in the lyr

    FUNCTION:
      To get the count of the number of selected records in the lyr.
    """

##    print '    Starting Get_Count()...'

    # See if there are any selected records
    desc = arcpy.Describe(lyr)

    if desc.fidSet: # True if there are selected records
        result = arcpy.GetCount_management(lyr)
        count_selected = int(result.getOutput(0))

    # If there weren't any selected records
    else:
        count_selected = 0

    print '      Count of Selected: {}'.format(str(count_selected))

##    print '    Finished Get_Count()'

    return count_selected

#-------------------------------------------------------------------------------
#-------------------------------------------------------------------------------
if __name__ == '__main__':
    main()
