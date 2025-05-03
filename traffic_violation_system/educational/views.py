from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth.decorators import user_passes_test
from django.http import JsonResponse, HttpResponseRedirect
from django.urls import reverse
from django.utils import timezone
from django.contrib import messages
from django.db.models import Count, Q, Prefetch, Sum, Avg, F, Max, Case, When, Value, IntegerField
from .models import EducationalCategory, EducationalTopic, TopicAttachment, UserBookmark, UserProgress, Quiz, QuizQuestion, QuizAnswer, UserQuizAttempt, UserQuestionResponse
from django.views.decorators.http import require_http_methods, require_POST
from PyPDF2 import PdfReader
import io
import tempfile
import os
import base64
from PIL import Image
from django.core.paginator import Paginator
from django.conf import settings

from .decorators import educator_required

# Helper function to check if a user is an admin or educator
def is_admin(user):
    return user.is_superuser or (hasattr(user, 'userprofile') and user.userprofile.role in ['ADMIN', 'EDUCATOR'])

# Helper function to check if a user is an educator
def is_educator(user):
    return hasattr(user, 'userprofile') and user.userprofile.role == 'EDUCATOR'

# Admin views
@login_required
@educator_required
def admin_educational_dashboard(request):
    categories_count = EducationalCategory.objects.count()
    topics_count = EducationalTopic.objects.count()
    published_topics = EducationalTopic.objects.filter(is_published=True).count()
    draft_topics = topics_count - published_topics
    recent_topics = EducationalTopic.objects.all().order_by('-created_at')[:5]
    
    context = {
        'categories_count': categories_count,
        'topics_count': topics_count,
        'published_topics': published_topics,
        'draft_topics': draft_topics,
        'recent_topics': recent_topics,
    }
    return render(request, 'admin/educational/dashboard.html', context)


@login_required
@educator_required
def admin_category_list(request):
    categories = EducationalCategory.objects.all().annotate(topics_count=Count('topics'))
    context = {
        'categories': categories
    }
    return render(request, 'admin/educational/category_list.html', context)


@login_required
@educator_required
def admin_category_create(request):
    if request.method == 'POST':
        title = request.POST.get('title')
        description = request.POST.get('description')
        order = request.POST.get('order', 0)
        
        if not title:
            messages.error(request, 'Title is required')
            return redirect('educational:admin_category_create')
        
        category = EducationalCategory.objects.create(
            title=title,
            description=description,
            order=order
        )
        
        messages.success(request, f'Category "{category.title}" created successfully')
        return redirect('educational:admin_category_list')
    
    return render(request, 'admin/educational/category_form.html')


@login_required
@educator_required
def admin_category_edit(request, category_id):
    category = get_object_or_404(EducationalCategory, id=category_id)
    
    if request.method == 'POST':
        title = request.POST.get('title')
        description = request.POST.get('description')
        order = request.POST.get('order', category.order)
        
        if not title:
            messages.error(request, 'Title is required')
            return redirect('educational:admin_category_edit', category_id=category.id)
        
        category.title = title
        category.description = description
        category.order = order
        category.save()
        
        messages.success(request, f'Category "{category.title}" updated successfully')
        return redirect('educational:admin_category_list')
    
    context = {
        'category': category,
        'is_edit': True
    }
    return render(request, 'admin/educational/category_form.html', context)


@login_required
@educator_required
def admin_category_delete(request, category_id):
    category = get_object_or_404(EducationalCategory, id=category_id)
    
    if request.method == 'POST':
        category_title = category.title
        category.delete()
        messages.success(request, f'Category "{category_title}" deleted successfully')
        return redirect('educational:admin_category_list')
    
    context = {
        'category': category
    }
    return render(request, 'admin/educational/category_delete.html', context)


@login_required
@educator_required
def admin_topic_list(request):
    topics = EducationalTopic.objects.all().select_related('category', 'created_by')
    
    # Filter by status
    status_filter = request.GET.get('status')
    if status_filter == 'published':
        topics = topics.filter(is_published=True)
    elif status_filter == 'draft':
        topics = topics.filter(is_published=False)
    
    # Filter by category
    category_filter = request.GET.get('category')
    if category_filter:
        topics = topics.filter(category_id=category_filter)
    
    # Search functionality
    search_query = request.GET.get('q')
    if search_query:
        topics = topics.filter(
            Q(title__icontains=search_query) | 
            Q(content__icontains=search_query)
        )
    
    categories = EducationalCategory.objects.all()
    
    context = {
        'topics': topics,
        'categories': categories,
        'status_filter': status_filter,
        'category_filter': category_filter,
        'search_query': search_query
    }
    return render(request, 'admin/educational/topic_list.html', context)


@login_required
@educator_required
def admin_topic_create(request):
    categories = EducationalCategory.objects.all()
    
    if request.method == 'POST':
        title = request.POST.get('title')
        category_id = request.POST.get('category')
        content = request.POST.get('content')
        # Default to True if the checkbox doesn't exist at all (for backward compatibility)
        is_published = request.POST.get('is_published', 'on') == 'on'
        
        if not title or not category_id or not content:
            messages.error(request, 'Title, category, and content are required')
            return redirect('educational:admin_topic_create')
        
        category = get_object_or_404(EducationalCategory, id=category_id)
        
        topic = EducationalTopic.objects.create(
            title=title,
            category=category,
            content=content,
            is_published=is_published,
            created_by=request.user
        )
        
        # Process attachments
        files = request.FILES.getlist('attachments')
        for file in files:
            file_type = 'OTHER'
            file_name = file.name.lower()
            
            if file_name.endswith('.pdf'):
                file_type = 'PDF'
            elif file_name.endswith(('.jpg', '.jpeg', '.png', '.gif')):
                file_type = 'IMAGE'
            elif file_name.endswith(('.mp4', '.avi', '.mov', '.wmv')):
                file_type = 'VIDEO'
            
            TopicAttachment.objects.create(
                topic=topic,
                file=file,
                file_type=file_type,
                title=file.name
            )
        
        # Add a message about the publish status
        if is_published:
            messages.success(request, f'Topic "{topic.title}" created and published successfully')
        else:
            messages.success(request, f'Topic "{topic.title}" saved as draft')
            
        return redirect('educational:admin_topic_list')
    
    context = {
        'categories': categories
    }
    return render(request, 'admin/educational/topic_form.html', context)


