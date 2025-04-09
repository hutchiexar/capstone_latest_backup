# Deploying to Render

This guide explains how to deploy the Traffic Violation System on Render.com.

## Prerequisites

- A Render.com account
- Git repository with your project code

## Deployment Steps

### 1. Push Your Code to GitHub

Make sure your code is pushed to a GitHub repository.

### 2. Deploy on Render

#### Option 1: Deploy via render.yaml

1. Log in to your Render dashboard: https://dashboard.render.com/
2. Click on "Blueprint" in the sidebar
3. Click on "New Blueprint Instance"
4. Connect your GitHub repository
5. Render will automatically detect the `render.yaml` file and set up the services
6. Review the configuration and click "Apply"

#### Option 2: Manual Deployment

1. Log in to your Render dashboard: https://dashboard.render.com/
2. Create a new PostgreSQL database:
   - Click on "New" > "PostgreSQL"
   - Give it a name: `traffic_violation_db`
   - Choose a region and plan according to your needs
   - Click "Create Database"

3. Create a new Web Service:
   - Click on "New" > "Web Service"
   - Connect your GitHub repository
   - Give it a name: `traffic-violation-system`
   - Choose the region and plan
   - Set the build command: `./build.sh`
   - Set the start command: `gunicorn CAPSTONE_PROJECT.wsgi:application`
   - Set environment variables:
     - `DJANGO_SETTINGS_MODULE`: `CAPSTONE_PROJECT.render_settings`
     - `SECRET_KEY`: (generate a secure random string)
     - `DEBUG`: `False`
     - `DATABASE_URL`: (use the Internal Database URL from your Render PostgreSQL service)
     - `DJANGO_ALLOWED_HOSTS`: `.onrender.com,your-custom-domain.com` (if you have one)
   - Add a Persistent Disk:
     - Mount path: `/opt/render/project/src/media`
     - Size: 10 GB (or adjust based on your needs)
   - Click "Create Web Service"

### 3. Check Deployment

After deployment is complete, you can access your application at the URL provided by Render (e.g., `https://traffic-violation-system.onrender.com`).

### 4. Create a Superuser

To create a superuser for the admin panel, use the Render Shell:

1. Go to your Web Service in the Render dashboard
2. Click on "Shell" in the top-right corner
3. Run the following command:
   ```
   python manage.py createsuperuser
   ```
4. Follow the prompts to create your admin user

## Troubleshooting

- If your deployment fails, check the logs in the Render dashboard for errors.
- Make sure your DATABASE_URL environment variable is correctly set.
- If static files aren't loading, verify that collectstatic ran successfully during deployment.
- If you encounter issues with media file uploads, check that your disk is mounted properly. 