"""WSGI entry point, used by Gunicorn (Docker) and by Vercel."""

import os

from django.core.wsgi import get_wsgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

application = get_wsgi_application()

# Serverless hosts start each instance with an empty /tmp, so the database has
# to be created when the app boots. Docker runs `migrate` itself instead.
if os.environ.get("DJANGO_MIGRATE_ON_START", "").strip().lower() in {"1", "true", "yes", "on"}:
    from core.bootstrap import prepare_database

    prepare_database()
