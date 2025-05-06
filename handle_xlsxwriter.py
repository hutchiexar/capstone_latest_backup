"""
Utility script to handle xlsxwriter import errors.

This module provides fallback mechanisms when xlsxwriter is not properly installed.
"""

import logging
import io
import csv
from typing import Dict, Any, List, Optional

logger = logging.getLogger(__name__)

def try_import_xlsxwriter():
    """
    Try to import xlsxwriter module, return True if successful.
    """
    try:
        import xlsxwriter
        return True
    except (ImportError, ModuleNotFoundError):
        logger.warning("xlsxwriter module not available. Excel export functionality disabled.")
        return False
    except Exception as e:
        logger.error(f"Error importing xlsxwriter: {str(e)}")
        return False

class DummyWorkbook:
    """
    Fallback implementation for xlsxwriter.Workbook that generates CSV instead.
    
    This provides a minimally compatible interface that logs warnings
    and creates a CSV file instead of Excel.
    """
    
    def __init__(self, filename=None, options=None):
        self.filename = filename or 'output.csv'
        self.sheets = {}
        self.active_sheet = None
        self.csv_data = {}
        logger.warning(f"Using dummy xlsxwriter Workbook. Excel export disabled - will create CSV instead.")
        
    def add_worksheet(self, name=None):
        """Create a worksheet object that writes to CSV data."""
        sheet_name = name or f"Sheet{len(self.sheets) + 1}"
        sheet = DummyWorksheet(sheet_name, self)
        self.sheets[sheet_name] = sheet
        if not self.active_sheet:
            self.active_sheet = sheet
        return sheet
    
    def close(self):
        """
        'Close' the workbook by writing all CSV data to files.
        """
        for name, sheet in self.sheets.items():
            # For the primary output, use the main filename
            if sheet == self.active_sheet:
                output_filename = self.filename.replace('.xlsx', '.csv')
            else:
                # For additional sheets, add sheet name to filename
                base = self.filename.replace('.xlsx', '')
                output_filename = f"{base}_{name}.csv"
                
            try:
                with open(output_filename, 'w', newline='') as f:
                    writer = csv.writer(f)
                    for row in sheet.data:
                        writer.writerow(row)
                logger.info(f"Wrote CSV data to {output_filename}")
            except Exception as e:
                logger.error(f"Error writing CSV data: {str(e)}")


class DummyWorksheet:
    """
    Dummy implementation of xlsxwriter Worksheet.
    """
    
    def __init__(self, name, workbook):
        self.name = name
        self.workbook = workbook
        self.data = []
        self.current_row = 0
        
    def write_row(self, row, col, data, cell_format=None):
        """Write a row of data."""
        # Ensure we have enough rows
        while len(self.data) <= row:
            self.data.append([])
            
        # Convert data to list if it's not already
        if not isinstance(data, list):
            data = [data]
            
        # Write each data item to the appropriate column
        for i, item in enumerate(data):
            col_idx = col + i
            # Ensure we have enough columns
            current_row = self.data[row]
            while len(current_row) <= col_idx:
                current_row.append('')
            current_row[col_idx] = item
            
        return True
        
    def write(self, row, col, data, cell_format=None):
        """Write data to a cell."""
        # Ensure we have enough rows
        while len(self.data) <= row:
            self.data.append([])
            
        # Ensure we have enough columns in this row
        current_row = self.data[row]
        while len(current_row) <= col:
            current_row.append('')
            
        # Write the data
        current_row[col] = data
        return True
    
    def set_column(self, first_col, last_col, width=None, cell_format=None, options=None):
        """Dummy implementation of set_column - does nothing."""
        pass
        
    def merge_range(self, first_row, first_col, last_row, last_col, data, cell_format=None):
        """Dummy implementation of merge_range - just writes to the first cell."""
        return self.write(first_row, first_col, data, cell_format)


def get_workbook_class():
    """
    Get a Workbook implementation, either real xlsxwriter or dummy fallback.
    """
    if try_import_xlsxwriter():
        try:
            import xlsxwriter
            return xlsxwriter.Workbook
        except Exception as e:
            logger.error(f"Error importing Workbook class: {str(e)}")
            return DummyWorkbook
    else:
        return DummyWorkbook

# Example usage in application code:
#
# from handle_xlsxwriter import get_workbook_class
#
# Workbook = get_workbook_class()
# workbook = Workbook('output.xlsx')
# worksheet = workbook.add_worksheet()
# # ... use worksheet as normal ...
# workbook.close() 