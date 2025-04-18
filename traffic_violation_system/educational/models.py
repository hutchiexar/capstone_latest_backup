from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
import os

def topic_attachment_path(instance, filename):
    """Generate a unique path for each attachment file."""
    return f"educational/attachments/{instance.topic.id}/{filename}"

def question_image_path(instance, filename):
    """Generate a unique path for each question image file."""
    # Ensure filename is unique by adding a timestamp if needed
    base, ext = os.path.splitext(filename)
    return f"educational/questions/{instance.quiz.id}/{base}{ext}"

class EducationalCategory(models.Model):
    title = models.CharField(max_length=100)
    description = models.TextField(blank=True, null=True)
    order = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name_plural = "Educational Categories"
        ordering = ['order', 'title']

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

# Quiz Models
class Quiz(models.Model):
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True, null=True)
    topic = models.ForeignKey(EducationalTopic, on_delete=models.SET_NULL, null=True, blank=True, related_name='quizzes')
    passing_score = models.PositiveIntegerField(default=70, help_text="Minimum percentage required to pass")
    is_published = models.BooleanField(default=False)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='created_quizzes')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name_plural = "Quizzes"
        ordering = ['-created_at']
    
    def __str__(self):
        return self.title
    
    def publish(self):
        self.is_published = True
        self.save()
    
    def unpublish(self):
        self.is_published = False
        self.save()
    
    def get_total_points(self):
        return sum(question.points for question in self.questions.all())

class QuizQuestion(models.Model):
    QUESTION_TYPE_CHOICES = (
        ('MULTIPLE_CHOICE', 'Multiple Choice'),
        ('TRUE_FALSE', 'True/False'),
    )
    
    quiz = models.ForeignKey('Quiz', on_delete=models.CASCADE, related_name='questions')
    text = models.TextField()
    question_type = models.CharField(max_length=20, choices=QUESTION_TYPE_CHOICES, default='MULTIPLE_CHOICE')
    points = models.PositiveIntegerField(default=1)
    order = models.PositiveIntegerField(default=0)
    image = models.ImageField(upload_to=question_image_path, null=True, blank=True)
    
    class Meta:
        ordering = ['order']
    
    def __str__(self):
        return f"{self.quiz.title} - Question {self.order}"

class QuizAnswer(models.Model):
    question = models.ForeignKey(QuizQuestion, on_delete=models.CASCADE, related_name='answers')
    text = models.CharField(max_length=255)
    is_correct = models.BooleanField(default=False)
    explanation = models.TextField(blank=True, null=True, help_text="Explanation for why this answer is correct/incorrect")
    
    def __str__(self):
        return f"{self.question} - {self.text[:30]}"

class UserQuizAttempt(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='quiz_attempts')
    quiz = models.ForeignKey(Quiz, on_delete=models.CASCADE, related_name='attempts')
    start_time = models.DateTimeField(auto_now_add=True)
    end_time = models.DateTimeField(null=True, blank=True)
    score = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    is_passed = models.BooleanField(null=True, blank=True)
    is_completed = models.BooleanField(default=False)
    
    class Meta:
        ordering = ['-start_time']
    
    def __str__(self):
        return f"{self.user.username} - {self.quiz.title} - {self.start_time.strftime('%Y-%m-%d %H:%M')}"
    
    def calculate_score(self):
        """Calculate the score based on the user's responses"""
        if not self.is_completed:
            return None
            
        total_points = self.quiz.get_total_points()
        if total_points == 0:
            return 0
            
        earned_points = sum(response.points_earned for response in self.responses.all())
        score_percentage = (earned_points / total_points) * 100
        self.score = score_percentage
        self.is_passed = score_percentage >= self.quiz.passing_score
        self.save()
        return self.score
    
    def complete(self):
        """Mark the quiz attempt as completed and calculate the score."""
        self.is_completed = True
        self.end_time = timezone.now()
        self.calculate_score()
        self.save()

class UserQuestionResponse(models.Model):
    attempt = models.ForeignKey(UserQuizAttempt, on_delete=models.CASCADE, related_name='responses')
    question = models.ForeignKey(QuizQuestion, on_delete=models.CASCADE)
    selected_answer = models.ForeignKey(QuizAnswer, on_delete=models.CASCADE)
    is_correct = models.BooleanField(default=False)
    points_earned = models.PositiveIntegerField(default=0)
    
    class Meta:
        unique_together = ('attempt', 'question')
    
    def __str__(self):
        return f"{self.attempt.user.username} - {self.question.text[:30]}"
    
    def save(self, *args, **kwargs):
        # Auto-calculate if the answer is correct
        self.is_correct = self.selected_answer.is_correct
        # Award points if correct
        self.points_earned = self.question.points if self.is_correct else 0
        super().save(*args, **kwargs) 