#!/usr/bin/env python3
"""
s01_agent_loop.py - The Agent Loop
The entire secret of an AI coding agent in one pattern:
    while stop_reason == "tool_use":
        response = LLM(messages, tools)
        execute tools
        append results
    +----------+      +-------+      +---------+
    |   User   | ---> |  LLM  | ---> |  Tool   |
    |  prompt  |      |       |      | execute |
    +----------+      +---+---+      +----+----+
                          ^               |
                          |   tool_result |
                          +---------------+
                          (loop continues)
This is the core loop: feed tool results back to the model
until the model decides to stop. Production agents layer
policy, hooks, and lifecycle controls on top.
Usage:
    pip install anthropic python-dotenv
    ANTHROPIC_API_KEY=... python s01_agent_loop/code.py
"""
import os
import subprocess
import sys
if sys.platform == 'win32':
    os.environ.setdefault('PYTHONUTF8', '1')
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')
    sys.stdin = open(sys.stdin.fileno(), mode='r', encoding='utf-8', errors='replace', buffering=1)
try:
    import readline
    # macOS 的 libedit 在处理中文输入时有退格问题，这四行修复它
    readline.parse_and_bind('set bind-tty-special-chars off')
    readline.parse_and_bind('set input-meta on')
    readline.parse_and_bind('set output-meta on')
    readline.parse_and_bind('set convert-meta off')
except ImportError:
    pass
from anthropic import Anthropic
from dotenv import load_dotenv
load_dotenv(override=True)
if os.getenv("ANTHROPIC_BASE_URL"):
    os.environ.pop("ANTHROPIC_AUTH_TOKEN", None)

client = Anthropic(base_url=os.getenv("ANTHROPIC_BASE_URL"))
MODEL = os.environ["MODEL_ID"]
SYSTEM = f"You are a coding agent at {os.getcwd()}. Use bash to solve tasks. Act, don't explain."
# ── Tool definition: just bash ────────────────────────────
TOOLS = [{
    "name": "bash",
    "description": "Run a shell command.",
    "input_schema": {
        "type": "object",
        "properties": {"command": {"type": "string"}},
        "required": ["command"],
    },
}]
# ── Tool execution ────────────────────────────────────────
def run_bash(command: str) -> str:
    # 安全拦截：简单黑名单过滤，防止 LLM 被 prompt injection 诱导执行毁灭性命令。
    # 注意这是字符串匹配，不是真正沙箱，"rm -rf /" 的变体（如加空格、双斜杠）能绕过。
    dangerous = ["rm -rf /", "sudo", "shutdown", "reboot", "> /dev/"]
    if any(d in command for d in dangerous):
        return "Error: Dangerous command blocked"
    try:
        # 在 agent 工作目录下执行命令，返回 stdout + stderr 合并后的文本。
        # shell=True 支持管道、通配符等 shell 语法；timeout=120 防止死循环卡死。
        r = subprocess.run(command, shell=True, cwd=os.getcwd(),
                           capture_output=True, text=True, timeout=120)
        out = (r.stdout + r.stderr).strip()
        # 截断至 50000 字符防止输出过长撑爆 LLM 上下文窗口；空输出返回占位符避免 LLM 误判。
        return out[:50000] if out else "(no output)"
    except subprocess.TimeoutExpired:
        return "Error: Timeout (120s)"
    except (FileNotFoundError, OSError) as e:
        return f"Error: {e}"
# ── The core pattern: a while loop that calls tools until the model stops ──
def agent_loop(messages: list):
    while True:
        # 调用 LLM，传入当前对话历史和工具定义
        response = client.messages.create(
            model=MODEL, system=SYSTEM, messages=messages,
            tools=TOOLS, max_tokens=8000,
        )
        # 将 assistant 的回复追加到历史，供下次迭代使用
        messages.append({"role": "assistant", "content": response.content})
        # 如果 LLM 没有调用任何工具，说明它已经给出了最终答案，循环结束
        if response.stop_reason != "tool_use":
            return
        # 遍历 LLM 返回的所有 block，执行 tool_use 类型的调用
        results = []
        for block in response.content:
            if block.type == "tool_use":
                print(f"print1：====> \033[33m$ {block.input['command']}\033[0m")
                # run_bash 是整个 agent 的"手"——没有它，LLM 只是自言自语，
                # 无法感知文件内容、运行代码、改变系统状态
                output = run_bash(block.input["command"])
                print(f"print2：====> {output[:200]}")
                results.append({
                    "type": "tool_result",
                    "tool_use_id": block.id,
                    "content": output,
                })
        # 将工具执行结果作为 user 消息追加回历史，LLM 可据此继续推理
        messages.append({"role": "user", "content": results})
# ── Entry point ──────────────────────────────────────────
if __name__ == "__main__":
    print("s01: Agent Loop")
    print("输入问题，回车发送。输入 q 退出。\n")
    history = []
    while True:
        try:
            query = input("\033[36ms01 >> \033[0m")
        except (EOFError, KeyboardInterrupt):
            break
        if query.strip().lower() in ("q", "exit", ""):
            break
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
