import re

from jenkins import Jenkins

from mcp_jenkins.models.job import Folder, Job, JobBase, MultibranchPipeline


class JenkinsJob:
    def __init__(self, jenkins: Jenkins) -> None:
        self._jenkins = jenkins

    @staticmethod
    def _to_model(job_data: dict) -> JobBase:
        if job_data['_class'].endswith('Folder'):
            return Folder.model_validate(job_data)
        elif job_data['_class'].endswith('WorkflowMultiBranchProject'):
            return MultibranchPipeline.model_validate(job_data)
        return Job.model_validate(job_data)

    def get_all_jobs(self) -> list[JobBase]:
        return [self._to_model(job) for job in self._jenkins.get_jobs(folder_depth=20)]

    def search_jobs(
        self,
        class_pattern: str = None,
        name_pattern: str = None,
        fullname_pattern: str = None,
        url_pattern: str = None,
        color_pattern: str = None,
    ) -> list[JobBase]:
        result = []

        jobs = self.get_all_jobs()

        class_pattern = re.compile(class_pattern) if class_pattern else None
        name_pattern = re.compile(name_pattern) if name_pattern else None
        fullname_pattern = re.compile(fullname_pattern) if fullname_pattern else None
        url_pattern = re.compile(url_pattern) if url_pattern else None
        color_pattern = re.compile(color_pattern) if color_pattern else None

        for job in jobs:
            if class_pattern and not class_pattern.match(job.class_):
                continue
            if name_pattern and not name_pattern.match(job.name):
                continue
            if fullname_pattern and not fullname_pattern.match(job.fullname):
                continue
            if url_pattern and not url_pattern.match(job.url):
                continue
            # Folder and MultibranchPipeline do not have attribute color
            if color_pattern and (isinstance(job, Folder | MultibranchPipeline) or not color_pattern.match(job.color)):
                continue
            result.append(job)

        return result

    def get_job_config(self, fullname: str) -> str:
        return self._jenkins.get_job_config(fullname)

    def get_job_info(self, fullname: str) -> JobBase:
        return self._to_model(self._jenkins.get_job_info(fullname, depth=1))
