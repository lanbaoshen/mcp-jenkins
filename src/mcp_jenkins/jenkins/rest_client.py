from typing import Literal

import requests
from pydantic import HttpUrl
from requests import Response
from requests.auth import HTTPBasicAuth
from requests.exceptions import HTTPError

from mcp_jenkins.jenkins import rest_endpoint
from mcp_jenkins.model.queue import Queue, QueueItem


class Jenkins:
    DEFAULT_HEADERS = {'Content-Type': 'text/xml; charset=utf-8'}

    def __init__(
        self,
        *,
        url: HttpUrl,
        username: str,
        password: str,
        timeout: int = 75,
        verify_ssl: bool = True,
    ) -> None:
        self.url = url.encoded_string()
        self.timeout = timeout

        self._crumb_header = None

        self._session = requests.Session()
        self._session.auth = HTTPBasicAuth(username, password)
        self._session.verify = verify_ssl

    def endpoint_url(self, endpoint: str) -> str:
        """Construct the full URL for a given Jenkins REST endpoint.

        Args:
            endpoint: The Jenkins REST endpoint path.

        Returns:
            The full URL as a string. (e.g., https://example.com/crumbIssuer/api/json)
        """
        return '/'.join(str(s).strip('/') for s in [self.url, endpoint])

    def request(
        self,
        method: Literal['GET', 'POST', 'PUT', 'DELETE', 'PATCH'],
        endpoint: str,
        *,
        headers: dict = None,
        crumb: bool = True,
    ) -> Response:
        """Send an HTTP request to a Jenkins REST endpoint.

        Args:
            method: HTTP method to use.
            endpoint: Jenkins REST endpoint path.
            headers: Optional headers to include in the request.
            crumb: Whether to include a CSRF crumb header.

        Returns:
            Response: The HTTP response object.

        Raises:
            HTTPError: If the response status is not successful.
        """
        if crumb:
            if headers is None:
                headers = {}
            headers.update(self.crumb_header)

        response = self._session.request(method=method, url=self.endpoint_url(endpoint), headers=headers)
        response.raise_for_status()
        return response

    @property
    def crumb_header(self) -> dict[str, str]:
        """Get the CSRF crumb header for Jenkins requests.

        Returns:
            A dictionary containing the crumb header.
        """
        if self._crumb_header is None:
            try:
                response = self.request('GET', rest_endpoint.CRUMB, crumb=False)
                crumb = response.json()
                self._crumb_header = {crumb['crumbRequestField']: crumb['crumb']}
            except HTTPError as e:
                if e.response.status_code == 404:
                    self._crumb_header = {}
                else:
                    raise

        return self._crumb_header

    def _parse_fullname(self, fullname: str) -> tuple[str, str]:
        """Parse a fullname into folder URL and short name.

        Args:
            fullname: A string representing the full path (e.g., "folder1/folder2/name").

        Returns:
            A tuple containing:
                - folder: The constructed folder URL (e.g., "job/folder1/job/folder2/").
                - name: The last component of the path (e.g., "name").
        """
        parts = fullname.split('/')
        name = parts[-1]
        folder = f'job/{"/job/".join(parts[:-1])}/' if len(parts) > 1 else ''
        return folder, name

    def get_queue(self, *, depth: int = 1) -> Queue:
        """Get queue.

        Args:
            depth: The depth of the information to retrieve.

        Returns:
            A list of QueueItem objects.
        """
        response = self.request('GET', rest_endpoint.QUEUE(depth=depth))
        return Queue.model_validate(response.json())

    def get_queue_item(self, *, id: int, depth: int = 0) -> 'QueueItem':
        """Get a queue item by its ID.

        Args:
            id: The ID of the queue item.
            depth: The depth of the information to retrieve.

        Returns:
            The QueueItem object.
        """
        response = self.request('GET', rest_endpoint.QUEUE_ITEM(id=id, depth=depth))
        return QueueItem.model_validate(response.json())

    def cancel_queue_item(self, *, id: int) -> None:
        """Cancel a queue item by its ID.

        Args:
            id: The ID of the queue item to cancel.
        """
        self.request('POST', rest_endpoint.QUEUE_CANCEL_ITEM(id=id))
