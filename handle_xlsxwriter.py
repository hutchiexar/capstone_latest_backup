#!/usr/bin/env python
"""
handle_xlsxwriter.py

This module provides a graceful fallback for Excel export functionality when xlsxwriter is not available.
It implements classes that match the interface of xlsxwriter but use CSV as a fallback.
"""

import logging
import os

logger = logging.getLogger(__name__)

try:
    # Try to import the real xlsxwriter
    import xlsxwriter
    
    # If we get here, xlsxwriter is available
    XLSXWRITER_AVAILABLE = True
    
except ImportError:
    # Fallback implementation using CSV
    import csv
    import io
    
    logger.warning("xlsxwriter module not available. Excel export functionality is limited to CSV.")
    
    XLSXWRITER_AVAILABLE = False
    
    class Workbook:
        """
        Dummy implementation of xlsxwriter.Workbook that outputs CSV files instead
        """
        def __init__(self, filename=None):
            """Initialize a new workbook with the given filename"""
            self.filename = filename
            self.worksheets = []
            self.formats = {}
            self.format_count = 0
            
        def add_worksheet(self, name=None):
            """Add a new worksheet to the workbook"""
            worksheet = Worksheet(name, self)
            self.worksheets.append(worksheet)
            return worksheet
            
        def add_format(self, properties=None):
            """Create a dummy format object (not used in CSV)"""
            format_id = f"format_{self.format_count}"
            self.format_count += 1
            self.formats[format_id] = properties or {}
            return Format(format_id, properties)
            
        def close(self):
            """Close the workbook and write the CSV files"""
            if not self.filename:
                return
                
            # Create CSV files for each worksheet
            for worksheet in self.worksheets:
                # Generate CSV filename (if multiple worksheets)
                if len(self.worksheets) > 1:
                    base, ext = os.path.splitext(self.filename)
                    csv_filename = f"{base}_{worksheet.name}.csv"
                else:
                    base, ext = os.path.splitext(self.filename)
                    csv_filename = f"{base}.csv"
                
                # Write the CSV file
                with open(csv_filename, 'w', newline='', encoding='utf-8') as csvfile:
                    writer = csv.writer(csvfile)
                    
                    # Process each row in the data
                    for row_idx in range(worksheet.max_row):
                        row_data = []
                        
                        # Process each column in the row
                        for col_idx in range(worksheet.max_col):
                            # Get cell value or empty string
                            if row_idx in worksheet.data and col_idx in worksheet.data[row_idx]:
                                row_data.append(worksheet.data[row_idx][col_idx])
                            else:
                                row_data.append('')
                                
                        # Write the row to the CSV file
                        writer.writerow(row_data)
                        
            logger.info(f"CSV export completed successfully (xlsxwriter not available)")
    
    class Worksheet:
        """
        Dummy implementation of xlsxwriter.Worksheet
        """
        def __init__(self, name, workbook):
            """Initialize a new worksheet with the given name"""
            self.name = name or 'Sheet'
            self.workbook = workbook
            self.data = {}  # Dictionary to store cell data: {row: {col: value}}
            self.max_row = 0
            self.max_col = 0
            
        def write(self, row, col, data, cell_format=None):
            """Write data to a cell"""
            # Initialize row dictionary if it doesn't exist
            if row not in self.data:
                self.data[row] = {}
                
            # Store the cell value
            self.data[row][col] = data
            
            # Update max row and column indices
            self.max_row = max(self.max_row, row + 1)
            self.max_col = max(self.max_col, col + 1)
            
        def write_string(self, row, col, data, cell_format=None):
            """Write a string to a cell"""
            self.write(row, col, str(data), cell_format)
            
        def write_number(self, row, col, data, cell_format=None):
            """Write a number to a cell"""
            self.write(row, col, data, cell_format)
            
        def write_formula(self, row, col, formula, cell_format=None, value=None):
            """Write a formula to a cell (in CSV, we just write the value or the formula text)"""
            self.write(row, col, value if value is not None else formula, cell_format)
            
        def write_url(self, row, col, url, cell_format=None, string=None):
            """Write a URL to a cell (in CSV, we just write the URL or the display string)"""
            self.write(row, col, string if string is not None else url, cell_format)
            
        def set_column(self, first_col, last_col, width, cell_format=None, options=None):
            """Set column width (no effect in CSV)"""
            pass
            
        def set_row(self, row, height, cell_format=None, options=None):
            """Set row height (no effect in CSV)"""
            pass
            
        def merge_range(self, first_row, first_col, last_row, last_col, data, cell_format=None):
            """Merge cells (in CSV, we just write the data to the first cell)"""
            self.write(first_row, first_col, data, cell_format)
    
    class Format:
        """
        Dummy implementation of xlsxwriter.Format
        """
        def __init__(self, format_id, properties=None):
            """Initialize a new format with the given properties"""
            self.format_id = format_id
            self.properties = properties or {}
            
        def set_bold(self):
            """Set bold text (no effect in CSV)"""
            self.properties['bold'] = True
            return self
            
        def set_font_color(self, color):
            """Set font color (no effect in CSV)"""
            self.properties['font_color'] = color
            return self
            
        def set_align(self, align):
            """Set text alignment (no effect in CSV)"""
            self.properties['align'] = align
            return self
            
        def set_bg_color(self, color):
            """Set background color (no effect in CSV)"""
            self.properties['bg_color'] = color
            return self
    
    # Replace the xlsxwriter module with our fallback
    class XlsxwriterModule:
        Workbook = Workbook
        
    xlsxwriter = XlsxwriterModule()
    
def is_available():
    """Check if xlsxwriter is available"""
    return XLSXWRITER_AVAILABLE
    
def create_workbook(filename):
    """
    Create a new workbook, using the real xlsxwriter if available,
    otherwise using our CSV fallback
    """
    if not filename:
        return None
        
    if XLSXWRITER_AVAILABLE:
        return xlsxwriter.Workbook(filename)
    else:
        logger.warning(f"Using CSV fallback for Excel export to {filename}")
        return xlsxwriter.Workbook(filename) 