@login_required
@educator_required
def admin_topic_edit(request, topic_id):
    topic = get_object_or_404(EducationalTopic, id=topic_id)
    categories = EducationalCategory.objects.all()
    attachments = TopicAttachment.objects.filter(topic=topic)
    
    if request.method == 'POST':
        title = request.POST.get('title')
        category_id = request.POST.get('category')
        content = request.POST.get('content')
        is_published = request.POST.get('is_published') == 'on'
        
        if not title or not category_id or not content:
            messages.error(request, 'Title, category, and content are required')
            return redirect('educational:admin_topic_edit', topic_id=topic.id)
        
        category = get_object_or_404(EducationalCategory, id=category_id)
        
        # Check if publish status changed
        publish_status_changed = topic.is_published != is_published
        old_status = topic.is_published
        
        # Update topic
        topic.title = title
        topic.category = category
        topic.content = content
        topic.is_published = is_published
        topic.save()
        
        # Handle attachment deletions
        attachments_to_delete = request.POST.getlist('delete_attachment')
        if attachments_to_delete:
            TopicAttachment.objects.filter(id__in=attachments_to_delete).delete()
        
        # Process new attachments
        files = request.FILES.getlist('attachments')
        for file in files:
            file_type = 'OTHER'
            file_name = file.name.lower()
            
            if file_name.endswith('.pdf'):
                file_type = 'PDF'
            elif file_name.endswith(('.jpg', '.jpeg', '.png', '.gif')):
                file_type = 'IMAGE'
            elif file_name.endswith(('.mp4', '.avi', '.mov', '.wmv')):
                file_type = 'VIDEO'
            
            TopicAttachment.objects.create(
                topic=topic,
                file=file,
                file_type=file_type,
                title=file.name
            )
        
        # Add a message about the publish status change
        if publish_status_changed:
            if is_published:
                messages.success(request, f'Topic "{topic.title}" has been published and is now visible to users')
            else:
                messages.success(request, f'Topic "{topic.title}" has been unpublished and is now saved as a draft')
        else:
            messages.success(request, f'Topic "{topic.title}" updated successfully')
            
        return redirect('educational:admin_topic_list')
    
    context = {
        'topic': topic,
        'categories': categories,
        'attachments': attachments,
        'is_edit': True
    }
    return render(request, 'admin/educational/topic_form.html', context)


@login_required
@educator_required
def admin_topic_delete(request, topic_id):
    topic = get_object_or_404(EducationalTopic, id=topic_id)
    
    if request.method == 'POST':
        topic_title = topic.title
        topic.delete()
        
        # Check if request is AJAX/JSON
        if request.headers.get('Content-Type') == 'application/json':
            return JsonResponse({
                'success': True,
                'message': f'Topic "{topic_title}" deleted successfully'
            })
        
        messages.success(request, f'Topic "{topic_title}" deleted successfully')
        return redirect('educational:admin_topic_list')
    
    # If this is a GET request, we're still supporting the old way for backward compatibility
    context = {
        'topic': topic
    }
    return render(request, 'admin/educational/topic_delete.html', context)


@login_required
@educator_required
def admin_topic_publish(request, topic_id):
    topic = get_object_or_404(EducationalTopic, id=topic_id)
    
    topic.is_published = not topic.is_published
    topic.save()
    
    status = "published" if topic.is_published else "unpublished"
    messages.success(request, f'Topic "{topic.title}" {status} successfully')
    
    return redirect('educational:admin_topic_list')


@login_required
@educator_required
def admin_topic_preview(request, topic_id):
    topic = get_object_or_404(EducationalTopic, id=topic_id)
    attachments = TopicAttachment.objects.filter(topic=topic)
    
    context = {
        'topic': topic,
        'attachments': attachments,
        'is_preview': True
    }
    return render(request, 'admin/educational/topic_preview.html', context)


# User views
@login_required
def topic_list(request):
    """
    Display a list of all published educational topics.
    Filter by category if provided.
    """
    category_id = request.GET.get('category')
    
    # Get all published topics
    topics = EducationalTopic.objects.filter(is_published=True)
    
    # Filter by category if specified
    selected_category = None
    if category_id:
        try:
            selected_category = EducationalCategory.objects.get(id=category_id)
            topics = topics.filter(category=selected_category)
        except EducationalCategory.DoesNotExist:
            pass
    
    # Order topics by created date (newest first)
    topics = topics.order_by('-created_at')
    
    # Get user's bookmarked topics
    bookmarked_topics = UserBookmark.objects.filter(
        user=request.user
    ).values_list('topic_id', flat=True)
    
    # Get user's completed and in-progress topics
    user_progress = UserProgress.objects.filter(
        user=request.user
    )
    
    completed_topics = user_progress.filter(
        is_completed=True
    ).values_list('topic_id', flat=True)
    
    in_progress_topics = user_progress.filter(
        is_completed=False
    ).values_list('topic_id', flat=True)
    
    # Get all categories for navigation
    categories = EducationalCategory.objects.filter(
        topics__is_published=True
    ).distinct().order_by('title')
    
    context = {
        'topics': topics,
        'selected_category': selected_category,
        'categories': categories,
        'bookmarked_topics': bookmarked_topics,
        'completed_topics': completed_topics,
        'in_progress_topics': in_progress_topics,
        'active_page': 'education',
    }
    
    return render(request, 'user_portal/educational/topic_list.html', context)


@login_required
def topic_detail(request, topic_id):
    """
    Display details of a specific educational topic.
    """
    # Get topic or return 404
    topic = get_object_or_404(EducationalTopic, id=topic_id, is_published=True)
    
    # Get all categories for sidebar navigation
    categories = EducationalCategory.objects.all().order_by('title')
    
    # Check if topic is bookmarked by user
    is_bookmarked = False
    if request.user.is_authenticated:
        is_bookmarked = UserBookmark.objects.filter(
            user=request.user, 
            topic=topic
        ).exists()
    
    # Check if topic is completed by user
    is_completed = False
    if request.user.is_authenticated:
        is_completed = UserProgress.objects.filter(
            user=request.user, 
            topic=topic,
            is_completed=True
        ).exists()
    
    # Get related topics
    related_topics = EducationalTopic.objects.filter(
        category=topic.category, 
        is_published=True
    ).exclude(id=topic.id)[:5]
    
    # Track progress automatically
    if request.user.is_authenticated:
        # Check if already viewed
        viewed, created = UserProgress.objects.get_or_create(
            user=request.user,
            topic=topic,
            defaults={'last_accessed': timezone.now()}
        )
        if not created:
            # Update last viewed
            viewed.last_accessed = timezone.now()
            viewed.save()
    
    # Check for PDF attachment to show in viewer
    is_pdf_content = False
    pdf_url = None
    pdf_attachments = topic.attachments.filter(file_type='PDF')
    if pdf_attachments.exists():
        # If a PDF is attached, set flag to use PDF viewer instead of regular content display
        is_pdf_content = True
        pdf_url = pdf_attachments.first().file.url
    
    context = {
        'topic': topic,
        'categories': categories,
        'is_bookmarked': is_bookmarked,
        'is_completed': is_completed,
        'related_topics': related_topics,
        'attachments': topic.attachments.all(),
        'is_pdf_content': is_pdf_content,
        'pdf_url': pdf_url,
    }
    
    return render(request, 'user_portal/educational/topic_detail.html', context)


