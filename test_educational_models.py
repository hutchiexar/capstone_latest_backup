import os
import django

# Set up Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'traffic_violation_system.settings')
django.setup()

# Import models
from traffic_violation_system.educational.models import EducationalCategory, EducationalTopic
from django.contrib.auth.models import User

print('Models imported successfully')

# Get or create an admin user
admin_user, created = User.objects.get_or_create(
    username='admin',
    defaults={'is_staff': True, 'is_superuser': True}
)
if created:
    admin_user.set_password('admin123')
    admin_user.save()
    print(f'Created admin user: {admin_user}')
else:
    print(f'Using existing admin user: {admin_user}')

# Create a test category
category, cat_created = EducationalCategory.objects.get_or_create(
    title='Test Category',
    defaults={'description': 'A test category for the educational materials'}
)
if cat_created:
    print(f'Created category: {category}')
else:
    print(f'Using existing category: {category}')

# Create a test topic
topic, topic_created = EducationalTopic.objects.get_or_create(
    title='Test Topic',
    category=category,
    defaults={
        'content': '<p>This is a test educational topic with some example content.</p><p>Users can learn about traffic rules and regulations here.</p>',
        'is_published': True,
        'created_by': admin_user
    }
)
if topic_created:
    print(f'Created topic: {topic}')
else:
    print(f'Using existing topic: {topic}')

print('Test completed successfully!') 