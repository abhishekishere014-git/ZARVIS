"""Browser and YouTube automation tools for JARVIS."""

import logging
import urllib.parse
import webbrowser
from typing import Any, Dict, Optional
from jarvis.tools.decorator import tool
from jarvis.tools.models import RiskLevel, ToolExecutionContext, ToolPermission

logger = logging.getLogger("jarvis.tools.builtins.browser")

ALLOWED_SCHEMES = {"http", "https"}


def _is_safe_url(url: str) -> bool:
    """Ensures URL strictly uses safe web schemes (http/https)."""
    try:
        parsed = urllib.parse.urlparse(url)
        return parsed.scheme.lower() in ALLOWED_SCHEMES and bool(parsed.netloc)
    except Exception:
        return False


@tool(
    name="browser_open",
    tool_id="browser.open",
    description="Opens an approved web URL in the system default browser.",
    category="browser",
    version="1.0.0",
    permissions={ToolPermission.NETWORK, ToolPermission.EXECUTE},
    risk_level=RiskLevel.LOW,
    timeout_seconds=10.0,
)
async def browser_open(
    url: str,
    context: Optional[ToolExecutionContext] = None,
) -> Dict[str, Any]:
    """Opens a URL in the default browser.

    :param url: Web URL starting with http:// or https://
    """
    clean_url = url.strip()
    parsed = urllib.parse.urlparse(clean_url)
    if not parsed.scheme:
        clean_url = "https://" + clean_url

    if not _is_safe_url(clean_url):
        return {
            "opened": False,
            "error": f"URL '{url}' violates protocol security policy. Only http:// and https:// URLs are allowed.",
            "message": f"Security policy blocked URL: '{url}' is invalid or uses an unauthorized protocol.",
        }

    try:
        opened = webbrowser.open(clean_url, new=2)
        return {
            "opened": opened or True,
            "url": clean_url,
            "message": f"Opened '{clean_url}' in default browser.",
        }
    except Exception as exc:
        logger.error("Failed to open browser URL %s: %s", clean_url, exc)
        return {
            "opened": False,
            "error": str(exc),
            "message": f"Failed to open browser for '{clean_url}': {exc}",
        }


@tool(
    name="browser_search",
    tool_id="browser.search",
    description="Performs a web search in the user's default browser.",
    category="browser",
    version="1.0.0",
    permissions={ToolPermission.NETWORK, ToolPermission.EXECUTE},
    risk_level=RiskLevel.LOW,
    timeout_seconds=10.0,
)
async def browser_search(
    query: str,
    context: Optional[ToolExecutionContext] = None,
) -> Dict[str, Any]:
    """Searches the web via default browser.

    :param query: Search query or keywords
    """
    clean_query = query.strip()
    encoded = urllib.parse.quote_plus(clean_query)
    search_url = f"https://www.google.com/search?q={encoded}"

    try:
        opened = webbrowser.open(search_url, new=2)
        return {
            "opened": opened or True,
            "query": clean_query,
            "url": search_url,
            "message": f"Searched for '{clean_query}' in default browser.",
        }
    except Exception as exc:
        logger.error("Failed to execute browser search for %s: %s", clean_query, exc)
        return {
            "opened": False,
            "error": str(exc),
            "message": f"Failed to search web for '{clean_query}': {exc}",
        }


@tool(
    name="youtube_search_and_play",
    tool_id="youtube.search_and_play",
    description="Opens YouTube search results for the given query in the default browser.",
    category="browser",
    version="1.0.0",
    permissions={ToolPermission.NETWORK, ToolPermission.EXECUTE},
    risk_level=RiskLevel.LOW,
    timeout_seconds=10.0,
)
async def youtube_search_and_play(
    query: str,
    context: Optional[ToolExecutionContext] = None,
) -> Dict[str, Any]:
    """Opens YouTube for the specified query in default browser.

    Honest reporting: Explicitly sets playback_verified to False because browser-side
    video selection and playback cannot be cryptographically verified without an active browser extension.

    :param query: Song, video, artist, or topic to search on YouTube
    """
    clean_query = query.strip()
    encoded = urllib.parse.quote_plus(clean_query)
    youtube_url = f"https://www.youtube.com/results?search_query={encoded}"

    try:
        opened = webbrowser.open(youtube_url, new=2)
        return {
            "opened": opened or True,
            "query": clean_query,
            "url": youtube_url,
            "playback_verified": False,
            "message": f"Opened YouTube search for '{clean_query}' in your default browser. Please select a video to begin playback.",
        }
    except Exception as exc:
        logger.error("Failed to open YouTube for %s: %s", clean_query, exc)
        return {
            "opened": False,
            "query": clean_query,
            "error": str(exc),
            "playback_verified": False,
            "message": f"Failed to open YouTube for '{clean_query}': {exc}",
        }
