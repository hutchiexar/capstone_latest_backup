from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import User
from .models import Violator, Violation, Payment, UserProfile, ActivityLog

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

# Unregister the default UserAdmin and register our custom one
admin.site.unregister(User)
admin.site.register(User, UserAdmin)