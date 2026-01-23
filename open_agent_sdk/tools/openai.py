from __future__ import annotations

from typing import Any, Mapping, Sequence

from .registry import ToolRegistry


def tool_schemas_for_openai(tool_names: Sequence[str], *, registry: ToolRegistry | None = None) -> list[Mapping[str, Any]]:
    schemas: dict[str, Mapping[str, Any]] = {
        "AskUserQuestion": {
            "type": "function",
            "function": {
                "name": "AskUserQuestion",
                "description": "Ask the user a clarifying question.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "questions": {"type": "array"},
                        "answers": {"type": "object"},
                    },
                    "required": ["questions"],
                },
            },
        },
        "Read": {
            "type": "function",
            "function": {
                "name": "Read",
                "description": "Read a file from disk.",
                "parameters": {
                    "type": "object",
                    "properties": {"file_path": {"type": "string"}},
                    "required": ["file_path"],
                },
            },
        },
        "Write": {
            "type": "function",
            "function": {
                "name": "Write",
                "description": "Create or overwrite a file.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "file_path": {"type": "string"},
                        "content": {"type": "string"},
                        "overwrite": {"type": "boolean"},
                    },
                    "required": ["file_path", "content"],
                },
            },
        },
        "Edit": {
            "type": "function",
            "function": {
                "name": "Edit",
                "description": "Apply a precise edit (string replace) to a file.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "file_path": {"type": "string"},
                        "old": {"type": "string"},
                        "new": {"type": "string"},
                        "count": {"type": "integer"},
                    },
                    "required": ["file_path", "old", "new"],
                },
            },
        },
        "Glob": {
            "type": "function",
            "function": {
                "name": "Glob",
                "description": "Find files by glob pattern.",
                "parameters": {
                    "type": "object",
                    "properties": {"pattern": {"type": "string"}, "root": {"type": "string"}},
                    "required": ["pattern"],
                },
            },
        },
        "Grep": {
            "type": "function",
            "function": {
                "name": "Grep",
                "description": "Search file contents with a regex.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query": {"type": "string"},
                        "file_glob": {"type": "string"},
                        "root": {"type": "string"},
                        "case_sensitive": {"type": "boolean"},
                    },
                    "required": ["query"],
                },
            },
        },
        "Bash": {
            "type": "function",
            "function": {
                "name": "Bash",
                "description": "Run a shell command.",
                "parameters": {
                    "type": "object",
                    "properties": {"command": {"type": "string"}, "timeout_s": {"type": "number"}},
                    "required": ["command"],
                },
            },
        },
        "WebFetch": {
            "type": "function",
            "function": {
                "name": "WebFetch",
                "description": "Fetch a URL over HTTP(S).",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "url": {"type": "string"},
                        "headers": {"type": "object"},
                        "prompt": {"type": "string"},
                    },
                    "required": ["url"],
                },
            },
        },
        "WebSearch": {
            "type": "function",
            "function": {
                "name": "WebSearch",
                "description": "Search the web (Tavily backend).",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query": {"type": "string"},
                        "max_results": {"type": "integer"},
                        "allowed_domains": {"type": "array"},
                        "blocked_domains": {"type": "array"},
                    },
                    "required": ["query"],
                },
            },
        },
        "NotebookEdit": {
            "type": "function",
            "function": {
                "name": "NotebookEdit",
                "description": "Edit a Jupyter notebook (.ipynb).",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "notebook_path": {"type": "string"},
                        "cell_id": {"type": "string"},
                        "new_source": {"type": "string"},
                        "cell_type": {"type": "string"},
                        "edit_mode": {"type": "string"},
                    },
                    "required": ["notebook_path"],
                },
            },
        },
        "SlashCommand": {
            "type": "function",
            "function": {
                "name": "SlashCommand",
                "description": "Load a .claude slash command by name.",
                "parameters": {
                    "type": "object",
                    "properties": {"name": {"type": "string"}, "project_dir": {"type": "string"}},
                    "required": ["name"],
                },
            },
        },
        "SkillList": {
            "type": "function",
            "function": {
                "name": "SkillList",
                "description": "List skills from .claude/skills/**/SKILL.md.",
                "parameters": {
                    "type": "object",
                    "properties": {"project_dir": {"type": "string"}},
                },
            },
        },
        "SkillLoad": {
            "type": "function",
            "function": {
                "name": "SkillLoad",
                "description": "Load a skill's SKILL.md by name.",
                "parameters": {
                    "type": "object",
                    "properties": {"name": {"type": "string"}, "project_dir": {"type": "string"}},
                    "required": ["name"],
                },
            },
        },
        "SkillActivate": {
            "type": "function",
            "function": {
                "name": "SkillActivate",
                "description": "Activate a skill for the current session.",
                "parameters": {
                    "type": "object",
                    "properties": {"name": {"type": "string"}},
                    "required": ["name"],
                },
            },
        },
        "Task": {
            "type": "function",
            "function": {
                "name": "Task",
                "description": "Run a subagent by name.",
                "parameters": {
                    "type": "object",
                    "properties": {"agent": {"type": "string"}, "prompt": {"type": "string"}},
                    "required": ["agent", "prompt"],
                },
            },
        },
    }

    out: list[Mapping[str, Any]] = []
    for name in tool_names:
        schema = schemas.get(name)
        if schema is not None:
            out.append(schema)
            continue
        if registry is not None:
            try:
                tool = registry.get(name)
            except KeyError:
                continue
            openai_schema = getattr(tool, "openai_schema", None)
            if isinstance(openai_schema, dict):
                out.append(openai_schema)
    return out
