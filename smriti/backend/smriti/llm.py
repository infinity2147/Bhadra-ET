"""LLM client with two backends:

- ClaudeCLI: wraps `claude -p` headless mode (Claude Code subscription auth).
  Used when no ANTHROPIC_API_KEY is present. `--setting-sources ""` isolates the
  call from user hooks/plugins.
- AnthropicSDK: standard SDK path when a key is available (production/portable).

Public surface: complete(), complete_json(), stream().
"""
from __future__ import annotations

import json
import os
import re
import subprocess
from typing import Iterator, Optional

from . import config

_JSON_FENCE = re.compile(r"```(?:json)?\s*(.*?)\s*```", re.DOTALL)


def _extract_json(text: str):
    """Parse JSON out of a model reply that may wrap it in prose/fences."""
    for candidate in (m.group(1) for m in _JSON_FENCE.finditer(text)):
        try:
            return json.loads(candidate)
        except json.JSONDecodeError:
            pass
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    # last resort: first {...} or [...] span
    for open_c, close_c in (("{", "}"), ("[", "]")):
        start = text.find(open_c)
        end = text.rfind(close_c)
        if 0 <= start < end:
            try:
                return json.loads(text[start:end + 1])
            except json.JSONDecodeError:
                continue
    raise ValueError(f"No JSON found in model reply: {text[:300]!r}")


class ClaudeCLI:
    def _base_cmd(self, model: str) -> list[str]:
        return ["claude", "-p", "--model", model, "--setting-sources", "",
                "--disallowedTools", "*"]

    def complete(self, prompt: str, system: Optional[str] = None,
                 model: str = config.MODEL_STRONG, max_tokens: int = 4096) -> str:
        cmd = self._base_cmd(model) + ["--output-format", "json"]
        if system:
            cmd += ["--append-system-prompt", system]
        proc = subprocess.run(cmd, input=prompt, capture_output=True, text=True,
                              timeout=600)
        if proc.returncode != 0:
            raise RuntimeError(f"claude CLI failed: {proc.stderr[:500]}")
        payload = json.loads(proc.stdout)
        if payload.get("is_error"):
            raise RuntimeError(f"claude CLI error result: {payload.get('result')}")
        return payload["result"]

    def stream(self, prompt: str, system: Optional[str] = None,
               model: str = config.MODEL_STRONG) -> Iterator[str]:
        cmd = self._base_cmd(model) + ["--output-format", "stream-json",
                                       "--verbose", "--include-partial-messages"]
        if system:
            cmd += ["--append-system-prompt", system]
        proc = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                stderr=subprocess.DEVNULL, text=True)
        assert proc.stdin is not None and proc.stdout is not None
        proc.stdin.write(prompt)
        proc.stdin.close()
        try:
            for line in proc.stdout:
                line = line.strip()
                if not line:
                    continue
                try:
                    event = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if event.get("type") != "stream_event":
                    continue
                inner = event.get("event", {})
                if inner.get("type") == "content_block_delta":
                    delta = inner.get("delta", {})
                    if delta.get("type") == "text_delta":
                        yield delta.get("text", "")
        finally:
            proc.wait()


class AnthropicSDK:
    def __init__(self):
        import anthropic
        self._client = anthropic.Anthropic()

    def complete(self, prompt: str, system: Optional[str] = None,
                 model: str = config.MODEL_STRONG, max_tokens: int = 4096) -> str:
        kwargs = {"model": model, "max_tokens": max_tokens,
                  "messages": [{"role": "user", "content": prompt}]}
        if system:
            kwargs["system"] = system
        resp = self._client.messages.create(**kwargs)
        return "".join(b.text for b in resp.content if b.type == "text")

    def stream(self, prompt: str, system: Optional[str] = None,
               model: str = config.MODEL_STRONG) -> Iterator[str]:
        kwargs = {"model": model, "max_tokens": 8192,
                  "messages": [{"role": "user", "content": prompt}]}
        if system:
            kwargs["system"] = system
        with self._client.messages.stream(**kwargs) as s:
            yield from s.text_stream


_backend = None


def get_backend():
    global _backend
    if _backend is None:
        _backend = AnthropicSDK() if config.LLM_BACKEND == "sdk" else ClaudeCLI()
    return _backend


def complete(prompt: str, system: Optional[str] = None,
             model: str = config.MODEL_STRONG, max_tokens: int = 4096) -> str:
    return get_backend().complete(prompt, system=system, model=model,
                                  max_tokens=max_tokens)


def complete_json(prompt: str, system: Optional[str] = None,
                  model: str = config.MODEL_STRONG, retries: int = 2):
    """Complete and parse a JSON reply; one repair retry on parse failure."""
    text = complete(prompt, system=system, model=model)
    for attempt in range(retries + 1):
        try:
            return _extract_json(text)
        except ValueError:
            if attempt == retries:
                raise
            text = complete(
                "Your previous reply was not valid JSON. Reply again with ONLY the "
                "corrected JSON, no prose, no code fences.\n\nPrevious reply:\n" + text,
                model=model)


def stream(prompt: str, system: Optional[str] = None,
           model: str = config.MODEL_STRONG) -> Iterator[str]:
    return get_backend().stream(prompt, system=system, model=model)
