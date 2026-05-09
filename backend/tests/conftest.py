import os
import pytest

# Force offline mode for all tests
os.environ["OFFLINE_MODE"] = "true"
os.environ["APP_ENV"] = "test"
