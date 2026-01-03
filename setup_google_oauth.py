"""
Setup script to configure Django Site for Google OAuth.

Run this script once to initialize the Site model required by django-allauth.
"""

import os
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'mysite.settings')
django.setup()

from django.contrib.sites.models import Site

def setup_site():
    """Configure Django Site for Google OAuth."""
    site, created = Site.objects.get_or_create(
        id=1,
        defaults={
            'domain': 'localhost:8000',
            'name': 'MyHelperBuddy Local Development'
        }
    )
    
    if not created:
        # Update existing site
        site.domain = 'localhost:8000'
        site.name = 'MyHelperBuddy Local Development'
        site.save()
        print(f"✅ Site updated: {site.domain}")
    else:
        print(f"✅ Site created: {site.domain}")
    
    print("\n" + "="*50)
    print("Site configuration complete!")
    print("="*50)
    print("\nNext steps:")
    print("1. Add Google OAuth credentials to your .env file")
    print("2. Create OAuth credentials in Google Cloud Console")
    print("3. Run: python manage.py runserver")
    print("4. Visit: http://localhost:8000/login")
    print("5. Click 'Sign in with Google'")
    print("\nSee google_oauth_setup.md for detailed instructions.")
    print("="*50 + "\n")

if __name__ == '__main__':
    setup_site()
