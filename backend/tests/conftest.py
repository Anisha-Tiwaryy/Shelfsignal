# Celery runs tasks inline under pytest (see CELERY_TASK_ALWAYS_EAGER in
# config/settings.py). Setting that from this file does not work because
# pytest-django loads Django settings before any conftest runs.
