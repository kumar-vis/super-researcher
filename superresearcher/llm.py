from __future__ import annotations

import json
import subprocess
import tempfile
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

from .config import codex_bin


class LLMError(RuntimeError):
    pass


def extract_json(text: str) -> Any:
    text = text.strip()
    if not text:
        raise ValueError("empty response")
    if text.startswith("```"):
        lines = text.splitlines()
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].startswith("```"):
            lines = lines[:-1]
        text = "\n".join(lines).strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    start_obj = text.find("{")
    start_arr = text.find("[")
    starts = [p for p in [start_obj, start_arr] if p >= 0]
    if not starts:
        raise
    start = min(starts)
    opener = text[start]
    closer = "}" if opener == "{" else "]"
    end = text.rfind(closer)
    if end <= start:
        raise
    return json.loads(text[start : end + 1])


class LLMClient:
    def __init__(self, keys: dict[str, str], model: str = "gpt-5") -> None:
        self.keys = keys
        self.model = model

    def json_call(self, prompt: str, fallback: Any) -> Any:
        for call in (self._codex_call, self._gemini_call):
            try:
                raw = call(prompt)
                return extract_json(raw)
            except Exception:
                continue
        return fallback

    def text_call(self, prompt: str) -> str:
        errors = []
        for call in (self._codex_default_call, self._gemini_text_call):
            try:
                text = call(prompt).strip()
                return strip_markdown_fence(text)
            except Exception as exc:
                errors.append(str(exc))
        raise LLMError("LLM text call failed: " + " | ".join(error for error in errors if error))

    def _codex_call(self, prompt: str) -> str:
        return self._run_codex(prompt, use_default_model=False)

    def _codex_default_call(self, prompt: str) -> str:
        return self._run_codex(prompt, use_default_model=True)

    def _run_codex(self, prompt: str, use_default_model: bool = False) -> str:
        binary = codex_bin()
        if binary is None:
            raise LLMError("Codex binary not found")
        with tempfile.TemporaryDirectory() as tmpdir:
            out = Path(tmpdir) / "last_message.txt"
            cmd = [
                str(binary),
                "exec",
                "--skip-git-repo-check",
                "--sandbox",
                "read-only",
                "-c",
                'model_reasoning_effort="high"',
                "-o",
                str(out),
                "-",
            ]
            if self.model and not use_default_model:
                cmd[5:5] = ["-m", self.model]
            try:
                result = subprocess.run(
                    cmd,
                    input=prompt,
                    text=True,
                    capture_output=True,
                    timeout=180,
                    check=False,
                )
            except subprocess.TimeoutExpired as exc:
                raise LLMError("Codex call timed out") from exc
            if result.returncode != 0:
                # Some Codex builds may reject config keys; retry with the safest surface.
                cmd = [
                    str(binary),
                    "exec",
                    "--skip-git-repo-check",
                    "--sandbox",
                    "read-only",
                    "-o",
                    str(out),
                    "-",
                ]
                if self.model and not use_default_model:
                    cmd[5:5] = ["-m", self.model]
                result = subprocess.run(
                    cmd,
                    input=prompt,
                    text=True,
                    capture_output=True,
                    timeout=180,
                    check=False,
                )
            if result.returncode != 0:
                raise LLMError(result.stderr[-1000:])
            if out.exists():
                return out.read_text(encoding="utf-8")
            return result.stdout

    def _gemini_call(self, prompt: str) -> str:
        key = self.keys.get("GEMINI_API_KEY") or self.keys.get("GOOGLE_API_KEY")
        if not key:
            raise LLMError("Gemini key not configured")
        model = self.keys.get("GEMINI_MODEL", "gemini-2.0-flash")
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={key}"
        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {
                "temperature": 0.7,
                "responseMimeType": "application/json",
            },
        }
        req = urllib.request.Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=90) as resp:
                data = json.loads(resp.read().decode("utf-8", errors="replace"))
        except urllib.error.URLError as exc:
            raise LLMError(str(exc)) from exc
        parts = data.get("candidates", [{}])[0].get("content", {}).get("parts", [])
        text = "".join(part.get("text", "") for part in parts)
        if not text:
            raise LLMError("empty Gemini response")
        return text

    def _gemini_text_call(self, prompt: str) -> str:
        key = self.keys.get("GEMINI_API_KEY") or self.keys.get("GOOGLE_API_KEY")
        if not key:
            raise LLMError("Gemini key not configured")
        model = self.keys.get("GEMINI_MODEL", "gemini-2.0-flash")
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={key}"
        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {
                "temperature": 0.2,
            },
        }
        req = urllib.request.Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=90) as resp:
                data = json.loads(resp.read().decode("utf-8", errors="replace"))
        except urllib.error.URLError as exc:
            raise LLMError(str(exc)) from exc
        parts = data.get("candidates", [{}])[0].get("content", {}).get("parts", [])
        text = "".join(part.get("text", "") for part in parts)
        if not text:
            raise LLMError("empty Gemini response")
        return text


def strip_markdown_fence(text: str) -> str:
    text = text.strip()
    if not text.startswith("```"):
        return text
    lines = text.splitlines()
    if lines and lines[0].startswith("```"):
        lines = lines[1:]
    if lines and lines[-1].startswith("```"):
        lines = lines[:-1]
    return "\n".join(lines).strip()
