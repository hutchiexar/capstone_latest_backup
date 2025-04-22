#!/usr/bin/env python

"""
Script to test popup announcements and reset session data
This script helps diagnose and fix issues with popup announcements by:
1. Showing all popup announcements and their settings
2. Resetting session data to force popups to show again
3. Creating a test popup announcement if needed
"""

import os
import sys
import django

# Set up Django environment
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'TrafficViolationSystem.settings')
django.setup()

from django.utils import timezone
from django.contrib.sessions.models import Session
from django.contrib.auth.models import User
from traffic_violation_system.models import Announcement

def reset_popup_sessions():
    """Clear all popup announcement session data to make announcements show again"""
    active_sessions = Session.objects.filter(expire_date__gt=timezone.now())
    session_count = 0
    
    print(f"Found {active_sessions.count()} active sessions")
    
    for session in active_sessions:
        try:
            session_data = session.get_decoded()
            if 'seen_popup_announcements' in session_data:
                # Clear the seen announcements list
                session_data['seen_popup_announcements'] = []
                
                # Save the updated session data
                from django.contrib.sessions.backends.db import SessionStore
                s = SessionStore()
                session.session_data = s.encode(session_data)
                session.save()
                session_count += 1
                print(f"Reset session {session.pk}")
        except Exception as e:
            print(f"Error with session {session.pk}: {str(e)}")
            continue
    
    print(f"Reset {session_count} sessions")
    return session_count

def show_all_popups():
    """Show all popup announcements and their settings"""
    all_popups = Announcement.objects.filter(is_popup=True)
    active_popups = all_popups.filter(is_active=True)
    
    print(f"\nAll announcements with is_popup=True: {all_popups.count()}")
    print(f"Active announcements with is_popup=True: {active_popups.count()}")
    
    if all_popups.count() == 0:
        print("No popup announcements found.")
        return
        
    print("\nDetails of popup announcements:")
    for idx, popup in enumerate(all_popups, 1):
        print(f"\n{idx}. Title: {popup.title}")
        print(f"   ID: {popup.id}")
        print(f"   Active: {popup.is_active}")
        print(f"   Requires Acknowledgment: {popup.requires_acknowledgment}")
        print(f"   Created: {popup.created_at}")
        print(f"   Target Audience: {popup.target_audience}")
        if popup.publish_date:
            print(f"   Publish Date: {popup.publish_date}")
        if popup.expiration_date:
            print(f"   Expiration Date: {popup.expiration_date}")

def create_test_popup():
    """Create a test popup announcement"""
    print("\nCreating test popup announcement...")
    
    try:
        admin = User.objects.filter(is_superuser=True).first()
        if not admin:
            print("Error: No admin user found")
            return
            
        announcement = Announcement.objects.create(
            title="Test Popup Announcement",
            content="This is a test popup announcement to verify functionality. If you're seeing this, the popup system is working correctly.",
            created_by=admin,
            is_active=True,
            is_popup=True,
            priority="HIGH",
            target_audience="ALL"
        )
        print(f"Created test announcement with ID: {announcement.id}")
        return announcement
    except Exception as e:
        print(f"Error creating test announcement: {str(e)}")
        return None

if __name__ == "__main__":
    print("Popup Announcement Diagnostic Tool")
    print("=================================\n")
    
    # Show all popups
    show_all_popups()
    
    # Reset session data
    reset_popup_sessions()
    
    # Check if we need to create a test popup
    active_popups = Announcement.objects.filter(is_popup=True, is_active=True)
    if active_popups.count() == 0:
        print("\nNo active popup announcements found. Creating a test announcement.")
        create_test_popup()
    else:
        print("\nActive popup announcements exist. No need to create a test one.")
        
    print("\nDone! Popup announcements should now show on the next page load.") 