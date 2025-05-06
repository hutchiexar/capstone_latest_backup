# Handling Dependency Issues on Render

This guide provides solutions for common dependency issues you might encounter when deploying to Render.

## Python Version Compatibility

If you encounter errors related to package compatibility with Python versions, you have two options:

### Option 1: Update Python Version (Preferred)

We've updated the Python version in `render.yaml` from 3.9.0 to 3.10.0 to support packages like `contourpy==1.3.1` and `matplotlib==3.10.1` which require Python 3.10+.

```yaml
# In render.yaml
- key: PYTHON_VERSION
  value: "3.10.0"
```

This is generally the best approach as it allows you to use the latest package versions with better features and security updates.

### Option 2: Downgrade Package Versions

Alternatively, you can downgrade packages to versions compatible with Python 3.9.0:

```
# In requirements.txt
contourpy==1.0.7  # Instead of 1.3.1
matplotlib==3.7.2  # Instead of 3.10.1
```

## Resolving Package Dependency Conflicts

### Latest Fix for pyHanko and pyhanko-certvalidator

We discovered that the order and exact versions of pyHanko and pyhanko-certvalidator are crucial:

1. pyHanko 0.17.0 specifically requires pyhanko-certvalidator 0.20.*
2. The certvalidator must be installed BEFORE pyHanko

Our solution:
```
# Install in this specific order
pip install pyhanko-certvalidator==0.20.0
pip install pyHanko==0.17.0
```

Additionally, we've created a graceful degradation mechanism in `handle_pyhanko.py` that:
- Attempts to import pyHanko safely
- Provides a dummy implementation if imports fail
- Logs warnings instead of crashing the application

### Missing Django SSL Server Module

We encountered a `ModuleNotFoundError: No module named 'sslserver'` issue, which happens when Django can't find the django-sslserver package. 

The solution:
1. Ensure django-sslserver is in all requirement files
2. Add it explicitly to fallback installation mechanisms in build.sh:
```
pip install django-sslserver==0.22
```

### Previous Conflicts with pyHanko

We tried multiple combinations to resolve persistent conflicts:
1. First attempt: `pyHanko==0.20.1` and `pyhanko-certvalidator==0.23.0` (conflicted)
2. Second attempt: `pyHanko==0.19.0` and `pyhanko-certvalidator==0.22.0` (conflicted)
3. Third attempt: `pyHanko==0.17.0` and `pyhanko-certvalidator==0.19.5` (version mismatch)
4. Final solution: `pyhanko-certvalidator==0.20.0` and `pyHanko==0.17.0` (working)

### Previous Conflict with pyparsing

We also encountered a conflict with pyparsing and related packages:

```
ERROR: Cannot install -r requirements.txt (line 49), -r requirements.txt (line 59) and pyparsing==3.2.1 because these package versions have conflicting dependencies.
```

To resolve this, we created a simplified `requirements-fixed.txt` file with compatible versions:

1. Downgraded pyparsing to version 3.0.9
2. Adjusted related package versions (matplotlib, fonttools, etc.)
3. Removed unnecessary packages or those causing conflicts

## Multi-layered Solution Architecture

Our final approach implements multiple layers of protection:

### 1. Fixed Requirements File
- Primary installation mechanism with carefully curated compatible versions
- Proper ordering of interdependent packages

### 2. Filtering Mechanism
- If conflicts occur, automatically filter out problematic packages
- Try installation without the conflicting packages

### 3. Minimal Requirements Fallback
- If filtering doesn't work, fall back to minimal core requirements

### 4. Individual Package Installation
- Attempt to install problematic packages individually with error suppression

### 5. Graceful Degradation
- Utility code that handles missing or conflicting packages at runtime
- Dummy implementations for non-critical functionality

## Common Render Deployment Issues

### 1. Package Installation Errors

If Render fails to install packages, check:
- Python version compatibility
- Package version conflicts
- Special system dependencies

### 2. Database Connection Issues

If your app can't connect to the PostgreSQL database:
- Verify the `DATABASE_URL` environment variable is correctly set
- Check if your application is properly configured to use PostgreSQL
- Check if migrations have been applied correctly

### 3. Static and Media Files

If static or media files aren't loading:
- Ensure WhiteNoise is correctly configured
- Verify that `collectstatic` runs successfully during deployment
- Check permissions on media directories

## Checking Build Logs

Regularly check your Render build logs for errors:

1. Go to your Render dashboard
2. Select your web service
3. Click on "Logs" tab
4. Filter for "Build" logs

## Testing Dependencies Locally

Before deploying, you can test compatibility locally:

```bash
# Create a virtual environment with specific Python version
python -m venv venv --python=python3.10

# Activate the environment
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements-fixed.txt
```

## Updating Requirements

When adding new packages, remember to specify versions explicitly to avoid compatibility surprises:

```
# Good
Django==4.2.10
pillow==9.5.0

# Avoid
Django
pillow
```

## Resources

- [Render Python Documentation](https://render.com/docs/python)
- [Render Blueprint Spec](https://render.com/docs/blueprint-spec)
- [Python Dependency Management](https://render.com/docs/python#dependencies) 