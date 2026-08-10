from typing import Any

import requests

from app.core.settings import settings


class QuidaxClient:
    """
    Client responsible only for communicating with the Quidax API.

    This class handles HTTP communication and authentication.

    It does not contain market or trading business logic.

    Responsibilities:
    - Build Quidax API requests
    - Apply authentication
    - Handle GET requests
    - Handle POST requests
    - Return decoded JSON responses
    """

    def __init__(
        self,
        timeout: int | None = None,
    ):
        self.base_url = settings.QUIDAX_BASE_URL.rstrip("/")

        self.timeout = (
            timeout
            if timeout is not None
            else settings.REQUEST_TIMEOUT
        )

        self.order_poll_interval = (
            settings.QUIDAX_ORDER_POLL_INTERVAL
        )

        self.order_timeout = (
            settings.QUIDAX_ORDER_TIMEOUT
        )

    def _headers(self) -> dict[str, str]:
        """
        Returns headers required for authenticated Quidax requests.

        The API key is read from application settings and is never
        hard-coded into the client.
        """

        headers = {
            "Accept": "application/json",
            "Content-Type": "application/json",
        }

        if settings.QUIDAX_API_KEY:
            headers["Authorization"] = (
                f"Bearer {settings.QUIDAX_API_KEY}"
            )

        return headers

    def _request(
        self,
        method: str,
        endpoint: str,
        *,
        params: dict[str, Any] | None = None,
        json: dict[str, Any] | None = None,
        authenticated: bool = False,
    ) -> dict:
        """
        Executes an HTTP request against the Quidax API.
        """

        headers = (
            self._headers()
            if authenticated
            else {
                "Accept": "application/json",
                "Content-Type": "application/json",
            }
        )

        response = requests.request(
            method=method,
            url=f"{self.base_url}{endpoint}",
            params=params,
            json=json,
            headers=headers,
            timeout=self.timeout,
        )

        response.raise_for_status()

        return response.json()

    def get(
        self,
        endpoint: str,
        params: dict[str, Any] | None = None,
        *,
        authenticated: bool = False,
    ) -> dict:
        """
        Executes a GET request against the Quidax API.
        """

        return self._request(
            method="GET",
            endpoint=endpoint,
            params=params,
            authenticated=authenticated,
        )

    def post(
        self,
        endpoint: str,
        json: dict[str, Any] | None = None,
        *,
        authenticated: bool = True,
    ) -> dict:
        """
        Executes a POST request against the Quidax API.
        """

        return self._request(
            method="POST",
            endpoint=endpoint,
            json=json,
            authenticated=authenticated,
        )