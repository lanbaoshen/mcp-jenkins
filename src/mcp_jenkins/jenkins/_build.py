import re
from typing import Literal
from uuid import uuid4

import requests
from bs4 import BeautifulSoup
from jenkins import Jenkins

from mcp_jenkins.models.build import Build
from mcp_jenkins.models.test_result import JenkinsTestCase, JenkinsTestReport, JenkinsTestSuite


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

    def get_test_report(self, fullname: str, number: int) -> JenkinsTestReport:
        """
        Retrieve test results from a specific build in Jenkins.

        Args:
            fullname: The fullname of the job
            number: The build number

        Returns:
            TestReport: The test results of the build
        """
        test_report = self._jenkins.get_build_test_report(fullname, number)

        # If test_report is None (no test results), return empty test report
        if test_report is None:
            return JenkinsTestReport(
                failCount=0,
                skipCount=0,
                passCount=0,
                totalCount=0,
                duration=0.0,
                suites=[],
            )

        # Parse test suites and cases
        suites = []
        for suite_data in test_report.get('suites', []):
            cases = []
            for case_data in suite_data.get('cases', []):
                cases.append(
                    JenkinsTestCase(
                        className=case_data.get('className', ''),
                        name=case_data.get('name', ''),
                        status=case_data.get('status', ''),
                        duration=case_data.get('duration', 0.0),
                        errorDetails=case_data.get('errorDetails'),
                        errorStackTrace=case_data.get('errorStackTrace'),
                        skipped=case_data.get('skipped', False),
                        age=case_data.get('age', 0),
                    )
                )
            suites.append(
                JenkinsTestSuite(name=suite_data.get('name', ''), duration=suite_data.get('duration', 0.0), cases=cases)
            )

        return JenkinsTestReport(
            failCount=test_report.get('failCount', 0),
            skipCount=test_report.get('skipCount', 0),
            passCount=test_report.get('passCount', 0),
            totalCount=test_report.get('totalCount', 0),
            duration=test_report.get('duration', 0.0),
            suites=suites,
        )
