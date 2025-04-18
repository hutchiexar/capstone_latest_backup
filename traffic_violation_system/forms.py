from django import forms
from django.contrib.auth.models import User
from .models import Violation, Violator, UserProfile, Operator, Payment, ActivityLog, Announcement, LocationHistory, Vehicle, OperatorApplication, Driver, DriverVehicleAssignment
import os

class NCAPViolationForm(forms.ModelForm):
    """Form for handling NCAP (Non-Contact Apprehension Program) violations"""
    
    # Add a field for the violator's license number to find or create a violator
    license_number = forms.CharField(max_length=20, required=True, label="License Number")
    first_name = forms.CharField(max_length=100, required=True, label="First Name")
    last_name = forms.CharField(max_length=100, required=True, label="Last Name")
    
    class Meta:
        model = Violation
        fields = [
            'violation_date', 'location', 'violation_type', 'fine_amount', 
            'image', 'plate_number', 'vehicle_type', 'color', 'classification'
        ]
        widgets = {
            'violation_date': forms.DateTimeInput(attrs={'type': 'datetime-local'}),
            'fine_amount': forms.NumberInput(attrs={'step': '0.01', 'min': '0'}),
        }
    
    def clean_image(self):
        """Validate the uploaded image"""
        image = self.cleaned_data.get('image')
        if not image:
            raise forms.ValidationError("An image is required for NCAP violations")
        
        # Check file size (5MB limit)
        if image.size > 5 * 1024 * 1024:
            raise forms.ValidationError("Image file is too large. Please upload an image less than 5MB.")
        
        # Check file extension
        valid_extensions = ['.jpg', '.jpeg', '.png', '.webp']
        ext = os.path.splitext(image.name)[1].lower()
        if not any(ext == valid_ext for valid_ext in valid_extensions):
            raise forms.ValidationError(f"Unsupported file type. Please upload a JPG, PNG, or WEBP image.")
        
        return image
    
    def save(self, commit=True):
        """Override save to handle creating or fetching the violator"""
        # Don't save the form yet
        instance = super().save(commit=False)
        
        # Get or create the violator based on license number
        license_number = self.cleaned_data.get('license_number')
        first_name = self.cleaned_data.get('first_name')
        last_name = self.cleaned_data.get('last_name')
        
        try:
            # Try to find an existing violator
            violator = Violator.objects.get(license_number=license_number)
            # Update name if provided
            if first_name and last_name:
                violator.first_name = first_name
                violator.last_name = last_name
                violator.save()
        except Violator.DoesNotExist:
            # Create a new violator if not found
            violator = Violator.objects.create(
                license_number=license_number,
                first_name=first_name,
                last_name=last_name
            )
        
        # Set the violator for this violation
        instance.violator = violator
        
        # Save the violation if commit is True
        if commit:
            instance.save()
        
        return instance 

class ViolationForm(forms.ModelForm):
    """Form for handling regular traffic violations"""
    
    # Add a field for the violator's license number to find or create a violator
    license_number = forms.CharField(max_length=20, required=True, label="License Number")
    first_name = forms.CharField(max_length=100, required=True, label="First Name")
    last_name = forms.CharField(max_length=100, required=True, label="Last Name")
    
    class Meta:
        model = Violation
        fields = [
            'violation_date', 'location', 'violation_type', 'fine_amount',
            'description', 'plate_number', 'vehicle_type', 'color', 
            'classification', 'registration_number', 'registration_date',
            'vehicle_owner', 'vehicle_owner_address'
        ]
        widgets = {
            'violation_date': forms.DateTimeInput(attrs={'type': 'datetime-local'}),
            'fine_amount': forms.NumberInput(attrs={'step': '0.01', 'min': '0'}),
            'registration_date': forms.DateInput(attrs={'type': 'date'}),
            'description': forms.Textarea(attrs={'rows': 3}),
            'vehicle_owner_address': forms.Textarea(attrs={'rows': 2}),
        }
    
    def save(self, commit=True):
        """Override save to handle creating or fetching the violator"""
        # Don't save the form yet
        instance = super().save(commit=False)
        
        # Get or create the violator based on license number
        license_number = self.cleaned_data.get('license_number')
        first_name = self.cleaned_data.get('first_name')
        last_name = self.cleaned_data.get('last_name')
        
        try:
            # Try to find an existing violator
            violator = Violator.objects.get(license_number=license_number)
            # Update name if provided
            if first_name and last_name:
                violator.first_name = first_name
                violator.last_name = last_name
                violator.save()
        except Violator.DoesNotExist:
            # Create a new violator if not found
            violator = Violator.objects.create(
                license_number=license_number,
                first_name=first_name,
                last_name=last_name
            )
        
        # Set the violator for this violation
        instance.violator = violator
        
        # Save the violation if commit is True
        if commit:
            instance.save()
        
        return instance

