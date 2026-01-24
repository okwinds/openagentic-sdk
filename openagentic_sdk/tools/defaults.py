from __future__ import annotations

from .ask_user_question import AskUserQuestionTool
from .bash import BashTool
from .edit import EditTool
from .glob import GlobTool
from .grep import GrepTool
from .notebook_edit import NotebookEditTool
from .read import ReadTool
from .registry import ToolRegistry
from .skill import SkillTool
from .slash_command import SlashCommandTool
from .todo_write import TodoWriteTool
from .web_fetch import WebFetchTool
from .web_search_tavily import WebSearchTool
from .write import WriteTool
from .lsp import LspTool


def default_tool_registry() -> ToolRegistry:
    return ToolRegistry(
        [
            ReadTool(),
            AskUserQuestionTool(),
            WriteTool(),
            EditTool(),
            GlobTool(),
            GrepTool(),
            BashTool(),
            WebFetchTool(),
            WebSearchTool(),
            NotebookEditTool(),
            SlashCommandTool(),
            SkillTool(),
            TodoWriteTool(),
            LspTool(),
        ]
    )
