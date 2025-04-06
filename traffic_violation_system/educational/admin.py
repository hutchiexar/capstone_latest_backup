from django.contrib import admin
from .models import EducationalCategory, EducationalTopic, TopicAttachment, UserBookmark, UserProgress


class TopicAttachmentInline(admin.TabularInline):
    model = TopicAttachment
    extra = 1
    fields = ('title', 'file', 'file_type', 'description')


@admin.register(EducationalCategory)
class EducationalCategoryAdmin(admin.ModelAdmin):
    list_display = ('title', 'created_at')
    search_fields = ('title', 'description')
    list_filter = ('created_at',)
    ordering = ('title',)


@admin.register(EducationalTopic)
class EducationalTopicAdmin(admin.ModelAdmin):
    list_display = ('title', 'category', 'is_published', 'created_by', 'created_at', 'updated_at')
    list_filter = ('is_published', 'category', 'created_at', 'updated_at')
    search_fields = ('title', 'content')
    readonly_fields = ('created_at', 'updated_at')
    list_editable = ('is_published',)
    actions = ['publish_topics', 'unpublish_topics']
    fieldsets = (
        (None, {
            'fields': ('title', 'category', 'is_published')
        }),
        ('Content', {
            'fields': ('content',)
        }),
        ('Metadata', {
            'fields': ('created_by', 'created_at', 'updated_at')
        }),
    )
    inlines = [TopicAttachmentInline]
    
    def save_model(self, request, obj, form, change):
        """Set the created_by field to the current user if creating a new topic."""
        if not change and not obj.created_by:
            obj.created_by = request.user
        super().save_model(request, obj, form, change)
    
    def publish_topics(self, request, queryset):
        """Bulk action to publish multiple topics at once."""
        for topic in queryset:
            topic.publish()
        self.message_user(request, f'{queryset.count()} topics have been published.')
    publish_topics.short_description = "Publish selected topics"
    
    def unpublish_topics(self, request, queryset):
        """Bulk action to unpublish multiple topics at once."""
        for topic in queryset:
            topic.unpublish()
        self.message_user(request, f'{queryset.count()} topics have been unpublished.')
    unpublish_topics.short_description = "Unpublish selected topics"


@admin.register(TopicAttachment)
class TopicAttachmentAdmin(admin.ModelAdmin):
    list_display = ('title', 'topic', 'file_type', 'created_at')
    list_filter = ('file_type', 'created_at')
    search_fields = ('title', 'description', 'topic__title')


@admin.register(UserBookmark)
class UserBookmarkAdmin(admin.ModelAdmin):
    list_display = ('user', 'topic', 'created_at')
    list_filter = ('created_at',)
    search_fields = ('user__username', 'topic__title')
    date_hierarchy = 'created_at'


@admin.register(UserProgress)
class UserProgressAdmin(admin.ModelAdmin):
    list_display = ('user', 'topic', 'is_completed', 'last_accessed', 'completed_at')
    list_filter = ('is_completed', 'last_accessed', 'completed_at')
    search_fields = ('user__username', 'topic__title')
    date_hierarchy = 'last_accessed' 