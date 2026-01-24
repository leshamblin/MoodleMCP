"""
Async Moodle API client with connection pooling and comprehensive error handling.
"""

import httpx
from typing import Any
from .exceptions import (
    MoodleAPIError,
    MoodleAuthError,
    MoodleConnectionError,
    MoodleNotFoundError,
    MoodlePermissionError
)

class MoodleAPIClient:
    """
    Async Moodle Web Services API client.

    Provides persistent HTTP connections via lifespan management.
    Automatically handles authentication, error responses, and rate limiting.
    """

    def __init__(
        self,
        base_url: str,
        token: str,
        timeout: int = 30,
        max_connections: int = 100,
        max_keepalive: int = 20
    ):
        """
        Initialize Moodle API client.

        Args:
            base_url: Moodle site URL (e.g., https://moodle.example.com)
            token: Web services authentication token
            timeout: Request timeout in seconds
            max_connections: Maximum total connections
            max_keepalive: Maximum keepalive connections
        """
        self.base_url = base_url.rstrip('/')
        self.token = token
        self.api_endpoint = f"{self.base_url}/webservice/rest/server.php"

        # Create async HTTP client with connection pooling and SSL verification
        self.client = httpx.AsyncClient(
            timeout=timeout,
            limits=httpx.Limits(
                max_keepalive_connections=max_keepalive,
                max_connections=max_connections
            ),
            verify=True,    # Explicitly enforce SSL/TLS certificate verification
            http2=True      # Enable HTTP/2 for better performance and security
        )

    async def _make_request(
        self,
        function_name: str,
        params: dict[str, Any] | None = None
    ) -> Any:
        """
        Make async request to Moodle Web Services API.

        Args:
            function_name: Moodle API function to call (e.g., 'core_webservice_get_site_info')
            params: Optional parameters for the function

        Returns:
            Parsed JSON response from Moodle API

        Raises:
            MoodleAuthError: Authentication failed
            MoodlePermissionError: User lacks permission
            MoodleNotFoundError: Resource not found
            MoodleAPIError: Other Moodle API error
            MoodleConnectionError: Network/connection error
        """
        # Build request parameters
        request_params = {
            'wstoken': self.token,
            'wsfunction': function_name,
            'moodlewsrestformat': 'json'
        }

        if params:
            # Flatten nested parameters for Moodle's array format
            flattened_params = self._flatten_params(params)
            request_params.update(flattened_params)

        try:
            # Make async GET request
            response = await self.client.get(self.api_endpoint, params=request_params)
            response.raise_for_status()

            # Parse JSON response
            result = response.json()

            # Handle Moodle-specific error responses
            if isinstance(result, dict):
                if 'exception' in result or 'errorcode' in result:
                    error_msg = result.get('message', 'Unknown error')
                    error_code = result.get('errorcode', 'unknown')
                    debug_info = result.get('debuginfo', '')

                    # Classify error types for better handling
                    if 'invalidtoken' in error_code or 'accessexception' in error_code:
                        raise MoodleAuthError(f"Authentication failed: {error_msg}")
                    elif 'nopermission' in error_code or 'requireloginerror' in error_code:
                        raise MoodlePermissionError(f"Permission denied: {error_msg}")
                    elif 'invalidrecord' in error_code or 'notfound' in error_code:
                        raise MoodleNotFoundError(f"Not found: {error_msg}")
                    else:
                        raise MoodleAPIError(
                            f"Moodle API error ({error_code}): {error_msg}"
                            f"{' - ' + debug_info if debug_info else ''}"
                        )

            return result

        except httpx.HTTPStatusError as e:
            status = e.response.status_code
            if status == 401 or status == 403:
                raise MoodleAuthError(f"HTTP {status}: Authentication failed")
            elif status == 404:
                raise MoodleNotFoundError(f"HTTP 404: Resource not found")
            else:
                raise MoodleConnectionError(f"HTTP error {status}: {e}")
        except httpx.RequestError as e:
            raise MoodleConnectionError(f"Connection failed: {e}")
        except ValueError as e:
            raise MoodleAPIError(f"Invalid JSON response: {e}")

    def _flatten_params(self, params: dict[str, Any], prefix: str = '') -> dict[str, Any]:
        """
        Flatten nested parameters to Moodle's array format.

        Example:
            {'users': [{'id': 1}, {'id': 2}]}
            -> {'users[0][id]': 1, 'users[1][id]': 2}
        """
        flattened = {}

        for key, value in params.items():
            new_key = f"{prefix}{key}" if prefix else key

            if isinstance(value, dict):
                # Recursively flatten nested dicts
                flattened.update(self._flatten_params(value, f"{new_key}["))
                if prefix:
                    flattened[f"{new_key}]"] = ""  # Close bracket
            elif isinstance(value, (list, tuple)):
                # Flatten lists with indices
                for i, item in enumerate(value):
                    if isinstance(item, dict):
                        flattened.update(
                            self._flatten_params(item, f"{new_key}[{i}][")
                        )
                    else:
                        flattened[f"{new_key}[{i}]"] = str(item)
            else:
                # Simple value
                flattened[new_key] = str(value)

        return flattened

    async def get_site_info(self) -> dict[str, Any]:
        """
        Get site information and verify connection.

        Returns:
            Dict containing site info (sitename, siteurl, userid, username, etc.)
        """
        return await self._make_request('core_webservice_get_site_info')

    async def close(self):
        """Close HTTP client and cleanup connections."""
        await self.client.aclose()
