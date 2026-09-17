"""Tests for natural language intent routing in PlannerAgent."""

from jarvis.agents.builtins.planner import PlannerAgent


def test_youtube_intent_routing() -> None:
    planner = PlannerAgent()
    tasks = planner._deterministic_decompose("play lofi hip hop on youtube")
    assert len(tasks) == 2
    assert tasks[0].required_tools == ["youtube.search_and_play"]
    assert "lofi hip hop" in tasks[0].input_data["tool_args"]["query"]


def test_web_search_intent_routing() -> None:
    planner = PlannerAgent()
    tasks = planner._deterministic_decompose("search the web for quantum computing advances")
    assert len(tasks) == 2
    assert tasks[0].required_tools == ["browser.search"]
    assert "quantum computing advances" in tasks[0].input_data["tool_args"]["query"]


def test_app_launch_intent_routing() -> None:
    planner = PlannerAgent()
    tasks_calc = planner._deterministic_decompose("open calculator")
    assert tasks_calc[0].required_tools == ["app.launch"]
    assert tasks_calc[0].input_data["tool_args"]["app_name"] == "Calculator"

    tasks_vscode = planner._deterministic_decompose("launch visual studio code")
    assert tasks_vscode[0].required_tools == ["app.launch"]
    assert tasks_vscode[0].input_data["tool_args"]["app_name"] == "VS Code"


def test_folder_intent_routing() -> None:
    planner = PlannerAgent()
    tasks = planner._deterministic_decompose("open downloads folder")
    assert tasks[0].required_tools == ["file.open_directory"]
    assert tasks[0].input_data["tool_args"]["directory_name"] == "downloads"


def test_screenshot_intent_routing() -> None:
    planner = PlannerAgent()
    tasks = planner._deterministic_decompose("take a screenshot of the desktop")
    assert tasks[0].required_tools == ["os.screen.capture"]
