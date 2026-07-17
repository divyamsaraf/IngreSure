"""
HTTP GET/POST with retries and exponential backoff for external APIs.
"""
import logging
import time
from typing import Any, Optional, Tuple

import requests

logger = logging.getLogger(__name__)

DEFAULT_MAX_RETRIES = 3
DEFAULT_INITIAL_BACKOFF = 1.0


def _request_with_retries(
    method: str,
    url: str,
    *,
    params: Optional[dict] = None,
    data: Any = None,
    json_body: Any = None,
    headers: Optional[dict] = None,
    timeout: int = 10,
    max_retries: int = DEFAULT_MAX_RETRIES,
    initial_backoff: float = DEFAULT_INITIAL_BACKOFF,
) -> Tuple[Optional[requests.Response], Optional[str]]:
    """GET/POST with retries and exponential backoff on timeout/connection errors."""
    last_error: Optional[str] = None
    for attempt in range(max_retries):
        try:
            resp = requests.request(
                method,
                url,
                params=params or {},
                data=data,
                json=json_body,
                headers=headers,
                timeout=timeout,
            )
            return (resp, None)
        except requests.Timeout as e:
            last_error = f"Read timed out: {e}"
            logger.warning(
                "EXTERNAL_API retry attempt=%s/%s url=%s error=%s",
                attempt + 1, max_retries, url[:60], last_error,
            )
        except requests.RequestException as e:
            last_error = f"{type(e).__name__}: {e}"
            logger.warning(
                "EXTERNAL_API retry attempt=%s/%s url=%s error=%s",
                attempt + 1, max_retries, url[:60], last_error,
            )
        if attempt < max_retries - 1:
            delay = initial_backoff * (2 ** attempt)
            logger.info("EXTERNAL_API backoff %.1fs before retry", delay)
            time.sleep(delay)
    return (None, last_error)


def get_with_retries(
    url: str,
    params: Optional[dict] = None,
    timeout: int = 10,
    max_retries: int = DEFAULT_MAX_RETRIES,
    initial_backoff: float = DEFAULT_INITIAL_BACKOFF,
) -> Tuple[Optional[requests.Response], Optional[str]]:
    """
    GET with 2-3 retries and exponential backoff on timeout/connection errors.
    Returns (response, None) on success, (None, error_message) on failure.
    """
    return _request_with_retries(
        "GET",
        url,
        params=params,
        timeout=timeout,
        max_retries=max_retries,
        initial_backoff=initial_backoff,
    )


def post_with_retries(
    url: str,
    *,
    data: Any = None,
    json_body: Any = None,
    headers: Optional[dict] = None,
    timeout: int = 10,
    max_retries: int = DEFAULT_MAX_RETRIES,
    initial_backoff: float = DEFAULT_INITIAL_BACKOFF,
) -> Tuple[Optional[requests.Response], Optional[str]]:
    """
    POST with retries and exponential backoff on timeout/connection errors.
    Returns (response, None) on success, (None, error_message) on failure.
    """
    return _request_with_retries(
        "POST",
        url,
        data=data,
        json_body=json_body,
        headers=headers,
        timeout=timeout,
        max_retries=max_retries,
        initial_backoff=initial_backoff,
    )
