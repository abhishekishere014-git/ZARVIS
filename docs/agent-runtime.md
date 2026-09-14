# JARVIS Agent Runtime User & Developer Guide

## 1. Quick Start

### Instantiating the Agent System
```python
from jarvis.agents.factory import build_agent_system
from jarvis.tools.factory import build_tool_system

# 1. Build Phase 04 Tool Subsystem
tool_system = build_tool_system()

# 2. Build Phase 05 Autonomous Multi-Agent Runtime
agent_system = build_agent_system(tool_system=tool_system)

# 3. Execute a high-level goal
response = await agent_system.orchestrator.run("Create an executive presentation on AI security")

print("Status:", response.status.value)
print("Summary:", response.summary)
print("Artifacts:", response.verified_artifacts)
```

---

## 2. Orchestration State Machine

```
   IDLE
     │
     ▼
  PLANNING  ──(PlannerAgent decomposes goal)──► Plan Created
     │
     ▼
   READY    ──(PlanValidator validates DAG)──► Waves Partitioned
     │
     ▼
  RUNNING   ──(Specialized Agents execute)───► Observations Collected
     │
     ▼
 VERIFYING  ──(AgentVerifier inspects evidence)─►
     │
     ├──► [PASSED] ──► Next Wave / COMPLETED ──► FinalSynthesizer ──► User Response
     │
     └──► [FAILED] ──► RecoveryEngine ──► (Retry / Replan / Abort)
```

---

## 3. Creating a Custom Specialized Agent

To add a new specialized agent to the platform:

```python
from jarvis.agents.base import AgentContext, BaseAgent
from jarvis.agents.models import AgentCapability, AgentDefinition, AgentStepResult, TaskState
from jarvis.agents.observation import ObservationNormalizer

class TranslationAgent(BaseAgent):
    def __init__(self) -> None:
        definition = AgentDefinition(
            id="agent.translator",
            name="Translation Agent",
            description="Translates structured documents into target languages.",
            capabilities={AgentCapability.RESEARCH},
            allowed_tools={"office.create_docx"},
            risk_level="low",
        )
        super().__init__(definition)

    async def execute(self, context: AgentContext) -> AgentStepResult:
        # Task inputs are accessed via context.task.input_data
        target_lang = context.task.input_data.get("language", "French")
        translated_text = f"Translated into {target_lang}"

        obs = ObservationNormalizer.from_agent_computation(
            task_id=context.task.id,
            output=translated_text,
        )

        return AgentStepResult(
            task_id=context.task.id,
            agent_id=self.id,
            status=TaskState.COMPLETED,
            output=translated_text,
            observations=[obs],
        )

# Register with registry
agent_system.registry.register(TranslationAgent())
```
