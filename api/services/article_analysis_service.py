import json
import os
import shutil
import subprocess
import threading
from pathlib import Path

from fastapi import HTTPException
from pydantic import ValidationError

from api.model.models import SettingsAIArticleAnalysisRunResponse

_manual_run_lock = threading.Lock()
_REPOSITORY_ROOT = Path(__file__).resolve().parents[2]


def _batch_command() -> list[str]:
    configured = os.environ.get("SHIORI_FEED_BATCH_BIN")
    if configured:
        return [configured, "--article-analysis-only"]

    development_binary = (
        _REPOSITORY_ROOT / "batch" / "target" / "debug" / "shiori-feed-batch"
    )
    if development_binary.is_file() and os.access(development_binary, os.X_OK):
        return [str(development_binary), "--article-analysis-only"]

    installed = shutil.which("shiori-feed-batch")
    if installed:
        return [installed, "--article-analysis-only"]

    raise HTTPException(
        status_code=503,
        detail=(
            "Article analysis runner is not available. "
            "Run `cargo build --manifest-path batch/Cargo.toml` first."
        ),
    )


class ArticleAnalysisService:
    def run_manual(self) -> SettingsAIArticleAnalysisRunResponse:
        if not _manual_run_lock.acquire(blocking=False):
            raise HTTPException(
                status_code=409, detail="Article analysis is already running"
            )
        try:
            try:
                result = subprocess.run(
                    _batch_command(),
                    capture_output=True,
                    check=False,
                    text=True,
                    timeout=7200,
                )
            except (FileNotFoundError, PermissionError) as exc:
                raise HTTPException(
                    status_code=503, detail="Article analysis runner is not available"
                ) from exc
            except subprocess.TimeoutExpired as exc:
                raise HTTPException(
                    status_code=504, detail="Article analysis timed out"
                ) from exc

            if result.returncode != 0:
                detail = (
                    result.stderr.strip().splitlines()[-1]
                    if result.stderr.strip()
                    else ""
                )
                if "already running" in detail.lower():
                    raise HTTPException(status_code=409, detail=detail[:500])
                raise HTTPException(
                    status_code=502,
                    detail=detail[:500] or "Article analysis failed",
                )
            try:
                payload = json.loads(result.stdout.strip().splitlines()[-1])
                return SettingsAIArticleAnalysisRunResponse.model_validate(payload)
            except (IndexError, ValueError, ValidationError) as exc:
                raise HTTPException(
                    status_code=502,
                    detail="Article analysis returned an invalid result",
                ) from exc
        finally:
            _manual_run_lock.release()
