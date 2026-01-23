from __future__ import annotations

from .bash import BashTool
from .edit import EditTool
from .glob import GlobTool
from .grep import GrepTool
from .ask_user_question import AskUserQuestionTool
from .read import ReadTool
from .registry import ToolRegistry
from .slash_command import SlashCommandTool
from .skill import SkillTool
from .skill_activate import SkillActivateTool
from .skill_list import SkillListTool
from .skill_load import SkillLoadTool
from .notebook_edit import NotebookEditTool
from .web_fetch import WebFetchTool
from .web_search_tavily import WebSearchTool
from .write import WriteTool
from .todo_write import TodoWriteTool


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
            SkillListTool(),
            SkillLoadTool(),
            SkillActivateTool(),
            TodoWriteTool(),
        ]
    )
