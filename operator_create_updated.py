@login_required
def operator_create(request):
    """View to create a new operator"""
    if not request.user.userprofile.role in ['ADMIN', 'SUPERVISOR']:
        messages.error(request, "You don't have permission to create operators.")
        return redirect('operator_list')
    
    if request.method == 'POST':
        form = OperatorForm(request.POST)
        if form.is_valid():
            # Create the operator
            operator = form.save()
            
            # Check if number_of_units was provided
            number_of_units = request.POST.get('number_of_units')
            if number_of_units and number_of_units.isdigit():
                number_of_units = int(number_of_units)
                
                # Limit to 100 units max for safety
                if number_of_units > 100:
                    number_of_units = 100
                    messages.warning(request, "Maximum limit of 100 units applied.")
                
                vehicles_created = []
                
                # Create the specified number of vehicle records
                for i in range(1, number_of_units + 1):
                    # Generate potpot number in XXX format (001, 002, etc.)
                    potpot_number = str(i).zfill(3)
                    
                    # Create a vehicle record for this potpot
                    vehicle = Vehicle(
                        operator=operator,
                        potpot_number=potpot_number,
                        vehicle_type='Potpot',
                        active=True
                    )
                    
                    # Use the operator's new_pd_number as a base for the vehicle's pd number
                    # Format: [operator_pd]-[potpot_number]
                    if operator.new_pd_number:
                        vehicle.new_pd_number = f"{operator.new_pd_number}-{potpot_number}"
                    
                    # Save the vehicle
                    vehicle.save()
                    vehicles_created.append(potpot_number)
                
                # Add log entry for vehicles
                vehicles_str = ", ".join(vehicles_created[:5])
                if len(vehicles_created) > 5:
                    vehicles_str += f" and {len(vehicles_created) - 5} more"
                
                ActivityLog.objects.create(
                    user=request.user,
                    action=f"Created {len(vehicles_created)} vehicles (Potpot IDs: {vehicles_str}) for operator: {operator.last_name}, {operator.first_name}",
                    category="user"
                )
                
                messages.success(
                    request, 
                    f"Operator {operator.last_name}, {operator.first_name} created successfully with {len(vehicles_created)} potpot vehicles."
                )
            else:
                # Log activity for operator only
                ActivityLog.objects.create(
                    user=request.user,
                    action=f"Created operator: {operator.last_name}, {operator.first_name}",
                    category="user"
                )
                
                messages.success(request, f"Operator {operator.last_name}, {operator.first_name} created successfully.")
            
            return redirect('operator_list')
    else:
        form = OperatorForm()
    
    context = {
        'form': form,
        'title': 'Create Operator',
    }
    
    return render(request, 'operators/operator_form.html', context) 