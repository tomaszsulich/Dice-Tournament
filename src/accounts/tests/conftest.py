import pytest
from django.core.cache import cache


@pytest.fixture(autouse=True)
def clear_throttle_cache_between_tests():
    """Keep one auth test's rate-limit counters out of subsequent tests."""
    cache.clear()
    yield
    cache.clear()
