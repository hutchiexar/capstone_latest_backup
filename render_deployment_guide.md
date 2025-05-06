# Traffic Violation System Deployment Guide for Render

This guide provides detailed steps to deploy your Traffic Violation System to Render with PostgreSQL as the database.

## Prerequisites

1. GitHub repository with your code committed
2. Render account
3. All necessary API keys and credentials from your .env file

## Step 1: Prepare Your Repository

Ensure these files are properly configured in your repository:

- `render.yaml` - Defines your Render services 
- `build.sh` - Contains build commands (ensure it's executable with `git update-index --chmod=+x build.sh`)
- `CAPSTONE_PROJECT/postgresql_settings.py` - Contains PostgreSQL-specific settings
- `requirements.txt` - Lists all dependencies

## Step 2: Create Services on Render

### Option A: Blueprint Deployment (Recommended)

1. Log in to your Render dashboard at https://dashboard.render.com/
2. Click "New" in the top right
3. Select "Blueprint" from the dropdown menu
4. Connect your GitHub repository if you haven't already
5. Select your repository from the list
6. Render will automatically detect the `render.yaml` file and show the services to be created
7. Review the configuration and click "Apply"
8. Render will create all the defined services (web service and PostgreSQL database)

### Option B: Manual Setup

If the Blueprint method doesn't work:

1. **Create a PostgreSQL Database**:
   - Go to your Render dashboard
   - Click "New" → "PostgreSQL"
   - Name: `traffic_violation_db`
   - Database: `traffic_violation_db`
   - User: Leave as default
   - Select the Free plan
   - Click "Create Database"
   - Note the Internal Database URL for the next step

2. **Create a Web Service**:
   - Go to your Render dashboard
   - Click "New" → "Web Service"
   - Connect your GitHub repository
   - Name: `traffic-violation-system`
   - Environment: `Python`
   - Build Command: `chmod +x build.sh && ./build.sh`
   - Start Command: `gunicorn CAPSTONE_PROJECT.wsgi:application`
   - Select the Free plan (or other as needed)
   - Click "Advanced" and add the environment variables (see `render_env_variables.md`)
   - Be sure to add `DATABASE_URL` with the value from your PostgreSQL service
   - Click "Create Web Service"

## Step 3: Configure Environment Variables

After creating your web service, you need to set up environment variables:

1. Go to your web service in the Render dashboard
2. Click on the "Environment" tab
3. Add all required environment variables from your .env file 
   (see `render_env_variables.md` for the complete list)
4. Click "Save Changes"

## Step 4: Setup Persistent Disk for Media Files

Your `render.yaml` already configures a 10GB disk mounted at `/opt/render/project/src/media`. If you created services manually:

1. Go to your web service in the Render dashboard
2. Click on the "Disks" tab
3. Click "Add Disk"
4. Name: `media`
5. Mount Path: `/opt/render/project/src/media`
6. Size: 10 GB (or adjust as needed)
7. Click "Save"

## Step 5: Set Up Continuous Deployment

Continuous Deployment is enabled by default on Render. When you push changes to your GitHub repository:

1. For automatic deployments:
   - Go to your web service settings
   - Under "Deploy" tab, ensure "Auto-Deploy" is enabled
   - Select your main branch

2. For manual deployments:
   - Go to your web service dashboard
   - Click the "Manual Deploy" button
   - Select "Deploy latest commit" or specify a commit

## Step 6: Verify Deployment

After deployment completes:

1. Click the URL of your web service to open your application
2. Test the main functionality to ensure everything works
3. Check the logs for any errors:
   - Go to your web service
   - Click the "Logs" tab
   - Look for any errors or warnings

## Troubleshooting

If you encounter issues:

1. **Database Connection Issues**:
   - Verify the `DATABASE_URL` environment variable is correctly set
   - Check logs for connection errors

2. **Static Files Not Loading**:
   - Ensure `STATIC_ROOT` and `STATIC_URL` are correctly set
   - Verify WhiteNoise is properly configured
   - Run `python manage.py collectstatic` manually via SSH

3. **Media Files Issues**:
   - Ensure disk is properly mounted
   - Check permissions on media directories
   - Verify paths in settings

4. **Application Errors**:
   - Review logs for Python exceptions or errors
   - SSH into your service for debugging: From dashboard → Shell

## Maintenance

1. **Database Backups**:
   - Render automatically creates daily backups for PostgreSQL databases
   - Access them in the database service dashboard under "Backups"

2. **Scaling**:
   - You can upgrade your plan as needed for more resources
   - Scale vertically by changing plan or horizontally by adding instances

3. **Monitoring**:
   - Use Render's built-in monitoring tools
   - Set up external monitoring for comprehensive coverage

## Security Considerations

1. Always keep `DEBUG` set to `False` in production
2. Use HTTPS for all traffic (enabled by default on Render)
3. Regularly update dependencies for security patches
4. Secure your API keys and environment variables

## Next Steps

1. Set up a proper domain name (optional)
2. Configure email verification settings for production
3. Monitor application performance and logs
4. Set up regular database backups
5. Consider upgrading plans based on traffic and resource needs 