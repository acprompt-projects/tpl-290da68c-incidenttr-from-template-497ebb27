from __future__ import annotations
from enum import Enum
from datetime import datetime
from pydantic import BaseModel, Field
from typing import Optional


class Severity(str, Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


class IncidentStatus(str, Enum):
    OPEN = "open"
    TRIAGING = "triaging"
    ACKNOWLEDGED = "acknowledged"
    RESOLVED = "resolved"


class AlertSource(str, Enum):
    RULES_ENGINE = "rules_engine"
    MANUAL = "manual"
    INTEGRATION = "integration"


class AlertInput(BaseModel):
    rule_id: str = Field(..., description="ID of the rule that triggered this alert")
    fingerprint: str = Field(..., description="Dedup key for correlation")
    title: str
    description: str = ""
    raw_severity: Severity = Severity.MEDIUM
    labels: dict[str, str] = Field(default_factory=dict)
    source: AlertSource = AlertSource.RULES_ENGINE


class TriageUpdate(BaseModel):
    severity: Optional[Severity] = None
    status: Optional[IncidentStatus] = None
    assignee: Optional[str] = None
    notes: Optional[str] = None


class Incident(BaseModel):
    id: str
    fingerprint: str
    rule_id: str
    title: str
    description: str
    severity: Severity
    status: IncidentStatus = IncidentStatus.OPEN
    assignee: Optional[str] = None
    notes: Optional[str] = None
    labels: dict[str, str] = Field(default_factory=dict)
    alert_count: int = 1
    source: AlertSource = AlertSource.RULES_ENGINE
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class IncidentResponse(BaseModel):
    incident: Incident
    notifications_sent: list[str] = Field(default_factory=list)


class ErrorResponse(BaseModel):
    detail: str
    error_code: Optional[str] = None