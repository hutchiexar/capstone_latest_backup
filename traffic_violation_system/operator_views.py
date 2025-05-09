from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.contrib import messages
from django.http import JsonResponse
from .models import Operator, ActivityLog, Vehicle
from .forms import OperatorForm
from django.utils import timezone
from django.db import transaction

@login_required
def operator_enable(request, pk):
    """View to enable a previously disabled operator"""
    if not request.user.userprofile.role in ['ADMIN']:
        messages.error(request, "You don't have permission to enable operators.")
        return redirect('operator_list')
    
    operator = get_object_or_404(Operator, pk=pk)
    
    if request.method == 'POST':
        operator_name = f"{operator.last_name}, {operator.first_name}"
        
        try:
            # Enable the operator
            operator.active = True
            operator.save()
            
            # Log activity
            ActivityLog.objects.create(
                user=request.user,
                action=f"Enabled operator: {operator_name}",
                category="user"
            )
            
            messages.success(request, f"Operator {operator_name} has been enabled successfully.")
        except Exception as e:
            messages.error(request, f"Error enabling operator: {str(e)}")
            return JsonResponse({'success': False, 'error': str(e)})
        
        return JsonResponse({'success': True})
    
    # If it's not a POST request, return a 405 Method Not Allowed response
    return JsonResponse({
        'success': False, 
        'error': 'Method not allowed'
    }, status=405)


@login_required
def operator_create_with_potpots(request):
    """View to create a new operator with multiple vehicles"""
    if not request.user.userprofile.role in ['ADMIN', 'SUPERVISOR']:
        messages.error(request, "You don't have permission to create operators.")
        return redirect('operator_list')
    
    if request.method == 'POST':
        form = OperatorForm(request.POST)
        
        # Remove required validation for PD numbers since we'll auto-generate them
        if 'new_pd_number' in form.errors:
            del form.errors['new_pd_number']
        
        if form.is_valid() or ('new_pd_number' in form.errors and len(form.errors) == 1):
            # Get the operator without saving yet
            operator = form.save(commit=False)
            
            # Generate a system-wide unique New PD number
            # Find the highest existing new_pd_number in the system
            highest_pd = 0
            try:
                # Get all PD numbers, filtering out non-numeric ones
                pd_numbers = Operator.objects.filter(
                    new_pd_number__iregex=r'^\d+$'
                ).values_list('new_pd_number', flat=True)
                
                # Convert to integers for proper sorting
                numeric_pds = [int(pd) for pd in pd_numbers if pd and pd.isdigit()]
                
                if numeric_pds:
                    highest_pd = max(numeric_pds)
            except Exception as e:
                # If there's any error, log it but continue with default numbering
                print(f"Error determining highest PD number: {str(e)}")
            
            # Set the new PD number as next in sequence (XXX format)
            new_pd_number = str(highest_pd + 1).zfill(3)
            operator.new_pd_number = new_pd_number
            
            # Leave old PD number blank as requested
            operator.old_pd_number = ""
            
            # Generate a system-wide unique PO number if not provided
            if not operator.po_number:
                # Find the highest existing PO number in the system
                highest_po = 0
                try:
                    # Get all PO numbers, filtering out non-numeric ones
                    po_numbers = Operator.objects.filter(
                        po_number__iregex=r'^\d+$'
                    ).values_list('po_number', flat=True)
                    
                    # Convert to integers for proper sorting
                    numeric_pos = [int(po) for po in po_numbers if po and po.isdigit()]
                    
                    if numeric_pos:
                        highest_po = max(numeric_pos)
                except Exception as e:
                    # If there's any error, log it but continue with default numbering
                    print(f"Error determining highest PO number: {str(e)}")
                
                # Set the new PO number as next in sequence (XXX format)
                new_po_number = str(highest_po + 1).zfill(3)
                operator.po_number = new_po_number
            
            # Now save the operator with the assigned numbers
            operator.save()
            
            # Store the assigned numbers for logging
            pd_number_display = operator.new_pd_number
            po_number_display = operator.po_number
            
            # Process vehicles from the dynamic table
            vehicles_created = []
            vehicle_index = 0
            vehicle_types = {}  # Track count by vehicle type
            
            # Find the highest existing potpot number in the system
            highest_potpot = 0
            try:
                # Get all potpot numbers, filtering out non-numeric ones
                potpot_numbers = Vehicle.objects.filter(
                    potpot_number__iregex=r'^\d+$'
                ).values_list('potpot_number', flat=True)
                
                # Convert to integers for proper sorting
                numeric_potpots = [int(pn) for pn in potpot_numbers if pn and pn.isdigit()]
                
                if numeric_potpots:
                    highest_potpot = max(numeric_potpots)
            except Exception as e:
                # If there's any error, log it but continue with default numbering
                print(f"Error determining highest potpot number: {str(e)}")
            
            # Start numbering from the highest existing + 1
            potpot_number_counter = highest_potpot + 1
            
            # Extract vehicles data from POST data
            while f"vehicles[{vehicle_index}][vehicle_type]" in request.POST:
                vehicle_type = request.POST.get(f"vehicles[{vehicle_index}][vehicle_type]")
                count = request.POST.get(f"vehicles[{vehicle_index}][count]", "1")
                
                try:
                    count = int(count)
                    # Limit to 100 units max for safety
                    if count > 100:
                        count = 100
                except ValueError:
                    count = 1
                
                # Track count of each vehicle type
                if vehicle_type not in vehicle_types:
                    vehicle_types[vehicle_type] = 0
                vehicle_types[vehicle_type] += count
                
                # Create the specified number of vehicle records for this type
                for i in range(count):
                    # Generate potpot number in XXX format (001, 002, etc.)
                    potpot_number = str(potpot_number_counter).zfill(3)
                    potpot_number_counter += 1
                    
                    # Create a vehicle record
                    vehicle = Vehicle(
                        operator=operator,
                        potpot_number=potpot_number,
                        vehicle_type=vehicle_type,
                        active=True
                    )
                    
                    # Use the operator's new_pd_number as a base for the vehicle's pd number
                    # Format: [operator_pd]-[potpot_number]
                    if operator.new_pd_number:
                        vehicle.new_pd_number = f"{operator.new_pd_number}-{potpot_number}"
                    
                    # Save the vehicle
                    vehicle.save()
                    vehicles_created.append(potpot_number)
                
                vehicle_index += 1
            
            # Add log entry for vehicles
            if vehicles_created:
                vehicles_str = ", ".join(vehicles_created[:5])
                if len(vehicles_created) > 5:
                    vehicles_str += f" and {len(vehicles_created) - 5} more"
                
                # Provide details about the numbering range
                range_str = f"{vehicles_created[0]}-{vehicles_created[-1]}" if len(vehicles_created) > 1 else vehicles_created[0]
                
                # Create a summary of vehicle types
                vehicle_types_summary = ", ".join([f"{count} {vtype}" for vtype, count in vehicle_types.items()])
                
                ActivityLog.objects.create(
                    user=request.user,
                    action=f"Created operator (PO: {pd_number_display}) with {len(vehicles_created)} vehicles ({vehicle_types_summary}) (IDs range: {range_str}): {operator.last_name}, {operator.first_name}",
                    category="user"
                )
                
                messages.success(
                    request, 
                    f"Operator {operator.last_name}, {operator.first_name} (PO: {pd_number_display}) created successfully with {len(vehicles_created)} vehicles ({vehicle_types_summary})."
                )
            else:
                # Log activity for operator only
                ActivityLog.objects.create(
                    user=request.user,
                    action=f"Created operator (PO: {pd_number_display}): {operator.last_name}, {operator.first_name}",
                    category="user"
                )
                
                messages.success(request, f"Operator {operator.last_name}, {operator.first_name} (PO: {pd_number_display}) created successfully.")
            
            return redirect('operator_detail', pk=operator.id)
    else:
        form = OperatorForm()
    
    context = {
        'form': form,
        'title': 'Create Operator',
    }
    
    return render(request, 'operators/operator_form.html', context)

