from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth.models import User
from .models import UserProfile

@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        UserProfile.objects.get_or_create(user=instance)

@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    if hasattr(instance, 'profile'):
        instance.profile.save()

# Google OAuth signal handlers
try:
    from allauth.socialaccount.signals import pre_social_login
    
    @receiver(pre_social_login)
    def populate_user_from_google(sender, request, sociallogin, **kwargs):
        """Populate user data from Google profile."""
        if sociallogin.account.provider == 'google':
            data = sociallogin.account.extra_data
            user = sociallogin.user
            
            # Populate user fields from Google data
            if not user.first_name and data.get('given_name'):
                user.first_name = data.get('given_name', '')
            if not user.last_name and data.get('family_name'):
                user.last_name = data.get('family_name', '')
            if not user.email and data.get('email'):
                user.email = data.get('email')
except ImportError:
    # allauth not installed yet
    pass
