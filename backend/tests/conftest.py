import os
import pytest

# Force offline mode for all tests — aucun appel réseau réel
os.environ["OFFLINE_MODE"] = "true"
os.environ["GEOCODER"] = "mock"
os.environ["APP_ENV"] = "test"
