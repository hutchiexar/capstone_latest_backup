# Traffic Violation System Process Flow Charts

This document provides an overview of the flow charts created to visualize the key processes in the traffic violation system.

## 1. Violation Issuance Process

**File:** `violation_issuance_flow.drawio`

This flow chart illustrates how violations are issued in the system, covering both direct enforcement and NCAP (Non-Contact Apprehension Program) scenarios:

- **Direct Enforcement Path:** Traffic enforcer directly interacts with the violator, verifies identity, selects violation types, calculates fines, and issues a citation with signatures.
- **NCAP Path:** Enforcers capture photos of violations, record vehicle details, and upload to the system without direct interaction with the violator.
- **Common Paths:** Both types of violations are reviewed by a supervisor who either approves or rejects them. Approved violations proceed to payment due date assignment and notification.

## 2. Violation Payment Process

**File:** `payment_process_flow.drawio`

This flow chart shows how violators can pay their fines through two main channels:

- **In-Person Payment:** Violator visits the payment center, a treasurer verifies violation details, and the violator pays the fine.
- **Online Payment:** Violator accesses the online payment portal, logs in, locates their violation, and completes payment electronically.
- **Common Processing:** Both payment methods update the violation status to PAID, generate a receipt, and send a confirmation notification.

## 3. Violation Adjudication Process

**File:** `adjudication_process_flow.drawio`

This flow chart describes how contested violations are handled:

- When a violator contests a violation, the status is changed to CONTESTED.
- An adjudicator schedules a hearing and notifies all relevant parties.
- During the hearing, the adjudicator makes a decision: uphold, modify, or dismiss the violation.
- The violation status is updated accordingly, and an adjudication report is generated.

## 4. Educational Content Management Process

**File:** `educational_content_flow.drawio`

This flow chart illustrates how educational content is created and managed:

- **Content Creation:** Educators can create categories, topics, or quizzes. Each has its specific workflow but all end in being saved and published.
- **Content Management:** Existing content can be edited, published/unpublished, or deleted.
- The system maintains a record of all content changes in the database.

## 5. User Registration Process

**File:** `user_registration_flow.drawio`

This flow chart shows the registration paths for users:

- **Regular Registration:** User visits the registration page, fills in personal information, enters credentials, and submits.
- **QR-Based Registration:** User scans a QR code from a violation ticket, views pre-filled information, completes any missing details, and submits.
- **Common Processing:** System validates the information, creates the account, sends a verification email, and links any violations (for QR registrations).

## 6. Report Generation Process

**File:** `report_generation_flow.drawio`

This flow chart demonstrates how reports are generated:

- **On-Demand Reports:** User selects a report type and configures parameters.
- **Scheduled Reports:** System automatically triggers report generation with predefined configurations.
- **Common Processing:** System validates parameters, executes the query, processes data, and generates the output in the desired format (dashboard, PDF, or email).
- All generated reports are stored in the database for future reference.

## How to Use These Flow Charts

1. Open each `.drawio` file using the draw.io extension in VS Code or the online draw.io application.
2. Use these visualizations to understand the system workflows or for documentation purposes.
3. These diagrams can be helpful for training new staff or when making modifications to the system.

The color-coding in each diagram provides visual cues:
- Green ovals: Start/End points
- Blue rectangles: Process steps
- Yellow diamonds: Decision points
- Red rectangles: Error conditions or critical actions 