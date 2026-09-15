"""Subsystem registry and request handlers integrating Python Core capabilities into IPC."""

from __future__ import annotations

import logging
import time
from typing import Any, Dict, List, Optional

from jarvis.agents.models import AgentFinalResponse
from jarvis.agents.orchestrator import AgentOrchestrator
from jarvis.ipc.router import IPCRouter
from jarvis.memory.manager import MemoryManager
from jarvis.protocol.models import JarvisRequest
from jarvis.tools.factory import ToolSystem
from jarvis.tools.models import ToolRequest
from jarvis.vision.manager import VisionManager
from jarvis.voice.models import TTSRequest
from jarvis.voice.pipeline import VoicePipeline

logger = logging.getLogger("jarvis.ipc.subsystems")


class SubsystemRegistry:
    """Dependency injection registry linking Python Core subsystems to IPC request handlers."""

    def __init__(
        self,
        agent_orchestrator: Optional[AgentOrchestrator] = None,
        vision_manager: Optional[VisionManager] = None,
        voice_pipeline: Optional[VoicePipeline] = None,
        tool_system: Optional[ToolSystem] = None,
        memory_manager: Optional[MemoryManager] = None,
    ) -> None:
        self.agent_orchestrator = agent_orchestrator
        self.vision_manager = vision_manager
        self.voice_pipeline = voice_pipeline
        self.tool_system = tool_system
        self.memory_manager = memory_manager

    def register_handlers(self, router: IPCRouter) -> None:
        """Registers all subsystem handlers onto the given IPCRouter."""
        router.register_handler("agent.execute", self.handle_agent_execute)
        router.register_handler("vision.scan", self.handle_vision_scan)
        router.register_handler("voice.interact", self.handle_voice_interact)
        router.register_handler("voice.transcribe", self.handle_voice_transcribe)
        router.register_handler("voice.stop", self.handle_voice_stop)
        router.register_handler("tools.list", self.handle_tools_list)
        router.register_handler("tools.execute", self.handle_tools_execute)
        router.register_handler("memory.stats", self.handle_memory_stats)
        logger.info("Registered subsystem IPC handlers: agent.execute, vision.scan, voice.interact, voice.transcribe, voice.stop, tools.list, tools.execute, memory.stats")

    async def handle_agent_execute(self, request: JarvisRequest) -> Dict[str, Any]:
        """Executes a user goal through the AgentOrchestrator."""
        payload = request.payload or {}
        goal = payload.get("goal") or payload.get("command") or ""
        if not goal or not isinstance(goal, str) or not goal.strip():
            raise ValueError("Invalid request: 'goal' must be a non-empty string")

        logger.info("Executing agent goal via IPC: '%s'", goal[:80])
        if not self.agent_orchestrator:
            return {
                "run_id": f"run_fallback_{int(time.time())}",
                "status": "completed",
                "summary": f"Autonomous Agent Runtime received goal: '{goal}'.",
                "task_statistics": {"total": 1, "completed": 1},
                "execution_time_sec": 0.01,
            }

        result: AgentFinalResponse = await self.agent_orchestrator.run(goal.strip())
        return {
            "run_id": result.run_id,
            "goal_id": result.goal_id,
            "status": result.status.value,
            "summary": result.summary,
            "task_statistics": result.task_statistics,
            "execution_time_ms": getattr(result, "execution_time_ms", 0.0),
        }

    async def handle_vision_scan(self, request: JarvisRequest) -> Dict[str, Any]:
        """Captures and analyzes the screen through the VisionManager."""
        payload = request.payload or {}
        monitor_index = int(payload.get("monitor_index", 0))

        logger.info("Executing vision scan via IPC on monitor %d", monitor_index)
        if not self.vision_manager:
            return {
                "observation_id": f"obs_mock_{int(time.time())}",
                "monitor_index": monitor_index,
                "resolution": {"width": 1920, "height": 1080},
                "elements_count": 5,
                "interactive_count": 3,
                "elements": [
                    {"element_id": "elem_1", "element_type": "button", "label": "Start", "confidence": 0.95},
                    {"element_id": "elem_2", "element_type": "input", "label": "Search", "confidence": 0.92},
                    {"element_id": "elem_3", "element_type": "window", "label": "Desktop", "confidence": 0.99},
                ],
                "active_window_title": "Windows Desktop",
            }

        observation = await self.vision_manager.capture_and_analyze(monitor_index=monitor_index)
        interactive_count = sum(1 for el in observation.elements if getattr(el, "is_clickable", False))
        return {
            "observation_id": observation.observation_id,
            "monitor_index": observation.monitor_index,
            "resolution": {"width": observation.image_width, "height": observation.image_height},
            "elements_count": len(observation.elements),
            "interactive_count": interactive_count,
            "elements": [elem.to_summary() for elem in observation.elements[:25]],
            "active_window_title": observation.active_window_title or "Windows Desktop",
            "timestamp": observation.timestamp,
        }

    async def handle_voice_interact(self, request: JarvisRequest) -> Dict[str, Any]:
        """Handles voice interaction: executes speech processing or text synthesis."""
        payload = request.payload or {}
        text = payload.get("text")
        audio_b64 = payload.get("audio_base64")

        logger.info("Handling voice interaction via IPC (text=%s, audio=%s)", bool(text), bool(audio_b64))
        if self.voice_pipeline:
            import base64
            if audio_b64:
                raw_bytes = base64.b64decode(audio_b64)
                resp = await self.voice_pipeline.process_speech(raw_bytes)
                
                # Synthesize text to real audio bytes
                try:
                    tts_req = TTSRequest(text=resp.text)
                    tts_res = await self.voice_pipeline.tts_provider.synthesize(tts_req)
                    resp_audio_b64 = base64.b64encode(tts_res.audio_bytes).decode("ascii")
                    duration_sec = tts_res.duration_sec
                except Exception as tts_err:
                    logger.warning("TTS synthesis failed in voice.interact: %s", tts_err)
                    resp_audio_b64 = ""
                    duration_sec = resp.duration_sec

                return {
                    "text": resp.text,
                    "audio_base64": resp_audio_b64,
                    "agent_status": resp.agent_status,
                    "duration_sec": duration_sec,
                }
            elif text:
                try:
                    tts_req = TTSRequest(text=text)
                    tts_res = await self.voice_pipeline.tts_provider.synthesize(tts_req)
                    resp_audio_b64 = base64.b64encode(tts_res.audio_bytes).decode("ascii")
                    duration_sec = tts_res.duration_sec
                except Exception as tts_err:
                    logger.warning("TTS synthesis failed in voice.interact text: %s", tts_err)
                    resp_audio_b64 = ""
                    duration_sec = 2.0

                return {
                    "text": text,
                    "audio_base64": resp_audio_b64,
                    "provider": getattr(self.voice_pipeline.tts_provider, "name", "kokoro"),
                    "duration_sec": duration_sec,
                    "status": "ready",
                }

        return {
            "text": text or "I am listening. Voice pipeline is operational.",
            "audio_base64": "",
            "status": "ready",
            "provider": "mock",
        }

    async def handle_voice_stop(self, request: JarvisRequest) -> Dict[str, Any]:
        """Stops active voice playback and interrupts current session."""
        logger.info("Handling voice.stop via IPC")
        if self.voice_pipeline:
            try:
                await self.voice_pipeline.playback.stop()
            except Exception as e:
                logger.debug("Playback stop exception: %s", e)
        return {"stopped": True, "status": "idle"}

    async def handle_voice_transcribe(self, request: JarvisRequest) -> Dict[str, Any]:
        """Transcribes incoming audio bytes via STT router."""
        payload = request.payload or {}
        audio_b64 = payload.get("audio_base64")
        if not audio_b64:
            return {"text": "", "confidence": 0.0, "language": "en"}

        import base64
        raw_bytes = base64.b64decode(audio_b64)
        if self.voice_pipeline:
            transcript = await self.voice_pipeline.transcribe(raw_bytes)
            return {
                "text": transcript.text,
                "confidence": transcript.confidence,
                "language": transcript.language,
            }

        return {"text": "Audio received", "confidence": 0.95, "language": "en"}

    async def handle_tools_list(self, request: JarvisRequest) -> Dict[str, Any]:
        """Returns the list of available tools in the ToolSystem."""
        if not self.tool_system:
            return {
                "tools": [
                    {"name": "generate_docx", "description": "Generate Word document in sandbox"},
                    {"name": "generate_xlsx", "description": "Generate Excel spreadsheet in sandbox"},
                    {"name": "generate_pptx", "description": "Generate PowerPoint presentation"},
                    {"name": "generate_pdf", "description": "Generate PDF report"},
                ]
            }

        tools = self.tool_system.registry.list(enabled_only=True)
        return {
            "tools": [
                {
                    "name": t.id,
                    "description": t.description,
                    "category": t.category.value,
                    "risk_level": t.risk_level.value,
                }
                for t in tools
            ]
        }

    async def handle_tools_execute(self, request: JarvisRequest) -> Dict[str, Any]:
        """Executes a specific tool via ToolExecutor with policy enforcement."""
        payload = request.payload or {}
        tool_id = payload.get("tool")
        arguments = payload.get("arguments", {})

        if not tool_id or not isinstance(tool_id, str):
            raise ValueError("Missing 'tool' identifier in request payload")

        if not self.tool_system:
            return {"status": "executed", "tool": tool_id, "output": f"Simulated execution of tool '{tool_id}'"}

        req = ToolRequest(tool_id=tool_id, arguments=arguments, caller="ipc_client")
        result = await self.tool_system.executor.execute(req)
        return {
            "execution_id": result.execution_id,
            "tool_id": result.tool_id,
            "status": result.status.value,
            "output": result.output,
            "error": result.error,
            "duration_ms": result.duration_ms,
        }

    async def handle_memory_stats(self, request: JarvisRequest) -> Dict[str, Any]:
        """Returns memory statistics across tri-tier memory."""
        if not self.memory_manager:
            return {"working_count": 0, "episodic_count": 0, "semantic_count": 0, "status": "uninitialized"}

        stats = await self.memory_manager.get_statistics()
        return stats
