from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class Severity(Enum):
    P1 = "P1"
    P2 = "P2"
    P3 = "P3"
    P4 = "P4"


class Category(Enum):
    INFRA = "infra"
    APP = "app"
    SECURITY = "security"
    NETWORK = "network"


@dataclass
class TriageLabel:
    severity: Severity
    category: Category
    confidence: float
    rules_matched: List[str] = field(default_factory=list)
    overrides: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "severity": self.severity.value,
            "category": self.category.value,
            "confidence": round(self.confidence, 3),
            "rules_matched": self.rules_matched,
            "overrides": self.overrides,
        }


@dataclass
class ThresholdConfig:
    error_rate_critical: float = 0.5
    error_rate_high: float = 0.2
    error_rate_medium: float = 0.05
    latency_ms_critical: float = 5000
    latency_ms_high: float = 2000
    latency_ms_medium: float = 500
    cpu_pct_critical: float = 95
    cpu_pct_high: float = 80
    cpu_pct_medium: float = 60
    disk_pct_critical: float = 95
    disk_pct_high: float = 85
    disk_pct_medium: float = 70
    min_confidence: float = 0.3
    keyword_boost: float = 0.15


_CATEGORY_KEYWORDS: Dict[Category, List[str]] = {
    Category.INFRA: [
        "cpu", "memory", "disk", "oom", "out of memory", "host", "node",
        "vm", "pod", "container", "kube", "deployment", "replicaset",
        "resource", "capacity", "threshold exceeded", "iops", "throughput",
    ],
    Category.APP: [
        "error", "exception", "traceback", "crash", "500", "502", "503",
        "504", "timeout", "fail", "panic", "segfault", "deadlock",
        "assertion", "nullref", "unhandled", "apdex", "error_rate",
    ],
    Category.SECURITY: [
        "auth", "unauthorized", "forbidden", "breach", "intrusion", "malware",
        "vulnerability", "cve", "exploit", "phishing", "ddos", "brute",
        "privilege", "escalation", "token", "credential", "secret leak",
        "ssl", "tls", "certificate", "encryption",
    ],
    Category.NETWORK: [
        "dns", "latency", "packet", "dropped", "connection refused",
        "connection reset", "tcp", "udp", "route", "bandwidth", "packet loss",
        "unreachable", "socket", "firewall", "load balancer", "proxy",
        "gateway", "ping", "ttl",
    ],
}

_SEVERITY_KEYWORDS: Dict[Severity, List[str]] = {
    Severity.P1: ["outage", "down", "critical", "catastrophic", "data loss", "breach"],
    Severity.P2: ["degraded", "high error", "partial outage", "severe", "urgent"],
    Severity.P3: ["elevated", "warning", "intermittent", "slow", "retry"],
    Severity.P4: ["info", "low", "minor", "transient", "normal"],
}


