from enum import Enum
from typing import Dict, List, Optional
from pydantic import BaseModel, Field


class Severity(str, Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


class Channel(str, Enum):
    SLACK = "slack"
    PAGERDUTY = "pagerduty"
    EMAIL = "email"


class Incident(BaseModel):
    id: str
    title: str
    description: str = ""
    severity: Severity
    category: str
    metadata: Dict = Field(default_factory=dict)


class RoutingRule(BaseModel):
    severities: List[Severity]
    categories: List[str] = Field(default_factory=lambda: ["*"])
    channels: List[Channel]


class RateLimitConfig(BaseModel):
    max_tokens: int = 10
    refill_rate: float = 1.0


class ChannelConfig(BaseModel):
    slack_webhook_url: Optional[str] = None
    pagerduty_routing_key: Optional[str] = None
    pagerduty_api_url: str = "https://events.pagerduty.com/v2/enqueue"
    email_smtp_host: Optional[str] = None
    email_smtp_port: int = 587
    email_username: Optional[str] = None
    email_password: Optional[str] = None
    email_from: Optional[str] = None
    email_recipients: Optional[List[str]] = None


class DispatcherConfig(BaseModel):
    routing_rules: List[RoutingRule]
    channel_config: ChannelConfig = Field(default_factory=ChannelConfig)
    rate_limits: Dict[str, RateLimitConfig] = Field(default_factory=dict)