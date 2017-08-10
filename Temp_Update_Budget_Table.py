#-------------------------------------------------------------------------------
# Name:        module1
# Purpose:
#
# Author:      mgrue
#
# Created:     09/08/2017
# Copyright:   (c) mgrue 2017
# Licence:     <your licence>
#-------------------------------------------------------------------------------
import arcpy, os

def main():

    imported_table = r'P:\CIP\DPW-CIP_updates\DEV\Data\wkg_FGDB.gdb\CIP_5YEAR_POLY_2017_8_8__15_30_46'  # TODO: Have the imported_table point to the just imported table when moving into script
    budget_table = r'P:\CIP\DPW-CIP_updates\DEV\Data\wkg_FGDB.gdb\CIP_5YR_PLAN_BUDGET_LUT'  # TODO: Point this var to the table in SDW

    budget_flds_to_ignore = ['OBJECTID', 'PROJECT_ID']

    #---------------------------------------------------------------------------
    # Get the names of the tables
    import_table_name = os.path.basename(imported_table)
    print 'Name of imported table: "{}"'.format(imported_table_name)

    sdw_cip_budget_name = os.path.basename(budget_table)
    print 'Name of budget table: "{}"\n'.format(budget_table_nm)

    #---------------------------------------------------------------------------
    # Get a list of fields from the budget_table that need to be updated
    fields_to_analyze = arcpy.ListFields(budget_table)  # List of all fields in budget_table
    fields_to_update = []  # Container for fields that should be updated
    for field in fields_to_analyze:

        if field.name not in budget_flds_to_ignore:
            print 'Field "{}" will be updated'.format(field.name)
            fields_to_update.append(field.name)
        else:
            print 'Ignoring field "{}"'.format(field.name)

##    print 'Update Fields'
##    print ', '.join(fields_to_update)
    #---------------------------------------------------------------------------
    joined_budget_table = Join_2_Objects(budget_table, 'PROJECT_ID', imported_table, 'PROJECT_ID', 'KEEP_COMMON')

    #---------------------------------------------------------------------------
    for field in fields_to_update:
        field_to_calc = '{}.{}'.format(sdw_cip_budget_name, field)
        expression    = '!{}.{}!'.format(import_table_name, field)

        print '  In joined budget table, calculating field "{}", to equal "{}"'.format(field_to_calc, expression)
        arcpy.CalculateField_management(joined_budget_table, field_to_calc, expression, 'PYTHON_9.3')






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
    """

    print '    Starting Join_2_Objects()...'

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
    print '      Joining layers'
    arcpy.AddJoin_management('target_obj', target_join_field, 'to_join_obj', to_join_field, join_type)

    # Print the fields (only really needed during testing)
    fields = arcpy.ListFields('target_obj')
    print '  Fields in joined layer:'
    for field in fields:
        print '    ' + field.name

    print '    Finished Join_2_Objects()'

    # Return the layer/view of the joined object so it can be processed
    return 'target_obj'



if __name__ == '__main__':
    main()
