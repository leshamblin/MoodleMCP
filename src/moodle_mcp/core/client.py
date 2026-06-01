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
    Handles authentication and Moodle error-response classification. The auth
    token is sent in the request body (POST), never in the URL.
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

    async def call(
        self,
        function_name: str,
        params: dict[str, Any] | None = None
    ) -> Any:
        """
        Public entry point for calling a Moodle Web Services function.

        Tools should call this rather than the underscore-prefixed
        ``_make_request``. Pass parameters as plain nested dicts/lists; the
        client flattens them into Moodle's PHP-bracket form for you.

        Args:
            function_name: Moodle API function (e.g. 'core_course_get_courses')
            params: Nested parameters, e.g.
                {'enrolments': [{'roleid': 5, 'userid': 624, 'courseid': 7299}]}

        Returns:
            Parsed JSON response. Three success shapes are possible:
            - ``dict``: most read functions and some writes
            - ``list``: list-returning functions
            - ``None``: functions that return ``null`` on success
              (e.g. enrol_manual_enrol_users, core_group_add_group_members)
        """
        return await self._make_request(function_name, params)

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
            Parsed JSON response from Moodle API. May be a dict, a list, or
            ``None``. A ``None`` result means the function returned ``null``,
            which Moodle uses to signal success for functions with no return
            value (enrol/unenrol, group add/delete members, calendar delete).

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
            # POST (not GET): the wstoken must travel in the request body, never
            # in the URL query string, or it leaks into access logs, proxy
            # caches, and APM traces. server.php reads parameters identically
            # from a form-encoded body. This also lifts the ~8 KB URL length cap
            # on large write payloads (forum/feedback HTML).
            response = await self.client.post(self.api_endpoint, data=request_params)
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
                        # debug_info can echo back request internals; only
                        # surface it in DEV. In PROD keep the message minimal.
                        detail = (
                            f" - {debug_info}"
                            if debug_info and not self._is_production()
                            else ""
                        )
                        raise MoodleAPIError(
                            f"Moodle API error ({error_code}): {error_msg}{detail}"
                        )

            return result

        except httpx.HTTPStatusError as e:
            status = e.response.status_code
            if status == 401 or status == 403:
                raise MoodleAuthError(f"HTTP {status}: Authentication failed")
            elif status == 404:
                raise MoodleNotFoundError("HTTP 404: Resource not found")
            else:
                # str(e) embeds the request URL; with POST the token is no
                # longer in it, but scrub defensively in case it ever appears.
                raise MoodleConnectionError(
                    f"HTTP error {status}: {self._scrub(str(e))}"
                )
        except httpx.RequestError as e:
            raise MoodleConnectionError(f"Connection failed: {self._scrub(str(e))}")
        except ValueError as e:
            raise MoodleAPIError(f"Invalid JSON response: {self._scrub(str(e))}")

    def _scrub(self, text: str) -> str:
        """Remove the auth token from any text before it reaches the caller."""
        if self.token and self.token in text:
            text = text.replace(self.token, "***")
        return text

    def _is_production(self) -> bool:
        """Best-effort production check for error-detail gating (PROD-safe default)."""
        try:
            from .config import get_config
            return get_config().is_production
        except Exception:
            # If config can't be resolved, assume PROD and withhold details.
            return True

    def _flatten_params(self, params: dict[str, Any]) -> dict[str, str]:
        """
        Flatten nested dict/list parameters into Moodle's PHP-bracket form.

        Only leaf scalars produce an output key; intermediate dict/list nodes
        never emit a key of their own. ``None`` values are dropped (Moodle
        treats an absent optional param as unset), and booleans are encoded as
        ``"1"``/``"0"`` (Moodle's PARAM_BOOL expects integers, not "True").

        An already-bracketed string key (e.g. ``"enrolments[0][roleid]"``) is
        treated as an opaque top-level scalar, so legacy tools that pre-flatten
        their parameters keep working until they are refactored.

        Examples:
            {'enrolments': [{'roleid': 5, 'userid': 624}]}
              -> {'enrolments[0][roleid]': '5', 'enrolments[0][userid]': '624'}

            {'plugindata': {'assignfeedbackcomments_editor': {'text': 'Hi', 'format': 1}}}
              -> {'plugindata[assignfeedbackcomments_editor][text]': 'Hi',
                  'plugindata[assignfeedbackcomments_editor][format]': '1'}
        """
        out: dict[str, str] = {}

        def encode(value: Any, prefix: str) -> None:
            if value is None:
                return  # omit unset optionals; never send the literal "None"
            if isinstance(value, bool):
                out[prefix] = "1" if value else "0"
            elif isinstance(value, (str, int, float)):
                out[prefix] = str(value)
            elif isinstance(value, dict):
                for k, v in value.items():
                    child = f"{prefix}[{k}]" if prefix else str(k)
                    encode(v, child)
            elif isinstance(value, (list, tuple)):
                for i, item in enumerate(value):
                    encode(item, f"{prefix}[{i}]")
            else:
                out[prefix] = str(value)

        for key, value in params.items():
            encode(value, str(key))

        return out

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


def raise_on_row_errors(
    rows: Any,
    *,
    error_keys: tuple[str, ...] = ("errormessage",),
) -> None:
    """
    Inspect per-row results and raise if any row carries an error.

    Some Moodle functions return HTTP 200 with no top-level ``exception`` but
    report per-row failures inside the result (e.g.
    ``core_message_send_instant_messages`` returns ``errormessage`` per
    message, and ``core_calendar_create_calendar_events`` returns a
    ``warnings`` list). Those would otherwise look like success. Wrappers for
    such functions should call this on the relevant list.

    Args:
        rows: The list of per-row result dicts (non-list input is ignored).
        error_keys: Keys whose truthy presence on a row signals an error.

    Raises:
        MoodleAPIError: If any row contains a truthy value for an error key.
    """
    if not isinstance(rows, (list, tuple)):
        return

    problems = [
        r for r in rows
        if isinstance(r, dict) and any(r.get(k) for k in error_keys)
    ]
    if problems:
        details = "; ".join(
            str(next((p.get(k) for k in error_keys if p.get(k)), p))
            for p in problems
        )
        raise MoodleAPIError(f"Operation reported per-row errors: {details}")
