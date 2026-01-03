from accounts.models import UtilityModule, User

# Get the TRANSACTION module
transaction = UtilityModule.objects.get(key='TRANSACTION')

# Get your user
your_user = User.objects.get(username='yash04')

# Add your user to the allowed list
transaction.allowed_users_list.add(your_user)

print(f"✅ Added {your_user.username} to TRANSACTION module")
print(f"Now allowed users: {list(transaction.allowed_users_list.all().values_list('username', flat=True))}")
print(f"Testing access: {transaction.has_access(your_user)}")
