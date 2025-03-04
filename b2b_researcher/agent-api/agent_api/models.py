from pydantic import BaseModel
from datetime import datetime


class AnalysisStep(BaseModel):
    idx: int
    message: str
    details: str
    output: str
    totalSteps: int


class AnalysisSteps(BaseModel):
    steps: list[AnalysisStep]


class AgentExecutionRequest(BaseModel):
    submissionId: str
    companyUrl: str
    targetUrl: str


class AgentExecutionResponse(BaseModel):
    submissionId: str
    status: str
    startedAt: datetime