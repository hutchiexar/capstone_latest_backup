from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import User
from .models import Violator, Violation, Payment, UserProfile, ActivityLog, Operator, Vehicle, OperatorApplication, Driver
from django.utils import timezone

# Define inline admin classes
class UserProfileInline(admin.StackedInline):
    model = UserProfile
    can_delete = False
    verbose_name_plural = 'User Profile'

# Define custom UserAdmin
class UserAdmin(BaseUserAdmin):
    inlines = (UserProfileInline,)
    list_display = ('username', 'email', 'first_name', 'last_name', 'is_staff', 'get_role')
    
    def get_role(self, obj):
        return obj.userprofile.get_role_display() if hasattr(obj, 'userprofile') else ''
    get_role.short_description = 'Role'

# Register Violator
@admin.register(Violator)
class ViolatorAdmin(admin.ModelAdmin):
    list_display = ('license_number', 'first_name', 'last_name', 'phone_number')
    search_fields = ('license_number', 'first_name', 'last_name', 'phone_number')
    list_filter = ('created_at',)

# Register Violation
@admin.register(Violation)
class ViolationAdmin(admin.ModelAdmin):
    list_display = ('id', 'violator', 'violation_date', 'violation_type', 'status', 'fine_amount')
    list_filter = ('status', 'violation_type', 'violation_date')
    search_fields = ('violator__license_number', 'violation_type', 'location')
    date_hierarchy = 'violation_date'

# Register Payment
@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ('violation', 'amount_paid', 'payment_date', 'payment_method', 'transaction_id')
    list_filter = ('payment_date', 'payment_method')
    search_fields = ('transaction_id', 'violation__violator__license_number')
    date_hierarchy = 'payment_date'

# Register ActivityLog
@admin.register(ActivityLog)
class ActivityLogAdmin(admin.ModelAdmin):
    list_display = ('timestamp', 'user', 'action', 'category')
    list_filter = ('timestamp', 'category')
    search_fields = ('user__username', 'action', 'details')
    date_hierarchy = 'timestamp'
    readonly_fields = ('timestamp',)

# Register Operator
@admin.register(Operator)
class OperatorAdmin(admin.ModelAdmin):
    list_display = ('last_name', 'first_name', 'middle_initial', 'new_pd_number', 'old_pd_number', 'created_at')
    list_filter = ('created_at', 'updated_at')
    search_fields = ('last_name', 'first_name', 'new_pd_number', 'old_pd_number', 'address')
    date_hierarchy = 'created_at'

# Register OperatorApplication
class OperatorApplicationAdmin(admin.ModelAdmin):
    list_display = ('user', 'status', 'submitted_at', 'processed_at', 'processed_by')
    list_filter = ('status', 'submitted_at', 'processed_at')
    search_fields = ('user__username', 'user__first_name', 'user__last_name', 'notes')
    readonly_fields = ('submitted_at',)
    fieldsets = (
        ('Application Info', {
            'fields': ('user', 'status', 'submitted_at', 'processed_at', 'processed_by')
        }),
        ('Documents', {
            'fields': ('business_permit', 'other_documents')
        }),
        ('Notes', {
            'fields': ('notes',)
        }),
    )

    def save_model(self, request, obj, form, change):
        if 'status' in form.changed_data:
            # If status changed to APPROVED or REJECTED, set processed details
            if obj.status in ['APPROVED', 'REJECTED']:
                obj.processed_at = timezone.now()
                obj.processed_by = request.user
                
                # If approved, update the user profile
                if obj.status == 'APPROVED':
                    profile = obj.user.userprofile
                    profile.is_operator = True
                    profile.operator_since = timezone.now()
                    profile.save()
                    
                    # Log activity
                    ActivityLog.objects.create(
                        user=request.user,
                        action=f"Approved operator application for user {obj.user.username}",
                        category="user"
                    )
        super().save_model(request, obj, form, change)

# Unregister the default UserAdmin and register our custom one
admin.site.unregister(User)
admin.site.register(User, UserAdmin)
admin.site.register(OperatorApplication, OperatorApplicationAdmin)

# Register Driver
@admin.register(Driver)
class DriverAdmin(admin.ModelAdmin):
    list_display = ('last_name', 'first_name', 'middle_initial', 'address', 'old_pd_number', 'new_pd_number', 'operator')
    list_filter = ('operator',)
    search_fields = ('last_name', 'first_name', 'address', 'old_pd_number', 'new_pd_number')
    ordering = ('last_name', 'first_name')