import asyncio
import pytest
from jarvis.ai.errors import AICancelledError, AuthenticationError, RateLimitError
from jarvis.ai.retry import RetryPolicy


@pytest.mark.asyncio
async def test_retry_policy_success_first_attempt():
    policy = RetryPolicy(max_retries=2, initial_delay=0.01)
    call_count = 0

    async def operation():
        nonlocal call_count
        call_count += 1
        return "success"

    result = await policy.execute(operation)
    assert result == "success"
    assert call_count == 1


@pytest.mark.asyncio
async def test_retry_policy_retries_on_rate_limit_and_succeeds():
    policy = RetryPolicy(max_retries=3, initial_delay=0.01, jitter=False)
    call_count = 0

    async def operation():
        nonlocal call_count
        call_count += 1
        if call_count < 3:
            raise RateLimitError("Rate limit hit", retry_after=0.01)
        return "eventual_success"

    result = await policy.execute(operation)
    assert result == "eventual_success"
    assert call_count == 3


@pytest.mark.asyncio
async def test_retry_policy_does_not_retry_non_retryable_error():
    policy = RetryPolicy(max_retries=3, initial_delay=0.01)
    call_count = 0

    async def operation():
        nonlocal call_count
        call_count += 1
        raise AuthenticationError("Invalid API Key")

    with pytest.raises(AuthenticationError):
        await policy.execute(operation)

    # Must fail immediately without retrying
    assert call_count == 1


@pytest.mark.asyncio
async def test_retry_policy_exhaustion():
    policy = RetryPolicy(max_retries=2, initial_delay=0.01, jitter=False)
    call_count = 0

    async def operation():
        nonlocal call_count
        call_count += 1
        raise RateLimitError("Rate limit", retry_after=0.01)

    with pytest.raises(RateLimitError):
        await policy.execute(operation)

    # 1 initial + 2 retries = 3 attempts
    assert call_count == 3
