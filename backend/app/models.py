"""Pydantic domain models for ArenaPulse."""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class UserRole(str, Enum):
    FAN = "fan"
    VOLUNTEER = "volunteer"
    ORGANIZER = "organizer"


class User(BaseModel):
    id: int
    username: str
    email: str
    role: UserRole
    created_at: datetime


class Token(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class TokenData(BaseModel):
    user_id: int | None = None
    username: str | None = None
    role: UserRole | None = None


class PathNode(BaseModel):
    name: str
    type: str  # Gate, Zone, Section, Exit, etc.
    distance_m: int | None = None
    step_free: bool = True
    estimated_time_s: int | None = None


class NavigationRequest(BaseModel):
    start_location: str = Field(..., description="Zone or Section name, e.g. 'Section_214'")
    destination_intent: str = Field(
        ...,
        description="e.g. 'nearest_exit', 'nearest_restroom', 'transit', 'Gate_C'",
    )
    step_free: bool = Field(False, description="Require step-free route")
    language: str = Field("en", description="ISO language code")
    user_id: int | None = None


class NavigationResponse(BaseModel):
    path: list[PathNode]
    total_distance_m: int
    total_time_s: int
    step_free: bool
    explanation: str
    avoid_reason: str | None = None


class ChatMessage(BaseModel):
    role: str  # user | assistant
    content: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class ChatRequest(BaseModel):
    message: str = Field(..., max_length=2000)
    language: str = "en"
    session_id: str | None = None
    stream: bool = False


class ChatResponse(BaseModel):
    response: str
    sources: list[dict[str, Any]] = []
    detected_intent: str = "general"
    language: str = "en"


class CrowdAlertSeverity(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ZoneDensity(BaseModel):
    zone: str
    density: float = Field(..., ge=0.0, le=1.0)
    capacity: int
    current_occupancy: int
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    trend: float = 0.0  # change per minute


class CrowdAlert(BaseModel):
    id: str
    zone: str
    severity: CrowdAlertSeverity
    message: str
    detected_at: datetime
    density: float = Field(..., ge=0.0, le=1.0)
    predicted_crossing_time_min: float | None = None
    suggested_mitigation: str
    affected_population: int


class OpsActionStatus(str, Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    COMPLETED = "completed"


class OpsActionPriority(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class OpsAction(BaseModel):
    id: int
    title: str
    description: str
    reasoning: str
    priority: OpsActionPriority
    status: OpsActionStatus
    recommended_by: str
    approved_by: int | None = None
    approved_at: datetime | None = None
    created_at: datetime
    affected_zones: list[str]
    affected_population: int
    time_to_impact_min: float | None = None


class TransitMode(str, Enum):
    METRO = "metro"
    BUS = "bus"
    RIDESHARE = "rideshare"
    WALK = "walk"
    SHUTTLE = "shuttle"


class SustainabilitySummary(BaseModel):
    transit_split: dict[TransitMode, float]
    estimated_co2_kg: float
    sustainability_score: int = Field(..., ge=0, le=100)
    eco_tips: list[str]
    waste_bin_fill_pct: dict[str, float]
    water_refill_usage: int


class StadiumFact(BaseModel):
    entity_type: str
    name: str
    attributes: dict[str, Any]


class AccessibilitySettings(BaseModel):
    high_contrast: bool = False
    large_text: bool = False
    reduced_motion: bool = False
    voice_enabled: bool = False
