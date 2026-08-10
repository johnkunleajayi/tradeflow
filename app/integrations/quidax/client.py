from typing import Any

import requests

from app.core.settings import settings


class QuidaxClient:
    """
    Client responsible only for communicating with the Quidax API.

    This class handles HTTP communication and does not contain
    market or trading business logic.
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

    def get(
        self,
        endpoint: str,
        params: dict[str, Any] | None = None,
    ) -> dict:
        """
        Executes a GET request against the Quidax API.
        """

        response = requests.get(
            f"{self.base_url}{endpoint}",
            params=params,
            timeout=self.timeout,
        )

        response.raise_for_status()

        return response.json()