import re
from typing import Literal
from uuid import uuid4

import requests
from bs4 import BeautifulSoup
from jenkins import Jenkins

from mcp_jenkins.models.build import Build


class JenkinsBuild:
    def __init__(self, jenkins: Jenkins) -> None:
        self._jenkins = jenkins

    @staticmethod
    def _to_model(data: dict) -> Build:
        return Build.model_validate(data)

    def get_running_builds(self) -> list[Build]:
        builds = self._jenkins.get_running_builds()
        return [self._to_model(build) for build in builds]

    def get_build_info(self, fullname: str, number: int) -> Build:
        return self._to_model(self._jenkins.get_build_info(fullname, number))

    def build_job(self, fullname: str, parameters: dict = None) -> int:
        if not parameters:
            for property_ in self._jenkins.get_job_info(fullname).get('property', []):
                if property_.get('parameterDefinitions') is not None:
                    # In jenkins lib, {} is same as None, so I need to mock a foo param to make it work
                    foo = str(uuid4())
                    parameters = {foo: foo} if not parameters else parameters
                    break
        return self._jenkins.build_job(fullname, parameters)

    def get_build_logs(
        self, fullname: str, number: int, pattern: str = None, limit: int = 1000, seq: Literal['asc', 'desc'] = 'asc'
    ) -> str:
        """
        Retrieve logs from a specific build.

        Args:
            fullname: The fullname of the job
            number: The build number
            pattern: A pattern to filter the logs
            limit: The maximum number of lines to retrieve
            seq: Priority order of log returns

        Returns:
            str: The logs of the build
        """
        result = []
        lines = self._jenkins.get_build_console_output(fullname, number).split('\n')
        for line in lines if seq == 'asc' else reversed(lines):
            if pattern is None or re.search(pattern, line):
                result.append(line)
            if len(result) >= limit:
                break
        return '\n'.join(result if seq == 'asc' else reversed(result))

    def stop_build(self, fullname: str, number: int) -> None:
        return self._jenkins.stop_build(fullname, number)

    def get_build_sourcecode(self, fullname: str, number: int) -> str:
        """
        Retrieve the pipeline source code of a specific build in Jenkins.

        Args:
            fullname: The fullname of the job
            number: The build number

        Returns:
            str: The source code of the Jenkins pipeline for the specified build.
        """

        splitted_path = fullname.split('/')

        name = '/job/'.join(splitted_path[:-1])
        short_name = splitted_path[-1]

        jenkins_url = self._jenkins.server.rstrip('/')
        build_info = f'{jenkins_url}/job/{name}/job/{short_name}/{number}/replay'

        response = self._jenkins.jenkins_open(
            requests.Request(
                'GET',
                build_info,
            )
        )

        soup = BeautifulSoup(response, 'html.parser')
        textarea = soup.find('textarea', {'name': '_.mainScript'})
        if textarea:
            return str(textarea.text)
        else:
            return 'No Script found'
