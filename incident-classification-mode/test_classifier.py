import pytest
from classifier import IncidentClassifier, Severity, Category, ThresholdConfig


@pytest.fixture
def clf():
    return IncidentClassifier()


def test_critical_error_rate(clf):
    inc = {"title": "API errors", "metrics": {"error_rate": 0.6}}
    label = clf.classify(inc)
    assert label.severity == Severity.P1
    assert label.category == Category.APP


def test_infra_cpu(clf):
    inc = {"title": "CPU spike on node-01", "metrics": {"cpu_percent": 97}}
    label = clf.classify(inc)
    assert label.severity == Severity.P1
    assert label.category == Category.INFRA


def test_security_breach(clf):
    inc = {"title": "Possible breach detected", "description": "Unauthorized access attempt"}
    label = clf.classify(inc)
    assert label.category == Category.SECURITY
    assert label.severity in (Severity.P1, Severity.P2)


def test_network_latency(clf):
    inc = {"title": "High latency", "metrics": {"latency_ms": 3000}, "source": "datadog-apm"}
    label = clf.classify(inc)
    assert label.severity == Severity.P2
    assert label.category == Category.NETWORK


def test_explicit_severity_and_category(clf):
    inc = {"title": "Low disk", "severity": "P3", "category": "infra", "metrics": {"disk_percent": 75}}
    label = clf.classify(inc)
    assert label.severity == Severity.P3
    assert label.category == Category.INFRA


def test_default_classification(clf):
    inc = {"title": "Something happened"}
    label = clf.classify(inc)
    assert label.severity in set(Severity)
    assert label.category in set(Category)
    assert label.confidence >= clf.config.min_confidence


def test_custom_thresholds():
    cfg = ThresholdConfig(error_rate_critical=0.9, error_rate_high=0.6, error_rate_medium=0.3)
    clf = IncidentClassifier(cfg)
    label = clf.classify({"title": "errors", "metrics": {"error_rate": 0.65}})
    assert label.severity == Severity.P2


def test_output_structure(clf):
    inc = {"title": "OOM kill", "description": "Out of memory on host-3", "assignee": "sre-team"}
    label = clf.classify(inc)
    d = label.to_dict()
    assert d["severity"] in ("P1", "P2", "P3", "P4")
    assert d["category"] in ("infra", "app", "security", "network")
    assert isinstance(d["confidence"], float)
    assert isinstance(d["rules_matched"], list)
    assert len(d["rules_matched"]) > 0
    assert d["overrides"]["assignee"] == "sre-team"


def test_disk_severity(clf):
    label = clf.classify({"title": "Disk full", "metrics": {"disk_percent": 96}})
    assert label.severity == Severity.P1
    label2 = clf.classify({"title": "Disk usage", "metrics": {"disk_percent": 72}})
    assert label2.severity == Severity.P3