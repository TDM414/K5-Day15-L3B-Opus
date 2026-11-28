"""Model adapter. All provider calls go through this module and are traced."""
import json
import os
import re
import time
import urllib.error
import urllib.parse
import urllib.request

from tracing import model_call

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
GEMINI_URL_TEMPLATE = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"


def load_env(path=os.path.join(ROOT, ".env")):
    """Load KEY=VALUE settings without overriding process environment."""
    if not os.path.exists(path):
        return
    with open(path, encoding="utf-8-sig") as source:
        for line in source:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


load_env()
MODEL_PROVIDER = (os.environ.get("MODEL_PROVIDER") or "fake").strip().lower()
MODEL_NAME = (os.environ.get("MODEL_NAME") or "").strip()
API_KEY = (os.environ.get("OPENROUTER_API_KEY") or os.environ.get("API_KEY") or "").strip()
GEMINI_API_KEY = (os.environ.get("GEMINI_API_KEY") or os.environ.get("API_KEY") or "").strip()


class ModelError(RuntimeError):
    """Safe, user-displayable model configuration or transport error."""


def _post_json_with_retry(url: str, headers: dict, body: dict, provider_label: str) -> dict:
    """POST JSON with retry on transient HTTP/network failures without leaking secrets."""
    request = urllib.request.Request(
        url,
        data=json.dumps(body, ensure_ascii=False).encode("utf-8"),
        headers=headers,
        method="POST",
    )
    last_error = None
    for attempt in range(3):
        try:
            with urllib.request.urlopen(request, timeout=40) as response:
                return json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            provider_message = ""
            try:
                error_payload = json.loads(exc.read(16384).decode("utf-8", "replace"))
                provider_message = str((error_payload.get("error") or {}).get("message") or "")[:240]
            except (ValueError, AttributeError):
                pass
            if exc.code not in (408, 429, 500, 502, 503, 504) or attempt == 2:
                labels = {
                    400: "Yêu cầu hoặc tên model không hợp lệ",
                    401: "API key bị từ chối",
                    402: "Tài khoản/provider không đủ credit",
                    403: "API key không có quyền hoặc bị từ chối",
                    404: "Không tìm thấy model hoặc endpoint",
                    429: "Đã chạm giới hạn lượt gọi",
                }
                detail = (" " + provider_message) if provider_message else ""
                raise ModelError(
                    f"{provider_label} lỗi HTTP {exc.code}: {labels.get(exc.code, 'request thất bại')}.{detail}"
                ) from None
            last_error = exc
            delay = 1.5 * (attempt + 1)
            if exc.code == 429:
                retry_match = re.search(r"retry in\s+([0-9]+(?:\.[0-9]+)?)s", provider_message, re.I)
                delay = min(35.0, float(retry_match.group(1)) + 1.0) if retry_match else (10.0 * (attempt + 1))
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
            if attempt == 2:
                raise ModelError(
                    f"Không kết nối hoặc phản hồi {provider_label} không hợp lệ ({type(exc).__name__})."
                ) from None
            last_error = exc
            delay = 1.5 * (attempt + 1)
        if attempt < 2:
            time.sleep(delay)
    raise ModelError(f"{provider_label} tạm thời không khả dụng ({type(last_error).__name__}).")


