import pytest
import time
from ses.server.ratelimit import RateLimiter

def test_rate_limiter_allows_requests_within_limit():
    limiter = RateLimiter(requests_per_minute=60, burst_limit=5)
    key = "test_key"

    # First 5 should be allowed (burst)
    for _ in range(5):
        assert limiter.is_allowed(key) is True

    # 6th should fail immediately
    assert limiter.is_allowed(key) is False

def test_rate_limiter_replenishes_tokens(monkeypatch):
    limiter = RateLimiter(requests_per_minute=60, burst_limit=1)
    key = "test_replenish"

    # Mock time
    current_time = 1000.0
    monkeypatch.setattr(time, "time", lambda: current_time)

    assert limiter.is_allowed(key) is True
    assert limiter.is_allowed(key) is False

    # 1 request per second (60 per minute). Wait 1 second.
    current_time += 1.1
    assert limiter.is_allowed(key) is True
    assert limiter.is_allowed(key) is False

def test_rate_limiter_weights():
    limiter = RateLimiter(requests_per_minute=60, burst_limit=10)
    key = "test_weights"

    # Consumes 5 tokens
    assert limiter.is_allowed(key, weight=5) is True

    # Consumes another 5 tokens
    assert limiter.is_allowed(key, weight=5) is True

    # No tokens left
    assert limiter.is_allowed(key, weight=1) is False

    # Cannot consume more than burst limit initially
    assert limiter.is_allowed("new_key", weight=11) is False
