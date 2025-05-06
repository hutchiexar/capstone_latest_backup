# Traffic Violation System

## Overview
A comprehensive web-based traffic violation management system built with Django. This system enables efficient handling of traffic violations, including reporting, tracking, and managing violations with features like QR code generation and face recognition for enhanced security.

## Features
- **User Authentication & Authorization**
  - Role-based access control (Admin, Staff, Regular Users)
  - Secure login and registration system
  - Password reset functionality

- **Violation Management**
  - Record and track traffic violations
  - Generate violation tickets
  - QR code integration for quick access to violation details
  - Face recognition for identity verification
  - NCAP violation handling
  - Adjudication process management

- **User Portal**
  - Personal dashboard for users
  - View and track violation history
  - Online payment integration
  - Document upload capability

- **Administrative Features**
  - User management
  - Violation type configuration
  - System-wide announcements
  - Activity logging and monitoring
  - Report generation

## Technology Stack
- **Backend**: Django 4.x
- **Frontend**: HTML5, CSS3, JavaScript, Bootstrap
- **Database**: SQLite (Development) / MySQL (Production)
- **Authentication**: Django Authentication System
- **Additional Libraries**:
  - Face Recognition
  - QR Code Generation
  - PDF Generation
  - Image Processing

## Installation

### Prerequisites
- Python 3.8 or higher
- pip (Python package manager)
- Virtual environment (recommended)
- MySQL (for production)

### Setup Instructions

1. **Clone the Repository**
   ```bash
   git clone https://github.com/xf00889/traffic-violation-system.git
   cd traffic-violation-system
   ```

2. **Create and Activate Virtual Environment**
   ```bash
   python -m venv venv
   # On Windows
   venv\Scripts\activate
   # On Unix or MacOS
   source venv/bin/activate
   ```

3. **Install Dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Environment Configuration**
   - Copy `.env.example` to `.env`
   - Update the environment variables in `.env` with your configurations
   ```bash
   cp .env.example .env
   ```

5. **Database Setup**
   ```bash
   python manage.py migrate
   ```

6. **Create Superuser**
   ```bash
   python manage.py createsuperuser
   ```

7. **Run Development Server**
   ```bash
   python manage.py runserver
   ```

## Usage

### Accessing the System
- **Main Application**: http://localhost:8000
- **Admin Interface**: http://localhost:8000/admin

### User Types and Capabilities
1. **Admin Users**
   - Full system access
   - User management
   - System configuration
   - Report generation

2. **Staff Users**
   - Violation recording
   - Ticket generation
   - User assistance

3. **Regular Users**
   - View personal violations
   - Make payments
   - Submit appeals

## Development

### Project Structure
```
traffic_violation_system/
├── CAPSTONE_PROJECT/      # Project settings
├── traffic_violation_system/  # Main application
├── templates/             # HTML templates
├── static/               # Static files
├── media/                # User-uploaded files
└── requirements.txt      # Project dependencies
```

### Key Components
- `settings.py`: Project configuration
- `urls.py`: URL routing
- `views.py`: View logic
- `models.py`: Database models
- `forms.py`: Form definitions

## Security Features
- SSL/TLS encryption support
- CSRF protection
- Password hashing
- Session management
- Face recognition verification
- QR code authentication

## Contributing
1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request

## Production Deployment
- Configure production settings
- Set up a production database
- Configure static file serving
- Set up SSL certificates
- Use a production-grade web server (e.g., Nginx)
- Configure environment variables

## License
This project is licensed under the MIT License - see the LICENSE file for details.

## Support
For support, please open an issue in the GitHub repository or contact the development team.

## Acknowledgments
- Django Framework
- Bootstrap
- Face Recognition Libraries
- QR Code Generation Tools
- All contributors and testers

# CTTMO VMS Educational Module - PDF Viewer Integration

This project enhances the Traffic Violation Management System's educational module by integrating a fully embedded PDF viewer for better manual and educational content presentation.

## Features

### PDF Viewer Integration

- **Embedded PDF Viewer**: Uses PDF.js to render PDF documents directly in the browser without requiring users to download or open in a new tab
- **Interactive Controls**: Navigation buttons, page selector, zoom controls, and search functionality
- **Responsive Design**: Adapts to different screen sizes while maintaining usability
- **Sidebar Navigation**: Synchronized with PDF content to highlight current section

### User Experience Improvements

- **Reduced Text Fatigue**: Viewing content in its original PDF format preserves professional layout and reduces wall-of-text fatigue
- **Seamless Experience**: Users stay within the application for all educational content
- **Content Hierarchy**: Better visual hierarchy through PDF's native formatting
- **Accessibility**: Controls for adjusting zoom level for better readability

## Technical Implementation

### Libraries Used

- **PDF.js**: Mozilla's powerful JavaScript library for rendering PDFs in the browser
- **Bootstrap**: For responsive layout and UI components
- **SweetAlert2**: For user notifications and alerts

### Key Files

- `topic_detail.html`: Main template file for displaying educational content
- `views.py`: Backend logic for serving PDF content and tracking user progress
- `models.py`: Data models for educational content and attachments

