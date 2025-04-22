from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.models import User
from .models import VehicleRegistration, UserReport, UserNotification, UserProfile, UserVehicle, UserPreferences, OperatorLookup, DriverApplication

class VehicleRegistrationInline(admin.TabularInline):
    model = VehicleRegistration
    extra = 0
    fields = ('plate_number', 'vehicle_type', 'make', 'model', 'year_model', 'or_number', 'cr_number', 'is_active')
    readonly_fields = ('created_at', 'updated_at')

# Extend the existing UserAdmin
class CustomUserAdmin(UserAdmin):
    list_display = ('username', 'email', 'first_name', 'last_name', 'is_staff', 'get_vehicle_count')
    list_filter = ('is_staff', 'is_superuser', 'is_active')
    search_fields = ('username', 'email', 'first_name', 'last_name')
    
    inlines = [VehicleRegistrationInline]
    
    def get_vehicle_count(self, obj):
        return obj.vehicleregistration_set.count()
    get_vehicle_count.short_description = 'Vehicles'

# Register VehicleRegistration model
@admin.register(VehicleRegistration)
class VehicleRegistrationAdmin(admin.ModelAdmin):
    list_display = ('plate_number', 'user', 'vehicle_type', 'make', 'model', 'or_number', 'cr_number', 'is_active')
    list_filter = ('is_active', 'vehicle_type')
    search_fields = ('plate_number', 'or_number', 'cr_number', 'user__username', 'user__email')
    date_hierarchy = 'created_at'
    
    fieldsets = (
        ('User Information', {
            'fields': ('user',)
        }),
        ('Vehicle Details', {
            'fields': ('plate_number', 'vehicle_type', 'make', 'model', 'year_model', 'color', 'classification')
        }),
        ('Registration Information', {
            'fields': ('or_number', 'cr_number', 'registration_date', 'expiry_date', 'or_cr_image')
        }),
        ('Status', {
            'fields': ('is_active',)
        }),
    )

# Register UserReport model
@admin.register(UserReport)
class UserReportAdmin(admin.ModelAdmin):
    list_display = ('subject', 'user', 'type', 'incident_date', 'status', 'created_at')
    list_filter = ('status', 'type')
    search_fields = ('subject', 'description', 'user__username')
    date_hierarchy = 'created_at'

# Register UserNotification model
@admin.register(UserNotification)
class UserNotificationAdmin(admin.ModelAdmin):
    list_display = ('user', 'message', 'type', 'is_read', 'created_at')
    list_filter = ('is_read', 'type')
    search_fields = ('user__username', 'message')
    date_hierarchy = 'created_at'

# Register UserProfile model
@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'address', 'city', 'state', 'zip_code')
    search_fields = ('user__username', 'address', 'city', 'state', 'zip_code')

# Register UserVehicle model
@admin.register(UserVehicle)
class UserVehicleAdmin(admin.ModelAdmin):
    list_display = ('user', 'vehicle', 'is_primary')
    search_fields = ('user__username', 'vehicle__plate_number')

# Register UserPreferences model
@admin.register(UserPreferences)
class UserPreferencesAdmin(admin.ModelAdmin):
    list_display = ('user', 'notification_preference', 'language')
    search_fields = ('user__username', 'notification_preference', 'language')

# Register OperatorLookup model
@admin.register(OperatorLookup)
class OperatorLookupAdmin(admin.ModelAdmin):
    list_display = ('name', 'type')
    search_fields = ('name', 'type')

# Register DriverApplication model
@admin.register(DriverApplication)
class DriverApplicationAdmin(admin.ModelAdmin):
    list_display = ('user', 'status', 'submitted_at', 'processed_at', 'processed_by')
    list_filter = ('status', 'submitted_at', 'processed_at')
    search_fields = ('user__username', 'user__first_name', 'user__last_name', 'notes')
    readonly_fields = ('submitted_at',)
    raw_id_fields = ('user', 'processed_by')
    date_hierarchy = 'submitted_at'
    
    fieldsets = (
        (None, {
            'fields': ('user', 'status', 'notes')
        }),
        ('Documents', {
            'fields': ('cttmo_seminar_certificate', 'xray_results', 'medical_certificate', 
                      'police_clearance', 'mayors_permit', 'other_documents')
        }),
        ('Processing Information', {
            'fields': ('processed_by', 'processed_at', 'submitted_at')
        }),
    )

# Unregister the default UserAdmin and register our custom one
admin.site.unregister(User)
admin.site.register(User, CustomUserAdmin) 