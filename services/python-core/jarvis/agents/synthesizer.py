"""Synthesizer distilling multi-agent task observations into a single coherent JARVIS response."""

import logging
from pathlib import Path
from typing import Optional
from jarvis.agents.models import (
    AgentFinalResponse,
    AgentRun,
    AgentState,
    TaskState,
    VerificationState,
)
from jarvis.ai.models import ChatMessage, LLMRequest
from jarvis.ai.router import AIRouter

logger = logging.getLogger("jarvis.agents.synthesizer")


class FinalSynthesizer:
    """Consolidates verified multi-agent task executions into a single authoritative user response."""

    def __init__(self, router: Optional[AIRouter] = None) -> None:
        self.router = router

    async def synthesize(self, run: AgentRun) -> AgentFinalResponse:
        """Produces a unified, evidence-based final response from the completed or terminated run."""
        task_stats = {
            "total": len(run.plan.tasks) if run.plan else 0,
            "completed": len(run.completed_tasks),
            "failed": len(run.failed_tasks),
        }

        # Collect verified artifacts
        verified_artifacts = []
        for ver in run.verifications.values():
            if ver.state == VerificationState.PASSED:
                verified_artifacts.extend(ver.verified_artifacts)
        verified_artifacts = list(dict.fromkeys(verified_artifacts))  # deduplicate preserving order

        # Determine overall narrative
        if run.state == AgentState.COMPLETED:
            base_summary = f"Objective successfully accomplished: '{run.goal.user_prompt}'."
        elif run.state == AgentState.CANCELLED:
            base_summary = f"Execution cancelled for goal: '{run.goal.user_prompt}'."
        else:
            base_summary = f"Execution incomplete for goal: '{run.goal.user_prompt}'."

        findings = []
        for task_id, res in run.task_results.items():
            if res.status == TaskState.COMPLETED and res.output:
                out_str = str(res.output)
                if len(out_str) > 200:
                    out_str = out_str[:197] + "..."
                findings.append(f"• {task_id}: {out_str}")

        if findings:
            findings_text = "\n" + "\n".join(findings)
        else:
            findings_text = ""

        if verified_artifacts:
            artifact_text = f"\nVerified artifacts created ({len(verified_artifacts)}):\n" + "\n".join(
                f"• {Path(a).name}" for a in verified_artifacts
            )
        else:
            artifact_text = ""

        summary_text = f"{base_summary}{findings_text}{artifact_text}"

        # If an AI router is available and there are multiple complex findings, synthesize via LLM
        if self.router and findings:
            try:
                system_prompt = (
                    "You are JARVIS. Synthesize a concise, authoritative, professional status response "
                    "for the user summarizing the completed tasks. Do NOT expose internal chain of thought, "
                    "reasoning logs, or internal agent IDs. Focus strictly on what was achieved and produced."
                )
                user_msg = (
                    f"User Goal: {run.goal.user_prompt}\n"
                    f"Completed Tasks: {findings}\n"
                    f"Verified Artifacts: {verified_artifacts}"
                )
                req = LLMRequest(
                    messages=[
                        ChatMessage.system(system_prompt),
                        ChatMessage.user(user_msg),
                    ],
                    temperature=0.3,
                )
                llm_res = await self.router.generate(req)
                if llm_res.content:
                    summary_text = llm_res.content.strip()
            except Exception as exc:
                logger.warning("LLM synthesis failed, falling back to deterministic template: %s", exc)

        return AgentFinalResponse(
            run_id=run.run_id,
            goal_id=run.goal.id,
            status=run.state,
            summary=summary_text,
            verified_artifacts=verified_artifacts,
            task_statistics=task_stats,
            execution_time_ms=round(run.duration_ms, 2),
            error=run.error,
        )
