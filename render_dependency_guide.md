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

### Ongoing Issues with pyHanko and pyhanko-certvalidator

We've encountered persistent conflicts with pyHanko and pyhanko-certvalidator. After multiple attempts, we've found that these packages are particularly sensitive to version compatibility.

We tried:
1. First attempt: `pyHanko==0.20.1` and `pyhanko-certvalidator==0.23.0` (conflicted)
2. Second attempt: `pyHanko==0.19.0` and `pyhanko-certvalidator==0.22.0` (conflicted)
3. Current attempt: `pyHanko==0.17.0` and `pyhanko-certvalidator==0.19.5`

These packages have a complex dependency tree and often require exact version matches. If the current combination doesn't work, we may need to:
- Further downgrade to even older versions
- Consider removing these packages if they're not critical to your application
- Fork and modify the packages to resolve internal dependency issues

### Previous Conflict with pyparsing

We also encountered a conflict with pyparsing and related packages:

```
ERROR: Cannot install -r requirements.txt (line 49), -r requirements.txt (line 59) and pyparsing==3.2.1 because these package versions have conflicting dependencies.
```

To resolve this, we created a simplified `requirements-fixed.txt` file with compatible versions:

1. Downgraded pyparsing to version 3.0.9
2. Adjusted related package versions (matplotlib, fonttools, etc.)
3. Removed unnecessary packages or those causing conflicts

### How to Use the Fixed Requirements File

Replace your current requirements.txt with the simplified version:

```bash
# Backup your current requirements file
cp requirements.txt requirements.txt.backup

# Replace with the simplified version
cp requirements-fixed.txt requirements.txt

# Or update render.yaml to use the fixed file
# Change buildCommand to:
# buildCommand: chmod +x build.sh && REQUIREMENTS_FILE=requirements-fixed.txt ./build.sh
```

### Last Resort: Minimal Dependencies

If you continue to encounter dependency issues, consider:

1. **Creating a minimal requirements file** with only the absolutely essential packages
2. **Installing problematic packages separately** after the main installation
3. **Using our resilient build script** which falls back to core dependencies if all else fails

### General Strategy for Resolving Dependencies

When facing dependency conflicts:

1. **Identify the conflicting packages** - Look for packages that depend on the same library but require different versions
2. **Find compatible versions** - Use tools like `pip-tools` to find versions that work together
3. **Simplify requirements** - Remove unnecessary packages or find alternatives
4. **Test locally first** - Always test your changes locally before deploying
5. **Check package documentation** - Look for compatibility matrices for related packages (like pyHanko and its validator)

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