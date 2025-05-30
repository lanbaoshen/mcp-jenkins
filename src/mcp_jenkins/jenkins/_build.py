from uuid import uuid4

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

    def get_build_logs(self, fullname: str, number: int) -> str:
        """
        Retrieve logs from a specific build.

        Args:
            fullname: The fullname of the job
            number: The build number

        Returns:
            str: The logs of the build
        """
        return self._jenkins.get_build_console_output(fullname, number)

    def stop_build(self, fullname: str, number: int) -> None:
        return self._jenkins.stop_build(fullname, number)
