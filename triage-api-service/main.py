from __future__ import annotations
import os
import uuid
import httpx
import logging
from datetime import datetime
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException
from typing import Optional

from models import (
    AlertInput, Incident, IncidentResponse,
    TriageUpdate, Severity, IncidentStatus, ErrorResponse,
)

logger = logging.getLogger("triage-api")
incident_store: dict[str, Incident] = {}
fingerprint_index: dict[str, str] = {}

SLACK_WEBHOOK_URL = os.getenv("SLACK_WEBHOOK_URL", "")
PAGERDUTY_API_KEY = os.getenv("PAGERDUTY_API_KEY", "")
PAGERDUTY_SERVICE_ID = os.getenv("PAGERDUTY_SERVICE_ID", "")

SEVERITY_SCORE = {
    Severity.CRITICAL: 4, Severity.HIGH: 3,
    Severity.MEDIUM: 2, Severity.LOW: 1, Severity.INFO: 0,
}


def classify_severity(alert: AlertInput) -> Severity:
    score = SEVERITY_SCORE.get(alert.raw_severity, 2)
    if alert.labels.get("env") in ("production", "prod"):
        score = min(score + 1, 4)
    if alert.labels.get("oncall") == "true":
        score = min(score + 1, 4)
    if "critical" in alert.title.lower() or "outage" in alert.title.lower():
        score = 4
    for sev, val in reversed(list(SEVERITY_SCORE.items())):
        if val <= score:
            return sev
    return Severity.MEDIUM


async def notify_slack(incident: Incident) -> bool:
    if not SLACK_WEBHOOK_URL:
        logger.info("Slack webhook not configured; skipping")
        return False
    payload = {
        "text": f"🚨 [{incident.severity.value.upper()}] {incident.title}",
        "blocks": [{"type": "section", "text": {
            "type": "mrkdwn",
            "text": f"*{incident.severity.value.upper()}* — `{incident.id}`\n{incident.description}",
        }}],
    }
    try:
        async with httpx.AsyncClient(timeout=5) as client:
            resp = await client.post(SLACK_WEBHOOK_URL, json=payload)
            resp.raise_for_status()
            return True
    except Exception as exc:
        logger.error("Slack notification failed: %s", exc)
        return False


async def notify_pagerduty(incident: Incident) -> bool:
    if not PAGERDUTY_API_KEY or not PAGERDUTY_SERVICE_ID:
        logger.info("PagerDuty not configured; skipping")
        return False
    payload = {
        "event": {"action": "trigger",
                   "severity": incident.severity.value,
                   "source": {"id": incident.id, "type": "incident"},
                   "summary": incident.title,
                   "component": incident.rule_id},
        "routing_key": PAGERDUTY_API_KEY,
    }
    try:
        async with httpx.AsyncClient(timeout=5) as client:
            resp = await client.post(
                "https://events.pagerduty.com/v2/events",
                json=payload,
                headers={"Authorization": f"Token token={PAGERDUTY_API_KEY}"},
            )
            resp.raise_for_status()
            return True
    except Exception as exc:
        logger.error("PagerDuty notification failed: %s", exc)
        return False


@asynccontextmanager
async def lifespan(app: FastAPI):
    logging.basicConfig(level=logging.INFO)
    logger.info("Triage API starting — Slack: %s, PD: %s",
                "configured" if SLACK_WEBHOOK_URL else "off",
                "configured" if PAGERDUTY_API_KEY else "off")
    yield

app = FastAPI(title="Incident Triage API", version="1.0.0", lifespan=lifespan)


@app.post("/incidents", response_model=IncidentResponse,
          responses={409: {"model": ErrorResponse}})
async def create_incident(alert: AlertInput):
    if alert.fingerprint in fingerprint_index:
        existing_id = fingerprint_index[alert.fingerprint]
        existing = incident_store[existing_id]
        existing.alert_count += 1
        new_sev = classify_severity(alert)
        if SEVERITY_SCORE[new_sev] > SEVERITY_SCORE[existing.severity]:
            existing.severity = new_sev
        existing.updated_at = datetime.utcnow()
        return IncidentResponse(incident=existing, notifications_sent=[])

    incident_id = str(uuid.uuid4())
    severity = classify_severity(alert)
    incident = Incident(
        id=incident_id, fingerprint=alert.fingerprint,
        rule_id=alert.rule_id, title=alert.title,
        description=alert.description, severity=severity,
        labels=alert.labels, source=alert.source,
    )
    incident_store[incident_id] = incident
    fingerprint_index[alert.fingerprint] = incident_id

    notifications: list[str] = []
    if await notify_slack(incident):
        notifications.append("slack")
    if severity in (Severity.CRITICAL, Severity.HIGH):
        if await notify_pagerduty(incident):
            notifications.append("pagerduty")

    return IncidentResponse(incident=incident, notifications_sent=notifications)


@app.get("/incidents/{incident_id}", response_model=IncidentResponse,
         responses={404: {"model": ErrorResponse}})
async def get_incident(incident_id: str):
    if incident_id not in incident_store:
        raise HTTPException(status_code=404, detail="Incident not found")
    return IncidentResponse(incident=incident_store[incident_id])


@app.patch("/incidents/{incident_id}/triage", response_model=IncidentResponse,
           responses={404: {"model": ErrorResponse}, 409: {"model": ErrorResponse}})
async def update_triage(incident_id: str, update: TriageUpdate):
    if incident_id not in incident_store:
        raise HTTPException(status_code=404, detail="Incident not found")
    incident = incident_store[incident_id]
    if incident.status == IncidentStatus.RESOLVED:
        raise HTTPException(status_code=409, detail="Cannot triage a resolved incident")
    if update.severity is not None:
        incident.severity = update.severity
    if update.status is not None:
        incident.status = update.status
    if update.assignee is not None:
        incident.assignee = update.assignee
    if update.notes is not None:
        incident.notes = update.notes
    incident.updated_at = datetime.utcnow()

    notifications: list[str] = []
    if incident.status == IncidentStatus.ACKNOWLEDGED:
        if await notify_slack(incident):
            notifications.append("slack")

    return IncidentResponse(incident=incident, notifications_sent=notifications)