from jenkins import Jenkins

from mcp_jenkins.jenkins._build import JenkinsBuild
from mcp_jenkins.jenkins._job import JenkinsJob
from mcp_jenkins.jenkins._node import JenkinsNode
from mcp_jenkins.jenkins._queue_item import JenkinsQueueItem


class JenkinsClient:
    def __init__(self, *, url: str, username: str, password: str, timeout: int = 5) -> None:
        self._jenkins = Jenkins(url=url, username=username, password=password, timeout=timeout)

        self.job = JenkinsJob(self._jenkins)
        self.build = JenkinsBuild(self._jenkins)
        self.node = JenkinsNode(self._jenkins)
        self.queue_item = JenkinsQueueItem(self._jenkins)
