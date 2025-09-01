#!/usr/bin/env python
import os
import sys
import django

# Add the project directory to Python path
sys.path.insert(0, '/app')

# Set Django settings
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ingest.settings.prod')

# Setup Django
django.setup()

# Test admin site
from ingest.admin import admin_site

print("=== Custom Admin Site Debug ===")
print(f"Total registered models: {len(admin_site._registry)}")
print("\nRegistered models by app:")

apps = {}
for model in admin_site._registry:
    app_label = model._meta.app_label
    if app_label not in apps:
        apps[app_label] = []
    apps[app_label].append(model.__name__)

for app_label, models in sorted(apps.items()):
    print(f"  {app_label}: {models}")

print("\n=== Testing app_list method ===")
from django.contrib.auth.models import AnonymousUser
from django.http import HttpRequest

# Create a mock request
request = HttpRequest()
request.user = AnonymousUser()

try:
    app_list = admin_site.get_app_list(request)
    print(f"App list length: {len(app_list)}")
    for app in app_list:
        print(f"  App: {app.get('name', 'Unknown')} ({app.get('app_label', 'Unknown')})")
        for model in app.get('models', []):
            print(f"    Model: {model.get('name', 'Unknown')}")
except Exception as e:
    print(f"Error getting app list: {e}")