class OperatorForm(forms.ModelForm):
    class Meta:
        model = Operator
        fields = ['last_name', 'first_name', 'middle_initial', 'address', 'old_pd_number', 'new_pd_number']
        widgets = {
            'last_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Last Name'}),
            'first_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'First Name'}),
            'middle_initial': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'M.I.'}),
            'address': forms.Textarea(attrs={'class': 'form-control', 'placeholder': 'Address', 'rows': 3}),
            'old_pd_number': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Old P.O. No.'}),
            'new_pd_number': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'New P.O. No.'}),
        }

class ImportOperatorsForm(forms.Form):
    file = forms.FileField(
        label='Select a file',
        help_text='Allowed file types: .xlsx, .csv',
        widget=forms.FileInput(attrs={'class': 'form-control'})
    )

class OperatorApplicationForm(forms.ModelForm):
    class Meta:
        model = OperatorApplication
        fields = [
            'business_permit', 
            'police_clearance', 
            'barangay_certificate', 
            'cedula', 
            'cenro_tickets',
            'mayors_permit', 
            'other_documents'
        ]
        widgets = {
            'business_permit': forms.FileInput(attrs={'class': 'form-control'}),
            'police_clearance': forms.FileInput(attrs={'class': 'form-control'}),
            'barangay_certificate': forms.FileInput(attrs={'class': 'form-control'}),
            'cedula': forms.FileInput(attrs={'class': 'form-control'}),
            'cenro_tickets': forms.FileInput(attrs={'class': 'form-control'}),
            'mayors_permit': forms.FileInput(attrs={'class': 'form-control'}),
            'other_documents': forms.FileInput(attrs={'class': 'form-control'}),
        }
        help_texts = {
            'business_permit': 'Upload a scanned copy of your business permit (PDF/JPG/PNG)',
            'police_clearance': 'Upload a scanned copy of your police clearance (JPG/PNG)',
            'barangay_certificate': 'Upload a scanned copy of your barangay certificate (JPG/PNG)',
            'cedula': 'Upload a scanned copy of your community tax certificate (JPG/PNG)',
            'cenro_tickets': 'Upload a scanned copy of your CENRO tickets or permits (JPG/PNG)',
            'mayors_permit': 'Upload a scanned copy of your mayor\'s permit (PDF/JPG/PNG)',
            'other_documents': 'Upload any additional supporting documents (PDF/JPG/PNG)',
        }
    
    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        
    def clean(self):
        cleaned_data = super().clean()
        # Check if user already has a pending application
        if self.user and OperatorApplication.objects.filter(user=self.user, status='PENDING').exists():
            raise forms.ValidationError("You already have a pending application. Please wait for it to be processed.")
        return cleaned_data
        
    def save(self, commit=True):
        instance = super().save(commit=False)
        if self.user:
            instance.user = self.user
        if commit:
            instance.save()
        return instance 

class PaymentForm(forms.ModelForm):
    """Form for handling payments for violations"""
    class Meta:
        model = Payment
        fields = ['amount_paid', 'payment_method', 'transaction_id']
        widgets = {
            'amount_paid': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'min': '0'}),
            'payment_method': forms.Select(attrs={'class': 'form-control'}, choices=[
                ('CASH', 'Cash'),
                ('CREDIT', 'Credit Card'),
                ('DEBIT', 'Debit Card'),
                ('BANK', 'Bank Transfer'),
                ('ONLINE', 'Online Payment'),
                ('OTHER', 'Other')
            ]),
            'transaction_id': forms.TextInput(attrs={'class': 'form-control'}),
        }

class ProfileUpdateForm(forms.ModelForm):
    """Form for updating user profile information"""
    class Meta:
        model = UserProfile
        fields = ['phone_number', 'address', 'avatar', 'license_number']
        widgets = {
            'phone_number': forms.TextInput(attrs={'class': 'form-control'}),
            'address': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'avatar': forms.FileInput(attrs={'class': 'form-control'}),
            'license_number': forms.TextInput(attrs={'class': 'form-control'}),
        }

