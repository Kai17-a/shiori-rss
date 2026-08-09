import json
import os
import subprocess
import threading

from fastapi import HTTPException
from pydantic import ValidationError

from api.model.models import SettingsAIArticleAnalysisRunResponse

_manual_run_lock = threading.Lock()


class ArticleAnalysisService:
    def run_manual(self) -> SettingsAIArticleAnalysisRunResponse:
        if not _manual_run_lock.acquire(blocking=False):
            raise HTTPException(
                status_code=409, detail="Article analysis is already running"
            )
        try:
            binary = os.environ.get("SHIORI_FEED_BATCH_BIN", "shiori-feed-batch")
            try:
                result = subprocess.run(
                    [binary, "--article-analysis-only"],
                    capture_output=True,
                    check=False,
                    text=True,
                    timeout=7200,
                )
            except FileNotFoundError as exc:
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