@login_required
def operator_print_slip(request, pk):
    """View to display a printable version of operator details"""
    operator = get_object_or_404(Operator, pk=pk)
    
    # Get all vehicles associated with this operator
    vehicles = Vehicle.objects.filter(operator=operator, active=True).order_by('potpot_number')
    
    context = {
        'operator': operator,
        'vehicles': vehicles,
        'current_date': timezone.now(),
    }
    
    # Log that someone viewed the print slip
    ActivityLog.objects.create(
        user=request.user,
        action=f"Generated print slip for operator: {operator.last_name}, {operator.first_name}",
        category="user"
    )
    
    return render(request, 'operators/operator_print_slip.html', context)

@login_required
def operator_print_own_slip(request):
    """View to allow operators to print their own operator slip"""
    # Check if the user is an operator
    if not request.user.userprofile.is_operator:
        messages.error(request, 'You are not registered as an operator.')
        return redirect('user_portal:user_dashboard')
    
    try:
        # Get the operator profile for the current user
        operator = Operator.objects.get(user=request.user)
        
        # Get all vehicles associated with this operator
        vehicles = Vehicle.objects.filter(operator=operator, active=True).order_by('potpot_number')
        
        context = {
            'operator': operator,
            'vehicles': vehicles,
            'current_date': timezone.now(),
        }
        
        # Log that the operator viewed their own print slip
        ActivityLog.objects.create(
            user=request.user,
            action=f"Operator generated their own print slip",
            category="user"
        )
        
        return render(request, 'operators/operator_print_slip.html', context)
    
    except Operator.DoesNotExist:
        # Fix the inconsistency: The user has is_operator=True but no operator profile
        messages.warning(request, 'Your operator profile was not found. If you believe this is an error, please contact support.')
        return redirect('operator_dashboard') 

