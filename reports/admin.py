from django.contrib import admin
from .models import Report, ReportPermission, ReportSchedule, GeneratedReport

class ReportPermissionInline(admin.TabularInline):
    model = ReportPermission
    extra = 1

@admin.register(Report)
class ReportAdmin(admin.ModelAdmin):
    list_display = ('name', 'type', 'chart_enabled', 'is_active', 'created_at')
    list_filter = ('type', 'is_active', 'chart_enabled')
    search_fields = ('name', 'description')
    inlines = [ReportPermissionInline]
    fieldsets = (
        (None, {
            'fields': ('name', 'description', 'type', 'is_active')
        }),
        ('Query Configuration', {
            'fields': ('query_template',),
        }),
        ('Chart Options', {
            'fields': ('chart_enabled', 'chart_type'),
            'classes': ('collapse',),
        }),
    )

@admin.register(ReportSchedule)
class ReportScheduleAdmin(admin.ModelAdmin):
    list_display = ('report', 'user', 'frequency', 'next_run', 'is_active')
    list_filter = ('frequency', 'is_active')
    search_fields = ('report__name', 'user__username', 'email_recipients')
    raw_id_fields = ('user',)

@admin.register(GeneratedReport)
class GeneratedReportAdmin(admin.ModelAdmin):
    list_display = ('report', 'user', 'generated_at', 'pdf_file')
    list_filter = ('generated_at',)
    search_fields = ('report__name', 'user__username')
    date_hierarchy = 'generated_at'
    readonly_fields = ('generated_at',)
    raw_id_fields = ('user', 'report', 'schedule')