@login_required
def toggle_bookmark(request, topic_id):
    """
    Toggle bookmark status for a topic.
    Returns JSON response for AJAX requests.
    """
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)
    
    try:
        topic = EducationalTopic.objects.get(id=topic_id, is_published=True)
        bookmark, created = UserBookmark.objects.get_or_create(
            user=request.user,
            topic=topic
        )
        
        # If bookmark existed and we didn't create a new one, delete it
        if not created:
            bookmark.delete()
            return JsonResponse({
                'status': 'removed',
                'message': 'Bookmark removed successfully'
            })
        
        return JsonResponse({
            'status': 'added',
            'message': 'Topic bookmarked successfully'
        })
    except EducationalTopic.DoesNotExist:
        return JsonResponse({'error': 'Topic not found'}, status=404)


@login_required
def mark_as_completed(request, topic_id):
    topic = get_object_or_404(EducationalTopic, id=topic_id, is_published=True)
    
    # Get or create user progress
    progress, created = UserProgress.objects.get_or_create(
        user=request.user,
        topic=topic,
        defaults={'last_accessed': timezone.now(), 'is_completed': True, 'completed_at': timezone.now()}
    )
    
    # Toggle completion status if not created
    if not created:
        progress.is_completed = not progress.is_completed
        if progress.is_completed:
            progress.completed_at = timezone.now()
        else:
            progress.completed_at = None
        progress.save()
    
    # Return JSON if AJAX request
    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        return JsonResponse({
            'success': True,
            'is_completed': progress.is_completed
        })
    
    action = 'marked as completed' if progress.is_completed else 'marked as incomplete'
    messages.success(request, f'Topic "{topic.title}" {action}')
    
    return HttpResponseRedirect(request.META.get('HTTP_REFERER', reverse('educational:topic_list')))


@login_required
def user_bookmarks(request):
    bookmarks = UserBookmark.objects.filter(user=request.user).select_related('topic', 'topic__category')
    
    # Get user progress for bookmarked topics
    user_progress = {}
    topic_ids = [b.topic.id for b in bookmarks]
    progress_objects = UserProgress.objects.filter(user=request.user, topic_id__in=topic_ids)
    user_progress = {p.topic_id: p.is_completed for p in progress_objects}
    
    # Add progress info to bookmarks
    bookmarks_with_meta = []
    for bookmark in bookmarks:
        bookmark_dict = {
            'bookmark': bookmark,
            'is_completed': user_progress.get(bookmark.topic.id, False)
        }
        bookmarks_with_meta.append(bookmark_dict)
    
    context = {
        'bookmarks': bookmarks_with_meta
    }
    return render(request, 'user_portal/educational/bookmarks.html', context)


@login_required
def user_progress(request):
    """Display the user's learning progress for educational topics."""
    # Get all user progress records
    completed_topics = UserProgress.objects.filter(
        user=request.user,
        is_completed=True
    ).select_related('topic', 'topic__category').order_by('-completed_at')
    
    in_progress_topics = UserProgress.objects.filter(
        user=request.user,
        is_completed=False
    ).select_related('topic', 'topic__category').order_by('-last_accessed')
    
    # Calculate statistics
    total_count = EducationalTopic.objects.filter(is_published=True).count()
    completed_count = completed_topics.count()
    in_progress_count = in_progress_topics.count()
    
    completion_percentage = 0
    if total_count > 0:
        completion_percentage = int((completed_count / total_count) * 100)
    
    stats = {
        'total_count': total_count,
        'completed_count': completed_count,
        'in_progress_count': in_progress_count,
        'completion_percentage': completion_percentage
    }
    
    context = {
        'completed_topics': completed_topics,
        'in_progress_topics': in_progress_topics,
        'stats': stats
    }
    return render(request, 'user_portal/educational/my_progress.html', context)


@login_required
def landing_page(request):
    """
    Display a landing page for educational materials with categories.
    """
    # Get all published categories with at least one published topic
    categories = EducationalCategory.objects.filter(
        topics__is_published=True
    ).distinct().order_by('title')
    
    return render(request, 'user_portal/educational/landing_page.html', {
        'categories': categories,
        'active_page': 'education',
    })


@login_required
def get_topic(request, topic_id):
    """API endpoint to get topic data for modal display"""
    try:
        topic = EducationalTopic.objects.get(id=topic_id, is_published=True)
        
        # Get attachments data
        attachments = []
        for attachment in topic.attachments.all():
            attachments.append({
                'id': attachment.id,
                'title': attachment.title,
                'description': attachment.description,
                'file_type': attachment.get_file_type_display(),
                'file': attachment.file.url,
                'size': attachment.get_file_size_display()
            })
        
        return JsonResponse({
            'id': topic.id,
            'title': topic.title,
            'content': topic.content,
            'category': {
                'id': topic.category.id,
                'title': topic.category.title
            },
            'attachments': attachments,
            'created_at': topic.created_at.strftime('%b %d, %Y')
        })
    except EducationalTopic.DoesNotExist:
        return JsonResponse({'error': 'Topic not found'}, status=404)

@login_required
def mark_completed(request, topic_id):
    """API endpoint to mark a topic as completed"""
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)
    
    try:
        topic = EducationalTopic.objects.get(id=topic_id, is_published=True)
        
        # Get or create user progress
        user_progress, created = UserProgress.objects.get_or_create(
            user=request.user,
            topic=topic,
            defaults={'is_completed': True, 'completed_at': timezone.now()}
        )
        
        # If not created, update the progress
        if not created and not user_progress.is_completed:
            user_progress.is_completed = True
            user_progress.completed_at = timezone.now()
            user_progress.save()
        
        return JsonResponse({
            'status': 'completed',
            'message': 'Topic marked as completed successfully'
        })
    except EducationalTopic.DoesNotExist:
        return JsonResponse({'error': 'Topic not found'}, status=404)

@login_required
def track_progress(request, topic_id):
    """API endpoint to track a user's progress on a topic"""
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)
    
    try:
        topic = EducationalTopic.objects.get(id=topic_id, is_published=True)
        
        # Get or create user progress
        user_progress, created = UserProgress.objects.get_or_create(
            user=request.user,
            topic=topic,
            defaults={'last_accessed': timezone.now()}
        )
        
        # If not created, update the last accessed timestamp
        if not created:
            user_progress.last_accessed = timezone.now()
            user_progress.save()
        
        return JsonResponse({
            'status': 'success',
            'message': 'Progress tracked successfully'
        })
    except EducationalTopic.DoesNotExist:
        return JsonResponse({'error': 'Topic not found'}, status=404)

