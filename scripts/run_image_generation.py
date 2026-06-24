#!/usr/bin/env python3
"""Run configured real image generation for a qiaomu-ppt project.

This consumes the existing image-generation queue/staging contract:

1. Ensure `assets/images/generation_batch/` exists.
2. Generate files into `generation_batch/generated/`.
3. Optionally import those files through `import_generated_assets.py`.

The script is intentionally explicit: without `--execute` it performs a dry
run and writes the exact planned work. This prevents accidental paid API use
while making final-quality image replacement a first-class, reproducible step.
"""

from __future__ import annotations

import argparse
import base64
import json
import os
import sys
import time
from datetime import datetime, timezone
from io import BytesIO
from pathlib import Path
from typing import Any

import requests
from PIL import Image, ImageFilter

from import_generated_assets import import_assets
from stage_image_generation import stage_batch


SCRIPT_DIR = Path(__file__).resolve().parent
DEFAULT_PROVIDER_CONFIG = SCRIPT_DIR.parent / "data" / "image_generation_providers.json"
SUPPORTED_OPENAI_SIZES = {
    "auto",
    "1024x1024",
    "1536x1024",
    "1024x1536",
    "1792x1024",
    "1024x1792",
    "512x512",
    "256x256",
}
DEFAULT_DONE_STATUSES = {"succeeded", "success", "completed", "complete", "done", "finished"}
DEFAULT_FAILED_STATUSES = {"failed", "failure", "error", "cancelled", "canceled", "timeout"}


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def load_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as fh:
        return json.load(fh)


