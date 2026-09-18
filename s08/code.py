import os
import sys
from dotenv import load_dotenv
from anthropic import Anthropic
from pathlib import Path
load_dotenv(override=True)
WORKDIR = Path.cwd()

from tool_use import TOOLS, TOOL_HANDLERS
from hooks import trigger_hooks
from load_skill import SYSTEM as SKILLS_SYSTEM
client = Anthropic(base_url=os.getenv("ANTHROPIC_BASE_URL"))
MODEL = os.environ["MODEL_ID"]
from context_compact import snip_compact,micro_compact,tool_result_budget,reactive_compact,estimate_size,CONTEXT_LIMIT,compact_history

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

if os.getenv("ANTHROPIC_BASE_URL"):
    os.environ.pop("ANTHROPIC_AUTH_TOKEN", None)

# s05 change: SYSTEM prompt adds planning guidance
# s07: 拼接 load_skill 构建的 skills SYSTEM，让主 agent 感知可用技能
SYSTEM = (
    f"You are a coding agent at {WORKDIR}. "
    "Before starting any multi-step task, use todo_write to plan your steps. "
    "Update status as you go."
    "For complex sub-problems, use the task tool to spawn a subagent.\n\n"
    f"{SKILLS_SYSTEM}"
)
# 最大无操作提示todolist
rounds_since_todo = 0
# LLM调用接口报错最大重试次数
MAX_REACTIVE_RETRIES = 1
"""
:message  消息队列
:description agent loop循环
"""
def agent_loop(messages: list):
    global rounds_since_todo
    reactive_retries = 0
    while True:
        # s08 先进行最大文件落盘 -> 掐头去尾保留中间的数据替换成占位符 ->  压缩
        # L3
        messages[:] = tool_result_budget(messages)
        # L1
        messages[:] = snip_compact(messages)
        # L2
        messages[:] = micro_compact(messages)
        # s05 如果无操作循环进行了3次，更新模型的todolist，注入提醒
        if rounds_since_todo >= 3 and messages:
            messages.append({
                "role": "user",
                "content": "<reminder>Update your todos.</reminder>"
            })
            rounds_since_todo = 0
        # s08 L4执行，文件落盘，调用LLM返回总结
        print(f"message:字符长度：{estimate_size(messages)}字符信息：====》{messages}")
        if estimate_size(messages) > CONTEXT_LIMIT:
            print("[L4:->auto compact]")
            messages[:] = compact_history(messages)
            
        try:
            # 调用 LLM，传入当前对话历史和工具定义
            response = client.messages.create(
                model=MODEL,
                # 全局指令，设定模型的身份和行为
                system=SYSTEM,
                messages=messages,
                tools=TOOLS,
                max_tokens=8000,
            )
            # 接口调用没报错置为0
            reactive_retries = 0
        except Exception as e:
            if ("prompt_too_long" in str(e).lower() or "too many tokens" in str(e).lower()) and reactive_retries < MAX_REACTIVE_RETRIES:
                print("[reactive compact]")
                # 调用报错启用L5应急策略，保留最后5条message 和 摘要
                messages[:] = reactive_compact(messages)
                reactive_retries += 1
                continue
            raise
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
            if block.type != "tool_use": continue
            print(f"\033[33m> block.name {block.name}\033[0m")
            if block.name == "compact":
                messages[:] = compact_history(messages)
                results.append({
                    "type": "tool_result",
                    "tool_use_id": block.id,
                    "content": "[Compacted. Conversation history has been summarized.]"
                })
                messages.append({
                    "role": "user",
                    "content": results
                })
                break  # 结束当前回合，用压缩的上下文重新开始
            # s04 调用工具前调用hook拦截【工具权限判断】
            blocked = trigger_hooks("PreToolUse", block)
            if blocked:
                results.append({
                    "type": "tool_result",
                    "tool_use_id": block.id,
                    "content": str(blocked)
                })
                continue
            handler = TOOL_HANDLERS.get(block.name)
            try:
                output = handler(**block.input) if handler else f"Unknown: {block.name}"
            except Exception as e:
                output = f"Error: {e}"
            # 	工具执行后调用
            trigger_hooks("PostToolUse", block, output)  # s04: post hook
            # s05: 当调用 todo_write 时重置提醒计数器
            if block.name == "todo_write": rounds_since_todo = 0
            results.append(
                {
                    "type": "tool_result",
                    "tool_use_id": block.id,
                    "content": output,
                }
            )
        else:
            # 正常路径：没有调用压缩
            messages.append({"role": "user", "content": results})
        continue
        # 将工具执行结果作为 user 消息追加回历史，LLM 可据此继续推理
        messages.append({"role": "user", "content": results})


# ── Entry point ──────────────────────────────────────────
if __name__ == "__main__":
    print("s07: skills")
    print("输入问题，回车发送。输入 q 退出。\n")
    history = []
    while True:
        try:
            query = input("\033[36ms06 >> \033[0m")
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
                    print(f"final====>{block.text}")
        print()
