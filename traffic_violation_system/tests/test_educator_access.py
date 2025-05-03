from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth.models import User
from traffic_violation_system.models import UserProfile

class EducatorAccessTests(TestCase):
    def setUp(self):
        # Create an educator user
        self.educator_user = User.objects.create_user(
            username='educator1',
            email='educator@example.com',
            password='testpassword123'
        )
        self.educator_profile = UserProfile.objects.get(user=self.educator_user)
        self.educator_profile.role = 'EDUCATOR'
        self.educator_profile.save()

        # Set up client
        self.client = Client()
        self.client.login(username='educator1', password='testpassword123')

    def test_educator_can_access_educational_pages(self):
        """Educators should have access to educational admin pages"""
        # Test educational admin dashboard access
        response = self.client.get(reverse('educational:admin_index'))
        self.assertEqual(response.status_code, 200)

        # Test educational admin category list access
        response = self.client.get(reverse('educational:admin_category_list'))
        self.assertEqual(response.status_code, 200)

        # Test educational admin topic list access
        response = self.client.get(reverse('educational:admin_topic_list'))
        self.assertEqual(response.status_code, 200)

        # Test educational admin quiz list access
        response = self.client.get(reverse('educational:admin_quiz_list'))
        self.assertEqual(response.status_code, 200)

    def test_educator_cannot_access_restricted_pages(self):
        """Educators should not have access to restricted pages"""
        # Test restrictions to violations list
        response = self.client.get(reverse('violations_list'))
        self.assertNotEqual(response.status_code, 200)  # Should be 302 (redirect) or 403 (forbidden)

        # Test restrictions to issue ticket page
        response = self.client.get(reverse('issue_ticket'))
        self.assertNotEqual(response.status_code, 200)

        # Test restrictions to QR scanner page
        response = self.client.get(reverse('qr_scanner'))
        self.assertNotEqual(response.status_code, 200)

        # Test restrictions to main dashboard
        response = self.client.get(reverse('admin_dashboard'))
        self.assertNotEqual(response.status_code, 200) 