def load_provider_presets(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {"providers": {}}
    payload = load_json(path)
    if not isinstance(payload, dict):
        raise SystemExit(f"Invalid provider config: {path}")
    providers = payload.get("providers")
    if not isinstance(providers, dict):
        raise SystemExit(f"Provider config missing providers object: {path}")
    return payload


def resolve_provider(
    provider: str,
    *,
    model: str,
    provider_config: Path,
    api_key_env: str,
    base_url: str,
    request_format: str,
    auth_scheme: str,
    endpoint_path: str,
    submit_path: str,
    status_path_template: str,
    poll_interval: float,
    poll_timeout: float,
) -> dict[str, Any]:
    presets = load_provider_presets(provider_config)
    provider_map = presets.get("providers", {})
    config = dict(provider_map.get(provider, {}))
    if not config and provider not in {"openai", "gpt-image-2"}:
        raise SystemExit(f"Unknown image provider preset: {provider}. Add it to {provider_config}.")
    config.setdefault("name", provider)
    config.setdefault("request_format", "openai-sdk" if provider in {"openai", "gpt-image-2"} else "openai-images-http")
    config.setdefault("model", "gpt-image-2")
    config.setdefault("api_key_env", "OPENAI_API_KEY")
    config.setdefault("auth_scheme", "bearer")
    if model:
        config["model"] = model
    if api_key_env:
        config["api_key_env"] = api_key_env
    if base_url:
        config["base_url"] = base_url
    if request_format:
        config["request_format"] = request_format
    if auth_scheme:
        config["auth_scheme"] = auth_scheme
    if endpoint_path:
        config["endpoint_path"] = endpoint_path
    if submit_path:
        config["submit_path"] = submit_path
    if status_path_template:
        config["status_path_template"] = status_path_template
    if poll_interval > 0:
        config["poll_interval_seconds"] = poll_interval
    if poll_timeout > 0:
        config["poll_timeout_seconds"] = poll_timeout
    return config


def redact_url(value: str) -> str:
    raw = str(value or "")
    if not raw:
        return ""
    return raw.split("?", 1)[0]


def join_url(base_url: str, path: str) -> str:
    base = str(base_url or "").rstrip("/")
    suffix = str(path or "").strip()
    if suffix.startswith("http://") or suffix.startswith("https://"):
        return suffix
    if not base:
        raise RuntimeError("provider base_url is not configured")
    if not suffix:
        return base
    return base + "/" + suffix.lstrip("/")


def auth_headers(api_key: str, scheme: str) -> dict[str, str]:
    normalized = str(scheme or "bearer").strip().lower()
    if normalized in {"none", "no-auth"}:
        return {}
    if not api_key:
        return {}
    if normalized in {"x-api-key", "x_api_key", "apikey"}:
        return {"X-API-Key": api_key}
    if normalized in {"authorization", "bearer"}:
        return {"Authorization": f"Bearer {api_key}"}
    return {scheme: api_key}


def recursive_find(payload: Any, keys: set[str]) -> Any:
    if isinstance(payload, dict):
        for key, value in payload.items():
            if key in keys and value not in (None, ""):
                return value
        for value in payload.values():
            found = recursive_find(value, keys)
            if found not in (None, ""):
                return found
    elif isinstance(payload, list):
        for value in payload:
            found = recursive_find(value, keys)
            if found not in (None, ""):
                return found
    return None


def render_template(value: Any, context: dict[str, Any]) -> Any:
    if isinstance(value, str):
        try:
            return value.format(**context)
        except Exception:
            return value
    if isinstance(value, list):
        return [render_template(item, context) for item in value]
    if isinstance(value, dict):
        return {key: render_template(item, context) for key, item in value.items()}
    return value


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8").strip()


def normalize_openai_size(value: str, aspect_ratio: str = "16:9") -> str:
    raw = str(value or "").strip().lower()
    if raw in SUPPORTED_OPENAI_SIZES:
        return raw
    if raw in {"2k", "wide", "landscape", "16:9", ""} or "16:9" in str(aspect_ratio):
        return "1536x1024"
    if raw in {"portrait", "9:16"}:
        return "1024x1536"
    return "auto"


def load_batch_items(batch_manifest: Path, *, only_missing: bool, limit: int) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    manifest = load_json(batch_manifest)
    items = manifest.get("items") if isinstance(manifest, dict) else []
    if not isinstance(items, list):
        raise SystemExit(f"Invalid batch manifest: {batch_manifest}")
    selected: list[dict[str, Any]] = []
    for item in items:
        if not isinstance(item, dict):
            continue
        if is_source_ai_fallback(item):
            skipped = manifest.setdefault("skipped_source_fallbacks", [])
            if isinstance(skipped, list):
                skipped.append(str(item.get("asset_id") or item.get("filename") or "unknown"))
            continue
        expected = Path(str(item.get("expected_output") or ""))
        if only_missing and expected.exists():
            continue
        selected.append(item)
        if limit and len(selected) >= limit:
            break
    return manifest, selected


def is_source_ai_fallback(item: dict[str, Any]) -> bool:
    asset_id = str(item.get("asset_id") or "").strip().lower()
    policy = str(item.get("generation_policy") or item.get("notes") or "").strip().lower()
    return asset_id.endswith("-ai-fallback") or "preview_fallback_only" in policy or "dormant fallback" in policy or (
        "ai fallback for preview/production while the remote source image remains" in policy
    )


def image_from_response_item(item: Any) -> bytes:
    b64_json = getattr(item, "b64_json", None)
    if b64_json:
        return base64.b64decode(b64_json)
    url = getattr(item, "url", None)
    if url:
        response = requests.get(url, timeout=180)
        response.raise_for_status()
        return response.content
    if isinstance(item, dict):
        if item.get("b64_json"):
            return base64.b64decode(str(item["b64_json"]))
        if item.get("base64"):
            return base64.b64decode(str(item["base64"]))
        if item.get("image_base64"):
            return base64.b64decode(str(item["image_base64"]))
        if item.get("url"):
            response = requests.get(str(item["url"]), timeout=180)
            response.raise_for_status()
            return response.content
        if item.get("image_url"):
            response = requests.get(str(item["image_url"]), timeout=180)
            response.raise_for_status()
            return response.content
    raise RuntimeError("image generation response contained neither b64_json nor url")


def image_from_payload(payload: Any) -> bytes:
    if isinstance(payload, dict):
        data = payload.get("data")
        if isinstance(data, list) and data:
            return image_from_response_item(data[0])
        if isinstance(data, dict):
            try:
                return image_from_response_item(data)
            except RuntimeError:
                pass
        for key in ("b64_json", "base64", "image_base64", "url", "image_url"):
            value = recursive_find(payload, {key})
            if value:
                return image_from_response_item({key: value})
    if isinstance(payload, list) and payload:
        return image_from_response_item(payload[0])
    return image_from_response_item(payload)


def save_png_16x9(raw: bytes, output: Path, *, mode: str) -> list[int]:
    image = Image.open(BytesIO(raw)).convert("RGB")
    target = (1600, 900)
    if mode == "none":
        output.parent.mkdir(parents=True, exist_ok=True)
        image.save(output, format="PNG", optimize=True)
        return [int(image.width), int(image.height)]
    if mode == "crop":
        ratio = target[0] / target[1]
        source_ratio = image.width / image.height
        if source_ratio > ratio:
            new_w = int(image.height * ratio)
            left = max(0, (image.width - new_w) // 2)
            image = image.crop((left, 0, left + new_w, image.height))
        else:
            new_h = int(image.width / ratio)
            top = max(0, (image.height - new_h) // 2)
            image = image.crop((0, top, image.width, top + new_h))
        image = image.resize(target, Image.Resampling.LANCZOS)
    else:
        bg = image.copy()
        bg_ratio = target[0] / target[1]
        source_ratio = bg.width / bg.height
        if source_ratio > bg_ratio:
            new_h = int(bg.width / bg_ratio)
            canvas = Image.new("RGB", (bg.width, new_h), tuple(bg.resize((1, 1)).getpixel((0, 0))))
            canvas.paste(bg, (0, (new_h - bg.height) // 2))
            bg = canvas
        else:
            new_w = int(bg.height * bg_ratio)
            canvas = Image.new("RGB", (new_w, bg.height), tuple(bg.resize((1, 1)).getpixel((0, 0))))
            canvas.paste(bg, ((new_w - bg.width) // 2, 0))
            bg = canvas
        bg = bg.resize(target, Image.Resampling.LANCZOS).filter(ImageFilter.GaussianBlur(18))
        bg = Image.blend(bg, Image.new("RGB", target, (245, 240, 232)), 0.18)
        contained = image.copy()
        contained.thumbnail(target, Image.Resampling.LANCZOS)
        x = (target[0] - contained.width) // 2
        y = (target[1] - contained.height) // 2
        bg.paste(contained, (x, y))
        image = bg
    output.parent.mkdir(parents=True, exist_ok=True)
    image.save(output, format="PNG", optimize=True)
    return [target[0], target[1]]


def openai_generate(
    *,
    prompt: str,
    output: Path,
    model: str,
    size: str,
    quality: str,
    output_format: str,
    api_key_env: str,
    base_url: str,
    postprocess: str,
) -> dict[str, Any]:
    try:
        from openai import OpenAI
    except Exception as exc:  # pragma: no cover - environment-specific
        raise RuntimeError("OpenAI Python SDK is not installed; run `python3 -m pip install openai`.") from exc

    api_key = os.environ.get(api_key_env)
    if not api_key:
        raise RuntimeError(f"{api_key_env} is not set; refusing to call OpenAI image generation.")
    client_kwargs: dict[str, Any] = {"api_key": api_key}
    if base_url:
        client_kwargs["base_url"] = base_url
    client = OpenAI(**client_kwargs)
    request: dict[str, Any] = {
        "model": model,
        "prompt": prompt,
        "size": size,
        "quality": quality,
        "n": 1,
        "response_format": "b64_json",
    }
    if output_format:
        request["output_format"] = output_format
    attempts: list[dict[str, Any]] = [request]
    if "output_format" in request:
        simpler = dict(request)
        simpler.pop("output_format", None)
        attempts.append(simpler)
    simplest = dict(request)
    simplest.pop("output_format", None)
    simplest.pop("response_format", None)
    attempts.append(simplest)
    last_error: Exception | None = None
    response = None
    seen: set[str] = set()
    for attempt in attempts:
        key = json.dumps(sorted(attempt.keys()))
        if key in seen:
            continue
        seen.add(key)
        try:
            response = client.images.generate(**attempt)
            break
        except Exception as exc:
            last_error = exc
    if response is None:
        raise RuntimeError(f"OpenAI image generation failed: {last_error}")
    data = getattr(response, "data", None)
    if not data:
        raise RuntimeError("OpenAI image generation returned no images.")
    raw = image_from_response_item(data[0])
    dimensions = save_png_16x9(raw, output, mode=postprocess)
    revised_prompt = getattr(data[0], "revised_prompt", None)
    return {
        "output": str(output),
        "dimensions": dimensions,
        "model": model,
        "size": size,
        "quality": quality,
        "revised_prompt": revised_prompt or "",
    }


def http_images_generate(
    *,
    prompt: str,
    output: Path,
    provider_config: dict[str, Any],
    model: str,
    size: str,
    quality: str,
    output_format: str,
    postprocess: str,
) -> dict[str, Any]:
    api_key_env = str(provider_config.get("api_key_env") or "OPENAI_API_KEY")
    api_key = os.environ.get(api_key_env, "")
    auth_scheme = str(provider_config.get("auth_scheme") or "bearer")
    if auth_scheme.lower() not in {"none", "no-auth"} and not api_key:
        raise RuntimeError(f"{api_key_env} is not set; refusing to call configured image provider.")
    endpoint = join_url(
        str(provider_config.get("base_url") or ""),
        str(provider_config.get("endpoint_path") or provider_config.get("path") or "images/generations"),
    )
    payload = {
        "model": model,
        "prompt": prompt,
        "n": 1,
        "size": size,
        "quality": quality,
        "response_format": "b64_json",
    }
    if output_format:
        payload["output_format"] = output_format
    if isinstance(provider_config.get("extra_payload"), dict):
        payload.update(provider_config["extra_payload"])
    response = requests.post(
        endpoint,
        headers={"Content-Type": "application/json", **auth_headers(api_key, auth_scheme)},
        json=payload,
        timeout=float(provider_config.get("request_timeout_seconds") or 300),
    )
    try:
        response.raise_for_status()
    except requests.HTTPError as exc:
        raise RuntimeError(f"HTTP image provider failed {response.status_code}: {response.text[:500]}") from exc
    raw = image_from_payload(response.json())
    dimensions = save_png_16x9(raw, output, mode=postprocess)
    return {
        "output": str(output),
        "dimensions": dimensions,
        "model": model,
        "size": size,
        "quality": quality,
        "endpoint": redact_url(endpoint),
    }


def async_task_generate(
    *,
    prompt: str,
    output: Path,
    provider_config: dict[str, Any],
    model: str,
    size: str,
    quality: str,
    output_format: str,
    postprocess: str,
) -> dict[str, Any]:
    api_key_env = str(provider_config.get("api_key_env") or "IMAGE_API_KEY")
    api_key = os.environ.get(api_key_env, "")
    auth_scheme = str(provider_config.get("auth_scheme") or "bearer")
    if auth_scheme.lower() not in {"none", "no-auth"} and not api_key:
        raise RuntimeError(f"{api_key_env} is not set; refusing to call configured async image provider.")

    context = {
        "model": model,
        "prompt": prompt,
        "size": size,
        "quality": quality,
        "output_format": output_format,
    }
    template = provider_config.get("payload_template")
    if isinstance(template, dict):
        payload = render_template(template, context)
    else:
        payload = {
            "model": model,
            "prompt": prompt,
            "n": 1,
            "size": size,
            "quality": quality,
            "response_format": "b64_json",
        }
        if output_format:
            payload["output_format"] = output_format
    submit_url = join_url(str(provider_config.get("base_url") or ""), str(provider_config.get("submit_path") or "/v1/tasks"))
    headers = {"Content-Type": "application/json", **auth_headers(api_key, auth_scheme)}
    submit_response = requests.post(
        submit_url,
        headers=headers,
        json=payload,
        timeout=float(provider_config.get("request_timeout_seconds") or 300),
    )
    try:
        submit_response.raise_for_status()
    except requests.HTTPError as exc:
        raise RuntimeError(f"async image task submit failed {submit_response.status_code}: {submit_response.text[:500]}") from exc
    submit_payload = submit_response.json()
    try:
        raw = image_from_payload(submit_payload)
        dimensions = save_png_16x9(raw, output, mode=postprocess)
        return {
            "output": str(output),
            "dimensions": dimensions,
            "model": model,
            "size": size,
            "quality": quality,
            "submit_endpoint": redact_url(submit_url),
            "task_status": "inline_result",
        }
    except RuntimeError:
        pass

    task_id = recursive_find(submit_payload, {"task_id", "id", "request_id"})
    if not task_id:
        raise RuntimeError("async image provider returned no task id and no inline image")
    status_template = str(provider_config.get("status_path_template") or "/v1/tasks/{task_id}")
    status_url = join_url(str(provider_config.get("base_url") or ""), status_template.format(task_id=task_id))
    done_statuses = {str(item).lower() for item in provider_config.get("done_statuses", list(DEFAULT_DONE_STATUSES))}
    failed_statuses = {str(item).lower() for item in provider_config.get("failed_statuses", list(DEFAULT_FAILED_STATUSES))}
    interval = float(provider_config.get("poll_interval_seconds") or 3)
    deadline = time.time() + float(provider_config.get("poll_timeout_seconds") or 600)
    last_payload: Any = None
    while time.time() < deadline:
        status_response = requests.get(
            status_url,
            headers=auth_headers(api_key, auth_scheme),
            timeout=float(provider_config.get("request_timeout_seconds") or 120),
        )
        try:
            status_response.raise_for_status()
        except requests.HTTPError as exc:
            raise RuntimeError(f"async image task poll failed {status_response.status_code}: {status_response.text[:500]}") from exc
        last_payload = status_response.json()
        status = str(recursive_find(last_payload, {"status", "state", "task_status"}) or "").lower()
        if status in failed_statuses:
            raise RuntimeError(f"async image task failed with status {status}: {json.dumps(last_payload, ensure_ascii=False)[:500]}")
        try:
            raw = image_from_payload(last_payload)
            dimensions = save_png_16x9(raw, output, mode=postprocess)
            return {
                "output": str(output),
                "dimensions": dimensions,
                "model": model,
                "size": size,
                "quality": quality,
                "submit_endpoint": redact_url(submit_url),
                "status_endpoint": redact_url(status_url),
                "task_id": str(task_id),
                "task_status": status or "image_found",
            }
        except RuntimeError:
            if status and status not in done_statuses:
                time.sleep(interval)
                continue
            if status in done_statuses:
                raise RuntimeError(f"async image task completed without an image payload: {json.dumps(last_payload, ensure_ascii=False)[:500]}")
        time.sleep(interval)
    raise RuntimeError(f"async image task timed out after polling {redact_url(status_url)}")


def build_prompt(item: dict[str, Any], *, include_negative: bool) -> str:
    prompt_path = Path(str(item.get("prompt_file") or ""))
    negative_path = Path(str(item.get("negative_prompt_file") or ""))
    prompt = read_text(prompt_path) if prompt_path.exists() else ""
    negative = read_text(negative_path) if negative_path.exists() else ""
    if include_negative and negative:
        prompt = prompt.rstrip() + "\n\nNegative constraints:\n" + negative
    return prompt.strip()


def preflight_provider(
    *,
    provider: str,
    provider_config: Path,
    resolved_provider: dict[str, Any],
    effective_format: str,
    effective_api_key_env: str,
    effective_base_url: str,
    items: list[dict[str, Any]],
    require_auth: bool,
    include_negative: bool,
) -> dict[str, Any]:
    failures: list[str] = []
    warnings: list[str] = []
    auth_scheme = str(resolved_provider.get("auth_scheme") or "bearer").lower()
    if not provider_config.exists():
        failures.append(f"provider config not found: {provider_config}")
    if effective_format == "openai-sdk":
        try:
            from openai import OpenAI as _OpenAI  # noqa: F401
        except Exception:
            failures.append("OpenAI Python SDK is not installed; run `python3 -m pip install openai`.")
    elif effective_format in {"openai-images-http", "async-task"}:
        if not effective_base_url:
            failures.append(f"{provider} provider requires base_url for {effective_format}.")
        if effective_format == "openai-images-http" and not (
            resolved_provider.get("endpoint_path") or resolved_provider.get("path")
        ):
            warnings.append("HTTP provider has no endpoint_path; defaulting to images/generations.")
        if effective_format == "async-task" and not resolved_provider.get("submit_path"):
            warnings.append("Async provider has no submit_path; defaulting to /v1/tasks.")
    else:
        failures.append(f"unsupported request format: {effective_format}")

    if require_auth and auth_scheme not in {"none", "no-auth"} and not os.environ.get(effective_api_key_env, ""):
        failures.append(f"{effective_api_key_env} is not set; refusing to call real image generation.")

    empty_prompt_assets: list[str] = []
    for item in items:
        prompt = build_prompt(item, include_negative=include_negative)
        if not prompt:
            empty_prompt_assets.append(str(item.get("asset_id") or item.get("filename") or "unknown"))
    if empty_prompt_assets:
        failures.append("empty prompt for asset(s): " + ", ".join(empty_prompt_assets[:8]))
    if not items:
        warnings.append("No queued image assets selected; nothing to generate.")

    return {
        "ok": not failures,
        "provider": provider,
        "request_format": effective_format,
        "provider_config": str(provider_config),
        "api_key_env": effective_api_key_env,
        "api_key_present": bool(os.environ.get(effective_api_key_env, "")),
        "auth_scheme": auth_scheme,
        "base_url": redact_url(effective_base_url),
        "selected_count": len(items),
        "failures": failures,
        "warnings": warnings,
    }


def run_generation(
    project: Path,
    *,
    provider: str,
    model: str,
    provider_config: Path,
    queue: Path,
    batch_dir: Path,
    force_stage: bool,
    only_missing: bool,
    limit: int,
    execute: bool,
    import_results: bool,
    api_key_env: str,
    base_url: str,
    size: str,
    quality: str,
    output_format: str,
    postprocess: str,
    include_negative: bool,
    sleep_seconds: float,
    preflight_only: bool,
    request_format: str,
    auth_scheme: str,
    endpoint_path: str,
    submit_path: str,
    status_path_template: str,
    poll_interval: float,
    poll_timeout: float,
) -> dict[str, Any]:
    resolved_provider = resolve_provider(
        provider,
        model=model,
        provider_config=provider_config,
        api_key_env=api_key_env,
        base_url=base_url,
        request_format=request_format,
        auth_scheme=auth_scheme,
        endpoint_path=endpoint_path,
        submit_path=submit_path,
        status_path_template=status_path_template,
        poll_interval=poll_interval,
        poll_timeout=poll_timeout,
    )
    effective_model = str(resolved_provider.get("model") or model or "gpt-image-2")
    effective_format = str(resolved_provider.get("request_format") or "openai-sdk")
    effective_api_key_env = str(resolved_provider.get("api_key_env") or api_key_env or "OPENAI_API_KEY")
    effective_base_url = str(resolved_provider.get("base_url") or base_url or "")
    if force_stage or not (batch_dir / "manifest.json").exists():
        stage_batch(
            project,
            queue,
            batch_dir,
            provider=provider,
            model=effective_model,
            force=force_stage,
            only_missing=False,
            limit=0,
        )
    batch_manifest_path = batch_dir / "manifest.json"
    batch_manifest, items = load_batch_items(batch_manifest_path, only_missing=only_missing, limit=limit)
    generated_dir = Path(str(batch_manifest.get("generated_dir") or batch_dir / "generated"))
    generated_dir.mkdir(parents=True, exist_ok=True)
    preflight = preflight_provider(
        provider=provider,
        provider_config=provider_config,
        resolved_provider=resolved_provider,
        effective_format=effective_format,
        effective_api_key_env=effective_api_key_env,
        effective_base_url=effective_base_url,
        items=items,
        require_auth=execute or preflight_only,
        include_negative=include_negative,
    )

    if preflight_only or (execute and not preflight["ok"]):
        failures = [{"asset_id": "preflight", "error": item} for item in preflight.get("failures", [])]
        report = {
            "schema_version": "1.0.0",
            "generated_at": utc_now(),
            "project": str(project),
            "provider": provider,
            "provider_config": str(provider_config),
            "request_format": effective_format,
            "model": effective_model,
            "api_key_env": effective_api_key_env,
            "base_url": redact_url(effective_base_url),
            "auth_scheme": str(resolved_provider.get("auth_scheme") or ""),
            "execute": False,
            "dry_run": True,
            "preflight_only": preflight_only,
            "preflight": preflight,
            "batch_manifest": str(batch_manifest_path),
            "generated_dir": str(generated_dir),
            "selected_count": len(items),
            "generated_count": 0,
            "failed_count": len(failures),
            "records": [],
            "failures": failures,
            "import_results": False,
            "import": None,
            "next_steps": (
                "Fix preflight failures, then rerun with --execute --import-results."
                if failures
                else "Preflight passed. Rerun with --execute --import-results to create real images."
            ),
        }
        write_json(project / "assets" / "images" / "image_generation_run.json", report)
        return report

    records: list[dict[str, Any]] = []
    failures: list[dict[str, str]] = []
    for idx, item in enumerate(items, start=1):
        expected_output = Path(str(item.get("expected_output") or generated_dir / str(item.get("filename") or f"asset-{idx}.png")))
        prompt = build_prompt(item, include_negative=include_negative)
        metadata_path = Path(str(item.get("metadata_file") or ""))
        metadata = load_json(metadata_path) if metadata_path.exists() else {}
        item_size = normalize_openai_size(size or str(metadata.get("size") or ""), str(metadata.get("aspect_ratio") or "16:9"))
        record: dict[str, Any] = {
            "asset_id": item.get("asset_id"),
            "slide_no": item.get("slide_no"),
            "expected_output": str(expected_output),
            "provider": provider,
            "request_format": effective_format,
            "model": effective_model,
            "size": item_size,
            "status": "planned",
            "prompt_chars": len(prompt),
        }
        if not prompt:
            record["status"] = "failed"
            record["error"] = "empty prompt"
            failures.append({"asset_id": str(item.get("asset_id") or ""), "error": "empty prompt"})
            records.append(record)
            continue
        if not execute:
            record["status"] = "dry_run"
            records.append(record)
            continue
        try:
            started = time.time()
            if effective_format == "openai-sdk":
                result = openai_generate(
                    prompt=prompt,
                    output=expected_output,
                    model=effective_model,
                    size=item_size,
                    quality=quality,
                    output_format=output_format,
                    api_key_env=effective_api_key_env,
                    base_url=effective_base_url,
                    postprocess=postprocess,
                )
            elif effective_format == "openai-images-http":
                result = http_images_generate(
                    prompt=prompt,
                    output=expected_output,
                    provider_config=resolved_provider,
                    model=effective_model,
                    size=item_size,
                    quality=quality,
                    output_format=output_format,
                    postprocess=postprocess,
                )
            elif effective_format == "async-task":
                result = async_task_generate(
                    prompt=prompt,
                    output=expected_output,
                    provider_config=resolved_provider,
                    model=effective_model,
                    size=item_size,
                    quality=quality,
                    output_format=output_format,
                    postprocess=postprocess,
                )
            else:
                raise RuntimeError(f"unsupported request format: {effective_format}")
            record.update(result)
            record["status"] = "generated"
            record["duration_seconds"] = round(time.time() - started, 2)
        except Exception as exc:
            record["status"] = "failed"
            record["error"] = str(exc)
            failures.append({"asset_id": str(item.get("asset_id") or ""), "error": str(exc)})
        records.append(record)
        if sleep_seconds > 0 and idx < len(items):
            time.sleep(sleep_seconds)

    imported: dict[str, Any] | None = None
    if execute and import_results and any(record.get("status") == "generated" for record in records):
        imported = import_assets(
            project,
            project / "visual_asset_manifest.json",
            generated_dir,
            batch_dir / "import_mapping.template.json",
            generator=f"{provider}:{effective_model}",
            force=True,
            only_pending=False,
        )

    report = {
        "schema_version": "1.0.0",
        "generated_at": utc_now(),
        "project": str(project),
        "provider": provider,
        "provider_config": str(provider_config),
        "request_format": effective_format,
        "model": effective_model,
        "api_key_env": effective_api_key_env,
        "base_url": redact_url(effective_base_url),
        "auth_scheme": str(resolved_provider.get("auth_scheme") or ""),
        "execute": execute,
        "dry_run": not execute,
        "preflight_only": False,
        "preflight": preflight,
        "batch_manifest": str(batch_manifest_path),
        "generated_dir": str(generated_dir),
        "selected_count": len(items),
        "generated_count": sum(1 for record in records if record.get("status") == "generated"),
        "failed_count": len(failures),
        "records": records,
        "failures": failures,
        "import_results": import_results,
        "import": imported,
        "next_steps": (
            "Run with --execute to create real images."
            if not execute
            else "Run produce_deck.py without --materialize-assets, or with --require-real-imagegen to enforce real-image evidence."
        ),
    }
    write_json(project / "assets" / "images" / "image_generation_run.json", report)
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("project", type=Path, help="qiaomu-ppt project directory.")
    parser.add_argument("--provider", default="openai", help="Image provider preset name from data/image_generation_providers.json.")
    parser.add_argument("--model", default="", help="Image model name to pass to the provider. Defaults to the provider preset.")
    parser.add_argument("--provider-config", type=Path, default=DEFAULT_PROVIDER_CONFIG, help="Provider preset JSON.")
    parser.add_argument("--queue", type=Path, help="image_generation_queue.json path.")
    parser.add_argument("--batch-dir", type=Path, help="Existing or new staging batch directory.")
    parser.add_argument("--stage", action="store_true", help="Create/refresh generation_batch before running.")
    parser.add_argument("--only-missing", action="store_true", help="Skip expected output files that already exist.")
    parser.add_argument("--limit", type=int, default=0, help="Maximum images to generate or plan. 0 means all.")
    parser.add_argument("--execute", action="store_true", help="Actually call the provider. Without this, writes a dry-run report only.")
    parser.add_argument("--preflight", action="store_true", help="Validate provider config, SDK/key presence, and prompts without generating images.")
    parser.add_argument("--import-results", action="store_true", help="Import generated files into visual_asset_manifest.json after generation.")
    parser.add_argument("--api-key-env", default="", help="Environment variable containing the provider API key. Defaults to provider preset.")
    parser.add_argument("--base-url", default="", help="Provider base URL override.")
    parser.add_argument("--request-format", default="", choices=["", "openai-sdk", "openai-images-http", "async-task"], help="Provider request format override.")
    parser.add_argument("--auth-scheme", default="", help="Auth scheme override: bearer, x-api-key, none, or a custom header name.")
    parser.add_argument("--endpoint-path", default="", help="HTTP image generation endpoint path override.")
    parser.add_argument("--submit-path", default="", help="Async task submit endpoint path override.")
    parser.add_argument("--status-path-template", default="", help="Async task status path template, e.g. /v1/tasks/{task_id}.")
    parser.add_argument("--poll-interval", type=float, default=0.0, help="Async task poll interval seconds. Defaults to provider preset.")
    parser.add_argument("--poll-timeout", type=float, default=0.0, help="Async task timeout seconds. Defaults to provider preset.")
    parser.add_argument("--size", default="", help="Provider image size. Default derives from queue metadata; OpenAI wide fallback is 1536x1024.")
    parser.add_argument("--quality", default="auto", help="Provider quality, e.g. auto/high/medium/low.")
    parser.add_argument("--output-format", default="png", choices=["png", "jpeg", "webp"], help="Provider output format request.")
    parser.add_argument("--postprocess", default="pad", choices=["pad", "crop", "none"], help="Normalize generated images to 1600x900.")
    parser.add_argument("--no-negative", action="store_true", help="Do not append negative constraints to the prompt.")
    parser.add_argument("--sleep", type=float, default=0.0, help="Seconds to wait between provider requests.")
    args = parser.parse_args()

    project = args.project.expanduser().resolve()
    queue = args.queue or project / "assets" / "images" / "image_generation_queue.json"
    batch_dir = args.batch_dir or project / "assets" / "images" / "generation_batch"
    report = run_generation(
        project,
        provider=args.provider,
        model=args.model,
        provider_config=args.provider_config.expanduser().resolve(),
        queue=queue,
        batch_dir=batch_dir,
        force_stage=args.stage,
        only_missing=args.only_missing,
        limit=max(0, args.limit),
        execute=args.execute,
        import_results=args.import_results,
        api_key_env=args.api_key_env,
        base_url=args.base_url,
        size=args.size,
        quality=args.quality,
        output_format=args.output_format,
        postprocess=args.postprocess,
        include_negative=not args.no_negative,
        sleep_seconds=max(0.0, args.sleep),
        preflight_only=args.preflight,
        request_format=args.request_format,
        auth_scheme=args.auth_scheme,
        endpoint_path=args.endpoint_path,
        submit_path=args.submit_path,
        status_path_template=args.status_path_template,
        poll_interval=max(0.0, args.poll_interval),
        poll_timeout=max(0.0, args.poll_timeout),
    )
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 2 if report["failed_count"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
