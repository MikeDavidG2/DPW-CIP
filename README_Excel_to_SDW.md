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