from django import forms
from django.contrib.auth.models import User
from .models import Violation, Violator, UserProfile, Operator, Payment, ActivityLog, Announcement, LocationHistory, Vehicle, OperatorApplication, Driver
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
            'old_pd_number': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Old P.D. No.'}),
            'new_pd_number': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'New P.D. No.'}),
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
        fields = ['business_permit', 'other_documents']
        widgets = {
            'business_permit': forms.FileInput(attrs={'class': 'form-control'}),
            'other_documents': forms.FileInput(attrs={'class': 'form-control'}),
        }
        help_texts = {
            'business_permit': 'Upload a scanned copy of your business permit (PDF/JPG/PNG)',
            'other_documents': 'Upload any additional required documents (PDF/JPG/PNG)',
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
    """Form for creating/updating driver information"""
    class Meta:
        model = Driver
        fields = ['last_name', 'first_name', 'middle_initial', 'address', 'old_pd_number', 'new_pd_number', 'operator']
        widgets = {
            'last_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Last Name'}),
            'first_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'First Name'}),
            'middle_initial': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'M.I.'}),
            'address': forms.Textarea(attrs={'class': 'form-control', 'placeholder': 'Address', 'rows': 3}),
            'old_pd_number': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Old P.D. No.'}),
            'new_pd_number': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'New P.D. No.'}),
            'operator': forms.Select(attrs={'class': 'form-control'}),
        }

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