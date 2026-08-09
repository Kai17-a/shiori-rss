import json
import logging
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
_logger = logging.getLogger("uvicorn.error")
_RUN_TIMEOUT_SECONDS = 7200


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
                process = subprocess.Popen(
                    _batch_command(),
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                    bufsize=1,
                )
            except (FileNotFoundError, PermissionError) as exc:
                raise HTTPException(
                    status_code=503, detail="Article analysis runner is not available"
                ) from exc
            timed_out = threading.Event()

            def terminate_on_timeout() -> None:
                timed_out.set()
                process.kill()

            timeout = threading.Timer(_RUN_TIMEOUT_SECONDS, terminate_on_timeout)
            timeout.start()
            output_lines: list[str] = []
            report: SettingsAIArticleAnalysisRunResponse | None = None
            _logger.info("Starting manual AI article analysis")
            try:
                if process.stdout is None:
                    raise HTTPException(
                        status_code=502, detail="Article analysis produced no output"
                    )
                for raw_line in process.stdout:
                    line = raw_line.strip()
                    if not line:
                        continue
                    try:
                        report = SettingsAIArticleAnalysisRunResponse.model_validate(
                            json.loads(line)
                        )
                        continue
                    except (ValueError, ValidationError):
                        output_lines.append(line)
                        output_lines = output_lines[-20:]
                        _logger.info("AI article analysis: %s", line)
                returncode = process.wait()
            finally:
                timeout.cancel()

            if timed_out.is_set():
                raise HTTPException(
                    status_code=504, detail="Article analysis timed out"
                )
            if returncode != 0:
                detail = output_lines[-1] if output_lines else ""
                if "already running" in detail.lower():
                    raise HTTPException(status_code=409, detail=detail[:500])
                raise HTTPException(
                    status_code=502,
                    detail=detail[:500] or "Article analysis failed",
                )
            if report is None:
                raise HTTPException(
                    status_code=502,
                    detail="Article analysis returned an invalid result",
                )
            _logger.info(
                "Manual AI article analysis completed: processed=%d succeeded=%d failed=%d skipped=%d",
                report.processed,
                report.succeeded,
                report.failed,
                report.skipped_current,
            )
            return report
        finally:
            _manual_run_lock.release()
