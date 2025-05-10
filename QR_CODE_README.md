# QR Code Registration for Traffic Violations

This documentation explains the QR code functionality added to the Traffic Violation System to help violators register with their violations efficiently.

## Overview

The QR code functionality allows traffic enforcement officers to generate QR codes for violations they issue. The violator can scan this QR code to register an account that is automatically linked to their violation. This simplifies the user onboarding process and ensures violations are properly connected to user accounts.

## Features

1. **QR Code Generation**: Automatically generate QR codes for any violation ticket
2. **Printable QR Code View**: A printable page with the QR code and violation details
3. **Registration with Violations**: Custom registration flow that links users to their violations
4. **Direct Ticket Integration**: QR code generation is integrated into the direct ticket issuance workflow

## Technical Implementation

### Files Added/Modified:

1. **views_violation_qr.py**: Contains core QR code functionality
   - QR hash generation and storage
   - QR code image generation
   - Registration with violations view

2. **Templates**:
   - `qr_code_print.html`: Printable QR code view with violation details
   - `register_with_violations.html`: Registration form that connects violations

3. **URLs**: Added routes for:
   - `/violation/<int:violation_id>/qr-print/`: Printable QR code view
   - `/violation/<int:violation_id>/qr-image/`: Raw QR code image
   - `/violation/qr-info/<str:hash_id>/`: API endpoint for QR code information
   - `/register/violations/<str:hash_id>/`: Registration with violations

4. **Direct Ticket Integration**:
   - Updated the `issue_direct_ticket` view to generate QR codes
   - Added QR code buttons to the success message

## How It Works

1. When an officer issues a violation ticket, a unique hash ID is generated for that violation
2. A QR code is created that encodes a registration URL with this hash ID
3. The officer can print the QR code and give it to the violator
4. When the violator scans the QR code, they are directed to a special registration page
5. After registration, their account is automatically linked to the violation

## Implementation Details

### QR Hash Generation

The system uses a combination of:
- Violation ID
- Violator's name
- Random UUID
- SHA-256 hashing

This ensures each QR code is unique and securely tied to a specific violation.

### In-Memory Storage

For simplicity, the implementation uses an in-memory dictionary to store QR hash mappings. In a production environment, this should be replaced with a database model to ensure persistence.

### QR Code Format

- Size: 300x300 pixels
- Error correction: Low (L)
- Border: 4 units
- Format: PNG

## Usage

### For Officers:

1. Issue a violation ticket using the direct ticket issuance form
2. After successful ticket issuance, click the "Print QR Code" button
3. Print the QR code page and provide it to the violator

### For Violators:

1. Scan the QR code with any smartphone camera
2. Complete the registration form on the linked page
3. After registration, the violation will be available in the user's dashboard

## Testing

A test script (`test_qr_code.py`) is provided to verify the QR code generation functionality.

## Future Enhancements

1. **Database Storage**: Move QR hash mappings to a database model
2. **Expiration Time**: Add expiration time for QR codes
3. **Multiple Violations**: Support registration with multiple violations
4. **Analytics**: Track QR code usage and conversion rates 