@login_required
def get_category_topics(request):
    """API endpoint to get all topics for a specific category"""
    category_id = request.GET.get('category')
    
    if not category_id:
        return JsonResponse({'error': 'Category ID is required'}, status=400)
    
    try:
        category = EducationalCategory.objects.get(id=category_id)
        topics = EducationalTopic.objects.filter(
            category=category,
            is_published=True
        ).order_by('-created_at')
        
        topics_data = []
        for topic in topics:
            topics_data.append({
                'id': topic.id,
                'title': topic.title,
                'created_at': topic.created_at.strftime('%b %d, %Y')
            })
        
        return JsonResponse({
            'category': {
                'id': category.id,
                'title': category.title,
                'description': category.description
            },
            'topics': topics_data
        })
    except EducationalCategory.DoesNotExist:
        return JsonResponse({'error': 'Category not found'}, status=404)

@staff_member_required
def admin_index(request):
    """
    Display the educational dashboard for administrators.
    Shows statistics and summary of educational content.
    """
    # Get counts
    total_categories = EducationalCategory.objects.count()
    total_topics = EducationalTopic.objects.count()
    published_topics = EducationalTopic.objects.filter(is_published=True).count()
    draft_topics = total_topics - published_topics
    
    # Get recent topics
    recent_topics = EducationalTopic.objects.order_by('-created_at')[:5]
    
    # Get popular topics (based on progress)
    popular_topics = EducationalTopic.objects.annotate(
        view_count=Count('user_progress')
    ).order_by('-view_count')[:5]
    
    # Get categories with topic counts
    categories = EducationalCategory.objects.annotate(
        topic_count=Count('topics')
    ).order_by('-topic_count')
    
    context = {
        'total_categories': total_categories,
        'total_topics': total_topics,
        'published_topics': published_topics,
        'draft_topics': draft_topics,
        'recent_topics': recent_topics,
        'popular_topics': popular_topics,
        'categories': categories,
    }
    
    return render(request, 'admin/educational/dashboard.html', context)

@login_required
@educator_required
def admin_educational_data(request):
    """
    Comprehensive admin view that displays all educational data (topics, categories, attachments)
    in a unified, tabbed interface with search and filtering capabilities.
    """
    # Get all data with related objects to minimize database queries
    topics = EducationalTopic.objects.all().select_related('category', 'created_by')
    categories = EducationalCategory.objects.all().annotate(topics_count=Count('topics'))
    attachments = TopicAttachment.objects.all().select_related('topic')
    
    # Filter by status
    status_filter = request.GET.get('status')
    if status_filter == 'published':
        topics = topics.filter(is_published=True)
    elif status_filter == 'draft':
        topics = topics.filter(is_published=False)
    
    # Filter by category
    category_filter = request.GET.get('category')
    if category_filter:
        topics = topics.filter(category_id=category_filter)
        attachments = attachments.filter(topic__category_id=category_filter)
    
    # Search functionality
    search_query = request.GET.get('q')
    if search_query:
        topics = topics.filter(
            Q(title__icontains=search_query) | 
            Q(content__icontains=search_query)
        )
        categories = categories.filter(
            Q(title__icontains=search_query) | 
            Q(description__icontains=search_query)
        )
        attachments = attachments.filter(
            Q(title__icontains=search_query) | 
            Q(description__icontains=search_query) |
            Q(topic__title__icontains=search_query)
        )
    
    # Get the active tab
    tab = request.GET.get('tab', 'all-data')
    
    context = {
        'topics': topics,
        'categories': categories,
        'attachments': attachments,
        'status_filter': status_filter,
        'category_filter': category_filter,
        'search_query': search_query,
        'tab': tab
    }
    return render(request, 'admin/educational/admin_educational_data.html', context)

@login_required
@educator_required
@require_http_methods(["POST"])
def extract_pdf_text(request):
    try:
        print("PDF extraction request received")
        pdf_file = request.FILES.get('pdf_file')
        if not pdf_file:
            print("No file uploaded")
            return JsonResponse({
                'success': False,
                'error': 'No file uploaded'
            })
            
        if not pdf_file.name.lower().endswith('.pdf'):
            print(f"Invalid file type: {pdf_file.name}")
            return JsonResponse({
                'success': False,
                'error': 'Please upload a valid PDF file'
            })

        print(f"Processing PDF file: {pdf_file.name}")
        
        # Read the PDF file as bytes
        try:
            import fitz  # PyMuPDF
            
            pdf_bytes = pdf_file.read()
            
            # Set a reasonable page limit to avoid heavy processing
            MAX_PAGES = 10
            
            # Extract page images with lower resolution to save storage
            page_images = []
            
            # Process each page
            for page_num in range(MAX_PAGES):
                try:
                    # Open a new document instance for each page to avoid "document closed" errors
                    pdf_document = fitz.open(stream=pdf_bytes, filetype="pdf")
                    
                    # Check if we've reached the end of the document
                    if page_num >= len(pdf_document):
                        break
                            
                    print(f"Processing page {page_num + 1} of {len(pdf_document)}")
                    page = pdf_document[page_num]
                    
                    # Set resolution to a lower value (100 DPI instead of 300)
                    matrix = fitz.Matrix(1.0, 1.0)  # Scaling factor for 100 DPI
                    pix = page.get_pixmap(matrix=matrix)
                    
                    # Convert to JPEG using a temporary file (better compression than PNG)
                    with tempfile.NamedTemporaryFile(delete=False, suffix=".jpg") as temp_file:
                        temp_filename = temp_file.name
                    
                    # Save the pixmap to the temporary file as JPEG
                    success = False
                    try:
                        pix.save(temp_filename, "jpeg", quality=70)  # Lower quality for better compression
                        success = True
                    except TypeError:
                        # Fallback if JPEG with quality parameter is not supported
                        try:
                            pix.save(temp_filename, "jpeg")  # Try without quality parameter
                            success = True
                        except:
                            try:
                                pix.save(temp_filename)  # Try with default format
                                success = True
                            except Exception as e:
                                print(f"All PyMuPDF save methods failed: {str(e)}")
                    
                    # If PyMuPDF save failed, try using PIL as a fallback
                    if not success:
                        try:
                            # Get pixmap dimensions and samples
                            img_array = pix.samples
                            width, height = pix.width, pix.height
                            
                            # Convert pixmap to PIL Image
                            mode = "RGBA" if pix.alpha else "RGB"
                            img = Image.frombytes(mode, [width, height], img_array)
                            
                            # Save using PIL instead
                            img.save(temp_filename, format="JPEG", quality=70)
                            print("Successfully saved using PIL fallback")
                        except Exception as e:
                            print(f"PIL fallback also failed: {str(e)}")
                            # Continue to next page instead of failing the whole process
                            pdf_document.close()
                            continue
                    
                    # Read the file back
                    with open(temp_filename, "rb") as f:
                        img_bytes = f.read()
                    
                    # Delete the temporary file
                    os.unlink(temp_filename)
                    
                    # Convert to base64 for sending to browser
                    img_base64 = base64.b64encode(img_bytes).decode('utf-8')
                    
                    # Also extract text for each page for search/accessibility
                    text = page.get_text()
                    
                    page_images.append({
                        'page': page_num + 1,
                        'data': img_base64,
                        'text': text
                    })
                    
                    print(f"Processed page {page_num + 1}, image size: {len(img_base64) // 1024}KB")
                    
                    # Close the document for this iteration
                    pdf_document.close()
                    
                except Exception as e:
                    print(f"Error processing page {page_num + 1}: {str(e)}")
                    # Make sure to close the document even if there's an error
                    try:
                        if 'pdf_document' in locals() and pdf_document:
                            pdf_document.close()
                    except:
                        pass
                    continue
            
            if not page_images:
                print("No pages could be rendered from the PDF")
                return JsonResponse({
                    'success': False,
                    'error': 'No pages could be rendered from the PDF'
                })
            
            print(f"Successfully rendered {len(page_images)} pages from PDF")
            
            # Get the total pages from a fresh document
            try:
                temp_doc = fitz.open(stream=pdf_bytes, filetype="pdf")
                total_pages = len(temp_doc)
                temp_doc.close()
            except:
                total_pages = len(page_images)
                    
            return JsonResponse({
                'success': True,
                'images': page_images,
                'total_pages': total_pages,
                'pages_rendered': len(page_images)
            })
            
        except ImportError as e:
            print(f"Error importing PyMuPDF: {str(e)}")
            return JsonResponse({
                'success': False,
                'error': 'PyMuPDF not installed. Please install it with: pip install pymupdf'
            })
        except Exception as e:
            print(f"Error processing PDF: {str(e)}")
            return JsonResponse({
                'success': False,
                'error': f'Error processing PDF: {str(e)}'
            })
            
    except Exception as e:
        print(f"Error during PDF processing: {str(e)}")
        return JsonResponse({
            'success': False,
            'error': f'Error processing PDF: {str(e)}'
        })

