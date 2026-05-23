from django.conf import settings
from decouple import config

def firebase_config(request):
    """
    Injects Firebase configuration into the template context for the JS SDK.
    These values are safe to expose to the frontend.
    """
    return {
        'FIREBASE_VAPID_PUBLIC_KEY': getattr(settings, 'FIREBASE_VAPID_PUBLIC_KEY', config('FIREBASE_VAPID_PUBLIC_KEY', default='')),
        'firebase_api_key': config('FIREBASE_API_KEY', default=''),
        'firebase_app_id': config('FIREBASE_APP_ID', default=''),
        'firebase_sender_id': config('FIREBASE_SENDER_ID', default=''),
    }
