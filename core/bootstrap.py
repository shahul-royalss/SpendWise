"""Prepare the database on hosts that start from an empty filesystem.

Serverless platforms such as Vercel only allow writes to /tmp, which is empty
whenever a new instance starts. When ``DJANGO_MIGRATE_ON_START`` is set, the
WSGI entry point calls :func:`prepare_database` so the SQLite schema exists
before the first request, and an optional demo account is created from
``DEMO_USERNAME`` / ``DEMO_PASSWORD``.
"""

import os
from io import StringIO

from django.contrib.auth import get_user_model
from django.core.management import call_command


def prepare_database():
    call_command("migrate", interactive=False, verbosity=0)

    username = os.environ.get("DEMO_USERNAME", "").strip()
    password = os.environ.get("DEMO_PASSWORD", "")
    if not (username and password):
        return
    if get_user_model().objects.filter(username__iexact=username).exists():
        return
    call_command("seed_demo", username=username, password=password, stdout=StringIO())