# Quiz Views - Admin

@login_required
@educator_required
def admin_quiz_list(request):
    """View for admins to see all quizzes."""
    if not request.user.is_staff:
        messages.error(request, "You don't have permission to access this page.")
        return redirect('educational:topic_list')
        
    quizzes = Quiz.objects.select_related('topic', 'created_by')
    
    # Filter by search query
    query = request.GET.get('q')
    if query:
        quizzes = quizzes.filter(
            Q(title__icontains=query) | 
            Q(description__icontains=query) |
            Q(topic__title__icontains=query)
        )
    
    # Filter by topic
    topic_id = request.GET.get('topic')
    if topic_id:
        quizzes = quizzes.filter(topic_id=topic_id)
    
    # Filter by status
    status = request.GET.get('status')
    if status == 'published':
        quizzes = quizzes.filter(is_published=True)
    elif status == 'draft':
        quizzes = quizzes.filter(is_published=False)
    
    # Pagination
    paginator = Paginator(quizzes, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Get topics for filter dropdown
    topics = EducationalTopic.objects.filter(is_published=True).order_by('title')
    
    context = {
        'page_obj': page_obj,
        'topics': topics,
        'query': query,
        'selected_topic': topic_id,
        'selected_status': status,
        'total_count': quizzes.count(),
    }
    
    return render(request, 'educational/admin/quiz_list.html', context)

@login_required
@educator_required
def admin_quiz_detail(request, quiz_id):
    """View for admins to see quiz details, including questions and statistics."""
    if not request.user.is_staff:
        messages.error(request, "You don't have permission to access this page.")
        return redirect('educational:topic_list')
    
    quiz = get_object_or_404(Quiz.objects.select_related('topic', 'created_by'), pk=quiz_id)
    
    # Get questions with answers
    questions = QuizQuestion.objects.filter(quiz=quiz).prefetch_related('answers').order_by('order')
    
    # Get quiz statistics
    total_attempts = UserQuizAttempt.objects.filter(quiz=quiz).count()
    completed_attempts = UserQuizAttempt.objects.filter(quiz=quiz, is_completed=True).count()
    passing_attempts = UserQuizAttempt.objects.filter(quiz=quiz, is_passed=True).count()
    
    avg_score = UserQuizAttempt.objects.filter(
        quiz=quiz, 
        is_completed=True
    ).aggregate(avg_score=Avg('score'))['avg_score'] or 0
    
    context = {
        'quiz': quiz,
        'questions': questions,
        'total_attempts': total_attempts,
        'completed_attempts': completed_attempts,
        'passing_attempts': passing_attempts,
        'passing_rate': (passing_attempts / completed_attempts * 100) if completed_attempts > 0 else 0,
        'avg_score': avg_score,
    }
    
    return render(request, 'educational/admin/quiz_detail.html', context)

@login_required
@educator_required
def admin_create_quiz(request):
    """View for admins to create a new quiz."""
    if not request.user.is_staff:
        messages.error(request, "You don't have permission to access this page.")
        return redirect('educational:topic_list')
    
    if request.method == 'POST':
        title = request.POST.get('title')
        description = request.POST.get('description', '')
        topic_id = request.POST.get('topic')
        passing_score = int(request.POST.get('passing_score', 70))
        
        if not title:
            messages.error(request, "Title is required.")
            return redirect('educational:admin_create_quiz')
        
        topic = None
        if topic_id:
            topic = get_object_or_404(EducationalTopic, pk=topic_id)
        
        quiz = Quiz.objects.create(
            title=title,
            description=description,
            topic=topic,
            passing_score=passing_score,
            created_by=request.user
        )
        
        messages.success(request, f"Quiz '{quiz.title}' has been created. Now add some questions.")
        return redirect('educational:admin_edit_quiz', quiz_id=quiz.id)
    
    # Get topics for dropdown
    topics = EducationalTopic.objects.filter(is_published=True).order_by('title')
    
    context = {
        'topics': topics,
    }
    
    return render(request, 'educational/admin/quiz_form.html', context)

@login_required
@educator_required
def admin_edit_quiz(request, quiz_id):
    """View for admins to edit an existing quiz."""
    if not request.user.is_staff:
        messages.error(request, "You don't have permission to access this page.")
        return redirect('educational:topic_list')
    
    quiz = get_object_or_404(Quiz, pk=quiz_id)
    
    if request.method == 'POST':
        title = request.POST.get('title')
        description = request.POST.get('description', '')
        topic_id = request.POST.get('topic')
        passing_score = int(request.POST.get('passing_score', 70))
        is_published = request.POST.get('is_published') == 'on'
        
        if not title:
            messages.error(request, "Title is required.")
            return redirect('educational:admin_edit_quiz', quiz_id=quiz.id)
        
        topic = None
        if topic_id:
            topic = get_object_or_404(EducationalTopic, pk=topic_id)
        
        quiz.title = title
        quiz.description = description
        quiz.topic = topic
        quiz.passing_score = passing_score
        quiz.is_published = is_published
        quiz.save()
        
        messages.success(request, f"Quiz '{quiz.title}' has been updated.")
        return redirect('educational:admin_quiz_detail', quiz_id=quiz.id)
    
    # Get questions with answers for this quiz
    questions = QuizQuestion.objects.filter(quiz=quiz).prefetch_related('answers').order_by('order')
    
    # Get topics for dropdown
    topics = EducationalTopic.objects.filter(is_published=True).order_by('title')
    
    context = {
        'quiz': quiz,
        'questions': questions,
        'topics': topics,
    }
    
    return render(request, 'educational/admin/quiz_form.html', context)

@login_required
@educator_required
def admin_add_question(request, quiz_id):
    """View for admins to add a question to a quiz."""
    if not request.user.is_staff:
        messages.error(request, "You don't have permission to access this page.")
        return redirect('educational:topic_list')
    
    quiz = get_object_or_404(Quiz, pk=quiz_id)
    
    if request.method == 'POST':
        text = request.POST.get('text')
        question_type = request.POST.get('question_type')
        points = int(request.POST.get('points', 1))
        image = request.FILES.get('image')
        
        if not text:
            messages.error(request, "Question text is required.")
            return redirect('educational:admin_add_question', quiz_id=quiz.id)
        
        # Get the next order number
        next_order = QuizQuestion.objects.filter(quiz=quiz).count() + 1
        
        question = QuizQuestion.objects.create(
            quiz=quiz,
            text=text,
            question_type=question_type,
            points=points,
            order=next_order,
            image=image
        )
        
        # For True/False questions, automatically create the two answer options
        if question_type == 'TRUE_FALSE':
            QuizAnswer.objects.create(
                question=question,
                text="True",
                is_correct=request.POST.get('correct_answer') == 'true'
            )
            QuizAnswer.objects.create(
                question=question,
                text="False",
                is_correct=request.POST.get('correct_answer') == 'false'
            )
            messages.success(request, "Question added with True/False options.")
            return redirect('educational:admin_edit_quiz', quiz_id=quiz.id)
        else:
            # Handle multiple choice options in a single submission
            option_texts = request.POST.getlist('option_text[]')
            option_explanations = request.POST.getlist('option_explanation[]')
            correct_option = int(request.POST.get('correct_option', 0))
            
            # Create answer options for multiple choice questions
            for i, text in enumerate(option_texts):
                if text.strip():  # Only add non-empty options
                    QuizAnswer.objects.create(
                        question=question,
                        text=text,
                        is_correct=(i == correct_option),
                        explanation=option_explanations[i] if i < len(option_explanations) else ''
                    )
            
            messages.success(request, "Question and answer options added successfully.")
            return redirect('educational:admin_edit_quiz', quiz_id=quiz.id)
    
    context = {
        'quiz': quiz,
    }
    
    return render(request, 'educational/admin/question_form.html', context)

@login_required
@educator_required
def admin_edit_question(request, question_id):
    """View for admins to edit a question and its answers."""
    if not request.user.is_staff:
        messages.error(request, "You don't have permission to access this page.")
        return redirect('educational:topic_list')
    
    question = get_object_or_404(QuizQuestion.objects.select_related('quiz'), pk=question_id)
    
    if request.method == 'POST':
        text = request.POST.get('text')
        question_type = request.POST.get('question_type')
        points = int(request.POST.get('points', 1))
        
        if not text:
            messages.error(request, "Question text is required.")
            return redirect('educational:admin_edit_question', question_id=question.id)
        
        # Handle image upload or removal
        if 'image' in request.FILES:
            # If there's a new image, use it
            question.image = request.FILES['image']
        elif request.POST.get('remove_image') == 'on' and question.image:
            # If remove_image is checked and there's an existing image, delete it
            question.image.delete()
            question.image = None
        
        question.text = text
        question.question_type = question_type
        question.points = points
        question.save()
        
        # Handle answer updates for True/False questions
        if question_type == 'TRUE_FALSE':
            correct_answer = request.POST.get('correct_answer')
            true_answer = QuizAnswer.objects.filter(question=question, text="True").first()
            false_answer = QuizAnswer.objects.filter(question=question, text="False").first()
            
            if true_answer and false_answer:
                true_answer.is_correct = correct_answer == 'true'
                false_answer.is_correct = correct_answer == 'false'
                true_answer.save()
                false_answer.save()
            else:
                # Create new True/False answers if they don't exist
                if not true_answer:
                    QuizAnswer.objects.create(
                        question=question,
                        text="True",
                        is_correct=correct_answer == 'true'
                    )
                if not false_answer:
                    QuizAnswer.objects.create(
                        question=question,
                        text="False",
                        is_correct=correct_answer == 'false'
                    )
        else:
            # Handle multiple choice options in a single submission
            option_texts = request.POST.getlist('option_text[]')
            option_explanations = request.POST.getlist('option_explanation[]')
            correct_option = int(request.POST.get('correct_option', 0))
            
            # Remove all existing answers for multiple choice
            QuizAnswer.objects.filter(question=question).delete()
            
            # Create new answer options
            for i, text in enumerate(option_texts):
                if text.strip():  # Only add non-empty options
                    QuizAnswer.objects.create(
                        question=question,
                        text=text,
                        is_correct=(i == correct_option),
                        explanation=option_explanations[i] if i < len(option_explanations) else ''
                    )
        
        messages.success(request, "Question updated successfully.")
        return redirect('educational:admin_edit_quiz', quiz_id=question.quiz.id)
    
    # Get answers for this question
    answers = QuizAnswer.objects.filter(question=question)
    
    # For True/False questions, determine which option is correct
    correct_answer = None
    if question.question_type == 'TRUE_FALSE':
        true_answer = QuizAnswer.objects.filter(question=question, text="True").first()
        if true_answer and true_answer.is_correct:
            correct_answer = 'true'
        else:
            correct_answer = 'false'
    
    context = {
        'question': question,
        'answers': answers,
        'correct_answer': correct_answer,
    }
    
    return render(request, 'educational/admin/question_form.html', context)

@login_required
@educator_required
@require_POST
def admin_add_answer(request, question_id):
    """View for admins to add an answer to a question."""
    if not request.user.is_staff:
        messages.error(request, "You don't have permission to access this page.")
        return redirect('educational:topic_list')
    
    question = get_object_or_404(QuizQuestion, pk=question_id)
    
    text = request.POST.get('text')
    is_correct = request.POST.get('is_correct') == 'on'
    explanation = request.POST.get('explanation', '')
    
    if not text:
        messages.error(request, "Answer text is required.")
        return redirect('educational:admin_edit_question', question_id=question.id)
    
    # For multiple choice, ensure only one answer is marked correct
    if question.question_type == 'MULTIPLE_CHOICE' and is_correct:
        QuizAnswer.objects.filter(question=question).update(is_correct=False)
    
    QuizAnswer.objects.create(
        question=question,
        text=text,
        is_correct=is_correct,
        explanation=explanation
    )
    
    messages.success(request, "Answer option added.")
    return redirect('educational:admin_edit_question', question_id=question.id)

@login_required
@educator_required
@require_POST
def admin_delete_question(request, question_id):
    """View for admins to delete a question."""
    if not request.user.is_staff:
        messages.error(request, "You don't have permission to access this page.")
        return redirect('educational:topic_list')
    
    question = get_object_or_404(QuizQuestion, pk=question_id)
    quiz_id = question.quiz.id
    
    # Delete the question and its answers (CASCADE will handle answers)
    question.delete()
    
    # Reorder remaining questions
    questions = QuizQuestion.objects.filter(quiz_id=quiz_id).order_by('order')
    for i, q in enumerate(questions, 1):
        q.order = i
        q.save()
    
    messages.success(request, "Question deleted.")
    return redirect('educational:admin_edit_quiz', quiz_id=quiz_id)

@login_required
@educator_required
@require_POST
def admin_delete_answer(request, answer_id):
    """View for admins to delete an answer."""
    if not request.user.is_staff:
        messages.error(request, "You don't have permission to access this page.")
        return redirect('educational:topic_list')
    
    answer = get_object_or_404(QuizAnswer, pk=answer_id)
    question_id = answer.question.id
    
    # Ensure we're not deleting the only correct answer for multiple choice
    if answer.is_correct and answer.question.question_type == 'MULTIPLE_CHOICE':
        if QuizAnswer.objects.filter(question=answer.question, is_correct=True).count() <= 1:
            messages.error(request, "Cannot delete the only correct answer. Please mark another answer as correct first.")
            return redirect('educational:admin_edit_question', question_id=question_id)
    
    # Don't allow deleting True/False options
    if answer.question.question_type == 'TRUE_FALSE' and answer.text in ["True", "False"]:
        messages.error(request, "Cannot delete True/False options. You can only change which one is correct.")
        return redirect('educational:admin_edit_question', question_id=question_id)
    
    answer.delete()
    
    messages.success(request, "Answer deleted.")
    return redirect('educational:admin_edit_question', question_id=question_id)

@login_required
@educator_required
@require_POST
def admin_publish_quiz(request, quiz_id):
    """View for admins to publish a quiz."""
    if not request.user.is_staff:
        messages.error(request, "You don't have permission to access this page.")
        return redirect('educational:topic_list')
    
    quiz = get_object_or_404(Quiz, pk=quiz_id)
    
    # Check if the quiz has questions
    if not QuizQuestion.objects.filter(quiz=quiz).exists():
        messages.error(request, "Cannot publish a quiz without questions.")
        return redirect('educational:admin_edit_quiz', quiz_id=quiz.id)
    
    # Check if all questions have at least one correct answer
    questions_without_correct = QuizQuestion.objects.filter(
        quiz=quiz
    ).exclude(
        id__in=QuizAnswer.objects.filter(
            question__quiz=quiz, 
            is_correct=True
        ).values_list('question_id', flat=True)
    )
    
    if questions_without_correct.exists():
        messages.error(request, f"All questions must have at least one correct answer. Please fix question: {questions_without_correct.first().text[:50]}...")
        return redirect('educational:admin_edit_quiz', quiz_id=quiz.id)
    
    quiz.publish()
    messages.success(request, f"Quiz '{quiz.title}' has been published.")
    
    return redirect('educational:admin_quiz_detail', quiz_id=quiz.id)

@login_required
@educator_required
@require_POST
def admin_unpublish_quiz(request, quiz_id):
    """View for admins to unpublish a quiz."""
    if not request.user.is_staff:
        messages.error(request, "You don't have permission to access this page.")
        return redirect('educational:topic_list')
    
    quiz = get_object_or_404(Quiz, pk=quiz_id)
    quiz.unpublish()
    messages.success(request, f"Quiz '{quiz.title}' has been unpublished.")
    
    return redirect('educational:admin_quiz_detail', quiz_id=quiz.id)

@login_required
@educator_required
@require_POST
def admin_delete_quiz(request, quiz_id):
    """View for admins to delete a quiz."""
    if not request.user.is_staff:
        messages.error(request, "You don't have permission to access this page.")
        return redirect('educational:topic_list')
    
    quiz = get_object_or_404(Quiz, pk=quiz_id)
    quiz_title = quiz.title
    
    try:
        # Delete the quiz (this will cascade delete all related questions and answers)
        quiz.delete()
        messages.success(request, f"Quiz '{quiz_title}' has been deleted successfully.")
    except Exception as e:
        messages.error(request, f"Error deleting quiz: {str(e)}")
    
    return redirect('educational:admin_quiz_list')

# Quiz Views - User

@login_required
def quiz_list(request):
    """View for users to see available quizzes."""
    # Get published quizzes
    quizzes = Quiz.objects.filter(is_published=True).select_related('topic')
    
    # Get user's quiz attempts for these quizzes
    user_attempts = UserQuizAttempt.objects.filter(
        user=request.user,
        quiz__in=quizzes
    ).select_related('quiz')
    
    # Create a dictionary of quiz_id -> user's best attempt
    user_quiz_attempts = {}
    for attempt in user_attempts:
        quiz_id = attempt.quiz.id
        if quiz_id not in user_quiz_attempts or (attempt.score is not None and (user_quiz_attempts[quiz_id].score is None or attempt.score > user_quiz_attempts[quiz_id].score)):
            user_quiz_attempts[quiz_id] = attempt
    
    # Filter by topic if provided
    topic_id = request.GET.get('topic')
    if topic_id:
        quizzes = quizzes.filter(topic_id=topic_id)
    
    # Search by title/description
    query = request.GET.get('q')
    if query:
        quizzes = quizzes.filter(
            Q(title__icontains=query) | 
            Q(description__icontains=query)
        )
    
    # Get topics with published quizzes for filter
    topics_with_quizzes = EducationalTopic.objects.filter(
        quizzes__is_published=True
    ).distinct().order_by('title')
    
    # Pagination
    paginator = Paginator(quizzes, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
        'topics': topics_with_quizzes,
        'selected_topic': topic_id,
        'query': query,
        'user_quiz_attempts': user_quiz_attempts,
    }
    
    return render(request, 'user_portal/educational/quiz/quiz_list.html', context)

@login_required
def quiz_detail(request, quiz_id):
    """View for users to see quiz details and start/resume a quiz."""
    quiz = get_object_or_404(Quiz.objects.select_related('topic'), pk=quiz_id, is_published=True)
    
    # Check if user has any attempts for this quiz
    user_attempts = UserQuizAttempt.objects.filter(
        user=request.user,
        quiz=quiz
    ).order_by('-start_time')
    
    # Get the most recent incomplete attempt, if any
    incomplete_attempt = user_attempts.filter(is_completed=False).first()
    
    # Get completed attempts
    completed_attempts = user_attempts.filter(is_completed=True)
    
    # Get quiz statistics
    total_questions = QuizQuestion.objects.filter(quiz=quiz).count()
    
    context = {
        'quiz': quiz,
        'user_attempts': completed_attempts,
        'incomplete_attempt': incomplete_attempt,
        'total_questions': total_questions,
    }
    
    return render(request, 'user_portal/educational/quiz/quiz_detail.html', context)

@login_required
def start_quiz(request, quiz_id):
    """View for users to start a new quiz attempt."""
    quiz = get_object_or_404(Quiz, pk=quiz_id, is_published=True)
    
    # Check for incomplete attempts and resume if exists
    incomplete_attempt = UserQuizAttempt.objects.filter(
        user=request.user,
        quiz=quiz,
        is_completed=False
    ).first()
    
    if incomplete_attempt:
        return redirect('educational:take_quiz', attempt_id=incomplete_attempt.id)
    
    # Create a new attempt
    attempt = UserQuizAttempt.objects.create(
        user=request.user,
        quiz=quiz
    )
    
    return redirect('educational:take_quiz', attempt_id=attempt.id)

@login_required
def take_quiz(request, attempt_id):
    """View for users to take a quiz."""
    attempt = get_object_or_404(
        UserQuizAttempt.objects.select_related('quiz', 'quiz__topic'),
        pk=attempt_id,
        user=request.user
    )
    
    # If the attempt is already completed, redirect to results
    if attempt.is_completed:
        return redirect('educational:quiz_results', attempt_id=attempt.id)
    
    # Get all questions for this quiz
    all_questions = QuizQuestion.objects.filter(
        quiz=attempt.quiz
    ).prefetch_related('answers').order_by('order')
    
    # Get the user's responses for this attempt
    responses = UserQuestionResponse.objects.filter(
        attempt=attempt
    ).select_related('question', 'selected_answer')
    
    # Create a dictionary of question_id -> response
    answered_questions = {response.question_id: response for response in responses}
    
    # Determine which question to show
    question_id = request.GET.get('question')
    
    # If a specific question is requested, show it
    if question_id:
        current_question = get_object_or_404(QuizQuestion, pk=question_id, quiz=attempt.quiz)
    else:
        # Otherwise, find the first unanswered question
        for question in all_questions:
            if question.id not in answered_questions:
                current_question = question
                break
        else:
            # All questions answered, show the first one
            current_question = all_questions.first() if all_questions else None
    
    # Handle submission of an answer
    if request.method == 'POST' and current_question:
        answer_id = request.POST.get('answer')
        
        if not answer_id:
            messages.error(request, "Please select an answer.")
        else:
            selected_answer = get_object_or_404(QuizAnswer, pk=answer_id, question=current_question)
            
            # Update or create the response
            if current_question.id in answered_questions:
                response = answered_questions[current_question.id]
                response.selected_answer = selected_answer
                response.save()
            else:
                response = UserQuestionResponse.objects.create(
                    attempt=attempt,
                    question=current_question,
                    selected_answer=selected_answer
                )
            
            # If all questions are answered, offer to complete
            if UserQuestionResponse.objects.filter(attempt=attempt).count() == all_questions.count():
                messages.success(request, "All questions answered! You can review your answers or submit the quiz.")
            
            # Find the next unanswered question, or go to the next question in sequence
            next_question = None
            for question in all_questions:
                if question.id not in answered_questions and question.id != current_question.id:
                    next_question = question
                    break
            
            if not next_question:
                # If no unanswered questions, go to the next one in sequence
                try:
                    current_index = list(all_questions).index(current_question)
                    next_question = all_questions[current_index + 1] if current_index + 1 < len(all_questions) else all_questions[0]
                except (ValueError, IndexError):
                    next_question = all_questions.first() if all_questions else None
            
            if next_question:
                return redirect(f"{request.path}?question={next_question.id}")
    
    # Calculate progress
    progress = (len(answered_questions) / all_questions.count() * 100) if all_questions.count() > 0 else 0
    
    # Get current response if exists
    current_response = answered_questions.get(current_question.id) if current_question else None
    
    context = {
        'attempt': attempt,
        'quiz': attempt.quiz,
        'current_question': current_question,
        'current_response': current_response,
        'all_questions': all_questions,
        'answered_questions': answered_questions,
        'progress': progress,
        'all_answered': len(answered_questions) == all_questions.count(),
    }
    
    return render(request, 'user_portal/educational/quiz/take_quiz.html', context)

@login_required
@educator_required
@require_POST
def complete_quiz(request, attempt_id):
    """View for users to complete a quiz attempt."""
    attempt = get_object_or_404(
        UserQuizAttempt,
        pk=attempt_id,
        user=request.user,
        is_completed=False
    )
    
    # Get all questions for this quiz
    all_questions = QuizQuestion.objects.filter(quiz=attempt.quiz)
    
    # Get the user's responses for this attempt
    responses = UserQuestionResponse.objects.filter(attempt=attempt)
    
    # Check if all questions have been answered
    if responses.count() < all_questions.count():
        unanswered_count = all_questions.count() - responses.count()
        messages.warning(request, f"You have {unanswered_count} unanswered questions. Are you sure you want to submit?")
        
        # Only complete if user confirmed
        if request.POST.get('confirmed') != 'true':
            return redirect('educational:take_quiz', attempt_id=attempt.id)
    
    # Complete the attempt
    attempt.complete()
    
    return redirect('educational:quiz_results', attempt_id=attempt.id)

@login_required
def quiz_results(request, attempt_id):
    """View for users to see their quiz results."""
    attempt = get_object_or_404(
        UserQuizAttempt.objects.select_related('quiz', 'quiz__topic'),
        pk=attempt_id,
        user=request.user,
        is_completed=True
    )
    
    # Get all questions with the user's responses
    questions = QuizQuestion.objects.filter(
        quiz=attempt.quiz
    ).prefetch_related(
        'answers'
    ).order_by('order')
    
    responses = UserQuestionResponse.objects.filter(
        attempt=attempt
    ).select_related('question', 'selected_answer')
    
    # Create a dictionary of question_id -> response
    user_responses = {response.question_id: response for response in responses}
    
    # Also get correct answers for all questions
    correct_answers = {}
    for question in questions:
        correct_answers[question.id] = QuizAnswer.objects.filter(
            question=question,
            is_correct=True
        )
    
    context = {
        'attempt': attempt,
        'quiz': attempt.quiz,
        'questions': questions,
        'user_responses': user_responses,
        'correct_answers': correct_answers,
    }
    
    return render(request, 'user_portal/educational/quiz/quiz_results.html', context)

@login_required
def search_educational_content(request):
    """
    Search educational topics based on user query.
    """
    query = request.GET.get('q', '').strip()
    results = []
    
    if query:
        # Search in topic titles and content
        results = EducationalTopic.objects.filter(
            Q(title__icontains=query) | 
            Q(content__icontains=query) |
            Q(category__title__icontains=query),
            is_published=True
        ).select_related('category').order_by('-created_at').distinct()
        
    context = {
        'query': query,
        'results': results,
        'active_page': 'education',
    }
    
    return render(request, 'user_portal/educational/search_results.html', context) 