@login_required
def operator_update_with_vehicles(request, pk):
    """View to update an existing operator and manage their vehicles"""
    if not request.user.userprofile.role in ['ADMIN', 'SUPERVISOR']:
        messages.error(request, "You don't have permission to update operators.")
        return redirect('operator_list')
    
    operator = get_object_or_404(Operator, pk=pk)
    # Get operator's existing vehicles
    existing_vehicles = Vehicle.objects.filter(operator=operator, active=True).order_by('vehicle_type', 'potpot_number')
    
    if request.method == 'POST':
        form = OperatorForm(request.POST, instance=operator)
        if form.is_valid():
            with transaction.atomic():
                # Save the operator details
                operator = form.save()
                
                # Process vehicles from the form
                vehicle_index = 0
                new_vehicles_count = 0
                vehicle_types = {}  # Track count by vehicle type
                
                # Find the highest existing potpot number in the system
                highest_potpot = 0
                try:
                    # Get all potpot numbers, filtering out non-numeric ones
                    potpot_numbers = Vehicle.objects.filter(
                        potpot_number__iregex=r'^\d+$'
                    ).values_list('potpot_number', flat=True)
                    
                    # Convert to integers for proper sorting
                    numeric_potpots = [int(pn) for pn in potpot_numbers if pn and pn.isdigit()]
                    
                    if numeric_potpots:
                        highest_potpot = max(numeric_potpots)
                except Exception as e:
                    # If there's any error, log it but continue with default numbering
                    print(f"Error determining highest potpot number: {str(e)}")
                
                # Start numbering from the highest existing + 1
                potpot_number_counter = highest_potpot + 1
                
                # Extract vehicles data from POST data
                while f"vehicles[{vehicle_index}][vehicle_type]" in request.POST:
                    vehicle_type = request.POST.get(f"vehicles[{vehicle_index}][vehicle_type]")
                    count = request.POST.get(f"vehicles[{vehicle_index}][count]", "1")
                    
                    try:
                        count = int(count)
                        # Limit to 100 units max for safety
                        if count > 100:
                            count = 100
                    except ValueError:
                        count = 1
                    
                    # Track count of each vehicle type
                    if vehicle_type not in vehicle_types:
                        vehicle_types[vehicle_type] = 0
                    vehicle_types[vehicle_type] += count
                    
                    # Create the specified number of vehicle records for this type
                    for i in range(count):
                        # Generate potpot number in XXX format (001, 002, etc.)
                        potpot_number = str(potpot_number_counter).zfill(3)
                        potpot_number_counter += 1
                        
                        # Create a vehicle record
                        vehicle = Vehicle(
                            operator=operator,
                            potpot_number=potpot_number,
                            vehicle_type=vehicle_type,
                            active=True
                        )
                        
                        # Use the operator's new_pd_number as a base for the vehicle's pd number
                        # Format: [operator_pd]-[potpot_number]
                        if operator.new_pd_number:
                            vehicle.new_pd_number = f"{operator.new_pd_number}-{potpot_number}"
                        
                        # Save the vehicle
                        vehicle.save()
                        new_vehicles_count += 1
                    
                    vehicle_index += 1
                
                # Create a summary of new vehicle types
                vehicle_types_summary = ", ".join([f"{count} {vtype}" for vtype, count in vehicle_types.items()])
                
                # Log activity with information about operator update and new vehicles
                log_message = f"Updated operator: {operator.last_name}, {operator.first_name}"
                if new_vehicles_count > 0:
                    log_message += f" and added {new_vehicles_count} new vehicles ({vehicle_types_summary})"
                
                ActivityLog.objects.create(
                    user=request.user,
                    action=log_message,
                    category="user"
                )
                
                # Create success message
                success_message = f"Operator {operator.last_name}, {operator.first_name} updated successfully"
                if new_vehicles_count > 0:
                    success_message += f" and {new_vehicles_count} new vehicles added ({vehicle_types_summary})"
                
                messages.success(request, success_message + ".")
                return redirect('operator_detail', pk=operator.id)
    else:
        form = OperatorForm(instance=operator)
    
    # Group vehicles by type for displaying in the form
    vehicle_groups = {}
    for vehicle in existing_vehicles:
        vehicle_type = vehicle.vehicle_type
        if vehicle_type not in vehicle_groups:
            vehicle_groups[vehicle_type] = []
        vehicle_groups[vehicle_type].append(vehicle)
    
    context = {
        'form': form,
        'operator': operator,
        'title': 'Update Operator',
        'existing_vehicles': existing_vehicles,
        'vehicle_groups': vehicle_groups,
    }
    
    return render(request, 'operators/operator_form.html', context) 