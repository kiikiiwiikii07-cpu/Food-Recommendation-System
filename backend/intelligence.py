"""Small NVIDIA NIM client. API keys stay server-side; caller owns safe validation/fallback."""
import json
import os
import re
import threading
import time

import httpx

BASE_URL = os.getenv("NVIDIA_BASE_URL", "https://integrate.api.nvidia.com/v1").rstrip("/")
MODEL = os.getenv("NVIDIA_MODEL", "nvidia/nemotron-3.5-lightning-30b-a3b")
_stats_lock = threading.Lock()
_stats = {"requests": 0, "successes": 0, "errors": 0, "latency_ms_total": 0, "input_tokens": 0, "output_tokens": 0}


class ProviderError(Exception):
    """Safe provider failure without exposing tokens or upstream body text."""


def metrics():
    with _stats_lock:
        return dict(_stats)


def _json_object(text):
    text = (text or "").strip()
    try:
        value = json.loads(text)
    except (ValueError, TypeError):
        start, end = text.find("{"), text.rfind("}")
        if start < 0 or end <= start:
            raise ProviderError("The model returned an invalid structured response")
        try:
            value = json.loads(text[start:end + 1])
        except ValueError:
            raise ProviderError("The model returned an invalid structured response")
    if not isinstance(value, dict):
        raise ProviderError("The model response was not an object")
    return value


def chat_json(system, prompt, max_tokens=700, timeout_seconds=15):
    key = os.getenv("NVIDIA_API_KEY", "").strip()
    if not key:
        raise ProviderError("NVIDIA API key is not configured")
    base_url = os.getenv("NVIDIA_BASE_URL", BASE_URL).rstrip("/")
    model = os.getenv("NVIDIA_MODEL", MODEL)
    started = time.monotonic()
    with _stats_lock:
        _stats["requests"] += 1
    try:
        response = httpx.post(
            base_url + "/chat/completions",
            headers={"Authorization": "Bearer " + key, "Content-Type": "application/json"},
            json={
                "model": model,
                "messages": [{"role": "system", "content": system}, {"role": "user", "content": prompt}],
                "temperature": 0.2,
                "top_p": 0.95,
                "max_tokens": max_tokens,
                "stream": False,
                "chat_template_kwargs": {"enable_thinking": False},
            },
            timeout=httpx.Timeout(float(timeout_seconds), connect=min(8.0, float(timeout_seconds))),
        )
        response.raise_for_status()
        payload = response.json()
        usage = payload.get("usage", {})
        with _stats_lock:
            _stats["input_tokens"] += int(usage.get("prompt_tokens", 0) or 0)
            _stats["output_tokens"] += int(usage.get("completion_tokens", 0) or 0)
        content = payload["choices"][0]["message"]["content"]
        result = _json_object(content)
        with _stats_lock:
            _stats["successes"] += 1
        return result
    except ProviderError:
        with _stats_lock:
            _stats["errors"] += 1
        raise
    except httpx.TimeoutException:
        with _stats_lock:
            _stats["errors"] += 1
        raise ProviderError("NVIDIA NIM timed out")
    except httpx.HTTPStatusError as exc:
        with _stats_lock:
            _stats["errors"] += 1
        raise ProviderError("NVIDIA NIM returned HTTP status " + str(exc.response.status_code))
    except httpx.ConnectError:
        with _stats_lock:
            _stats["errors"] += 1
        raise ProviderError("Cannot connect to NVIDIA NIM from this environment")
    except httpx.RequestError:
        with _stats_lock:
            _stats["errors"] += 1
        raise ProviderError("NVIDIA NIM request could not be completed")
    except (KeyError, IndexError, TypeError, ValueError):
        with _stats_lock:
            _stats["errors"] += 1
        raise ProviderError("NVIDIA NIM request failed or returned an invalid response")
    finally:
        with _stats_lock:
            _stats["latency_ms_total"] += int((time.monotonic() - started) * 1000)


def safe_intent(raw):
    """Allow-list model output and bound all user-controlled constraint values."""
    slots = {"breakfast", "lunch", "dinner", "snack"}
    diets = {"any", "vegetarian", "vegan", "non-vegetarian"}
    meal_type = raw.get("meal_type")
    diet = raw.get("diet")
    try:
        minutes = int(raw.get("max_minutes", 240))
    except (TypeError, ValueError):
        minutes = 240
    def words(value):
        if not isinstance(value, list):
            return []
        return [re.sub(r"[^a-zA-Z0-9 -]", "", x).strip().lower()[:40] for x in value if isinstance(x, str) and x.strip()][:8]
    return {
        "meal_type": meal_type if meal_type in slots else None,
        "diet": diet if diet in diets else "any",
        "max_minutes": min(240, max(5, minutes)),
        "include_ingredients": words(raw.get("include_ingredients")),
        "avoid_ingredients": words(raw.get("avoid_ingredients")),
        "food_ids": [x for x in raw.get("food_ids", []) if isinstance(x, str)][:6] if isinstance(raw.get("food_ids", []), list) else [],
    }


def safe_explanations(raw, allowed_ids):
    if not isinstance(raw, dict) or not isinstance(raw.get("items"), list):
        return {}
    result = {}
    for item in raw["items"][:6]:
        if not isinstance(item, dict) or item.get("id") not in allowed_ids:
            continue
        why = item.get("why")
        if isinstance(why, str):
            why = re.sub(r"[\r\n\x00-\x1f]", " ", why).strip()[:180]
            if why:
                result[item["id"]] = why
    return result
