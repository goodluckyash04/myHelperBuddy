import os
import django
import sys

# Add project root to sys.path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "mysite.settings")
django.setup()

from django.contrib.auth.models import User
from accounts.models import UserProfile

print("Checking for users without profiles...")
users = User.objects.all()
count = 0
for user in users:
    if not hasattr(user, 'profile'):
        print(f"Creating profile for user: {user.username}")
        UserProfile.objects.create(user=user)
        count += 1
    else:
        # print(f"User {user.username} already has profile.")
        pass

print(f"Created {count} missing profiles.")
