# Traffic Violation System Flowcharts

This directory contains flowcharts for all the main processes in the Traffic Violation System. Each flowchart is created using draw.io (diagrams.net) and can be opened and edited with that tool.

## Available Flowcharts

1. **Authentication Process** (`auth_process.drawio`)
   - Illustrates the user login and authentication flow
   - Shows role-based redirection to appropriate dashboards

2. **Violation Ticketing Process** (`violation_ticketing.drawio`)
   - Shows the process of issuing a traffic violation ticket
   - Includes creating/finding violator records and calculating fines

3. **Adjudication Process** (`adjudication_process.drawio`)
   - Depicts the workflow for reviewing and adjudicating violations
   - Shows the decision-making process for validating or dismissing violations

4. **Payment Process** (`payment_process.drawio`)
   - Illustrates how violators can pay their fines
   - Includes both online and in-office payment options

5. **NCAP Violation Processing** (`ncap_violation_process.drawio`)
   - Shows the No-Contact Apprehension Program violation workflow
   - Includes license plate recognition and owner identification

6. **Operator Management Process** (`operator_management.drawio`)
   - Depicts the workflow for managing public transport operators
   - Includes adding, viewing, editing, and importing operators

7. **Driver Management Process** (`driver_management.drawio`)
   - Shows how drivers are managed in the system
   - Includes creating, editing, and associating drivers with operators

8. **Announcements and Notifications Process** (`announcements_notifications.drawio`)
   - Illustrates how announcements are created and distributed
   - Shows notification delivery and acknowledgment flow

9. **Location Tracking Process** (`location_tracking.drawio`)
   - Depicts how enforcer locations are tracked and displayed
   - Shows the real-time location update cycle

## How to View and Edit

To view or edit these flowcharts:

1. Visit [diagrams.net](https://app.diagrams.net/) or use the desktop application
2. Open the desired .drawio file
3. Make edits as needed
4. Save your changes

## Notes

- These flowcharts represent the ideal process flows as implemented in the system
- Actual implementations may contain additional error handling or edge cases
- For detailed implementation, refer to the corresponding code files 