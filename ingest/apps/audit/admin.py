from django.contrib import admin

# Audit functionality is handled by:
# 1. SimpleHistoryAdmin on each model (shows change history)
# 2. LoginEventAdmin in accounts app
# 3. Built-in Django admin logging

# Custom audit admin views can be added here if needed
