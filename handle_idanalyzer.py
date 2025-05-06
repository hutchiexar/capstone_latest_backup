"""
Utility script to handle idanalyzer import errors.

This module provides fallback mechanisms when idanalyzer is not properly installed.
"""

import logging
import json
from typing import Dict, Any

logger = logging.getLogger(__name__)

def try_import_idanalyzer():
    """
    Try to import idanalyzer module, return False if not installed.
    """
    try:
        import idanalyzer
        return True
    except (ImportError, ModuleNotFoundError):
        logger.warning("idanalyzer module not available. ID analysis functionality disabled.")
        return False
    except Exception as e:
        logger.error(f"Error importing idanalyzer: {str(e)}")
        return False

def create_dummy_coreapi():
    """
    Create a dummy CoreAPI class that logs warnings instead of raising errors.
    """
    class DummyCoreAPI:
        """Dummy implementation of idanalyzer's CoreAPI class."""
        
        def __init__(self, *args, **kwargs):
            logger.warning("Using dummy idanalyzer CoreAPI. ID analysis functionality is disabled.")
            self.api_key = kwargs.get('api_key', 'dummy-key')
            self.region = kwargs.get('region', 'us')
            
        def scan(self, document_primary=None, **kwargs):
            """Dummy scan method that returns a mock response."""
            logger.info("Dummy ID scan requested - returning mock data")
            mock_response = {
                "success": False,
                "error": {
                    "code": "IDANALYZER_NOT_AVAILABLE",
                    "message": "ID Analyzer module is not available. This is a dummy implementation."
                },
                "result": {
                    "authenticate": False,
                    "documentNumber": "DUMMY-ID-NUMBER",
                    "firstName": "FIRST",
                    "middleName": "",
                    "lastName": "LAST",
                    "fullName": "FIRST LAST",
                    "gender": "Unknown",
                    "birthDate": "1990-01-01",
                    "issuedDate": "2020-01-01",
                    "expiryDate": "2030-01-01",
                    "country": "Unknown",
                    "nationality": "Unknown",
                    "documentType": "Unknown",
                    "documentSide": "front",
                    "idType": "other",
                    "age": 33
                }
            }
            return mock_response
            
        def setFaceThreshold(self, threshold):
            """Dummy method."""
            pass
            
        def enableAuthentication(self, enable=True):
            """Dummy method."""
            pass
            
        def enableImageOutput(self, enable=True):
            """Dummy method."""
            pass
    
    return DummyCoreAPI

def get_core_api():
    """
    Get a CoreAPI implementation, either real idanalyzer or a dummy.
    """
    if try_import_idanalyzer():
        try:
            # Import the real implementation
            from idanalyzer import CoreAPI
            return CoreAPI
        except Exception as e:
            logger.error(f"Error importing CoreAPI: {str(e)}")
            return create_dummy_coreapi()
    else:
        return create_dummy_coreapi()

# Example of how to use this in application code:
#
# from handle_idanalyzer import get_core_api
#
# CoreAPI = get_core_api()
# analyzer = CoreAPI(api_key="your-api-key")
# result = analyzer.scan(document_primary="path/to/document.jpg")
# # Will use real analyzer if available, dummy otherwise 