class UserUpdateForm(forms.ModelForm):
    """Form for updating user account information"""
    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'email']
        widgets = {
            'first_name': forms.TextInput(attrs={'class': 'form-control'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
        }

class ViolatorForm(forms.ModelForm):
    """Form for creating/updating violator information"""
    class Meta:
        model = Violator
        fields = ['first_name', 'last_name', 'license_number', 'phone_number', 'address']
        widgets = {
            'first_name': forms.TextInput(attrs={'class': 'form-control'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control'}),
            'license_number': forms.TextInput(attrs={'class': 'form-control'}),
            'phone_number': forms.TextInput(attrs={'class': 'form-control'}),
            'address': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }

class SignatureForm(forms.Form):
    """Form for handling signature captures"""
    signature_data = forms.CharField(widget=forms.HiddenInput())
    violation_id = forms.IntegerField(widget=forms.HiddenInput())
    signatory_type = forms.CharField(widget=forms.HiddenInput())

class OperatorImportForm(forms.Form):
    """Form for importing operators from CSV/Excel file"""
    file = forms.FileField(
        label='Select a file',
        help_text='Allowed file types: .xlsx, .csv',
        widget=forms.FileInput(attrs={'class': 'form-control'})
    )
    skip_header = forms.BooleanField(
        initial=True,
        required=False,
        help_text='Skip the first row (header row)'
    )

class DriverForm(forms.ModelForm):
    """Form for creating and updating drivers"""
    class Meta:
        model = Driver
        fields = [
            'last_name', 'first_name', 'middle_initial', 'address',
            'old_pd_number', 'new_pd_number',
            'license_number', 'contact_number', 'emergency_contact',
            'emergency_contact_number', 'active'
        ]
        widgets = {
            'last_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Last Name'}),
            'first_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'First Name'}),
            'middle_initial': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'M.I.'}),
            'address': forms.Textarea(attrs={'class': 'form-control', 'placeholder': 'Address', 'rows': 3}),
            'old_pd_number': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Previous PD number if available'}),
            'new_pd_number': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'D-XXXXX'}),
            'license_number': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Driver license number'}),
            'contact_number': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Contact number'}),
            'emergency_contact': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Emergency contact name'}),
            'emergency_contact_number': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Emergency contact number'}),
            'active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

    def __init__(self, *args, **kwargs):
        self.operator = kwargs.pop('operator', None)
        super().__init__(*args, **kwargs)
        
        # Add help texts
        self.fields['license_number'].help_text = "Valid driver's license number"
        self.fields['active'].help_text = "Whether this driver is currently employed"

    def save(self, commit=True):
        instance = super().save(commit=False)
        if self.operator:
            instance.operator = self.operator
        if commit:
            instance.save()
        return instance

class DriverVehicleAssignmentForm(forms.ModelForm):
    """Form for assigning drivers to vehicles"""
    class Meta:
        model = DriverVehicleAssignment
        fields = ['driver', 'vehicle', 'notes']
        widgets = {
            'driver': forms.Select(attrs={'class': 'form-select'}),
            'vehicle': forms.Select(attrs={'class': 'form-select'}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'placeholder': 'Assignment notes', 'rows': 3}),
        }
        
    def __init__(self, *args, **kwargs):
        self.operator = kwargs.pop('operator', None)
        super().__init__(*args, **kwargs)
        
        # Filter drivers and vehicles by operator
        if self.operator:
            self.fields['driver'].queryset = Driver.objects.filter(operator=self.operator, active=True)
            self.fields['vehicle'].queryset = Vehicle.objects.filter(operator=self.operator, active=True)
            
        # Add help texts
        self.fields['driver'].help_text = "Select the driver to assign"
        self.fields['vehicle'].help_text = "Select the vehicle to assign to this driver"
        self.fields['notes'].help_text = "Optional notes about this assignment"

class VehicleForm(forms.ModelForm):
    """Form for creating and updating vehicles"""
    
    capacity = forms.IntegerField(
        required=False,
        min_value=1,
        max_value=100,
        widget=forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Passenger capacity'}),
        help_text="Maximum number of passengers (default 4 for private vehicles)"
    )
    
    class Meta:
        model = Vehicle
        fields = [
            'vehicle_type', 'plate_number', 'potpot_number', 'engine_number', 'chassis_number',
            'capacity', 'year_model', 'color', 'notes', 'active'
        ]
        widgets = {
            'vehicle_type': forms.Select(attrs={'class': 'form-select', 'placeholder': 'Select vehicle type'}),
            'plate_number': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter plate number'}),
            'potpot_number': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter Potpot Number'}),
            'engine_number': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter engine number'}),
            'chassis_number': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter chassis number'}),
            'year_model': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter year model'}),
            'color': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter vehicle color'}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'placeholder': 'Additional notes', 'rows': 3}),
            'active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

    def __init__(self, *args, **kwargs):
        self.operator = kwargs.pop('operator', None)
        super().__init__(*args, **kwargs)
        
        # Make all fields except vehicle_type optional
        for field_name, field in self.fields.items():
            if field_name != 'vehicle_type':
                field.required = False
        
        # Add help texts
        self.fields['vehicle_type'].help_text = "Type of public utility vehicle"
        self.fields['potpot_number'].help_text = "Required for Potpot vehicle type"
        self.fields['active'].help_text = "Whether this vehicle is currently active in your fleet"

    def clean(self):
        cleaned_data = super().clean()
        vehicle_type = cleaned_data.get('vehicle_type')
        potpot_number = cleaned_data.get('potpot_number')
        
        # Make potpot_number required if vehicle_type is Potpot
        if vehicle_type == 'Potpot' and not potpot_number:
            self.add_error('potpot_number', 'Potpot Number is required for Potpot vehicle type')
            
        return cleaned_data

    def save(self, commit=True):
        instance = super().save(commit=False)
        if self.operator:
            instance.operator = self.operator
        if commit:
            instance.save()
        return instance

class DriverImportForm(forms.Form):
    """Form for importing drivers from CSV/Excel file - only reads the Drivers worksheet"""
    file = forms.FileField(
        label='Select a file',
        help_text='Allowed file types: .xlsx, .csv',
        widget=forms.FileInput(attrs={'class': 'form-control'})
    )
    skip_header = forms.BooleanField(
        initial=True,
        required=False,
        help_text='Skip the first row (header row)'
    ) 