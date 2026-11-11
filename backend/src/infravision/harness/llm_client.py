"""LLM and Embedding provider integration."""

import hashlib
import json
import math
from typing import List, Optional
import httpx

from infravision.config import settings


class LLMClient:
    """Provides embeddings and generation using configured provider."""

    def __init__(
        self,
        provider: Optional[str] = None,
        api_key: Optional[str] = None,
        embedding_dim: Optional[int] = None,
    ) -> None:
        self.provider = provider or settings.llm_provider
        self.api_key = api_key or settings.llm_api_key
        self.dim = embedding_dim or settings.embedding_dim

    async def get_embedding(self, text: str) -> List[float]:
        """Generate embedding vector for a piece of code or text."""
        if self.provider == "gemini" and self.api_key:
            return await self._get_gemini_embedding(text)
        elif self.provider == "openai" and self.api_key:
            return await self._get_openai_embedding(text)
        else:
            # Deterministic mock embedding based on sha256 hash for local/test use
            return self._generate_mock_embedding(text)

    async def generate_grounded_answer(
        self, prompt: str, code_context: str
    ) -> str:
        """Generate an LLM response conditioned on codebase context."""
        system_instruction = (
            "You are an expert software engineer and codebase intelligence assistant. "
            "Use the provided codebase context to answer the user request precisely. "
            "Cite file paths and symbol names when applicable."
        )

        full_prompt = (
            f"{system_instruction}\n\n"
            f"=== CODEBASE CONTEXT ===\n{code_context}\n========================\n\n"
            f"User Question: {prompt}\n"
        )

        if self.provider == "gemini" and self.api_key:
            return await self._call_gemini(full_prompt)
        elif self.provider == "openai" and self.api_key:
            return await self._call_openai(full_prompt)
        else:
            return (
                f"[Simulated Harness Response with Context ({len(code_context)} chars)]\n"
                f"Based on the indexed codebase, here is the synthesis for: '{prompt}'\n\n"
                f"Key relevant context excerpt:\n{code_context[:500]}..."
            )

    def _generate_mock_embedding(self, text: str) -> List[float]:
        """Generate a deterministic unit-length vector of length `self.dim`."""
        seed = int(hashlib.sha256(text.encode("utf-8")).hexdigest()[:8], 16)
        vec = [math.sin(seed + i * 0.1) for i in range(self.dim)]
        norm = math.sqrt(sum(x * x for x in vec)) or 1.0
        return [x / norm for x in vec]

    async def _get_gemini_embedding(self, text: str) -> List[float]:
        url = (
            f"https://generativelanguage.googleapis.com/v1beta/models/{settings.embedding_model}:embedContent"
            f"?key={self.api_key}"
        )
        payload = {"content": {"parts": [{"text": text}]}}
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(url, json=payload)
            resp.raise_for_status()
            data = resp.json()
            return data["embedding"]["values"]

    async def _get_openai_embedding(self, text: str) -> List[float]:
        url = "https://api.openai.com/v1/embeddings"
        headers = {"Authorization": f"Bearer {self.api_key}"}
        payload = {"input": text, "model": settings.embedding_model}
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(url, headers=headers, json=payload)
            resp.raise_for_status()
            data = resp.json()
            return data["data"][0]["embedding"]

    async def _call_gemini(self, prompt: str) -> str:
        url = (
            f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent"
            f"?key={self.api_key}"
        )
        payload = {"contents": [{"parts": [{"text": prompt}]}]}
        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.post(url, json=payload)
            resp.raise_for_status()
            data = resp.json()
            return data["candidates"][0]["content"]["parts"][0]["text"]

    async def _call_openai(self, prompt: str) -> str:
        url = "https://api.openai.com/v1/chat/completions"
        headers = {"Authorization": f"Bearer {self.api_key}"}
        payload = {
            "model": "gpt-4o-mini",
            "messages": [{"role": "user", "content": prompt}],
        }
        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.post(url, headers=headers, json=payload)
            resp.raise_for_status()
            data = resp.json()
            return data["choices"][0]["message"]["content"]
