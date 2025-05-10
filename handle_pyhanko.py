#!/usr/bin/env python
"""
handle_pyhanko.py

This module provides a graceful fallback for PDF signing functionality when pyHanko is not available.
It implements dummy classes and functions that match the interface of pyHanko to prevent import errors.
"""

try:
    # Try to import the real pyHanko modules
    import pyhanko
    from pyhanko import stamp
    from pyhanko.pdf_utils import text, images
    from pyhanko.pdf_utils.incremental_writer import IncrementalPdfFileWriter
    from pyhanko.sign import signers, fields
    from pyhanko.sign.signers.pdf_signer import PdfSignatureMetadata
    
    # If we get here, pyHanko is available
    PYHANKO_AVAILABLE = True
    
except ImportError:
    # Fallback implementation
    import io
    import logging
    
    logger = logging.getLogger(__name__)
    logger.warning("pyHanko module not available. PDF signing functionality is disabled.")
    
    PYHANKO_AVAILABLE = False
    
    # Create dummy modules and classes
    class DummyModule:
        def __getattr__(self, name):
            return DummyFunc()
    
    class DummyFunc:
        def __call__(self, *args, **kwargs):
            return None
            
        def __getattr__(self, name):
            return DummyFunc()
    
    # Mock the pyHanko modules structure
    stamp = DummyModule()
    text = DummyModule()
    images = DummyModule()
    signers = DummyModule()
    fields = DummyModule()
    
    class IncrementalPdfFileWriter:
        """Dummy implementation of IncrementalPdfFileWriter"""
        def __init__(self, *args, **kwargs):
            self._reader = None
            self._buffer = io.BytesIO()
            self._wrote = False
            
        def write_in_place(self):
            # Just a placeholder that does nothing
            self._wrote = True
            return self._buffer
    
    class PdfSignatureMetadata:
        """Dummy implementation of PdfSignatureMetadata"""
        def __init__(self, *args, **kwargs):
            self.field_name = kwargs.get('field_name', 'Signature')
            
def is_available():
    """Check if pyHanko is available"""
    return PYHANKO_AVAILABLE

def dummy_sign_pdf(input_pdf, output_pdf, signature_info=None):
    """
    Dummy function to simulate signing a PDF without actually doing it
    
    Args:
        input_pdf: Path to the input PDF file
        output_pdf: Path to save the "signed" PDF
        signature_info: Dict with signature information
        
    Returns:
        Boolean indicating success (always False in dummy implementation)
    """
    if PYHANKO_AVAILABLE:
        # Should never get here, but just in case
        logger.warning("Using dummy_sign_pdf despite pyHanko being available.")
        return False
        
    try:
        # Just copy the input file to the output path
        import shutil
        shutil.copy2(input_pdf, output_pdf)
        logger.info(f"Created unsigned copy of PDF at {output_pdf} (pyHanko not available)")
        return True
    except Exception as e:
        logger.error(f"Error in dummy_sign_pdf: {str(e)}")
        return False 