### Usage

1. **For Administrators**:
   - Upload PDF documents as attachments to educational topics
   - Select "PDF" as the file type when uploading
   - The system will automatically use the PDF viewer when a PDF attachment is present

2. **For Users**:
   - Navigate to the Educational section
   - PDF manuals will automatically open in the embedded viewer
   - Use the navigation controls to browse through the document
   - Bookmark or mark topics as completed just like regular content

## Development Notes

### Adding New Features

To extend the PDF viewer functionality:
- PDF.js offers additional features like annotations and form filling
- The sidebar synchronization can be enhanced for more precise navigation
- Advanced search with highlighting could be implemented for better text discovery

### Browser Compatibility

The PDF viewer is compatible with all modern browsers:
- Chrome 50+
- Firefox 52+
- Safari 11+
- Edge 79+

## Troubleshooting

If PDFs aren't displaying properly:
1. Ensure PDF attachments are properly uploaded with file type set to "PDF"
2. Check browser console for any JavaScript errors
3. Verify that PDF.js libraries are loading properly
4. For large PDFs, consider optimizing the file size for faster loading

# Traffic Violation System - Deployment Guide

## Project Overview

This is a Django-based Traffic Violation System designed to manage traffic violations, driver information, and adjudication processes. The system includes features for ID verification, PDF generation, and analytics.

## Deployment Process

### Deployment Architecture

The application is configured for deployment on Render.com using:
- Python 3.10.0
- PostgreSQL database
- Gunicorn web server
- Whitenoise for static files

### Deployment Files

Key deployment files:
- `render.yaml` - Configuration for Render.com services
- `build.sh` - Build script for dependency installation and setup
- `direct_import_patch.py` - Script to handle problematic imports
- `requirements-fixed.txt` - Optimized dependencies list
- `requirements-minimal.txt` - Fallback minimal dependencies

## Dependency Management

The system uses a multi-tier approach to dependency management:

1. **Primary Dependencies**: Listed in `requirements-fixed.txt` with specific version constraints
2. **Fallback Dependencies**: If primary installation fails, falls back to `requirements.txt` and then `requirements-minimal.txt`
3. **Individual Package Installation**: Critical packages are installed individually if all else fails

## Import Error Handling

The deployment process includes robust handling of import errors:

### The Direct Import Patching Approach

The `direct_import_patch.py` script:
- Scans for problematic import statements using regex
- Creates backups of affected files
- Replaces imports with try-except blocks that include fallback implementations
- Provides graceful degradation for problematic modules

Currently handled modules:
- **idanalyzer**: ID verification functionality
- **pyHanko**: PDF signing functionality

## Deployment Steps

1. **Update Dependencies**
   - Ensure `requirements-fixed.txt` is up-to-date
   - Verify Python version in `render.yaml` is set to 3.10.0

2. **Configure Build Process**
   - Verify `build.sh` permissions (`chmod +x build.sh`)
   - Ensure `direct_import_patch.py` is included in the repository

3. **Deploy to Render.com**
   - Connect your GitHub repository
   - Render will use the `render.yaml` configuration
   - Environment variables will be set automatically from `render.yaml`

4. **Post-Deployment Verification**
   - Check logs for successful dependency installation
   - Verify database migrations completed successfully
   - Test functionality that uses potentially problematic dependencies

## Troubleshooting

### Common Issues

#### 1. Module Import Errors

If the application reports "Module not found" errors:
- Check the build logs to ensure all dependencies were installed
- Verify the module is included in the patching script
- Add new fallback implementations as needed

#### 2. Database Connection Issues

If database connections fail:
- Verify the `DATABASE_URL` environment variable in Render dashboard
- Check PostgreSQL version compatibility
- Ensure the database specified in `render.yaml` was created

#### 3. Static Files

If static files don't load properly:
- Check `STATIC_ROOT` and `STATIC_URL` in settings
- Verify `whitenoise` middleware is configured
- Ensure `collectstatic` ran successfully during build

## Local Development Setup

For local development:

1. Clone the repository
2. Create a virtual environment: `python -m venv venv`
3. Activate the environment: 
   - Windows: `venv\Scripts\activate`
   - Unix/MacOS: `source venv/bin/activate`
4. Install dependencies: `pip install -r requirements-fixed.txt`
5. Create a `.env` file with required variables (see `.env.example`)
6. Run migrations: `python manage.py migrate`
7. Create a superuser: `python manage.py createsuperuser`
8. Run the development server: `python manage.py runserver`

## Environment Variables

Required environment variables:
- `SECRET_KEY` - Django secret key
- `DEBUG` - Set to "False" for production
- `DJANGO_ALLOWED_HOSTS` - Comma-separated list of allowed hosts
- `DATABASE_URL` - PostgreSQL connection string
- `RENDER` - Set to "True" when deploying to Render

## Maintenance and Updates

When updating the application:
1. Test all changes locally first
2. Update dependencies as needed in `requirements-fixed.txt`
3. If adding new dependencies that may cause conflicts, update the patching script
4. Commit and push changes to trigger a new deployment on Render
