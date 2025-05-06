# Deploying Traffic Violation System to Render

This project is configured for easy deployment to Render using Blueprint deployment.

## Quick Deployment Steps

1. Ensure your code is pushed to GitHub
2. Log in to your Render dashboard
3. Click "New" → "Blueprint"
4. Select your GitHub repository
5. Render will automatically set up your web service and PostgreSQL database
6. Add your environment variables in the web service settings

For detailed instructions, see:
- `render_deployment_guide.md` - Complete step-by-step deployment guide
- `render_env_variables.md` - List of required environment variables

## Files for Render Deployment

- `render.yaml` - Defines services and their configurations
- `build.sh` - Build script for the deployment process
- `CAPSTONE_PROJECT/postgresql_settings.py` - PostgreSQL-specific settings

## Post-Deployment

After deployment:
1. Test your application on the provided Render URL
2. Monitor logs for any errors
3. Set up continuous deployment as needed

## Support

If you encounter issues during deployment, refer to the troubleshooting section in the deployment guide or Render's documentation at https://render.com/docs 