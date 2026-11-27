"""Model adapter. All provider calls go through this module and are traced."""
import json
import os
import time
import urllib.error
import urllib.request

from tracing import model_call

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
API_URL = "https://openrouter.ai/api/v1/chat/completions"


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


class ModelError(RuntimeError):
    """Safe, user-displayable model configuration or transport error."""


@model_call
def call_model(system: str, user: str, schema=None, temperature=0.1) -> dict:
    if MODEL_PROVIDER == "fake":
        return {"text": "[câu trả lời giả — chưa nối model]", "model": "fake", "tokens_in": 0, "tokens_out": 0}
    if MODEL_PROVIDER != "openrouter":
        raise ModelError("MODEL_PROVIDER chỉ hỗ trợ openrouter hoặc fake.")
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
    request = urllib.request.Request(
        API_URL,
        data=json.dumps(body, ensure_ascii=False).encode("utf-8"),
        headers={"Authorization": "Bearer " + API_KEY, "Content-Type": "application/json", "HTTP-Referer": "http://localhost", "X-Title": "Lunchie CP3"},
        method="POST",
    )
    last_error = None
    for attempt in range(3):
        try:
            with urllib.request.urlopen(request, timeout=40) as response:
                payload = json.loads(response.read().decode("utf-8"))
            choice = payload.get("choices", [{}])[0]
            content = choice.get("message", {}).get("content")
            if isinstance(content, list):
                content = "".join(part.get("text", "") for part in content if isinstance(part, dict))
            usage = payload.get("usage") or {}
            if not isinstance(content, str) or not content.strip():
                message = choice.get("message") if isinstance(choice.get("message"), dict) else {}
                raise ModelError("OpenRouter trả về nội dung rỗng (finish_reason=%s, message_fields=%s, usage=%s)." % (
                    choice.get("finish_reason", "?"), ",".join(sorted(message.keys())),
                    {key: usage.get(key) for key in ("prompt_tokens", "completion_tokens", "total_tokens")}))
            if usage.get("prompt_tokens") is None or usage.get("completion_tokens") is None:
                raise ModelError("OpenRouter không trả usage token; không thể ghi nhận chi phí chính xác.")
            return {
                "text": content,
                "model": payload.get("model") or MODEL_NAME,
                "tokens_in": int(usage["prompt_tokens"]),
                "tokens_out": int(usage["completion_tokens"]),
            }
        except urllib.error.HTTPError as exc:
            # Only surface the provider's short error message, never the body or request headers.
            provider_message = ""
            try:
                error_payload = json.loads(exc.read(16384).decode("utf-8", "replace"))
                provider_message = str((error_payload.get("error") or {}).get("message") or "")[:240]
            except (ValueError, AttributeError):
                pass
            if exc.code not in (408, 429, 500, 502, 503, 504) or attempt == 2:
                labels = {401: "API key bị từ chối", 402: "Tài khoản/provider không đủ credit", 403: "Provider từ chối request", 404: "Không tìm thấy model hoặc endpoint", 429: "Đã chạm giới hạn lượt gọi"}
                detail = (" " + provider_message) if provider_message else ""
                raise ModelError(f"OpenRouter lỗi HTTP {exc.code}: {labels.get(exc.code, 'request thất bại')}.{detail}") from None
            last_error = exc
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
            if attempt == 2:
                raise ModelError(f"Không kết nối hoặc phản hồi OpenRouter không hợp lệ ({type(exc).__name__}).") from None
            last_error = exc
        if attempt < 2:
            time.sleep(1.5 * (attempt + 1))
    raise ModelError(f"OpenRouter tạm thời không khả dụng ({type(last_error).__name__}).")
