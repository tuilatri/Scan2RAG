"""Shared test environment: keep the local dev API usable without a real key."""

import os

os.environ.setdefault("ENVIRONMENT", "development")
os.environ.setdefault("ALLOW_UNAUTHENTICATED_DEV", "true")