class IncidentClassifier:
    def __init__(self, config: Optional[ThresholdConfig] = None):
        self.config = config or ThresholdConfig()
        self._cat_patterns = {
            cat: [re.compile(rf"\b{re.escape(kw)}\b", re.IGNORECASE) for kw in kws]
            for cat, kws in _CATEGORY_KEYWORDS.items()
        }
        self._sev_patterns = {
            sev: [re.compile(rf"\b{re.escape(kw)}\b", re.IGNORECASE) for kw in kws]
            for sev, kws in _SEVERITY_KEYWORDS.items()
        }

    def classify(self, incident: Dict[str, Any]) -> TriageLabel:
        severity, sev_conf, sev_rules = self._determine_severity(incident)
        category, cat_conf, cat_rules = self._determine_category(incident)
        confidence = (sev_conf + cat_conf) / 2.0
        confidence = max(confidence, self.config.min_confidence)
        overrides = self._extract_overrides(incident)
        return TriageLabel(
            severity=severity,
            category=category,
            confidence=confidence,
            rules_matched=sev_rules + cat_rules,
            overrides=overrides,
        )

    def _determine_severity(self, inc: Dict[str, Any]) -> tuple[Severity, float, List[str]]:
        rules: List[str] = []
        scores: Dict[Severity, float] = {s: 0.0 for s in Severity}
        text = self._text(inc)

        for sev, patterns in self._sev_patterns.items():
            for pat in patterns:
                if pat.search(text):
                    scores[sev] += self.config.keyword_boost
                    rules.append(f"sev_keyword:{pat.pattern}")

        for metric, value in inc.get("metrics", {}).items():
            rule_sev = self._metric_severity(metric, value)
            if rule_sev:
                scores[rule_sev] += 0.3
                rules.append(f"metric:{metric}={value}")

        if "severity" in inc:
            forced = self._parse_severity(inc["severity"])
            if forced:
                scores[forced] += 0.6
                rules.append(f"explicit_severity:{forced.value}")

        best = max(Severity, key=lambda s: scores[s])
        conf = min(scores[best], 1.0) if scores[best] > 0 else self.config.min_confidence
        if conf <= 0 and not rules:
            best = Severity.P3
            conf = self.config.min_confidence
        return best, conf, rules

    def _metric_severity(self, metric: str, value: float) -> Optional[Severity]:
        c = self.config
        if "error_rate" in metric:
            if value >= c.error_rate_critical:
                return Severity.P1
            if value >= c.error_rate_high:
                return Severity.P2
            if value >= c.error_rate_medium:
                return Severity.P3
            return Severity.P4
        if "latency" in metric or "duration" in metric:
            if value >= c.latency_ms_critical:
                return Severity.P1
            if value >= c.latency_ms_high:
                return Severity.P2
            if value >= c.latency_ms_medium:
                return Severity.P3
            return Severity.P4
        if "cpu" in metric:
            if value >= c.cpu_pct_critical:
                return Severity.P1
            if value >= c.cpu_pct_high:
                return Severity.P2
            if value >= c.cpu_pct_medium:
                return Severity.P3
            return Severity.P4
        if "disk" in metric or "storage" in metric:
            if value >= c.disk_pct_critical:
                return Severity.P1
            if value >= c.disk_pct_high:
                return Severity.P2
            if value >= c.disk_pct_medium:
                return Severity.P3
            return Severity.P4
        return None

    def _determine_category(self, inc: Dict[str, Any]) -> tuple[Category, float, List[str]]:
        rules: List[str] = []
        scores: Dict[Category, float] = {c: 0.0 for c in Category}
        text = self._text(inc)

        for cat, patterns in self._cat_patterns.items():
            for pat in patterns:
                if pat.search(text):
                    scores[cat] += self.config.keyword_boost
                    rules.append(f"cat_keyword:{pat.pattern}")

        if "category" in inc:
            forced = self._parse_category(inc["category"])
            if forced:
                scores[forced] += 0.6
                rules.append(f"explicit_category:{forced.value}")

        if "source" in inc:
            src = str(inc["source"]).lower()
            if src in ("kubernetes", "prometheus", "node_exporter"):
                scores[Category.INFRA] += 0.2
                rules.append(f"source_infra:{src}")
            elif src in ("app", "application", "sentry", "datadog-apm"):
                scores[Category.APP] += 0.2
                rules.append(f"source_app:{src}")
            elif src in ("waf", "ids", "vault", "okta"):
                scores[Category.SECURITY] += 0.2
                rules.append(f"source_security:{src}")

        best = max(Category, key=lambda c: scores[c])
        conf = min(scores[best], 1.0) if scores[best] > 0 else self.config.min_confidence
        return best, conf, rules

    def _text(self, inc: Dict[str, Any]) -> str:
        parts = [inc.get("title", ""), inc.get("description", ""), inc.get("message", "")]
        parts.extend(str(v) for v in inc.get("tags", {}).values())
        return " ".join(p for p in parts if p)

    @staticmethod
    def _parse_severity(val: Any) -> Optional[Severity]:
        try:
            return Severity(str(val).upper())
        except ValueError:
            return None

    @staticmethod
    def _parse_category(val: Any) -> Optional[Category]:
        try:
            return Category(str(val).lower())
        except ValueError:
            return None

    @staticmethod
    def _extract_overrides(inc: Dict[str, Any]) -> Dict[str, Any]:
        return {k: inc[k] for k in ("assignee", "runbook", "escalation_policy") if k in inc}