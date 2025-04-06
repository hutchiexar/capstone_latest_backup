from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone

def topic_attachment_path(instance, filename):
    """Generate a unique path for each attachment file."""
    return f"educational/attachments/{instance.topic.id}/{filename}"

class EducationalCategory(models.Model):
    title = models.CharField(max_length=100)
    description = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name_plural = "Educational Categories"
        ordering = ['title']

    def __str__(self):
        return self.title

class EducationalTopic(models.Model):
    title = models.CharField(max_length=200)
    content = models.TextField()
    category = models.ForeignKey(EducationalCategory, on_delete=models.CASCADE, related_name='topics')
    is_published = models.BooleanField(default=False)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='created_topics')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True, null=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return self.title
    
    def publish(self):
        self.is_published = True
        self.save()
    
    def unpublish(self):
        self.is_published = False
        self.save()

class TopicAttachment(models.Model):
    FILE_TYPE_CHOICES = (
        ('PDF', 'PDF Document'),
        ('IMAGE', 'Image'),
        ('VIDEO', 'Video'),
        ('OTHER', 'Other'),
    )
    
    topic = models.ForeignKey(EducationalTopic, on_delete=models.CASCADE, related_name='attachments')
    file = models.FileField(upload_to=topic_attachment_path)
    file_type = models.CharField(max_length=10, choices=FILE_TYPE_CHOICES, default='OTHER')
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return self.title

    def get_file_type_display(self):
        return dict(self.FILE_TYPE_CHOICES).get(self.file_type, 'Unknown')

class UserBookmark(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='bookmarks')
    topic = models.ForeignKey(EducationalTopic, on_delete=models.CASCADE, related_name='bookmarked_by')
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
        unique_together = ('user', 'topic')
    
    def __str__(self):
        return f"{self.user.username} - {self.topic.title}"

class UserProgress(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='progress')
    topic = models.ForeignKey(EducationalTopic, on_delete=models.CASCADE, related_name='user_progress')
    is_completed = models.BooleanField(default=False)
    last_accessed = models.DateTimeField(default=timezone.now)
    completed_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        verbose_name_plural = "User Progress"
        ordering = ['-last_accessed']
        unique_together = ('user', 'topic')
    
    def __str__(self):
        return f"{self.user.username} - {self.topic.title}"
    
    def mark_completed(self):
        self.is_completed = True
        self.completed_at = timezone.now()
        self.save() 