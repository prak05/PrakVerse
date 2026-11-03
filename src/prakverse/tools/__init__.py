"""Local tools and the safety-gated tool registry."""

from .registry import ToolContext, ToolRegistry
from .browser import BrowserController, register_browser_tools
from .gui import display_backend, register_gui_tools

__all__ = [
    "BrowserController",
    "ToolContext",
    "ToolRegistry",
    "display_backend",
    "register_browser_tools",
    "register_gui_tools",
]
