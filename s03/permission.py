from utils.printColor import print_color as printColor
from pathlib import Path

# 闸门 1：一张硬拒绝表，先查，命中就返回阻止信息。
DENY_LIST = [
    "rm -rf /",
    "sudo",
    "shutdown",
    "reboot",
    "mkfs",
    "dd if=",
    "> /dev/sda",
]


def check_deny_list(command: str) -> str | None:
    for pattern in DENY_LIST:
        if pattern in command:
            return f"Blocked: '{pattern}' is on the deny list"
    return None


# 闸门 2：规则匹配——描述"什么时候需要问用户"。每条规则指定工具和检查条件。
WORKDIR = Path.cwd()


def _is_file_edit(command: str) -> bool:
    """判断 bash 命令是否会写文件：输出重定向(> / >>) 或 sed -i / tee。

    重定向目标若以 & 开头（如 2>&1、>&2）是文件描述符重定向，不视为写文件。
    """
    if "sed -i" in command or "tee " in command:
        return True
    for op in (">>", ">"):
        idx = command.find(op)
        if idx != -1 and not command[idx + len(op):].strip().startswith("&"):
            return True
    return False


PERMISSION_RULES = [
    {
        "tools": ["write_file", "edit_file"],
        "check": lambda args: (
            not (WORKDIR / args.get("path", "")).resolve().is_relative_to(WORKDIR)
        ),
        "message": "Writing outside workspace",
    },
    {
        "tools": ["bash"],
        "check": lambda args: any(
            #  [删除文件或目录、修改文件权限]
            kw in args.get("command", "") for kw in ["rm ","> /etc/", "chmod 777"]
        ),
        "message": "Potentially destructive command",
    },
    {
        "tools": ["bash"],
        "check": lambda args: _is_file_edit(args.get("command", "")),
        "message": "Editing files via bash",
    },
]


def check_rules(tool_name: str, args: dict) -> str | None:
    for rule in PERMISSION_RULES:
        if tool_name in rule["tools"] and rule["check"](args):
            return rule["message"]
    return None


# 闸门 3：规则命中后，暂停等用户输入。


def ask_user(tool_name: str, args: dict, reason: str) -> str:
    print(f"\n⚠  {reason}")
    print(f"   Tool: {tool_name}({args})")
    choice = input("   Allow? [y/N] ").strip().lower()
    return "allow" if choice in ("y", "yes") else "deny"


# permission 函，把三道闸门串在一起
def check_permission(block) -> bool:
    # 闸门 1: 硬拒绝
    if block.name == "bash":
        reason = check_deny_list(block.input.get("command", ""))
        if reason:
            print(f"\n⛔ {reason}")
            return False

    # 闸门 2 + 3: 规则匹配 → 用户审批
    print(f"input:====> {block.input}")

    reason = check_rules(block.name, block.input)

    printColor(f"reason:====> {reason}", '#00ff00')
    if reason:
        decision = ask_user(block.name, block.input, reason)
        printColor(decision,"ff0000")
        if decision == "deny":
            return False

    return True