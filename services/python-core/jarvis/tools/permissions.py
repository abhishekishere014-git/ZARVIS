"""Security permissions and risk policy models for tool execution."""

from typing import Set
from pydantic import BaseModel, Field
from jarvis.tools.models import ApprovalMode, RiskLevel, ToolPermission


class SecurityProfile(BaseModel):
    """Execution security authorization granted to a caller / agent."""

    granted_permissions: Set[ToolPermission] = Field(
        default_factory=lambda: {
            ToolPermission.READ,
            ToolPermission.WRITE,
        },
        description="Active permission set granted to the executor",
    )
    max_risk_level: RiskLevel = Field(
        default=RiskLevel.MEDIUM,
        description="Highest risk level allowed without explicit user approval",
    )
    auto_approve_safe: bool = Field(
        default=True,
        description="Whether tools with LOW/MEDIUM risk can be auto-approved",
    )

    def has_permission(self, permission: ToolPermission) -> bool:
        return permission in self.granted_permissions

    def has_all_permissions(self, required: Set[ToolPermission]) -> bool:
        return required.issubset(self.granted_permissions)

    def is_risk_acceptable(self, risk: RiskLevel) -> bool:
        risk_order = [RiskLevel.LOW, RiskLevel.MEDIUM, RiskLevel.HIGH, RiskLevel.CRITICAL]
        return risk_order.index(risk) <= risk_order.index(self.max_risk_level)
