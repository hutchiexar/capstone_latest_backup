from django.contrib import admin
from .models import EducationalCategory, EducationalTopic, TopicAttachment, UserBookmark, UserProgress
from .models import Quiz, QuizQuestion, QuizAnswer, UserQuizAttempt, UserQuestionResponse


class TopicAttachmentInline(admin.TabularInline):
    model = TopicAttachment
    extra = 1
    fields = ('title', 'file', 'file_type', 'description')


@admin.register(EducationalCategory)
class EducationalCategoryAdmin(admin.ModelAdmin):
    list_display = ('title', 'order', 'created_at')
    list_filter = ('created_at',)
    search_fields = ('title', 'description')
    ordering = ('order', 'title')
    
    def get_queryset(self, request):
        return super().get_queryset(request).prefetch_related('topics')


@admin.register(EducationalTopic)
class EducationalTopicAdmin(admin.ModelAdmin):
    list_display = ('title', 'category', 'is_published', 'created_by', 'created_at')
    list_filter = ('is_published', 'category', 'created_at')
    search_fields = ('title', 'content')
    date_hierarchy = 'created_at'
    actions = ['publish_topics', 'unpublish_topics']
    inlines = [TopicAttachmentInline]
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('category', 'created_by')
    
    def save_model(self, request, obj, form, change):
        if not obj.created_by:
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


# Quiz Admin Classes
class QuizAnswerInline(admin.TabularInline):
    model = QuizAnswer
    extra = 2
    fields = ('text', 'is_correct', 'explanation')


class QuizQuestionInline(admin.StackedInline):
    model = QuizQuestion
    extra = 1
    fields = ('text', 'question_type', 'points', 'order')
    inlines = []  # Can't nest inlines in Django admin


@admin.register(Quiz)
class QuizAdmin(admin.ModelAdmin):
    list_display = ('title', 'topic', 'passing_score', 'is_published', 'created_by', 'created_at')
    list_filter = ('is_published', 'created_at')
    search_fields = ('title', 'description')
    date_hierarchy = 'created_at'
    actions = ['publish_quizzes', 'unpublish_quizzes']
    inlines = [QuizQuestionInline]
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('topic', 'created_by')
    
    def save_model(self, request, obj, form, change):
        if not obj.created_by:
            obj.created_by = request.user
        super().save_model(request, obj, form, change)
    
    def publish_quizzes(self, request, queryset):
        """Bulk action to publish multiple quizzes at once."""
        for quiz in queryset:
            quiz.publish()
        self.message_user(request, f'{queryset.count()} quizzes have been published.')
    publish_quizzes.short_description = "Publish selected quizzes"
    
    def unpublish_quizzes(self, request, queryset):
        """Bulk action to unpublish multiple quizzes at once."""
        for quiz in queryset:
            quiz.unpublish()
        self.message_user(request, f'{queryset.count()} quizzes have been unpublished.')
    unpublish_quizzes.short_description = "Unpublish selected quizzes"


@admin.register(QuizQuestion)
class QuizQuestionAdmin(admin.ModelAdmin):
    list_display = ('__str__', 'quiz', 'question_type', 'points', 'order')
    list_filter = ('question_type', 'quiz')
    search_fields = ('text', 'quiz__title')
    inlines = [QuizAnswerInline]


@admin.register(UserQuizAttempt)
class UserQuizAttemptAdmin(admin.ModelAdmin):
    list_display = ('user', 'quiz', 'score', 'is_passed', 'is_completed', 'start_time', 'end_time')
    list_filter = ('is_passed', 'is_completed', 'start_time')
    search_fields = ('user__username', 'quiz__title')
    date_hierarchy = 'start_time'
    readonly_fields = ('score', 'is_passed', 'start_time', 'end_time')


@admin.register(UserQuestionResponse)
class UserQuestionResponseAdmin(admin.ModelAdmin):
    list_display = ('attempt', 'question', 'selected_answer', 'is_correct', 'points_earned')
    list_filter = ('is_correct',)
    search_fields = ('attempt__user__username', 'question__text')
    readonly_fields = ('is_correct', 'points_earned') 