#!/usr/bin/env python

# Script to update operator functions to handle potpot numbers

import re

# Path to the file
file_path = 'traffic_violation_system/views.py'

# Read the file
with open(file_path, 'r', encoding='utf-8') as file:
    content = file.read()

# First, update the operator_apply function to store number_of_units in extra_data
operator_apply_pattern = r"(def operator_apply\(request\):.*?if form\.is_valid\(\):.*?application = form\.save\(commit=False\).*?application\.user = request\.user.*?)(application\.save\(\))"
operator_apply_match = re.search(operator_apply_pattern, content, re.DOTALL)

if not operator_apply_match:
    print("Could not find the operator_apply function with the expected pattern")
    exit(1)

# Build the replacement code with the number_of_units handling
operator_apply_replacement = f"{operator_apply_match.group(1)}\n            # Store the number of units in extra_data as JSON\n            import json\n            number_of_units = request.POST.get('number_of_units', '1')\n            try:\n                number_of_units = int(number_of_units)\n                if number_of_units < 1:\n                    number_of_units = 1\n                elif number_of_units > 100:\n                    number_of_units = 100\n            except (ValueError, TypeError):\n                number_of_units = 1\n                \n            application.extra_data = json.dumps({{'number_of_units': number_of_units}})\n            application.save()"

# Apply the first replacement
updated_content = content.replace(operator_apply_match.group(0), operator_apply_replacement)

# Now, update the operator_application_review function to create vehicles based on number_of_units
operator_review_pattern = r"(operator\.po_number = generate_po_number\(\).*?operator\.save\(\).*?# Update the user profile to mark them as an operator.*?user_profile\.operator_since = timezone\.now\(\).*?user_profile\.save\(\).*?)(# Create notification for the user)"
operator_review_match = re.search(operator_review_pattern, updated_content, re.DOTALL)

if not operator_review_match:
    print("Could not find the operator_application_review function with the expected pattern")
    exit(1)

# Build the replacement code to create potpot units
operator_review_replacement = f"{operator_review_match.group(1)}\n                        # Check if number_of_units was specified in the application\n                        import json\n                        units_created = 0\n                        vehicles_created = []\n                        \n                        try:\n                            if application.extra_data:\n                                # Parse the extra_data JSON\n                                extra_data = json.loads(application.extra_data)\n                                number_of_units = extra_data.get('number_of_units', 1)\n                                \n                                # Ensure it's an integer and within limits\n                                number_of_units = int(number_of_units)\n                                if number_of_units > 100:\n                                    number_of_units = 100  # Limit to 100 units\n                                \n                                if number_of_units > 0:\n                                    # Find the highest existing potpot number in the system\n                                    highest_potpot = 0\n                                    try:\n                                        # Get all potpot numbers, filtering out non-numeric ones\n                                        potpot_numbers = Vehicle.objects.filter(\n                                            potpot_number__iregex=r'^\\d+$'\n                                        ).values_list('potpot_number', flat=True)\n                                        \n                                        # Convert to integers for proper sorting\n                                        numeric_potpots = [int(pn) for pn in potpot_numbers if pn and pn.isdigit()]\n                                        \n                                        if numeric_potpots:\n                                            highest_potpot = max(numeric_potpots)\n                                    except Exception as e:\n                                        # If there's any error, log it but continue with default numbering\n                                        print(f\"Error determining highest potpot number: {{str(e)}}\")\n                                    \n                                    # Start numbering from the highest existing + 1\n                                    start_number = highest_potpot + 1\n                                    \n                                    # Create the specified number of vehicle records\n                                    for i in range(start_number, start_number + number_of_units):\n                                        # Generate potpot number in XXX format (001, 002, etc.)\n                                        potpot_number = str(i).zfill(3)\n                                        \n                                        # Create a vehicle record for this potpot\n                                        vehicle = Vehicle(\n                                            operator=operator,\n                                            potpot_number=potpot_number,\n                                            vehicle_type='Potpot',\n                                            active=True\n                                        )\n                                        \n                                        # Use the operator's new_pd_number as a base for the vehicle's pd number\n                                        # Format: [operator_pd]-[potpot_number]\n                                        if operator.new_pd_number:\n                                            vehicle.new_pd_number = f\"{{operator.new_pd_number}}-{{potpot_number}}\"\n                                        \n                                        # Save the vehicle\n                                        vehicle.save()\n                                        vehicles_created.append(potpot_number)\n                                        units_created += 1\n                        except Exception as e:\n                            # Log error but continue with the approval\n                            print(f\"Error creating potpot units: {{str(e)}}\")\n                        \n                        {operator_review_match.group(2)}"

# Apply the second replacement
final_content = updated_content.replace(operator_review_match.group(0), operator_review_replacement)

# Update the action log message to include details about the vehicles created
action_log_pattern = r"(ActivityLog\.objects\.create\(\s*user=request\.user,\s*action=f\"Approved operator application for \{application\.user\.username\}\",\s*details=f\"Assigned PO Number: \{operator\.po_number\}\",\s*category=\"operator\"\s*\))"
action_log_match = re.search(action_log_pattern, final_content, re.DOTALL)

if action_log_match:
    action_log_replacement = "ActivityLog.objects.create(\n                            user=request.user,\n                            action=f\"Approved operator application for {application.user.username}\",\n                            details=f\"Assigned PO Number: {operator.po_number}, Created {units_created} potpot vehicles\",\n                            category=\"operator\"\n                        )"
    final_content = final_content.replace(action_log_match.group(0), action_log_replacement)

# Update the notification message to include details about the vehicles created
notification_pattern = r"(UserNotification\.objects\.create\(\s*user=application\.user,\s*type='SYSTEM',\s*message=f'Your operator application has been approved\. You now have operator privileges\.'\s*\))"
notification_match = re.search(notification_pattern, final_content, re.DOTALL)

if notification_match:
    notification_replacement = "UserNotification.objects.create(\n                            user=application.user,\n                            type='SYSTEM',\n                            message=f'Your operator application has been approved. You now have operator privileges with {units_created} potpot vehicles created.'\n                        )"
    final_content = final_content.replace(notification_match.group(0), notification_replacement)

# Write the updated content back to the file
with open(file_path, 'w', encoding='utf-8') as file:
    file.write(final_content)

print("Successfully updated operator_apply and operator_application_review functions to handle potpot numbers") 