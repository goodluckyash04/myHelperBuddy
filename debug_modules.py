from accounts.models import UtilityModule

# Check TRANSACTION module configuration
transaction = UtilityModule.objects.get(key='TRANSACTION')

print("=== TRANSACTION Module Configuration ===")
print(f"Access Type: {transaction.access_type}")
print(f"Allowed Users (text): '{transaction.allowed_users}'")
print(f"Allowed Users (list): {list(transaction.allowed_users_list.all().values_list('username', flat=True))}")
print(f"Is Active: {transaction.is_active}")

# Test access for a specific user (change 'admin' to your username)
from accounts.models import User
try:
    test_user = User.objects.first()
    print(f"\nTesting access for user: {test_user.username}")
    print(f"Has Access: {transaction.has_access(test_user)}")
except:
    print("\nNo users found in database")

print("\n=== All Modules ===")
for module in UtilityModule.objects.all():
    user_count = module.allowed_users_list.count()
    print(f"{module.key}: {module.access_type}, allowed_users='{module.allowed_users}', selected_users={user_count}")
