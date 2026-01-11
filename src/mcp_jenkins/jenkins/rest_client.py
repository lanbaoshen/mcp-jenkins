import re
from functools import reduce
from typing import Literal

import requests
from bs4 import BeautifulSoup
from loguru import logger
from pydantic import HttpUrl
from requests import Response
from requests.auth import HTTPBasicAuth
from requests.exceptions import HTTPError

from mcp_jenkins.jenkins import rest_endpoint
from mcp_jenkins.model.build import Build, BuildReplay
from mcp_jenkins.model.item import FreeStyleProject, ItemType, Job, serialize_item
from mcp_jenkins.model.node import Node
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

        url = self.endpoint_url(endpoint)
        logger.debug(f'Sending [{method}] request to {url}')

        response = self._session.request(method=method, url=url, headers=headers)
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

    def get_node(self, *, name: str, depth: int = 0) -> Node:
        """Get a specific node by name.

        Args:
            name: The name of the node.
            depth: The depth of the information to retrieve.

        Returns:
            The Node object.
        """
        name = '(master)' if name in ('master', 'Built-In Node') else name
        response = self.request('GET', rest_endpoint.NODE(name=name, depth=depth))
        return Node.model_validate(response.json())

    def get_nodes(self, *, depth: int = 0) -> list[Node]:
        """Get a list of nodes connected to the Master

        Args:
            depth: The depth of the information to retrieve.

        Returns:
            A list of Node objects.
        """
        response = self.request('GET', rest_endpoint.NODES(depth=depth))
        return [Node.model_validate(node) for node in response.json()['computer']]

    def get_node_config(self, *, name: str) -> str:
        """Get the configuration for a node.

        Args:
            name: The name of the node.

        Returns:
            The node configuration as an XML string.
        """
        response = self.request('GET', rest_endpoint.NODE_CONFIG(name=name))
        return response.text

    def get_build(self, *, fullname: str, number: int, depth: int = 0) -> Build:
        """Get build by fullname and number.

        Args:
            fullname: The fullname of the job.
            number: The build number.
            depth: The depth of the information to retrieve.

        Returns:
            The Build object.
        """
        folder, name = self._parse_fullname(fullname)
        response = self.request('GET', rest_endpoint.BUILD(folder=folder, name=name, number=number, depth=depth))
        return Build.model_validate(response.json())

    def get_build_console_output(self, *, fullname: str, number: int) -> str:
        """Get the console output of a specific build.

        Args:
            fullname: The fullname of the job.
            number: The build number.

        Returns:
            The console output as a string.
        """
        folder, name = self._parse_fullname(fullname)
        response = self.request('GET', rest_endpoint.BUILD_CONSOLE_OUTPUT(folder=folder, name=name, number=number))
        return response.text

    def stop_build(self, *, fullname: str, number: int) -> None:
        """Stop a running Jenkins build.

        Args:
            fullname: The fullname of the job.
            number: The build number.
        """
        folder, name = self._parse_fullname(fullname)
        self.request('POST', rest_endpoint.BUILD_STOP(folder=folder, name=name, number=number))

    def get_build_replay(self, *, fullname: str, number: int) -> BuildReplay:
        """Get the build replay of a specific build.

        If you want to get the pipeline source code of a specific build in Jenkins, you can use this method.

        Args:
            fullname: The fullname of the job.
            number: The build number.

        Returns:
            The build replay object containing the pipeline scripts.
        """

        folder, name = self._parse_fullname(fullname)
        response = self.request('GET', rest_endpoint.BUILD_REPLAY(folder=folder, name=name, number=number))

        soup = BeautifulSoup(response.text, 'html.parser')

        scripts = [textarea.text for textarea in soup.find_all('textarea', {'name': re.compile(r'_\..*Script.*')})]
        return BuildReplay(scripts=scripts)

    def get_build_test_report(self, *, fullname: str, number: int, depth: int = 0) -> dict:
        """Get the test report of a specific build.

        Args:
            fullname: The fullname of the job.
            number: The build number.
            depth: The depth of the information to retrieve.

        Returns:
            A dictionary representing the test report.
        """
        folder, name = self._parse_fullname(fullname)
        response = self.request(
            'GET', rest_endpoint.BUILD_TEST_REPORT(folder=folder, name=name, number=number, depth=depth)
        )
        return response.json()

    def get_running_builds(self) -> list[Build]:
        """Get all running builds across all nodes.

        The build obtained through this method only includes the number, url and timestamp.

        Returns:
            A list of Build objects representing the running builds.
        """
        builds = []

        for node in self.get_nodes(depth=2):
            for executor in node.executors:
                if executor.currentExecutable and executor.currentExecutable.number:
                    builds.append(Build.model_validate(executor.currentExecutable.model_dump(mode='json')))

        return builds

    def get_items(self, *, folder_depth: int | None = None, folder_depth_per_request: int = 10) -> list[ItemType]:
        """Get items in the Jenkins instance up to a specified folder depth.

        Args:
            folder_depth: The maximum depth of folders to traverse. If None, traverses all levels.
            folder_depth_per_request: The depth of folders to request per API call.

        Returns:
            A list of ItemType objects representing the items.
        """
        query = reduce(lambda q, _: f'jobs[url,color,name,{q}]', range(folder_depth_per_request), 'jobs')
        response = self.request('GET', rest_endpoint.ITEMS(folder='', query=query))

        items = []

        item_stack = [(0, [], response.json()['jobs'])]
        for level, path, level_items in item_stack:
            current_items = level_items if isinstance(level_items, list) else [level_items]

            for item in current_items:
                job_path = path + [item['name']]
                item.setdefault('fullname', '/'.join(job_path))
                items.append(serialize_item(item))

                children = item.get('jobs')
                if isinstance(children, list) and (folder_depth is None or level < folder_depth):
                    item_stack.append((level + 1, job_path, children))

        return items

    def get_item(self, *, fullname: str, depth: int = 0) -> ItemType:
        """Get item by its fullname.

        Args:
            fullname: The full name of the item (e.g., "folder1/folder2/item").
            depth: The depth of the information to retrieve.

        Returns:
            The ItemType object representing the item.
        """
        folder, name = self._parse_fullname(fullname)
        response = self.request('GET', rest_endpoint.ITEM(folder=folder, name=name, depth=depth))
        return serialize_item(response.json())

    def get_item_config(self, *, fullname: str) -> str:
        """Get item configuration by its fullname.

        Args:
            fullname: The full name of the item (e.g., "folder1/folder2/item").

        Returns:
            The item configuration as an XML string.
        """
        folder, name = self._parse_fullname(fullname)
        response = self.request('GET', rest_endpoint.ITEM_CONFIG(folder=folder, name=name))
        return response.text

    def query_items(
        self,
        *,
        folder_depth: int | None = None,
        folder_depth_per_request: int = 10,
        class_pattern: str | None = None,
        fullname_pattern: str | None = None,
        color_pattern: str | None = None,
    ) -> list['ItemType']:
        """Query items by specific field patterns.

        Args:
            folder_depth: The maximum depth of folders to traverse. If None, traverses all levels.
            folder_depth_per_request: The depth of folders to request per API call.
            class_pattern: The pattern of the _class.
            fullname_pattern: The pattern of the fullname.
            color_pattern: The pattern of the color.

        Returns:
            A list of ItemType objects matching the specified patterns.
        """
        class_re, fullname_re, color_re = (
            re.compile(pattern) if pattern else None for pattern in (class_pattern, fullname_pattern, color_pattern)
        )

        items = self.get_items(folder_depth=folder_depth, folder_depth_per_request=folder_depth_per_request)

        result = []

        for item in items:
            if class_re and not class_re.search(item.class_):
                continue
            # fullname may be None for some items
            if item.fullname is None or (fullname_re and not fullname_re.search(item.fullname)):
                continue
            if color_re:
                # Only Job has color attribute
                if not isinstance(item, Job | FreeStyleProject) or not color_re.search(item.color):
                    continue
            result.append(item)

        return result
