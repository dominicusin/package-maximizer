"""Root conftest — sets PM_API_KEY before test modules import web.app."""

import os

# Ensure PM_API_KEY is set BEFORE any test module imports
# ``package_maximizer.web.app`` (which reads it at import time).
os.environ.setdefault("PM_API_KEY", "test-key-for-tests")
