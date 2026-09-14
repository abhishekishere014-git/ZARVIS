"""Performance benchmarks for the JARVIS Agent Runtime."""

import time
from pathlib import Path
import pytest
from jarvis.agents.factory import build_agent_system
from jarvis.agents.models import AgentPlan, AgentTask
from jarvis.agents.plan_validator import PlanValidator
from jarvis.tools.factory import build_tool_system


def test_plan_validator_latency_benchmark() -> None:
    validator = PlanValidator(max_steps=50)

    # 20-node DAG
    tasks = []
    for i in range(20):
        deps = [f"t{i-1}"] if i > 0 else []
        tasks.append(AgentTask(id=f"t{i}", title=f"Task {i}", description="Desc", assigned_agent="a1", dependencies=deps))
    plan = AgentPlan(goal_id="g_perf", tasks=tasks)

    # Benchmark 100 iterations of cycle detection & topological sort
    iterations = 100
    start = time.perf_counter()
    for _ in range(iterations):
        waves = validator.validate_and_sort(plan)
        assert len(waves) == 20
    total_time = time.perf_counter() - start

    avg_latency_ms = (total_time / iterations) * 1000.0
    print(f"\n[PERF] DAG Plan Validation: {avg_latency_ms:.3f} ms / validation across 20-node DAG")

    assert avg_latency_ms < 1.0, f"Plan validation overhead {avg_latency_ms:.3f}ms exceeds 1.0ms budget"


@pytest.mark.asyncio
async def test_orchestrator_dispatch_benchmark(tmp_path: Path) -> None:
    tool_system = build_tool_system(workspace_dir=tmp_path)
    agent_system = build_agent_system(tool_system=tool_system, checkpoint_dir=tmp_path / "checkpoints")

    start = time.perf_counter()
    res = await agent_system.orchestrator.run("Simple status check")
    duration = time.perf_counter() - start

    print(f"\n[PERF] Complete multi-agent workflow runtime: {duration * 1000.0:.2f} ms")
    assert res.status.value == "completed"
    assert duration < 2.0
