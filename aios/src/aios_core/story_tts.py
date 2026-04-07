from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import Any

import requests


class StoryTtsError(RuntimeError):
    pass


def _load_cfg(root_dir: Path) -> dict[str, Any]:
    p = root_dir / "config" / "story-audio.json"
    if not p.exists():
        return {"provider": "fpt", "fpt": {"api_base": "https://api.fpt.ai/hmi/tts/v5", "speed": "0", "voice_map": {"bac": "banmai", "trung": "myan", "nam": "thuminh"}}}
    return json.loads(p.read_text(encoding="utf-8"))


def _resolve_voice(cfg: dict[str, Any], voice_key: str) -> str:
    vm = ((cfg.get("fpt") or {}).get("voice_map") or {})
    return str(vm.get(voice_key, vm.get("bac", "banmai")))


def synth_story_audio(root_dir: Path, text: str, voice_key: str = "bac") -> bytes:
    cfg = _load_cfg(root_dir)
    provider = str(cfg.get("provider", "fpt")).lower()
    if provider != "fpt":
        raise StoryTtsError("only provider=fpt is currently supported")

    api_key = os.environ.get("FPT_TTS_API_KEY", "").strip()
    if not api_key:
        raise StoryTtsError("missing FPT_TTS_API_KEY in environment")

    fpt = cfg.get("fpt", {})
    api_base = str(fpt.get("api_base", "https://api.fpt.ai/hmi/tts/v5"))
    speed = str(fpt.get("speed", "0"))
    voice = _resolve_voice(cfg, voice_key)

    resp = requests.post(
        api_base,
        data=text.encode("utf-8"),
        headers={
            "api-key": api_key,
            "voice": voice,
            "speed": speed,
            "format": "mp3",
        },
        timeout=30,
    )
    if resp.status_code >= 300:
        raise StoryTtsError(f"fpt tts request failed: HTTP {resp.status_code}")

    payload = resp.json()
    audio_url = str(payload.get("async") or payload.get("url") or "").strip()
    if not audio_url:
        raise StoryTtsError(f"fpt tts response missing audio url: {payload}")

    last_err = ""
    for _ in range(20):
        try:
            a = requests.get(audio_url, timeout=30)
            if a.status_code == 200 and a.content:
                return a.content
            last_err = f"status={a.status_code}"
        except Exception as exc:  # noqa: BLE001
            last_err = str(exc)
        time.sleep(0.8)

    raise StoryTtsError(f"failed to download synthesized audio: {last_err}")
