"""
Pydantic models for structured agent responses
"""

from typing import List, Optional, Dict, Any, Literal
from pydantic import BaseModel, Field


class Citation(BaseModel):
    """Reference to source code location"""
    path: str = Field(description="File path relative to repository root")
    start_line: int = Field(description="Starting line number")
    end_line: int = Field(description="Ending line number")


class RetrievedSource(BaseModel):
    """External source from Tavily search"""
    title: str = Field(description="Title of the source")
    url: str = Field(description="URL of the source")


class ProposedPatch(BaseModel):
    """Proposed code changes in unified diff format"""
    status: Literal["FINAL", "DRAFT"] = Field(description="Status of the patch")
    diff: str = Field(description="Unified diff content")


class TestSuggestion(BaseModel):
    """Test suggestions for proposed changes"""
    suggested: bool = Field(description="Whether tests are suggested")
    commands: List[str] = Field(default=[], description="Test commands to run")
    new_tests: List[Dict[str, str]] = Field(
        default=[], 
        description="New test files to create with their purpose"
    )


class RiskAssessment(BaseModel):
    """Risk assessment for proposed changes"""
    level: Literal["low", "medium", "high"] = Field(description="Risk level")
    concerns: List[str] = Field(default=[], description="Specific risk concerns")
    roll_back: str = Field(description="How to roll back the changes")


class NavigatorResponse(BaseModel):
    """Structured response from the navigator agent"""
    answer: str = Field(description="Developer-friendly explanation")
    citations: List[Citation] = Field(
        default=[], 
        description="Repository code citations"
    )
    retrieved_sources: List[RetrievedSource] = Field(
        default=[], 
        description="External sources from Tavily"
    )
    proposed_patch: Optional[ProposedPatch] = Field(
        default=None,
        description="Proposed code changes if applicable"
    )
    tests: Optional[TestSuggestion] = Field(
        default=None,
        description="Test suggestions for changes"
    )
    risk: Optional[RiskAssessment] = Field(
        default=None,
        description="Risk assessment for changes"
    )