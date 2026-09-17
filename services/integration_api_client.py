"""Communicate with the internal Shippo integration API over HTTP + JSON.

This module is the backend's only transport boundary for the integration
service. It knows internal endpoint paths and HTTP semantics, but contains no
Shippo credentials, provider URLs, provider payloads, or provider retry logic.
"""

import logging
import os
import time
import uuid
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import requests
from dotenv import load_dotenv


logger = logging.getLogger(__name__)

DEFAULT_ENV_FILE = Path(__file__).resolve().parents[1] / ".env"
DEFAULT_CONNECT_TIMEOUT_SECONDS = 3.05
DEFAULT_READ_TIMEOUT_SECONDS = 30.0
CORRELATION_HEADER = "X-Correlation-ID"


class IntegrationConfigurationError(Exception):
    """Raised when the internal integration API location is unavailable."""


class IntegrationTimeoutError(Exception):
    """Raised when the internal integration API does not respond in time."""


class IntegrationAPIError(Exception):
    """Raised for connection or unsuccessful integration API responses."""


class IntegrationResponseError(Exception):
    """Raised when the integration API does not return a JSON object."""


class IntegrationAPIClient:
    """Execute the backend's allowed internal integration API operations."""

    def __init__(
        self,
        base_url: str | None = None,
        connect_timeout_seconds: float | None = None,
        read_timeout_seconds: float | None = None,
    ) -> None:
        """Create a client from explicit values or validated environment settings."""
        load_dotenv(dotenv_path=DEFAULT_ENV_FILE, override=False)
        configured_url = (
            base_url
            if base_url is not None
            else os.getenv("SHIPPO_INTEGRATION_BASE_URL", "")
        ).strip()
        parsed_url = urlparse(configured_url)
        if (
            not configured_url
            or parsed_url.scheme not in {"http", "https"}
            or not parsed_url.netloc
        ):
            raise IntegrationConfigurationError(
                "SHIPPO_INTEGRATION_BASE_URL must be an absolute HTTP or HTTPS URL."
            )

        try:
            connect_timeout = (
                connect_timeout_seconds
                if connect_timeout_seconds is not None
                else float(
                    os.getenv(
                        "SHIPPO_INTEGRATION_CONNECT_TIMEOUT_SECONDS",
                        DEFAULT_CONNECT_TIMEOUT_SECONDS,
                    )
                )
            )
            read_timeout = (
                read_timeout_seconds
                if read_timeout_seconds is not None
                else float(
                    os.getenv(
                        "SHIPPO_INTEGRATION_READ_TIMEOUT_SECONDS",
                        DEFAULT_READ_TIMEOUT_SECONDS,
                    )
                )
            )
        except ValueError as exc:
            raise IntegrationConfigurationError(
                "Integration API timeout settings must be numeric."
            ) from exc
        if connect_timeout <= 0 or read_timeout <= 0:
            raise IntegrationConfigurationError(
                "Integration API timeout settings must be greater than zero."
            )

        self.base_url = configured_url.rstrip("/")
        self.timeout = (connect_timeout, read_timeout)

    def _request(
        self,
        method: str,
        endpoint: str,
        *,
        json_body: dict[str, Any] | None = None,
        correlation_id: str | None = None,
    ) -> dict[str, Any]:
        """Execute one internal API request and return a decoded JSON object."""
        request_id = correlation_id or str(uuid.uuid4())
        normalized_endpoint = f"/{endpoint.lstrip('/')}"
        url = f"{self.base_url}{normalized_endpoint}"
        headers = {
            "Accept": "application/json",
            CORRELATION_HEADER: request_id,
        }
        if json_body is not None:
            headers["Content-Type"] = "application/json"

        started_at = time.perf_counter()
        try:
            response = requests.request(
                method,
                url,
                json=json_body,
                headers=headers,
                timeout=self.timeout,
            )
        except requests.Timeout as exc:
            logger.warning(
                "Integration API timeout correlation_id=%s operation=%s",
                request_id,
                normalized_endpoint,
            )
            raise IntegrationTimeoutError(
                "The integration API request timed out."
            ) from exc
        except requests.RequestException as exc:
            logger.error(
                "Integration API connection failure correlation_id=%s operation=%s",
                request_id,
                normalized_endpoint,
            )
            raise IntegrationAPIError(
                "Unable to communicate with the integration API."
            ) from exc
        finally:
            latency_ms = (time.perf_counter() - started_at) * 1000
            logger.debug(
                "Integration API request correlation_id=%s operation=%s "
                "latency_ms=%.2f",
                request_id,
                normalized_endpoint,
                latency_ms,
            )

        if response.status_code == 503:
            raise IntegrationConfigurationError(
                "The integration API is not configured."
            )
        if response.status_code == 504:
            raise IntegrationTimeoutError(
                "The integration API request timed out."
            )
        if not response.ok:
            raise IntegrationAPIError(
                f"Integration API returned HTTP {response.status_code}."
            )

        response_correlation = response.headers.get(CORRELATION_HEADER)
        if response_correlation and response_correlation != request_id:
            logger.warning(
                "Integration API correlation mismatch correlation_id=%s",
                request_id,
            )

        try:
            result = response.json()
        except ValueError as exc:
            raise IntegrationResponseError(
                "Integration API returned invalid JSON."
            ) from exc
        if not isinstance(result, dict):
            raise IntegrationResponseError(
                "Integration API returned a non-object JSON response."
            )
        return result

    def health(self, *, correlation_id: str | None = None) -> dict[str, Any]:
        """Request integration HTTP process liveness for diagnostics."""
        return self._request("GET", "/health", correlation_id=correlation_id)

    def validate_address(
        self,
        payload: dict[str, Any],
        *,
        correlation_id: str | None = None,
    ) -> dict[str, Any]:
        """Validate one address through the internal integration API."""
        return self._request(
            "POST",
            "/validate-address",
            json_body=payload,
            correlation_id=correlation_id,
        )

    def shipping_quote(
        self,
        payload: dict[str, Any],
        *,
        correlation_id: str | None = None,
    ) -> dict[str, Any]:
        """Request one shipping quote through the internal integration API."""
        return self._request(
            "POST",
            "/shipping-quote",
            json_body=payload,
            correlation_id=correlation_id,
        )