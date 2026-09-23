"""统一的 LLM 调用入口。

把 client.messages.create 封装成 call_llm：
- 常用字段：messages / system / tools / max_tokens（model 固定读 MODEL_ID）
- 扩展字段：其余参数通过 **extra 透传给 SDK（如 temperature、stop_sequences、thinking 等）
- 调用成功后自动记录 token 用量，再返回 response
"""

import os
from anthropic import Anthropic, NOT_GIVEN
from error_recovery import with_retry
import token_usage


client = Anthropic(base_url=os.getenv("ANTHROPIC_BASE_URL"))
MODEL = os.environ["MODEL_ID"]


def call_llm(messages, *, system=NOT_GIVEN, tools=NOT_GIVEN, max_tokens=8000, **extra):
    """调用 LLM，记录 token 用量并返回 response。"""
    response = client.messages.create(
        model=MODEL,
        messages=messages,
        system=system,
        tools=tools,
        max_tokens=max_tokens,
        **extra,
    )
    token_usage.record(response)
    return response

# 创建LLM调用
def create_llm_connect(messages, *, system=NOT_GIVEN, tools=NOT_GIVEN, max_tokens=8000, **extra):
    """调用 LLM，记录 token 用量并返回 response。"""
    response = client.messages.create(
        model=MODEL,
        messages=messages,
        system=system,
        tools=tools,
        max_tokens=max_tokens,
        **extra,
    )
    token_usage.record(response)
    return response
