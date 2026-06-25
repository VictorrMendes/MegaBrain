import json
from typing import AsyncIterator

import httpx

from kernel.config import settings
from kernel.logger import get_logger
from .base import (
    ChatMessage,
    EmbedResult,
    EmbeddingProvider,
    GenerateResult,
    LLMProvider,
)

logger = get_logger(__name__)


class OllamaProvider(LLMProvider, EmbeddingProvider):
    def __init__(
        self,
        base_url: str | None = None,
        model: str | None = None,
        embed_model: str | None = None,
    ):
        self.base_url = (base_url or settings.ollama_base_url).rstrip("/")
        self.model = model or settings.ollama_default_model
        self.embed_model = embed_model or settings.ollama_embedding_model

    async def generate(
        self, prompt: str, system: str | None = None, **kwargs
    ) -> GenerateResult:
        payload: dict = {"model": self.model, "prompt": prompt, "stream": False}
        if system:
            payload["system"] = system

        async with httpx.AsyncClient(timeout=120.0) as client:
            resp = await client.post(f"{self.base_url}/api/generate", json=payload)
            resp.raise_for_status()
            data = resp.json()

        logger.debug("ollama.generate", model=self.model, tokens=data.get("eval_count"))
        return GenerateResult(
            content=data["response"],
            model=self.model,
            tokens_used=data.get("eval_count", 0),
        )

    async def stream(
        self, prompt: str, system: str | None = None, **kwargs
    ) -> AsyncIterator[str]:
        payload: dict = {"model": self.model, "prompt": prompt, "stream": True}
        if system:
            payload["system"] = system

        async with httpx.AsyncClient(timeout=120.0) as client:
            async with client.stream(
                "POST", f"{self.base_url}/api/generate", json=payload
            ) as resp:
                resp.raise_for_status()
                async for line in resp.aiter_lines():
                    if line:
                        data = json.loads(line)
                        yield data.get("response", "")
                        if data.get("done"):
                            break

    async def chat(
        self, messages: list[ChatMessage], **kwargs
    ) -> GenerateResult:
        payload = {
            "model": self.model,
            "messages": [{"role": m.role, "content": m.content} for m in messages],
            "stream": False,
            "think": False,
        }
        async with httpx.AsyncClient(timeout=120.0) as client:
            resp = await client.post(f"{self.base_url}/api/chat", json=payload)
            resp.raise_for_status()
            data = resp.json()

        content = data["message"]["content"]
        logger.debug("ollama.chat", model=self.model, tokens=data.get("eval_count"))
        return GenerateResult(
            content=content,
            model=self.model,
            tokens_used=data.get("eval_count", 0),
        )

    async def chat_stream(
        self, messages: list[ChatMessage], **kwargs
    ) -> AsyncIterator[str]:
        payload = {
            "model": self.model,
            "messages": [{"role": m.role, "content": m.content} for m in messages],
            "stream": True,
            "think": False,
        }
        async with httpx.AsyncClient(timeout=120.0) as client:
            async with client.stream(
                "POST", f"{self.base_url}/api/chat", json=payload
            ) as resp:
                resp.raise_for_status()
                in_think = False
                buf = ""
                async for line in resp.aiter_lines():
                    if line:
                        data = json.loads(line)
                        chunk = data.get("message", {}).get("content", "")
                        if chunk:
                            buf += chunk
                            # strip <think>...</think> blocks that may span chunks
                            while True:
                                if in_think:
                                    end = buf.find("</think>")
                                    if end == -1:
                                        buf = ""
                                        break
                                    buf = buf[end + len("</think>"):]
                                    in_think = False
                                else:
                                    start = buf.find("<think>")
                                    if start == -1:
                                        yield buf
                                        buf = ""
                                        break
                                    if start > 0:
                                        yield buf[:start]
                                    buf = buf[start + len("<think>"):]
                                    in_think = True
                        if data.get("done"):
                            if buf and not in_think:
                                yield buf
                            break

    async def embed(self, text: str) -> EmbedResult:
        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.post(
                f"{self.base_url}/api/embed",
                json={"model": self.embed_model, "input": text},
            )
            resp.raise_for_status()
            data = resp.json()

        embedding = data["embeddings"][0]
        return EmbedResult(
            embedding=embedding,
            model=self.embed_model,
            dimensions=len(embedding),
        )

    async def embed_batch(self, texts: list[str]) -> list[EmbedResult]:
        async with httpx.AsyncClient(timeout=300.0) as client:
            resp = await client.post(
                f"{self.base_url}/api/embed",
                json={"model": self.embed_model, "input": texts},
            )
            resp.raise_for_status()
            data = resp.json()

        return [
            EmbedResult(
                embedding=emb, model=self.embed_model, dimensions=len(emb)
            )
            for emb in data["embeddings"]
        ]
