from .base import *

DEBUG = False

# Production security settings
SECURE_BROWSER_XSS_FILTER = True
X_FRAME_OPTIONS = 'DENY'
SECURE_CONTENT_TYPE_NOSNIFF = True
CSRF_COOKIE_SECURE = False  # Set to True if HTTPS
SESSION_COOKIE_SECURE = False  # Set to True if HTTPS