def _call_openrouter(system: str, user: str, schema=None, temperature=0.1) -> dict:
    if not API_KEY:
        raise ModelError("Thiếu OPENROUTER_API_KEY hoặc API_KEY trong môi trường/.env.")
    if not MODEL_NAME:
        raise ModelError("Thiếu MODEL_NAME trong môi trường/.env.")
    body = {
        "model": MODEL_NAME,
        "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}],
        "temperature": temperature,
        "max_tokens": 2048,
        "reasoning": {"enabled": False},
        "provider": {"require_parameters": True},
    }
    if schema:
        body["response_format"] = {
            "type": "json_schema",
            "json_schema": {"name": schema["name"], "strict": True, "schema": schema["schema"]},
        }
    headers = {
        "Authorization": "Bearer " + API_KEY,
        "Content-Type": "application/json",
        "HTTP-Referer": "http://localhost",
        "X-Title": "Lunchie CP3",
    }
    payload = _post_json_with_retry(OPENROUTER_URL, headers, body, "OpenRouter")
    choice = payload.get("choices", [{}])[0]
    content = choice.get("message", {}).get("content")
    if isinstance(content, list):
        content = "".join(part.get("text", "") for part in content if isinstance(part, dict))
    usage = payload.get("usage") or {}
    if not isinstance(content, str) or not content.strip():
        message = choice.get("message") if isinstance(choice.get("message"), dict) else {}
        raise ModelError(
            "OpenRouter trả về nội dung rỗng (finish_reason=%s, message_fields=%s, usage=%s)."
            % (
                choice.get("finish_reason", "?"),
                ",".join(sorted(message.keys())),
                {key: usage.get(key) for key in ("prompt_tokens", "completion_tokens", "total_tokens")},
            )
        )
    if usage.get("prompt_tokens") is None or usage.get("completion_tokens") is None:
        raise ModelError("OpenRouter không trả usage token; không thể ghi nhận chi phí chính xác.")
    return {
        "text": content,
        "model": payload.get("model") or MODEL_NAME,
        "tokens_in": int(usage["prompt_tokens"]),
        "tokens_out": int(usage["completion_tokens"]),
    }


def _call_gemini(system: str, user: str, schema=None, temperature=0.1) -> dict:
    if not GEMINI_API_KEY:
        raise ModelError("Thiếu GEMINI_API_KEY hoặc API_KEY trong môi trường/.env.")
    if not MODEL_NAME:
        raise ModelError("Thiếu MODEL_NAME trong môi trường/.env (vd: gemini-2.5-flash hoặc gemini-3.1-flash-lite).")
    model_id = MODEL_NAME[7:] if MODEL_NAME.startswith("models/") else MODEL_NAME
    url = GEMINI_URL_TEMPLATE.format(model=urllib.parse.quote(model_id, safe=".-_"))
    generation_config = {"temperature": temperature, "maxOutputTokens": 4096}
    if "2.5" in model_id:
        generation_config["thinkingConfig"] = {"thinkingBudget": 0}
    elif "3." in model_id:
        generation_config["thinkingConfig"] = {"thinkingLevel": "minimal"}
    if schema:
        generation_config["responseMimeType"] = "application/json"
        generation_config["responseJsonSchema"] = schema["schema"]
    body = {
        "contents": [{"role": "user", "parts": [{"text": user}]}],
        "generationConfig": generation_config,
    }
    if system:
        body["systemInstruction"] = {"parts": [{"text": system}]}
    headers = {
        "x-goog-api-key": GEMINI_API_KEY,
        "Content-Type": "application/json",
    }
    payload = _post_json_with_retry(url, headers, body, "Gemini")
    candidates = payload.get("candidates") or []
    parts = ((candidates[0].get("content") or {}).get("parts") or []) if candidates else []
    content = "".join(
        part.get("text", "")
        for part in parts
        if isinstance(part, dict) and not part.get("thought")
    )
    usage = payload.get("usageMetadata") or {}
    if not content.strip():
        finish = candidates[0].get("finishReason", "?") if candidates else "NO_CANDIDATES"
        raise ModelError(f"Gemini trả về nội dung rỗng (finishReason={finish}).")
    if usage.get("promptTokenCount") is None:
        raise ModelError("Gemini không trả usageMetadata.promptTokenCount; không thể ghi nhận chi phí chính xác.")
    candidates_tokens = usage.get("candidatesTokenCount") or 0
    thoughts_tokens = usage.get("thoughtsTokenCount") or 0
    return {
        "text": content,
        "model": model_id,
        "tokens_in": int(usage["promptTokenCount"]),
        "tokens_out": int(candidates_tokens) + int(thoughts_tokens),
    }


@model_call
def call_model(system: str, user: str, schema=None, temperature=0.1) -> dict:
    if MODEL_PROVIDER == "fake":
        return {"text": "[câu trả lời giả — chưa nối model]", "model": "fake", "tokens_in": 0, "tokens_out": 0}
    if MODEL_PROVIDER == "openrouter":
        return _call_openrouter(system, user, schema=schema, temperature=temperature)
    if MODEL_PROVIDER == "gemini":
        return _call_gemini(system, user, schema=schema, temperature=temperature)
    raise ModelError("MODEL_PROVIDER chỉ hỗ trợ gemini, openrouter hoặc fake.")
