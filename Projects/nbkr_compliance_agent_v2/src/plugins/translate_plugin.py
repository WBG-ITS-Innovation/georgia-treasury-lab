# src/plugins/translate_plugin.py
from __future__ import annotations

class TranslatePlugin:
    def __init__(self, kernel) -> None:
        self.kernel = kernel

    async def to_en(self, text: str) -> str:
        if not text: return ""
        msg = await self.kernel.invoke_prompt(f"Translate to EN (preserve legal meaning). Plain text:\n{text}")
        return msg or text
