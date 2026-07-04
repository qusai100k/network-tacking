from datetime import datetime
from typing import Literal, Optional, Union

from pydantic import BaseModel, ConfigDict, Field


Severity = Literal["low", "medium", "high", "critical"]
InternetStatus = Literal["online", "degraded", "offline"]


class TelemetrySnapshot(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    timestamp: datetime
    internet_status: InternetStatus
    download_speed_mbps: float
    upload_speed_mbps: float
    bandwidth_usage_percent: float
    throughput_mbps: float
    ping_ms: float
    latency_ms: float
    jitter_ms: float
    packet_loss_percent: float
    cpu_usage_percent: float
    ram_usage_percent: float
    disk_usage_percent: float
    network_adapter: str
    connection_type: str
    public_ip: str
    private_ip: str
    gateway: str
    dns: list[str]
    mac_address: str
    network_uptime_seconds: float
    isp: str


class AlertRecord(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    kind: str
    severity: Severity
    message: str
    created_at: datetime


class BootstrapPayload(BaseModel):
    latest: Optional[TelemetrySnapshot]
    history: list[TelemetrySnapshot]
    alerts: list[AlertRecord]


class TelemetryEnvelope(BaseModel):
    telemetry: TelemetrySnapshot
    alerts: list[AlertRecord] = []


class DeviceRecord(BaseModel):
    ip_address: str
    mac_address: str
    hostname: str
    vendor: str
    operating_system: str
    device_type: str
    status: str


class ProcessNetworkRecord(BaseModel):
    application: str
    pid: int
    upload_kbps: Optional[float] = None
    download_kbps: Optional[float] = None
    current_bandwidth_kbps: Optional[float] = None
    destination_ip: str
    destination_country: str
    protocol: str
    risk_level: str


class ConnectionRecord(BaseModel):
    remote_ip: str
    country: str
    latency_ms: Optional[float] = None
    port: int
    protocol: str
    application: str
    status: str
    suspicious_score: int


class AIRecommendation(BaseModel):
    id: str
    problem_summary: str
    severity: Severity
    confidence_score: int = Field(ge=0, le=100)
    possible_cause: str
    technical_explanation: str
    recommended_fixes: list[str]
    estimated_improvement: str
    priority_level: Literal["low", "medium", "high", "urgent"]
    supporting_metrics: dict[str, Union[str, float, int]]


class PredictionRecord(BaseModel):
    metric: str
    horizon: str
    predicted_value: float
    unit: str
    confidence_score: int = Field(ge=0, le=100)
    interpretation: str


class AIAnalysisPayload(BaseModel):
    generated_at: datetime
    recommendations: list[AIRecommendation]
    predictions: list[PredictionRecord]


class AIChatRequest(BaseModel):
    message: str
    provider: Optional[str] = None


class AIChatResponse(BaseModel):
    generated_at: datetime
    answer: str