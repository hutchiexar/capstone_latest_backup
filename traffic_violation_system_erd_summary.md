# Traffic Violation System - Entity Relationship Diagram Documentation

This document provides a comprehensive overview of the database structure for the Traffic Violation System. The complete Entity Relationship Diagram (ERD) has been split into four separate diagrams for clarity and better organization.

## 1. Core Violation System Components

**File**: `traffic_violation_system_erd.drawio`

This diagram covers the core entities of the traffic violation system:

- **Violator**: Represents individuals who commit traffic violations.
- **ViolationType**: Defines different categories of traffic violations.
- **UserProfile**: Extensions to the Django User model with role-based permissions.
- **Violation**: The central entity that records traffic violation incidents.
- **Payment**: Tracks financial transactions related to violation fines.
- **ViolatorQRHash**: Manages QR codes for violator identification.

Key relationships:
- A violator can have multiple violations
- Each violation is of a specific violation type
- Each violation can have multiple payments
- User profiles govern system access with specific roles

## 2. Operator and Vehicle Components

**File**: `traffic_violation_system_operators_erd.drawio`

This diagram focuses on transportation operators, vehicles, and drivers:

- **Operator**: Companies or individuals operating transportation services.
- **OperatorType**: Categorizes different types of transportation operators.
- **Vehicle**: Transportation assets like buses, taxis, etc.
- **Driver**: Individuals authorized to operate vehicles.
- **DriverVehicleAssignment**: Tracks which drivers are assigned to which vehicles.
- **OperatorApplication**: Manages the application process for new operators.

Key relationships:
- An operator can have multiple vehicles
- An operator can employ multiple drivers
- Drivers can be assigned to multiple vehicles (through assignments)
- Each operator has a specific operator type

## 3. Educational Components

**File**: `traffic_violation_system_educational_erd.drawio`

This diagram details the educational module of the system:

- **EducationalCategory**: Top-level organization for educational content.
- **EducationalTopic**: Specific learning materials within categories.
- **TopicAttachment**: Files and media associated with educational topics.
- **Quiz**: Assessments to test knowledge of educational materials.
- **QuizQuestion & QuizAnswer**: Components that make up quizzes.
- **UserBookmark, UserProgress, UserQuizAttempt**: Track user interaction with educational content.

Key relationships:
- Categories contain multiple topics
- Topics can have multiple attachments
- Quizzes are associated with specific topics
- User progress, bookmarks, and quiz attempts track individual learning journeys

## 4. Reporting and System Components

**File**: `traffic_violation_system_reports_erd.drawio`

This diagram covers reporting functionality and system management:

- **Report**: Templates for generating data reports.
- **ReportPermission**: Controls access to reports based on user roles.
- **ReportSchedule**: Configures automated report generation.
- **GeneratedReport**: Stores the output of report generation processes.
- **ActivityLog**: Tracks user actions throughout the system.
- **Announcement & AnnouncementAcknowledgment**: System-wide notifications.
- **LocationHistory**: Tracks location data for mobile users.
- **ViolationCertificate**: Official documentation for violations.
- **EmailVerificationToken**: Manages email verification.

Key relationships:
- Reports can have multiple permissions and schedules
- Reports generate multiple report outputs
- Announcements can have multiple acknowledgments
- User activities are tracked in the activity log

## How to Use These ERDs

1. **Open the Diagrams**: Use draw.io (https://app.diagrams.net/) to open each `.drawio` file.
2. **Navigate Between Diagrams**: Each diagram focuses on a specific aspect of the system.
3. **Reading Relationships**:
   - Lines with a single endpoint and many endpoints (crow's foot) indicate one-to-many relationships.
   - Lines with crow's feet on both ends indicate many-to-many relationships.
   - PK indicates Primary Key
   - FK indicates Foreign Key

## Color Coding

- **Core Violation Components** (Light Blue): Central violation-related entities
- **User-Related Entities** (Light Green): User profiles and authentication
- **Operator Components** (Light Yellow): Transportation operators and vehicles
- **Educational Components** (Light Purple): Learning materials and quizzes
- **Reporting Components** (Light Purple): Analytics and reporting
- **System Components** (Light Gray): System management and utilities

## Database Integrity and Constraints

The database implements several integrity constraints:

1. **Referential Integrity**: Foreign keys ensure related records exist
2. **Data Validation**: Field-level constraints ensure data quality
3. **Transaction Management**: Ensures operations complete fully or not at all
4. **Temporal Constraints**: Date fields track record lifecycles

## Schema Evolution Considerations

As the system evolves, consider these best practices:

1. Always use migrations for schema changes
2. Add new fields with default values where possible
3. Test data migrations thoroughly before production deployment
4. Document schema changes in version control

---

*Note: This ERD represents the current database schema as of the latest update. As the system evolves, the actual database structure may differ.* 