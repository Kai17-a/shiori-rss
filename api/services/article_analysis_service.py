import json
import logging
import os
import shutil
import subprocess
import threading
import time
from pathlib import Path

from fastapi import HTTPException
from pydantic import ValidationError

from api.database import get_db
from api.model.models import (
    SettingsAIArticleAnalysisRunResponse,
    SettingsAIArticleAnalysisStatusResponse,
)

_manual_run_lock = threading.Lock()
_REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
_logger = logging.getLogger("uvicorn.error")
_RUN_TIMEOUT_SECONDS = 7200
_RUN_LOCK_KEY = "ai_article_analysis_running"
_PROGRESS_KEY = "ai_article_analysis_progress"


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


def _parse_run_lock(value: str) -> tuple[int, int | None] | None:
    parts = value.split(":", 1)
    try:
        started_at = int(parts[0])
        process_id = int(parts[1]) if len(parts) == 2 else None
    except ValueError:
        return None
    return started_at, process_id


def _process_is_alive(process_id: int) -> bool:
    try:
        os.kill(process_id, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True


def _legacy_batch_is_alive() -> bool:
    proc = Path("/proc")
    if not proc.is_dir():
        return True
    for entry in proc.iterdir():
        if not entry.name.isdigit() or int(entry.name) == os.getpid():
            continue
        try:
            command = (entry / "cmdline").read_bytes().replace(b"\0", b" ")
        except (FileNotFoundError, PermissionError, ProcessLookupError):
            continue
        if b"shiori-feed-batch" in command:
            return True
    return False


def _delete_run_lock(value: str) -> None:
    with get_db() as conn:
        conn.execute(
            "DELETE FROM app_settings WHERE key = ? AND value = ?",
            (_RUN_LOCK_KEY, value),
        )
        conn.execute("DELETE FROM app_settings WHERE key = ?", (_PROGRESS_KEY,))


def _clear_process_run_lock(process_id: int) -> None:
    with get_db() as conn:
        row = conn.execute(
            "SELECT value FROM app_settings WHERE key = ?", (_RUN_LOCK_KEY,)
        ).fetchone()
        if row is None:
            return
        value = str(row["value"])
        parsed = _parse_run_lock(value)
        if parsed is not None and parsed[1] == process_id:
            conn.execute(
                "DELETE FROM app_settings WHERE key = ? AND value = ?",
                (_RUN_LOCK_KEY, value),
            )
            conn.execute("DELETE FROM app_settings WHERE key = ?", (_PROGRESS_KEY,))


class ArticleAnalysisService:
    def _status_response(self, running: bool) -> SettingsAIArticleAnalysisStatusResponse:
        if not running:
            return SettingsAIArticleAnalysisStatusResponse(running=False)
        with get_db() as conn:
            row = conn.execute(
                "SELECT value FROM app_settings WHERE key = ?", (_PROGRESS_KEY,)
            ).fetchone()
        if row is None:
            return SettingsAIArticleAnalysisStatusResponse(running=True)
        try:
            progress = json.loads(str(row["value"]))
            return SettingsAIArticleAnalysisStatusResponse(
                running=True,
                **progress,
            )
        except (TypeError, ValueError, ValidationError):
            return SettingsAIArticleAnalysisStatusResponse(running=True)

    def status(self) -> SettingsAIArticleAnalysisStatusResponse:
        if _manual_run_lock.locked():
            return self._status_response(True)
        with get_db() as conn:
            row = conn.execute(
                "SELECT value FROM app_settings WHERE key = ?", (_RUN_LOCK_KEY,)
            ).fetchone()
        if row is None:
            return self._status_response(False)
        value = str(row["value"])
        parsed = _parse_run_lock(value)
        if parsed is None:
            return self._status_response(False)
        started_at, process_id = parsed
        running = 0 <= int(time.time()) - started_at < _RUN_TIMEOUT_SECONDS
        if running and process_id is not None and not _process_is_alive(process_id):
            _delete_run_lock(value)
            running = False
        if running and process_id is None and not _legacy_batch_is_alive():
            _delete_run_lock(value)
            running = False
        return self._status_response(running)

    def run_manual(self) -> SettingsAIArticleAnalysisRunResponse:
        if not _manual_run_lock.acquire(blocking=False):
            raise HTTPException(
                status_code=409, detail="Article analysis is already running"
            )
        process: subprocess.Popen[str] | None = None
        try:
            with get_db() as conn:
                conn.execute("DELETE FROM app_settings WHERE key = ?", (_PROGRESS_KEY,))
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
            if process is not None:
                _clear_process_run_lock(process.pid)
            _manual_run_lock.release()
