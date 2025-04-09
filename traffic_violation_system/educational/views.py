from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.admin.views.decorators import staff_member_required
from django.http import JsonResponse, HttpResponseRedirect
from django.urls import reverse
from django.utils import timezone
from django.contrib import messages
from django.db.models import Count, Q
from .models import EducationalCategory, EducationalTopic, TopicAttachment, UserBookmark, UserProgress
from django.views.decorators.http import require_http_methods
from PyPDF2 import PdfReader
import io
import tempfile
import os
import base64
from PIL import Image


# Helper function to check if a user is an admin
def is_admin(user):
    return user.is_superuser or (hasattr(user, 'userprofile') and user.userprofile.role == 'ADMIN')

# Admin views
@login_required
@user_passes_test(is_admin)
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
@user_passes_test(is_admin)
def admin_category_list(request):
    categories = EducationalCategory.objects.all().annotate(topics_count=Count('topics'))
    context = {
        'categories': categories
    }
    return render(request, 'admin/educational/category_list.html', context)


@login_required
@user_passes_test(is_admin)
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
@user_passes_test(is_admin)
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
@user_passes_test(is_admin)
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
@user_passes_test(is_admin)
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
@user_passes_test(is_admin)
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
@user_passes_test(is_admin)
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
@user_passes_test(is_admin)
def admin_topic_delete(request, topic_id):
    topic = get_object_or_404(EducationalTopic, id=topic_id)
    
    if request.method == 'POST':
        topic_title = topic.title
        topic.delete()
        messages.success(request, f'Topic "{topic_title}" deleted successfully')
        return redirect('educational:admin_topic_list')
    
    context = {
        'topic': topic
    }
    return render(request, 'admin/educational/topic_delete.html', context)


@login_required
@user_passes_test(is_admin)
def admin_topic_publish(request, topic_id):
    topic = get_object_or_404(EducationalTopic, id=topic_id)
    
    topic.is_published = not topic.is_published
    topic.save()
    
    status = "published" if topic.is_published else "unpublished"
    messages.success(request, f'Topic "{topic.title}" {status} successfully')
    
    return redirect('educational:admin_topic_list')


@login_required
@user_passes_test(is_admin)
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
@user_passes_test(is_admin)
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
@user_passes_test(is_admin)
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