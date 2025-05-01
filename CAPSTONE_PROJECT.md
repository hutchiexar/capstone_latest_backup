# Traffic Violation System - CAPSTONE PROJECT

## Project Overview
The Traffic Violation System is a comprehensive web-based management system built with Django that handles the entire workflow of traffic violations, from issuance to resolution. The system serves multiple stakeholders including traffic enforcers, administrative staff, operators, drivers, and regular users.

## System Architecture
- **Backend**: Django 4.x with Python 3.8+
- **Frontend**: HTML, CSS, JavaScript, Bootstrap 
- **Database**: MySQL (Development & Production)
- **Authentication**: Django Authentication with Role-based Access Control
- **Additional Technologies**:
  - QR code generation for identification
  - Image processing for violation evidence
  - PDF generation for reports and receipts
  - Geolocation tracking for enforcers
  - Face recognition for identity verification
  - Adjudication workflow management

## Features Implemented
- User management with role-based permissions (Admin, Enforcer, Supervisor, Treasurer, Clerk, Regular User)
- Traffic violation recording and tracking with complete violation lifecycle
- NCAP (Non-Contact Apprehension Program) violation handling
- Operator and driver management with vehicle assignment
- Adjudication process with approval workflow
- Payment processing and receipt generation
- Educational resources for traffic rules awareness
- Announcement system with priority levels and targeted audiences
- Comprehensive activity logging for audit trails
- Location tracking for enforcers with path history
- Operator application system with document management
- API endpoints for mobile integration

## Database Schema

### User Management
- **User**: Django's built-in user model for authentication
- **UserProfile**: Extended user information with role-based permissions
  - Fields: `user` (OneToOne), `enforcer_id`, `avatar`, `phone_number`, `contact_number`, `address`, `qr_code`, `role` (ADMIN, ENFORCER, SUPERVISOR, TREASURER, CLERK, USER), location tracking data, emergency contacts, birthdate

### Violation Management
- **Violator**: Information about individuals who commit violations
  - Fields: `first_name`, `last_name`, `license_number`, `phone_number`, `address`, timestamps
- **ViolationType**: Catalog of different types of violations and their penalties
  - Fields: `name`, `description`, `amount`, `category` (LICENSING, REGISTRATION, DIMENSION, FRANCHISE, OTHER), `is_active`, `is_ncap`
- **Violation**: The core entity tracking violations
  - Fields: `violator`, `enforcer`, `violation_date`, `location`, `violation_type`, `fine_amount`, `status` (PENDING, ADJUDICATED, APPROVED, REJECTED, PAID, SETTLED, CONTESTED, HEARING_SCHEDULED, DISMISSED, EXPIRED), image evidence, vehicle info, processing details, payment tracking, adjudication information
- **Payment**: Tracks payments made for violations
  - Fields: `violation`, `amount_paid`, `payment_date`, `payment_method`, `transaction_id`
- **ViolationCertificate**: Certificate information for violations
  - Fields: `violation`, `operations_officer`, `ctm_officer`, `certificate_text`

### Operator & Vehicle Management
- **Operator**: Information about vehicle operators
  - Fields: `last_name`, `first_name`, `middle_initial`, `address`, `old_pd_number`, `new_pd_number`, `po_number`, `user`, `active`
- **OperatorType**: Types of operators (e.g., Tricycle, Jeepney)
  - Fields: `name`, `description`
- **Vehicle**: Vehicle information
  - Fields: `operator`, `old_pd_number`, `new_pd_number`, `potpot_number`, `vehicle_type` (Jeepney, Tricycle, Potpot, Other), `plate_number`, `engine_number`, `chassis_number`, `capacity`, `year_model`, `color`, `active`
- **Driver**: Driver information
  - Fields: `last_name`, `first_name`, `middle_initial`, `address`, `old_pd_number`, `new_pd_number`, `license_number`, `contact_number`, emergency contacts, `active`, `expiration_date`, `operator`
- **DriverVehicleAssignment**: Tracks which drivers are assigned to which vehicles
  - Fields: `driver`, `vehicle`, `start_date`, `end_date`, `is_active`, `notes`
- **OperatorApplication**: Applications for new operator permits
  - Fields: `user`, document uploads (`business_permit`, `police_clearance`, `barangay_certificate`, `cedula`, `cenro_tickets`, `mayors_permit`, `other_documents`), `status`, processing data

### Communication & Activity Tracking
- **Announcement**: System-wide or targeted announcements
  - Fields: `title`, `content`, `created_by`, timestamps, `is_active`, `priority` (LOW, MEDIUM, HIGH), `category` (GENERAL, POLICY, SYSTEM, EMERGENCY, EVENT), `target_audience` (ALL, ADMIN, ENFORCER, SUPERVISOR, TREASURER, CLERK, USER), visibility settings
- **AnnouncementAcknowledgment**: Tracks which users have seen announcements
  - Fields: `announcement`, `user`, `acknowledged_at`
- **ActivityLog**: System-wide activity logging
  - Fields: `user`, `timestamp`, `action`, `details`, `category` (general, violation, user, payment, system), `ip_address`
- **LocationHistory**: Tracks enforcer locations
  - Fields: `user_profile`, coordinates (`latitude`, `longitude`), `accuracy`, `heading`, `speed`, `is_active_duty`, `battery_level`, `timestamp`, `device_info`

## Key Workflows

### Violation Issuance and Processing
1. Enforcer records a violation using a mobile interface
2. System creates a violation record with PENDING status
3. Violation can be adjudicated to modify violation types or amounts
4. Supervisor approves or rejects the adjudication
5. Violator makes payment which is recorded in the system
6. Receipt is generated after payment is confirmed

### Operator and Vehicle Management
1. Operators can apply through the system with required documentation
2. Admin reviews and approves applications
3. Operators can register their vehicles and associate drivers
4. System maintains historical records of driver-vehicle assignments

### Enforcer Tracking
1. System tracks enforcer locations in real-time when on duty
2. Historical location data is stored for audit and management purposes
3. Map interface shows current enforcer positions

## API Endpoints
- `/api/violations/`: List and create violations
- `/api/users/`: User management
- `/api/operators/`: Operator management
- `/api/vehicles/`: Vehicle information
- `/api/announcements/`: System announcements
- `/api/locations/`: Location tracking for enforcers
- `/api/search-operators/`: Search operators by name or ID
- `/api/search-drivers/`: Search drivers by name or license number

## Future Enhancements
- Enhanced reporting dashboard with advanced analytics
- Mobile application for enforcers with offline capabilities
- Integration with external payment systems
- Real-time notification system using WebSockets
- Advanced analytics and trend reporting for traffic violations
- Integration with national driver's license database
- Automated violation detection using AI and video analytics

## Deployment Configuration
The application is designed to be deployed using:
- Web server with MySQL database
- Static file hosting for media and documents
- SSL/TLS encryption for secure communication
- Automated backups for data integrity

## Database Migration Management
All database schema changes should be tracked through Django's migration system:
```
python manage.py makemigrations
python manage.py migrate
```

New migrations should be documented in this file with a brief description of schema changes.

## Contributors
- CAPSTONE Team members

## License
This project is proprietary and all rights are reserved.
