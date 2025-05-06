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
pip install -r requirements.txt
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