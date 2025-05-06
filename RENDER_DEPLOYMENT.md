# Deploying Traffic Violation System to Render

This project is configured for easy deployment to Render using Blueprint deployment.

## Quick Deployment Steps

1. Ensure your code is pushed to GitHub
2. Log in to your Render dashboard
3. Click "New" → "Blueprint"
4. Select your GitHub repository
5. Render will automatically set up your web service and PostgreSQL database
6. Add your environment variables in the web service settings

## Important Updates

### Python Version
We've updated the Python version in `render.yaml` from 3.9.0 to 3.10.0 to ensure compatibility with packages like `contourpy` and other dependencies.

### Dependency Conflicts Fixed
We've addressed multiple dependency conflicts:

1. **contourpy/matplotlib compatibility**: Updated Python version to 3.10.0
2. **pyparsing conflicts**: Created a simplified `requirements-fixed.txt` with compatible versions
3. **pyHanko/pyhanko-certvalidator conflicts**: Corrected versions to ensure compatibility (pyhanko-certvalidator==0.20.0 must be installed before pyHanko==0.17.0)
4. **Missing django-sslserver**: Added django-sslserver to all fallback mechanisms to prevent import errors
5. **idanalyzer import errors**: Created handler to provide graceful degradation for ID analysis functionality
6. **Fallback mechanism**: Created `requirements-minimal.txt` with essential packages
7. **Enhanced build.sh**: Updated with proper installation order and more robust fallback options

### Graceful Degradation Implemented
1. **handle_pyhanko.py**: Utility that provides fallback for PDF signing functionality
   - Automatically detects if pyHanko is properly installed
   - Provides dummy implementation when unavailable
   - Logs warnings instead of causing application crashes

2. **handle_idanalyzer.py**: Utility that provides fallback for ID analysis functionality
   - Provides mock implementation when idanalyzer can't be imported
   - Returns dummy data for API calls
   - Prevents app crashes from missing dependency

3. **Patching mechanism**: During build, critical imports in views.py are patched to use our handlers

These robust changes ensure successful deployment even with dependency issues, allowing the application to run with limited functionality rather than crashing completely.

## Reference Documentation

For detailed instructions, see:
- `render_deployment_guide.md` - Complete step-by-step deployment guide
- `render_env_variables.md` - List of required environment variables
- `render_dependency_guide.md` - Guidance for handling dependency issues
- `render_dependency_summary.md` - Summary of all dependency issues and solutions

## Files for Render Deployment

- `render.yaml` - Defines services and their configurations
- `build.sh` - Enhanced build script with fallback mechanisms
- `CAPSTONE_PROJECT/postgresql_settings.py` - PostgreSQL-specific settings
- `requirements-fixed.txt` - Fixed dependencies file to resolve conflicts
- `requirements-minimal.txt` - Minimal dependencies for fallback
- `handle_pyhanko.py` - Utility for graceful degradation of PDF signing functionality
- `handle_idanalyzer.py` - Utility for graceful degradation of ID analysis functionality
- `patch_views_idanalyzer.py` - Script to patch problematic imports in views.py

## Post-Deployment

After deployment:
1. Test your application on the provided Render URL
2. Monitor logs for any errors
3. Set up continuous deployment as needed

## Troubleshooting Common Issues

If you encounter build failures, check the following:

1. **Python version compatibility**: Ensure your packages are compatible with Python 3.10.0
2. **Database connection**: Verify PostgreSQL connection settings
3. **Environment variables**: Make sure all required variables are set
4. **Build logs**: Review build logs for specific error messages

For more detailed troubleshooting, refer to `render_dependency_guide.md`.

## Support

If you encounter issues during deployment, refer to the troubleshooting section in the deployment guide or Render's documentation at https://render.com/docs 

# Render Deployment Guide

This guide provides instructions for deploying the Traffic Violation System on Render.com.

## Overview of Deployment Issues and Solutions

The deployment process addresses several dependency and import challenges:

1. **Python Version**: Using Python 3.10.0 on Render (specified in `render.yaml`)
2. **Dependency Conflicts**: Resolved through fallback installation mechanisms
3. **Import Errors**: Addressed through runtime patching and graceful degradation

## Dependency Management Strategy

We've implemented a robust dependency management strategy using multiple requirements files:

- `requirements.txt` - Original dependencies
- `requirements-fixed.txt` - Modified dependencies with version constraints
- `requirements-minimal.txt` - Minimal set of requirements for basic functionality

Our `build.sh` script attempts installation in the following order:
1. Try `requirements-fixed.txt`
2. If that fails, try `requirements.txt`
3. If that fails, try `requirements-minimal.txt`
4. Finally, install critical packages individually

## Import Error Handling

We've implemented a robust approach to handle import errors for dependencies that might fail on certain environments:

### Direct Import Patching

The `direct_import_patch.py` script modifies import statements in the codebase to include try-except blocks with graceful fallbacks:

1. It identifies problematic imports using regex patterns
2. Backs up original files
3. Replaces imports with try-except blocks that include fallback implementations
4. Logs all changes and results

Currently handled problematic modules:
- **idanalyzer**: Provides a dummy `CoreAPI` implementation that returns error responses
- **pyHanko**: Provides graceful fallback for PDF signing functionality

### Example Patched Import:

Original import:
```python
from idanalyzer import CoreAPI
```

Patched import:
```python
# Graceful degradation for idanalyzer import
try:
    from idanalyzer import CoreAPI
except ImportError:
    # Fallback implementation
    class CoreAPI:
        def __init__(self, *args, **kwargs):
            print("WARNING: Using dummy CoreAPI. ID analysis functionality is disabled.")
            # ... dummy implementation ...
```

## Build Process Overview

The build process is managed through `build.sh`, which:

1. Installs dependencies using the fallback strategy
2. Verifies critical packages are installed
3. Applies import patches using `direct_import_patch.py`
4. Runs database migrations
5. Collects static files

## Deployment Instructions

1. **Update render.yaml**: Make sure it specifies Python 3.10.0

   ```yaml
   - name: python
     version: 3.10.0
   ```

2. **Ensure build scripts are present**:
   - `build.sh` (main build script)
   - `direct_import_patch.py` (patching script)

3. **Deploy to Render**:
   - Connect your GitHub repository to Render
   - Render will automatically detect the `render.yaml` configuration
   - Select the appropriate branch and click "Deploy"

4. **Monitor logs**:
   - Watch for any dependency installation errors
   - Check for successful application of patches
   - Verify database migrations ran successfully

## Troubleshooting

### Common Issues

#### 1. Module Not Found Errors

If you encounter "Module not found" errors despite our patching:
- Check if the module is in `PATCH_RULES` in `direct_import_patch.py`
- Add new patterns and fallback implementations as needed
- Verify the build log shows successful patching

#### 2. Database Migration Errors

If database migrations fail:
- Check the database URL configuration
- Verify the database exists and is accessible
- Try running migrations manually:
  ```
  heroku run python manage.py migrate
  ```

#### 3. Static Files Not Loading

If static files aren't loading:
- Verify `STATIC_ROOT` is set correctly in `settings.py`
- Check if `collectstatic` ran successfully in the build log
- Ensure `whitenoise` middleware is configured properly

## Environment Variables Required

Ensure the following environment variables are set in Render:

- `DATABASE_URL`: PostgreSQL connection string
- `SECRET_KEY`: Django secret key for security
- `DEBUG`: Set to "False" for production
- `ALLOWED_HOSTS`: Add your Render domain 