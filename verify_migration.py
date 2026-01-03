import os
import django
import sys

# Add project root to sys.path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "mysite.settings")
django.setup()

from django.contrib.auth.models import User
from accounts.models import UserProfile, FinancialProduct


print(f"User model class: {User}")
users = User.objects.all()
for u in users:
    print(f"User: {u.username} (ID: {u.id})")
    try:
        if hasattr(u, 'profile'):
            print(f"  Profile found: {u.profile}")
        else:
            print("  Profile NOT found!")
    except Exception as e:
        print(f"  Error accessing profile: {e}")
    
    fp_count = FinancialProduct.objects.filter(created_by=u).count()
    print(f"  FinancialProducts linked: {fp_count}")


print("Verification complete.")
