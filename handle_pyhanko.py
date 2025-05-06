"""
Utility script to handle pyHanko import errors.

This module provides fallback mechanisms when pyHanko is not properly installed
or has dependency conflicts.
"""

import importlib
import logging

logger = logging.getLogger(__name__)

def try_import_pyhanko():
    """
    Try to import pyHanko modules, return False if not installed or incompatible.
    """
    try:
        import pyhanko
        import pyhanko_certvalidator
        return True
    except (ImportError, ModuleNotFoundError):
        logger.warning("pyHanko or pyhanko-certvalidator not available. PDF signing disabled.")
        return False
    except Exception as e:
        logger.error(f"Error importing pyHanko: {str(e)}")
        return False

def create_dummy_pdf_signer():
    """
    Create a dummy PDF signing class that logs warnings instead of raising errors.
    """
    class DummyPDFSigner:
        """Dummy implementation that simply returns the original document."""
        
        def __init__(self, *args, **kwargs):
            logger.warning("Using dummy PDF signer. No documents will be signed.")
            
        def sign(self, pdf_data, *args, **kwargs):
            logger.info("Dummy signing - returning original document")
            return pdf_data
            
        def verify(self, pdf_data, *args, **kwargs):
            logger.info("Dummy verification - returning True")
            return True
    
    return DummyPDFSigner

def get_pdf_signer():
    """
    Get a PDF signer implementation, either real pyHanko or a dummy.
    """
    if try_import_pyhanko():
        try:
            # Import the real implementation
            from pyhanko.sign import signers
            return signers.PdfSigner
        except Exception as e:
            logger.error(f"Error importing PdfSigner: {str(e)}")
            return create_dummy_pdf_signer()
    else:
        return create_dummy_pdf_signer()

# Example of how to use this in application code:
#
# from handle_pyhanko import get_pdf_signer
#
# PdfSigner = get_pdf_signer()
# signer = PdfSigner(...)  # Will use real signer if available, dummy otherwise 