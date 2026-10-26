"""Prompt composition layer: strict two-channel builder.

Keeps untrusted user content out of the trusted system channel. Exposes the
message builder and its channel components.
"""

from __future__ import annotations

from hirely.prompts.builder import (
    DATA_NOT_COMMANDS_NOTICE,
    HIRELY_PREAMBLE,
    UserSection,
    build_messages,
    build_system_prompt,
    build_user_prompt,
)

__all__ = [
    "DATA_NOT_COMMANDS_NOTICE",
    "HIRELY_PREAMBLE",
    "UserSection",
    "build_messages",
    "build_system_prompt",
    "build_user_prompt",
]
