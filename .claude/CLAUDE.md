# WelcomeScreen

AI Agent 学习项目，包含两个递进的 Agent Loop 实现。

## 当前工作模块

**当前编辑版本：s03**

> 当切换到 s01 或 s02 时，更新此行。所有命令执行和文件编辑都在对应模块路径下进行。

## 项目结构

```
WelcomeScreen/
├── hello.py              # 入门测试
├── s01/                  # Agent Loop 基础版
│   ├── code.py
│   ├── requirements.txt
│   └── README.md
└── s02/                  # Agent Loop 增强版
    ├── code.py
    └── requirements.txt
```

## 模块说明

### s01 — Agent Loop 基础版
- 仅暴露 `bash` 工具
- 核心模式：`while stop_reason == "tool_use"` 循环调用 LLM 并执行工具
- 运行：`python s01/code.py`

### s02 — Agent Loop 增强版
- 除 `bash` 外，额外暴露 `read_file`、`write_file`、`edit_file`、`glob` 四个文件操作工具
- 工具调用在 LLM 侧声明，实际执行仍由 `run_bash` 完成（当前实现为占位）
- 运行：`python s02/code.py`

## 环境变量要求

两个模块均需以下环境变量：
- `ANTHROPIC_API_KEY` — Anthropic API 密钥
- `MODEL_ID` — 模型 ID（如 `claude-sonnet-4-5`）
- `ANTHROPIC_BASE_URL`（可选）— 自定义 API 端点

使用 `.env` 文件管理：
```
ANTHROPIC_API_KEY=sk-ant-...
MODEL_ID=claude-sonnet-4-5
# ANTHROPIC_BASE_URL=https://your-proxy.com
```

## 安装依赖

```bash
pip install -r s01/requirements.txt   # 或 s02/requirements.txt（依赖相同）
cp .env.example .env
```

## Agent Loop 核心模式

两个模块共享同一个核心循环：

```
用户输入 → LLM (带 tools) → 返回 tool_use → 执行工具 → 结果回喂 LLM → 循环
                                            ↓
                                      stop_reason != tool_use → 输出最终答案
```