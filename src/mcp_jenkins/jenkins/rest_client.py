import re
from functools import reduce
from typing import Literal

import requests
from bs4 import BeautifulSoup
from loguru import logger
from requests import Response
from requests.auth import HTTPBasicAuth
from requests.exceptions import HTTPError

from mcp_jenkins.jenkins import rest_endpoint
from mcp_jenkins.jenkins.model.build import Artifact, Build, BuildReplay
from mcp_jenkins.jenkins.model.item import (
    FreeStyleProject,
    ItemType,
    Job,
    serialize_item,
)
from mcp_jenkins.jenkins.model.node import Node
from mcp_jenkins.jenkins.model.queue import Queue, QueueItem


class Jenkins:
    DEFAULT_HEADERS = {'Content-Type': 'text/xml; charset=utf-8'}

    def __init__(
        self,
        *,
        url: str,
        username: str,
        password: str,
        timeout: int = 75,
        verify_ssl: bool = True,
    ) -> None:
        self.url = url
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
        data: dict | str = None,
        headers: dict = None,
        crumb: bool = True,
        params: dict = None,
    ) -> Response:
        """Send an HTTP request to a Jenkins REST endpoint.

        Args:
            method: HTTP method to use.
            endpoint: Jenkins REST endpoint path.
            data: Data to send.
            headers: Optional headers to include in the request.
            crumb: Whether to include a CSRF crumb header.
            params: Optional query parameters to include in the request.

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

        response = self._session.request(
            method=method,
            url=url,
            headers=headers,
            params=params,
            data=data,
            timeout=self.timeout,
        )

        # When a Jenkins HTTP session expires the cached CSRF crumb becomes
        # invalid and every POST returns 403.  Retry once with a fresh crumb
        # before giving up — this covers the stale-session case while still
        # surfacing genuine permission errors on the second attempt.
        if crumb and response.status_code == 403 and self._crumb_header:
            logger.warning('Received 403 with a cached crumb — refreshing crumb and retrying the request')
            self._crumb_header = None
            headers.update(self.crumb_header)
            response = self._session.request(
                method=method,
                url=url,
                headers=headers,
                params=params,
                data=data,
                timeout=self.timeout,
            )

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

    def _build_view_path(self, view_path: str) -> str:
        """Build a Jenkins view URL path from a slash-separated view path.

        Args:
            view_path: Slash-separated view path (e.g. "frontend/nightly").

        Returns:
            The Jenkins URL path segment (e.g. "view/frontend/view/nightly").
        """
        from urllib.parse import quote

        parts = [quote(p.strip(), safe='') for p in view_path.split('/') if p.strip()]
        return '/'.join(f'view/{p}' for p in parts)

    def get_views(self) -> list[dict]:
        """Get all top-level views from Jenkins.

        Returns:
            A list of dictionaries with 'name' and 'url' for each view.
        """
        response = self.request('GET', rest_endpoint.VIEWS)
        return response.json().get('views', [])

    def get_view(self, *, view_path: str, depth: int = 0) -> dict:
        """Get a specific view by path.

        Supports nested views using slash-separated paths
        (e.g. "All", "frontend/nightly", "frontend/nightly/nightly linux").

        Args:
            view_path: Slash-separated view path.
            depth: The depth of the information to retrieve.

        Returns:
            A dictionary with the view's name, jobs, and/or nested views.
        """
        url_path = self._build_view_path(view_path)
        response = self.request('GET', rest_endpoint.VIEW(view_path=url_path, depth=depth))
        return response.json()

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

    def get_queue_item_raw(self, *, id: int) -> dict:
        """Get a queue item by its ID as raw JSON dict.

        Use this when you need fields not present in the QueueItem model,
        such as the 'build' field that appears when a queue item is
        assigned to a running build.

        Args:
            id: The ID of the queue item.

        Returns:
            A dictionary representing the queue item as returned by Jenkins.
        """
        response = self.request('GET', rest_endpoint.QUEUE_ITEM(id=id, depth=1))
        return response.json()

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

    def set_node_config(self, *, name: str, config_xml: str) -> None:
        """Set the configuration for a node.

        Args:
            name: The name of the node.
            config_xml: The node configuration as an XML string.
        """
        self.request(
            'POST',
            rest_endpoint.NODE_CONFIG(name=name),
            headers=self.DEFAULT_HEADERS,
            data=config_xml,
        )

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
        response = self.request(
            'GET',
            rest_endpoint.BUILD(folder=folder, name=name, number=number, depth=depth),
        )
        return Build.model_validate(response.json())

    def get_build_console_output(
        self,
        *,
        fullname: str,
        number: int,
        pattern: str | None = None,
        offset: int = 0,
        limit: int | None = None,
    ) -> str:
        """Get the console output of a specific build.

        Args:
            fullname: The fullname of the job.
            number: The build number.
            pattern: Optional regex pattern to filter lines (only matching lines are returned).
            offset: Number of lines to skip from the beginning (after pattern filtering).
            limit: Maximum number of lines to return (after pattern filtering and offset).

        Returns:
            The console output as a string.
        """
        folder, name = self._parse_fullname(fullname)
        compiled = re.compile(pattern) if pattern else None

        response = self._session.get(
            self.endpoint_url(rest_endpoint.BUILD_CONSOLE_OUTPUT(folder=folder, name=name, number=number)),
            timeout=self.timeout,
            stream=True,
        )
        response.raise_for_status()

        matched: list[str] = []
        skipped = 0

        for raw_line in response.iter_lines(decode_unicode=True):
            if compiled is not None and not compiled.search(raw_line):
                continue
            if skipped < offset:
                skipped += 1
                continue
            matched.append(raw_line)
            if limit is not None and len(matched) >= limit:
                break

        response.close()
        return '\n'.join(matched)

    def get_build_console_tail(
        self,
        *,
        fullname: str,
        number: int,
        n_lines: int = 200,
    ) -> str:
        """Get the last N lines of a build's console output.

        Args:
            fullname: The fullname of the job.
            number: The build number.
            n_lines: Number of lines to return from the end (default: 200).

        Returns:
            Last N lines of console output as a string.
        """
        folder, name = self._parse_fullname(fullname)
        response = self._session.get(
            self.endpoint_url(rest_endpoint.BUILD_CONSOLE_OUTPUT(folder=folder, name=name, number=number)),
            timeout=self.timeout,
        )
        response.raise_for_status()

        all_lines = response.text.split('\n')
        tail_lines = all_lines[-n_lines:] if len(all_lines) >= n_lines else all_lines
        return '\n'.join(tail_lines)

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

    def get_build_parameters(self, *, fullname: str, number: int) -> dict:
        """Get the build parameters of a specific build.

        Args:
            fullname: The fullname of the job.
            number: The build number.

        Returns:
            A dictionary representing the build parameters.
        """
        folder, name = self._parse_fullname(fullname)
        response = self.request(
            'GET',
            rest_endpoint.BUILD_PARAMETERS(folder=folder, name=name, number=number),
        )

        for action in response.json().get('actions', []):
            if 'parameters' in action:
                return {p['name']: p.get('value') for p in action['parameters']}
        return {}

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
            'GET',
            rest_endpoint.BUILD_TEST_REPORT(folder=folder, name=name, number=number, depth=depth),
        )
        return response.json()

    def get_build_artifacts(self, *, fullname: str, number: int) -> list[Artifact]:
        """Get the list of artifacts from a specific build.

        Args:
            fullname: The fullname of the job.
            number: The build number.

        Returns:
            A list of Artifact objects.
        """
        folder, name = self._parse_fullname(fullname)
        response = self.request(
            'GET',
            rest_endpoint.BUILD_ARTIFACTS(folder=folder, name=name, number=number),
        )
        return [Artifact.model_validate(a) for a in response.json().get('artifacts', [])]

    def get_build_artifact(self, *, fullname: str, number: int, relative_path: str) -> bytes:
        """Download the content of a specific artifact from a build.

        Args:
            fullname: The fullname of the job.
            number: The build number.
            relative_path: The relative path of the artifact.

        Returns:
            The artifact content as bytes.
        """
        folder, name = self._parse_fullname(fullname)
        response = self.request(
            'GET',
            rest_endpoint.BUILD_ARTIFACT(folder=folder, name=name, number=number, relative_path=relative_path),
        )
        return response.content

    def get_build_artifact_url(self, *, fullname: str, number: int, relative_path: str) -> str:
        """Get the direct URL of a specific artifact from a build.

        Args:
            fullname: The fullname of the job.
            number: The build number.
            relative_path: The relative path of the artifact.

        Returns:
            The direct URL of the artifact as a string.
        """
        folder, name = self._parse_fullname(fullname)
        return self.endpoint_url(
            rest_endpoint.BUILD_ARTIFACT(folder=folder, name=name, number=number, relative_path=relative_path),
        )

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
        query = reduce(
            lambda q, _: f'jobs[url,color,name,{q}]',
            range(folder_depth_per_request),
            'jobs',
        )
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

    def set_item_config(self, *, fullname: str, config_xml: str) -> None:
        """Set item configuration by its fullname.

        Args:
            fullname: The full name of the item (e.g., "folder1/folder2/item").
            config_xml: The item configuration as an XML string.
        """
        folder, name = self._parse_fullname(fullname)
        self.request(
            'POST',
            rest_endpoint.ITEM_CONFIG(folder=folder, name=name),
            headers=self.DEFAULT_HEADERS,
            data=config_xml,
        )

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

    def build_item(
        self,
        *,
        fullname: str,
        build_type: Literal['build', 'buildWithParameters'],
        data: dict | None = None,
    ) -> int:
        """Trigger a build for a specific item.

        Warnings:
            If your job is configured with parameters, you must use 'buildWithParameters' as build_type.

        Args:
            fullname: The fullname of the job.
            build_type: The type of build to trigger.
            data: The parameters to trigger the build with. Required if build_type is 'buildWithParameters'.

        Return:
            The queue item number of the job.
        """
        folder, name = self._parse_fullname(fullname)
        response = self.request(
            'POST',
            rest_endpoint.ITEM_BUILD(folder=folder, name=name, build_type=build_type),
            data=data,
        )

        return int(response.headers.get('Location', None).strip('/').split('/')[-1])

    def get_plugins(self, *, depth: int = 0) -> list[dict]:
        """Get a list of all installed plugins.

        Args:
            depth: The depth of the information to retrieve.

        Returns:
            A list of plugin dictionaries.
        """
        response = self.request('GET', rest_endpoint.PLUGIN_LIST(depth=depth))
        return response.json().get('plugins', [])

    def get_plugin(self, *, short_name: str, depth: int = 2) -> dict | None:
        """Get a specific plugin by short name.

                Args:
                    short_name: The short name of the plugin.
                    depth: The depth of the information to retrieve. Default is 2 (includes dependencies).

        Returns:
                    A list of plugins that can be downgraded.
        """
        plugins = self.get_plugins(depth=depth)
        for plugin in plugins:
            if plugin.get('shortName') == short_name:
                return plugin
        return None

    def get_plugins_with_problems(self) -> list[dict]:
        """Get a list of plugins that have dependency problems.

        Checks each plugin's dependencies against the installed plugins
        to identify missing dependencies or version mismatches.

        Returns:
            A list of plugins with dependency problems.
        """
        jenkins_version = self._get_jenkins_version()
        plugins = self.get_plugins(depth=2)

        installed = {p['shortName']: p for p in plugins}

        problems = []
        for plugin in plugins:
            short_name = plugin.get('shortName', '')
            version = plugin.get('version', '')
            required_core = plugin.get('requiredCoreVersion', '')

            if required_core and jenkins_version:
                if not self._is_core_compatible(jenkins_version, required_core):
                    problems.append(
                        {
                            'shortName': short_name,
                            'problem': 'incompatible_core_version',
                            'pluginVersion': version,
                            'requiredCoreVersion': required_core,
                            'jenkinsVersion': jenkins_version,
                            'severity': 'error',
                            'message': (
                                f'Plugin requires Jenkins {required_core}, but current version is {jenkins_version}'
                            ),
                        }
                    )

            if not plugin.get('enabled'):
                problems.append(
                    {
                        'shortName': short_name,
                        'problem': 'plugin_disabled',
                        'pluginVersion': version,
                        'severity': 'warning',
                        'message': 'Plugin is currently disabled',
                    }
                )

            deps = plugin.get('dependencies', [])
            for dep in deps:
                dep_name = dep.get('shortName', '')
                dep_version = dep.get('version', '')
                is_optional = dep.get('optional', False)
                is_bundled = dep.get('bundled', False)

                if dep_name not in installed:
                    if is_optional:
                        problems.append(
                            {
                                'shortName': short_name,
                                'problem': 'missing_optional_dependency',
                                'dependency': dep_name,
                                'requiredVersion': dep_version,
                                'severity': 'info',
                                'message': f'Missing optional dependency: {dep_name}',
                            }
                        )
                    elif not is_bundled:
                        problems.append(
                            {
                                'shortName': short_name,
                                'problem': 'missing_dependency',
                                'dependency': dep_name,
                                'requiredVersion': dep_version,
                                'severity': 'error',
                                'message': f'Missing required dependency: {dep_name}',
                            }
                        )
                else:
                    installed_ver = installed[dep_name].get('version', '')
                    if dep_version and installed_ver and installed_ver != dep_version:
                        if self._is_version_greater(installed_ver, dep_version):
                            continue
                        if is_optional:
                            problems.append(
                                {
                                    'shortName': short_name,
                                    'problem': 'version_mismatch_optional',
                                    'dependency': dep_name,
                                    'requiredVersion': dep_version,
                                    'installedVersion': installed_ver,
                                    'severity': 'info',
                                    'message': (
                                        f'Optional dependency {dep_name} version mismatch: '
                                        f'required {dep_version}, installed {installed_ver}'
                                    ),
                                }
                            )
                        else:
                            problems.append(
                                {
                                    'shortName': short_name,
                                    'problem': 'version_mismatch',
                                    'dependency': dep_name,
                                    'requiredVersion': dep_version,
                                    'installedVersion': installed_ver,
                                    'severity': 'error',
                                    'message': (
                                        f'Dependency {dep_name} version mismatch: '
                                        f'required {dep_version}, installed {installed_ver}'
                                    ),
                                }
                            )

        return problems

    def get_plugins_with_updates(self, depth: int = 0) -> list[dict]:
        """Get plugins that have available updates.

        Args:
            depth: The depth of the information to retrieve.

        Returns:
            A list of plugins with available updates.
        """
        plugins = self.get_plugins(depth=depth)
        return [
            {
                'shortName': p.get('shortName'),
                'longName': p.get('longName'),
                'version': p.get('version'),
            }
            for p in plugins
            if p.get('hasUpdate')
        ]

    def get_plugins_with_backup(self, depth: int = 0) -> list[dict]:
        """Get plugins that can be downgraded.

        Plugins with backupVersion and downgradable=true can be rolled back.

        Args:
            depth: The depth of the information to retrieve.

        Returns:
            A list of plugins that can be downgraded.
        """
        response = self.request('GET', rest_endpoint.PLUGIN_LIST(depth=depth))
        plugins = response.json().get('plugins', [])
        return [
            {
                'shortName': p.get('shortName'),
                'longName': p.get('longName'),
                'version': p.get('version'),
                'backupVersion': p.get('backupVersion'),
                'downgradable': p.get('downgradable'),
            }
            for p in plugins
            if p.get('backupVersion') and p.get('downgradable')
        ]

    def _get_jenkins_version(self) -> str:
        """Get the Jenkins core version from response header."""
        response = self.request('GET', '', crumb=False)
        return response.headers.get('X-Jenkins', '')

    def _is_core_compatible(self, jenkins_ver: str, required_ver: str) -> bool:
        """Check if Jenkins version is compatible with required core version."""
        if not isinstance(jenkins_ver, str) or not isinstance(required_ver, str):
            return True

        def normalize_version(v: str) -> tuple:
            parts = v.split('.')
            return tuple(int(p) if p.isdigit() else 0 for p in parts[:3])

        core = normalize_version(jenkins_ver)
        required = normalize_version(required_ver)
        return core >= required

    def _is_version_greater(self, installed_ver: str, required_ver: str) -> bool:
        """Check if installed version is greater than required version."""
        if not isinstance(installed_ver, str) or not isinstance(required_ver, str):
            return False

        def normalize_version(v: str) -> tuple:
            parts = v.split('.')
            return tuple(int(p) if p.isdigit() else 0 for p in parts[:3])

        installed = normalize_version(installed_ver)
        required = normalize_version(required_ver)
        return installed > required

    def get_plugin_dependency_graph(self, short_name: str) -> dict:
        """Get dependency graph for a specific plugin in Graphviz format.

        Recursively analyzes dependencies down to leaf nodes (plugins with no dependencies).

        Args:
            short_name: The short name of the plugin to analyze.

        Returns:
            A dictionary containing 'nodes' and 'edges' for Graphviz rendering.
        """
        plugins = self.get_plugins(depth=2)
        installed = {p['shortName']: p for p in plugins}

        if short_name not in installed:
            return {'nodes': [], 'edges': [], 'error': f'Plugin not found: {short_name}'}

        nodes = []
        edges = []
        visited = set()

        def traverse(name: str) -> None:
            if name in visited:
                return
            visited.add(name)

            if name not in installed:
                nodes.append({'id': name, 'label': name, 'status': 'missing'})
                return

            plugin = installed[name]
            nodes.append(
                {
                    'id': name,
                    'label': f'{name}\n({plugin.get("version", "?")})',
                    'status': 'installed',
                }
            )

            deps = plugin.get('dependencies', [])
            for dep in deps:
                dep_name = dep.get('shortName', '')
                edges.append({'from': name, 'to': dep_name})
                traverse(dep_name)

        traverse(short_name)

        return {'nodes': nodes, 'edges': edges}

    def run_script(self, script: str) -> str:  # noqa: N802
        """Execute a Groovy script on Jenkins.

        Args:
            script: The Groovy script code to execute.

        Returns:
            The result of the script execution.
        """
        response = self.request('POST', rest_endpoint.SCRIPT_TEXT, data={'script': script.encode('utf-8')})

        result = response.text
        result_prefix = 'Result: '
        if result.startswith(result_prefix):
            return result[len(result_prefix) :].rstrip('\n')
        return result
