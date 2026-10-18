"""LLM access: a small provider interface, plus a wrapper that caches and logs every call.

Adding a provider means adding one class with a `complete()` method and a branch in make_client().
"""

import hashlib
import json
import os
import time
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Protocol

from dotenv import load_dotenv

from kgqa.config import KGQA_DIR, LLM_CACHE_PATH, LLM_LOG_PATH

DEFAULT_MODEL = "gemini-3.5-flash-lite"
# Hard cap per call, thinking tokens included.
MAX_OUTPUT_TOKENS = 4000
# None = the model's default. Google recommends keeping the default (1.0) for Gemini 3 models
# and warns that lower values can cause looping, so we do not force temperature 0.
TEMPERATURE = None


@dataclass
class LLMResponse:
    text: str
    input_tokens: int | None
    output_tokens: int | None  # includes thinking tokens
    latency_s: float
    cached: bool = False


class LLMClient(Protocol):
    model: str

    def complete(self, system: str, user: str, json_schema: dict | None = None) -> LLMResponse: ...


class GeminiClient:
    """Google Gemini API. Waits between calls to respect the free tier's requests-per-minute limit."""

    RETRY_WAITS_S = (15, 60)  # waits before 2nd and 3rd attempt on 429/500/503 errors

    def __init__(self, model: str, requests_per_minute: int = 15):
        from google import genai  # imported here so other providers do not need this package

        self.model = model
        self._client = genai.Client()  # reads GEMINI_API_KEY from the environment
        self._min_interval_s = 60 / requests_per_minute
        self._last_call = 0.0

    def complete(self, system: str, user: str, json_schema: dict | None = None) -> LLMResponse:
        from google.genai import errors, types

        config = types.GenerateContentConfig(
            system_instruction=system,
            temperature=TEMPERATURE,
            max_output_tokens=MAX_OUTPUT_TOKENS,
            response_mime_type="application/json" if json_schema else None,
            response_json_schema=json_schema,
        )
        for wait_s in (0, *self.RETRY_WAITS_S):
            time.sleep(max(wait_s, self._last_call + self._min_interval_s - time.monotonic()))
            self._last_call = time.monotonic()
            start = time.perf_counter()
            try:
                response = self._client.models.generate_content(model=self.model, contents=user, config=config)
                break
            except errors.APIError as error:
                if error.code not in (429, 500, 503):  # only rate limits and server errors are worth retrying
                    raise
                last_error = error
        else:
            raise RuntimeError(
                f"Gemini API still failing after {len(self.RETRY_WAITS_S) + 1} attempts "
                f"({last_error.code}: {last_error.message}). If the daily quota is used up, run again "
                "later: answered calls are cached and will not be repeated."
            )
        usage = response.usage_metadata
        return LLMResponse(
            text=response.text or "",
            input_tokens=usage.prompt_token_count if usage else None,
            output_tokens=(usage.candidates_token_count or 0) + (usage.thoughts_token_count or 0) if usage else None,
            latency_s=round(time.perf_counter() - start, 2),
        )


class LoggedClient:
    """Wraps a provider client: identical requests are answered from a cache, and every
    call (cached or not) is appended to a JSONL log."""

    def __init__(self, client: LLMClient, cache_path: Path = LLM_CACHE_PATH, log_path: Path = LLM_LOG_PATH):
        self.client = client
        self.model = client.model
        self.cache_path = cache_path
        self.log_path = log_path
        self._cache = {}
        if cache_path.exists():
            for line in cache_path.read_text(encoding="utf-8").splitlines():
                entry = json.loads(line)
                self._cache[entry["key"]] = entry["response"]

    def complete(self, system: str, user: str, json_schema: dict | None = None, step: str = "") -> LLMResponse:
        # Everything that can change the reply is part of the key.
        request = [self.model, system, user, json_schema, TEMPERATURE, MAX_OUTPUT_TOKENS]
        key = hashlib.sha256(json.dumps(request, sort_keys=True).encode("utf-8")).hexdigest()
        if key in self._cache:
            response = LLMResponse(**{**self._cache[key], "cached": True})
        else:
            response = self.client.complete(system, user, json_schema)
            self._cache[key] = asdict(response)
            _append_jsonl(self.cache_path, {"key": key, "response": asdict(response)})
        _append_jsonl(self.log_path, {
            "timestamp": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "step": step,
            "model": self.model,
            "cached": response.cached,
            "system": system,
            "user": user,
            "response": response.text,
            "input_tokens": response.input_tokens,
            "output_tokens": response.output_tokens,
            "latency_s": response.latency_s,
        })
        return response


def _append_jsonl(path: Path, record: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as file:
        file.write(json.dumps(record, ensure_ascii=False) + "\n")


def make_client() -> LoggedClient:
    """Build the logged client from kgqa/.env (LLM_PROVIDER, LLM_MODEL, GEMINI_API_KEY)."""
    load_dotenv(KGQA_DIR / ".env")
    provider = os.getenv("LLM_PROVIDER") or "gemini"
    model = os.getenv("LLM_MODEL") or DEFAULT_MODEL
    if provider == "gemini":
        return LoggedClient(GeminiClient(model))
    raise ValueError(f"Unknown LLM_PROVIDER: {provider!r}")
