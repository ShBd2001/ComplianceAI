from __future__ import annotations

from typing import List, Literal

from pydantic import BaseModel, Field


DomainName = Literal["CYBER", "RGPD", "RSE"]
Severity = Literal["CRITIQUE", "MOYEN", "FAIBLE"]
Confidence = Literal["haute", "moyenne", "faible"]


class ContextPack(BaseModel):
    profile_summary: str
    executive_focus: str
    key_exposures: List[str] = Field(default_factory=list, max_length=8)
    regulatory_focus: List[str] = Field(default_factory=list, max_length=8)
    questionnaire_angles: List[str] = Field(default_factory=list, max_length=8)
    reporting_tone: str


class QuestionItem(BaseModel):
    id: str
    domain: DomainName
    label: str
    help_text: str
    rationale: str
    weight: int = Field(ge=1, le=20)
    critical: bool = False


class QuestionnairePack(BaseModel):
    intro: str
    questions: List[QuestionItem] = Field(min_length=9, max_length=21)


class DomainRisk(BaseModel):
    title: str
    severity: Severity
    reason: str
    business_impact: str


class DomainOutput(BaseModel):
    domain: DomainName
    score: int = Field(ge=0, le=100)
    summary: str
    strengths: List[str] = Field(default_factory=list, max_length=5)
    gaps: List[str] = Field(default_factory=list, max_length=6)
    risks: List[DomainRisk] = Field(default_factory=list, max_length=6)
    quick_wins: List[str] = Field(default_factory=list, max_length=5)
    recommended_actions: List[str] = Field(default_factory=list, max_length=6)
    confidence: Confidence


class OrchestratorOutput(BaseModel):
    executive_summary: str
    business_takeaway: str
    global_score: int = Field(ge=0, le=100)
    risk_level: Literal["faible", "modéré", "élevé"]
    top_priorities: List[str] = Field(default_factory=list, max_length=8)
    roadmap_30: List[str] = Field(default_factory=list, max_length=6)
    roadmap_60: List[str] = Field(default_factory=list, max_length=6)
    roadmap_90: List[str] = Field(default_factory=list, max_length=6)
    watchouts: List[str] = Field(default_factory=list, max_length=5)
    financial_range_low: int = Field(ge=0)
    financial_range_high: int = Field(ge=0)
