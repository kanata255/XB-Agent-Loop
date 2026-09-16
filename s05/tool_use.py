"""
tool_use.py — 工具定义与执行模块
包含所有 LLM 可调用的工具及其执行函数。
s02: Tool Use — 在 s01 基础上新增 4 个工具 + 分发映射。
运行: python s02_tool_use/code.py
需要: pip install anthropic python-dotenv + .env 中配置 ANTHROPIC_API_KEY
本文件 = s01 的全部代码 + 以下新增:
  + run_read / run_write / run_edit / run_glob 四个工具实现
  + TOOL_HANDLERS 分发映射（替代 s01 中硬编码的 run_bash 调用）
  + safe_path 路径安全校验
循环本身（agent_loop）与 s01 完全一致。
"""

from pathlib import Path
import ast, json, os, subprocess
WORKDIR = Path.cwd()


# ═══════════════════════════════════════════════════════════
#  NEW in s02: 4 个新工具
# ═══════════════════════════════════════════════════════════
def safe_path(p: str) -> Path:
    path = (WORKDIR / p).resolve()
    if not path.is_relative_to(WORKDIR):
        print(f"\n⚠  read_file 越界：{path}")
        choice = input("   允许读取工作区之外的文件吗? [y/N] ").strip().lower()
        if choice not in ("y", "yes"):
            raise ValueError(f"Permission denied: {p}")
    return path


def run_bash(command: str) -> str:
    """执行 shell 命令并返回输出。"""
    dangerous = ["rm -rf /", "sudo", "shutdown", "reboot", "> /dev/"]
    if any(d in command for d in dangerous):
        return "Error: Dangerous command blocked"
    try:
        r = subprocess.run(
            command,
            shell=True,
            cwd=os.getcwd(),
            capture_output=True,
            text=True,
            timeout=120,
        )
        out = (r.stdout + r.stderr).strip()
        return out[:50000] if out else "(no output)"
    except subprocess.TimeoutExpired:
        return "Error: Timeout (120s)"
    except (FileNotFoundError, OSError) as e:
        return f"Error: {e}"


def run_read(path, limit=None):
    lines = safe_path(path).read_text().splitlines()
    if limit:
        lines = lines[:limit]
    return "\n".join(lines)


def run_write(path, content):
    # 写操作不走 safe_path 的 workspace 限制：越界写已由 permission-已继承进hooks.py 的闸门 2+3 把关，
    # 用户批准后允许落到 workspace 外。这里直接按给定路径解析并写入。
    Path(path).resolve().write_text(content)
    return f"Wrote {len(content)} bytes to {path}"


def run_edit(path, old_text, new_text):
    # 与 run_write 同理：写操作不受 workspace 限制（闸门已把关）。
    target = Path(path).resolve()
    text = target.read_text()
    if old_text not in text:
        return "Error: text not found"
    target.write_text(text.replace(old_text, new_text, 1))
    return f"Edited {path}"


def run_glob(pattern):
    import glob as g

    return "\n".join(g.glob(pattern, root_dir=WORKDIR))


# todo_write 工具，接收一个带状态的列表，保存在当前进程内存中，同时在终端显示进度：
CURRENT_TODOS: list[dict] = []

def run_todo_write(todos: list) -> str:
    global CURRENT_TODOS
    CURRENT_TODOS = todos

    lines = ["\n## Current Tasks"]
    for t in CURRENT_TODOS:
        icon = {"pending": " ", "in_progress": "▸", "completed": "✓"}[t["status"]]
        lines.append(f"  [{icon}] {t['content']}")
    print("\n".join(lines))
    return f"Updated {len(CURRENT_TODOS)} tasks"

def _normalize_todos(todos):
    if isinstance(todos, str):
        try:
            todos = json.loads(todos)
        except json.JSONDecodeError:
            try:
                todos = ast.literal_eval(todos)
            except (SyntaxError, ValueError):
                return None, "Error: todos must be a list or JSON array string"
    if not isinstance(todos, list):
        return None, "Error: todos must be a list"
    for i, t in enumerate(todos):
        if not isinstance(t, dict):
            return None, f"Error: todos[{i}] must be an object"
        if "content" not in t or "status" not in t:
            return None, f"Error: todos[{i}] missing 'content' or 'status'"
        if t["status"] not in ("pending", "in_progress", "completed"):
            return None, f"Error: todos[{i}] has invalid status '{t['status']}'"
    return todos, None

TOOL_HANDLERS = {
    "bash": run_bash,
    "read_file": run_read,
    "write_file": run_write,
    "edit_file": run_edit,
    "glob": run_glob,
    "todo_write": run_todo_write,
}

# ── Tool definitions ──────────────────────────────────────
TOOLS = [
    {
        "name": "bash",
        "description": "Run a shell command.",
        "input_schema": {
            "type": "object",
            "properties": {"command": {"type": "string"}},
            "required": ["command"],
        },
    },
    {
        "name": "read_file",
        "description": "Read file contents.",
        "input_schema": {
            "type": "object",
            "properties": {"path": {"type": "string"}, "limit": {"type": "integer"}},
            "required": ["path"],
        },
    },
    {
        "name": "write_file",
        "description": "Write content to a file.",
        "input_schema": {
            "type": "object",
            "properties": {"path": {"type": "string"}, "content": {"type": "string"}},
            "required": ["path", "content"],
        },
    },
    {
        "name": "edit_file",
        "description": "Replace exact text in a file once.",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {"type": "string"},
                "old_text": {"type": "string"},
                "new_text": {"type": "string"},
            },
            "required": ["path", "old_text", "new_text"],
        },
    },
    {
        "name": "glob",
        "description": "Find files matching a glob pattern.",
        "input_schema": {
            "type": "object",
            "properties": {"pattern": {"type": "string"}},
            "required": ["pattern"],
        },
    },
    # s05: 新增一条
    {
        "name": "todo_write", "description": "Create and manage a task list ...",
        "input_schema": {
             "type": "object",
             "properties": {
                 "todos": {
                     "type": "array",
                     "items": {
                         "type": "object",
                         "properties": {
                             "content": {"type": "string"},
                             "status": {"type": "string", "enum": ["pending", "in_progress", "completed"]},
                         },
                     },
                 },
             },
        },
    },
]
