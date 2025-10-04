from pydantic import BaseModel, ConfigDict


class JenkinsTestCase(BaseModel):
    model_config = ConfigDict(validate_by_name=True)

    className: str
    name: str
    status: str
    duration: float
    errorDetails: str | None = None
    errorStackTrace: str | None = None
    skipped: bool = False
    age: int = 0


class JenkinsTestSuite(BaseModel):
    model_config = ConfigDict(validate_by_name=True)

    name: str
    duration: float
    cases: list[JenkinsTestCase] = []


class JenkinsTestReport(BaseModel):
    model_config = ConfigDict(validate_by_name=True)

    failCount: int
    skipCount: int
    passCount: int
    totalCount: int
    duration: float
    suites: list[JenkinsTestSuite] = []
