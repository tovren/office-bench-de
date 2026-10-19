"""Model and profile configuration (TOML files in configs/).

A model config says how to reach one model with one setting (e.g. a thinking level):

    name = "qwen3.8-27b-medium"             # id in results; one config per model and setting
    label = "Qwen3.8-27B, thinking medium"  # shown in reports
    base_url = "https://ai-gateway.vercel.sh/v1"
    model = "alibaba/qwen3.8-27b"
    api_key_env = "AI_GATEWAY_API_KEY"      # or api_key_file = "~/.config/…"; none for a local server
    [params]                                # merged into every request body as given
    reasoning = { effort = "medium" }
    temperature = 1.0
    [info]                                  # facts for the report (free keys)
    open_weights = true

A profile fixes everything around the model that the benchmark holds constant: system prompt, reference date,
how attachments are put into the message, tool settings and the round limit (configs/profiles/default.toml).
"""

from __future__ import annotations

import hashlib
import os
import re
import tomllib
from datetime import date
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, model_validator

ROOT = Path(__file__).resolve().parents[2]
PROFILES_DIR = ROOT / "configs" / "profiles"


class _Model(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class ModelConfig(_Model):
    name: str = Field(pattern=r"^[a-z0-9][a-z0-9._-]*$")
    label: str
    base_url: str
    model: str
    api_key_env: str | None = None
    api_key_file: str | None = None
    params: dict[str, Any] = {}
    info: dict[str, Any] = {}
    concurrency: int = Field(default=4, ge=1)  # parallel task runs against this endpoint

    @model_validator(mode="after")
    def _key(self):
        if self.api_key_env and self.api_key_file:
            raise ValueError("set api_key_env or api_key_file, not both")
        if {"messages", "tools", "stream", "model"} & set(self.params):
            raise ValueError("params must not set messages, tools, stream or model")
        return self

    def api_key(self) -> str | None:
        if self.api_key_env:
            key = os.environ.get(self.api_key_env)
            if not key:
                raise ValueError(f"environment variable {self.api_key_env} is not set")
            return key.strip()
        if self.api_key_file:
            return Path(self.api_key_file).expanduser().read_text(encoding="utf-8").strip()
        return None

    def public(self) -> dict:
        """The config as written into results (no key, only where it comes from)."""
        return self.model_dump()


class Profile(_Model):
    name: str
    description: str = ""
    today: date
    system_prompt: str
    # How the extracted text of attached files goes into the user message; {files} and {message} are filled in,
    # each file is rendered with attachment_file ({name}, {text}).
    attachment_message: str
    attachment_file: str
    valves: dict[str, Any] = {}
    max_rounds: int = Field(default=8, ge=1)  # tool rounds per user message

    def render_user_message(self, text: str, attachments) -> str:
        if not attachments:
            return text
        files = "\n\n".join(self.attachment_file.format(name=a.name, text=a.text) for a in attachments)
        return self.attachment_message.format(files=files, message=text)

    def digest(self) -> str:
        return hashlib.sha256(self.model_dump_json().encode()).hexdigest()[:12]


def _load(path: Path, cls):
    try:
        return cls.model_validate(tomllib.loads(path.read_text(encoding="utf-8")))
    except Exception as e:
        raise ValueError(f"{path}: {e}") from e


def load_model(path: str | Path) -> ModelConfig:
    return _load(Path(path), ModelConfig)


def load_profile(name_or_path: str | Path = "default") -> Profile:
    p = Path(name_or_path)
    if not p.suffix and not p.exists():
        p = PROFILES_DIR / f"{name_or_path}.toml"
    profile = _load(p, Profile)
    for field_name in ("attachment_message", "attachment_file"):
        fields = set(re.findall(r"\{(\w+)\}", getattr(profile, field_name)))
        allowed = {"files", "message"} if field_name == "attachment_message" else {"name", "text"}
        if fields != allowed:
            raise ValueError(f"{p}: {field_name} must use exactly {sorted(allowed)}")
    return profile
