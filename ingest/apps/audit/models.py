"""
Audit models are primarily handled by django-simple-history.
This module can be extended for custom audit functionality.
"""

# The audit functionality is primarily provided by:
# 1. simple_history.models.HistoricalRecords on each model
# 2. LoginEvent model in accounts app
# 3. Admin action logging (built into Django admin)

# Future custom audit models can be added here if needed
