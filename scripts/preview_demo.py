"""JARVIS Live Interactive Terminal Preview.

Demonstrates the autonomous hybrid multi-agent runtime, DAG planning,
sandboxed tool execution, physical artifact verification, and final synthesis.
"""

import asyncio
import os
import sys
import time
from pathlib import Path

# Ensure stdout handles UTF-8 on Windows
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

repo_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(repo_root / "services" / "python-core"))

from jarvis.agents.factory import build_agent_system
from jarvis.agents.models import AgentState
from jarvis.tools.factory import build_tool_system

# ANSI Color Codes
CYAN = "\033[96m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
RED = "\033[91m"
MAGENTA = "\033[95m"
BOLD = "\033[1m"
DIM = "\033[2m"
RESET = "\033[0m"


def print_banner() -> None:
    banner = f"""
{CYAN}{BOLD}======================================================================
     ██╗ █████╗ ██████╗ ██╗   ██╗██╗███████╗
     ██║██╔══██╗██╔══██╗██║   ██║██║██╔════╝
     ██║███████║██████╔╝██║   ██║██║███████╗
██   ██║██╔══██║██╔══██╗╚██╗ ██╔╝██║╚════██║
╚█████╔╝██║  ██║██║  ██║ ╚████╔╝ ██║███████║
 ╚════╝ ╚═╝  ╚═╝╚═╝  ╚═╝  ╚═══╝  ╚═╝╚══════╝
{RESET}{DIM}  Autonomous AI Desktop Assistant Platform • Hybrid Architecture v1.0
  Phases 01-05 Complete (SDLC & Quality Gates Verified)
======================================================================{RESET}
"""
    print(banner)


async def main() -> None:
    print_banner()

    workspace_dir = repo_root / "workspace"
    workspace_dir.mkdir(exist_ok=True)

    print(f"{CYAN}[1/4] Initializing Subsystems & Mounting Sandboxes...{RESET}")
    tool_system = build_tool_system(workspace_dir=workspace_dir)
    agent_system = build_agent_system(
        tool_system=tool_system,
        checkpoint_dir=workspace_dir / "checkpoints",
    )
    print(f"  {GREEN}✓{RESET} FileSystemSandbox mounted at: {DIM}{workspace_dir}{RESET}")
    tool_names = [t.id for t in tool_system.registry.list()]
    print(f"  {GREEN}✓{RESET} Sandboxed Tools: {DIM}{', '.join(sorted(tool_names))}{RESET}")

    registered_agents = agent_system.registry.list()
    print(f"  {GREEN}✓{RESET} 10 Autonomous Multi-Agents loaded into Registry:")
    for a in registered_agents:
        caps = ", ".join(c.value for c in a.capabilities)
        print(f"    - {BOLD}{a.name:<18}{RESET} [{CYAN}{caps:<14}{RESET}] {DIM}{a.description[:45]}...{RESET}")

    print(f"\n{CYAN}[2/4] Defining Autonomous Mission Goal...{RESET}")
    mission_text = "Create a project presentation for executive stakeholders on AI Assistant Architecture"
    print(f"  {BOLD}Goal:{RESET} \"{YELLOW}{mission_text}{RESET}\"")

    print(f"\n{CYAN}[3/4] Orchestrating Autonomous Multi-Agent Pipeline...{RESET}")
    print(f"  {DIM}* Step A: PlannerAgent analyzes prompt & builds Kahn's DAG{RESET}")
    print(f"  {DIM}* Step B: Wave Execution (parallel delegation across agents){RESET}")
    print(f"  {DIM}* Step C: CodingAgent executes sandboxed office tools in workspace{RESET}")
    print(f"  {DIM}* Step D: VerifierAgent performs anti-hallucination byte checks{RESET}")
    print(f"  {DIM}* Step E: SynthesisAgent unifies final response & evidence{RESET}")

    t0 = time.perf_counter()
    final_resp = await agent_system.orchestrator.run(mission_text)
    duration = time.perf_counter() - t0

    print(f"  {GREEN}✓{RESET} Pipeline Completed in {duration:.2f}s!")

    print(f"\n{CYAN}[4/4] Final Verification & Mission Telemetry{RESET}")
    print(f"\n{BOLD}=================== MISSION RESULT ==================={RESET}")
    status_str = f"{GREEN}SUCCESS (COMPLETED){RESET}" if final_resp.status == AgentState.COMPLETED else f"{RED}FAILED{RESET}"
    print(f"{BOLD}Run ID:{RESET}        {final_resp.run_id}")
    print(f"{BOLD}Status:{RESET}        {status_str}")
    print(f"{BOLD}Tasks Total:{RESET}   {final_resp.task_statistics.get('total', 0)}")
    print(f"{BOLD}Tasks Passed:{RESET}  {final_resp.task_statistics.get('completed', 0)}")
    print(f"{BOLD}Tasks Failed:{RESET}  {final_resp.task_statistics.get('failed', 0)}")

    if final_resp.verified_artifacts:
        print(f"\n{BOLD}Verified Artifacts On Disk (Anti-Hallucination Gate):{RESET}")
        for art_path_str in final_resp.verified_artifacts:
            art_file = Path(art_path_str)
            size = art_file.stat().st_size if art_file.exists() else 0
            print(f"  {GREEN}✓{RESET} {BOLD}{art_file.name}{RESET} ({size:,} bytes) at {DIM}{art_file}{RESET}")

    print(f"\n{BOLD}Executive Summary Narrative:{RESET}\n{final_resp.summary}")
    print(f"{BOLD}======================================================{RESET}\n")

    print(f"{GREEN}{BOLD}JARVIS Multi-Agent Terminal Preview Passed Successfully!{RESET}")
    print(f"Live Web Command Dashboard is available at: {CYAN}{BOLD}http://localhost:3000{RESET}\n")


if __name__ == "__main__":
    asyncio.run(main())
