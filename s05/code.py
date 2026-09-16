#!/usr/bin/env python3
"""
s05: TodoWrite — add a planning tool on top of s04 hooks.
  +---------+      +-------+      +------------------+
  |  User   | ---> |  LLM  | ---> | TOOL_HANDLERS    |
  | prompt  |      |       |      |  bash            |
  +---------+      +---+---+      |  read_file       |
                        ^         |  write_file      |
                        | result  |  edit_file       |
                        +---------+  glob            |
                                      todo_write ← NEW
                                   +------------------+
                                        |
                         in-memory current_todos
                                        |
                        if rounds_since_todo >= 3:
                          inject <reminder>

"""

import os
import sys

if sys.platform == "win32":
    os.environ.setdefault("PYTHONUTF8", "1")
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    sys.stdin = open(
        sys.stdin.fileno(), mode="r", encoding="utf-8", errors="replace", buffering=1
    )
try:
    import readline

    # macOS 的 libedit 在处理中文输入时有退格问题，这四行修复它
    readline.parse_and_bind("set bind-tty-special-chars off")
    readline.parse_and_bind("set input-meta on")
    readline.parse_and_bind("set output-meta on")
    readline.parse_and_bind("set convert-meta off")
except ImportError:
    pass
from anthropic import Anthropic
from dotenv import load_dotenv
from tool_use import TOOLS, TOOL_HANDLERS
from hooks import trigger_hooks
from pathlib import Path

WORKDIR = Path.cwd()
load_dotenv(override=True)
if os.getenv("ANTHROPIC_BASE_URL"):
    os.environ.pop("ANTHROPIC_AUTH_TOKEN", None)

client = Anthropic(base_url=os.getenv("ANTHROPIC_BASE_URL"))
MODEL = os.environ["MODEL_ID"]

# s05 change: SYSTEM prompt adds planning guidance
SYSTEM = (
    f"You are a coding agent at {WORKDIR}. "
    "Before starting any multi-step task, use todo_write to plan your steps. "
    "Update status as you go."
)

rounds_since_todo = 0
# ── The core pattern: a while loop that calls tools until the model stops ──
def agent_loop(messages: list):
    global rounds_since_todo
    while True:
        # s05 如果无操作循环进行了3次，更新模型的todolist，注入提醒
        if rounds_since_todo >= 3 and messages:
            messages.append({"role": "user",
                             "content": "<reminder>Update your todos.</reminder>"})
            rounds_since_todo = 0

        # 调用 LLM，传入当前对话历史和工具定义
        response = client.messages.create(
            model=MODEL,
            # 全局指令，设定模型的身份和行为
            system=SYSTEM,
            messages=messages,
            tools=TOOLS,
            max_tokens=8000,
        )
        # 将 assistant 的回复追加到历史，供下次迭代使用
        messages.append({"role": "assistant", "content": response.content})
        # 如果 LLM 没有调用任何工具，说明它已经给出了最终答案，循环结束
        if response.stop_reason != "tool_use":
            force = trigger_hooks("Stop", messages)   # ← 退出之前
            if force:
                # hook returned a message → inject it and continue
                messages.append({"role": "user", "content": force})
                continue
            return
        # 模型调用一次后累加
        rounds_since_todo += 1
        # 遍历 LLM 返回的所有 block，执行 tool_use 类型的调用
        results = []
        for block in response.content:
            if block.type == "tool_use":
                print(f"\033[33m> block.name {block.name}\033[0m")
                # s04 调用工具前调用hook拦截【工具权限判断、】
                blocked = trigger_hooks("PreToolUse", block)
                print(f"blocked:=====>{blocked}")
                if blocked:
                    results.append({"type": "tool_result", "tool_use_id": block.id,
                                    "content": str(blocked)})
                    continue
                handler = TOOL_HANDLERS.get(block.name)
                try:
                    output = handler(**block.input) if handler else f"Unknown: {block.name}"
                except Exception as e:
                    output = f"Error: {e}"
                print(f"print2：====> {str(output[:200])}")
                # 	工具执行后调用
                trigger_hooks("PostToolUse", block, output)  # s04: post hook
                # s05: 当调用 todo_write 时重置提醒计数器
                if block.name == "todo_write":
                    rounds_since_todo = 0
                results.append(
                    {
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": output,
                    }
                )
        # 将工具执行结果作为 user 消息追加回历史，LLM 可据此继续推理
        messages.append({"role": "user", "content": results})


# ── Entry point ──────────────────────────────────────────
if __name__ == "__main__":
    print("s5: TodoWrite")
    print("输入问题，回车发送。输入 q 退出。\n")
    history = []
    while True:
        try:
            query = input("\033[36ms03 >> \033[0m")
        except (EOFError, KeyboardInterrupt):
            break
        # 退出agent Loop
        if query.strip().lower() in ("q", "exit", ""):
            break
        # 用户输入提交后、进入 LLM 前调用Hooks，输入验证，注入上下文
        trigger_hooks("UserPromptSubmit", query)   # ← 进入 LLM 之前
        history.append({"role": "user", "content": query})
        agent_loop(history)
        # agent_loop 结束后，history[-1] 就是 assistant 的最后一条消息。
        # 遍历其 content block 列表，找到 type=="text" 的 block 并打印，这就是 LLM 的最终答案。
        # （中间打印的 print1/print2 是工具执行过程，不是最终答案。）
        response_content = history[-1]["content"]
        if isinstance(response_content, list):
            for block in response_content:
                if getattr(block, "type", None) == "text":
                    print(f"final print:====>{block.text}")
        print()
