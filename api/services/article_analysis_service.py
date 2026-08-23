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

from api.database import get_db, load_vec_extension
from api.model.models import (
    SettingsAIArticleAnalysisCancelResponse,
    SettingsAIArticleAnalysisClearResponse,
    SettingsAIArticleAnalysisRunResponse,
    SettingsAIArticleAnalysisStatusResponse,
)

_manual_run_lock = threading.Lock()
_REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
_logger = logging.getLogger("uvicorn.error")
_RUN_TIMEOUT_SECONDS = 7200
_SINGLE_ARTICLE_RUN_TIMEOUT_SECONDS = 300
_RUN_LOCK_KEY = "ai_article_analysis_running"
_PROGRESS_KEY = "ai_article_analysis_progress"
_CANCEL_KEY = "ai_article_analysis_cancel_requested"


def _batch_binary() -> str:
    configured = os.environ.get("SHIORI_FEED_BATCH_BIN")
    if configured:
        return configured

    development_binary = (
        _REPOSITORY_ROOT / "batch" / "target" / "debug" / "shiori-feed-batch"
    )
    if development_binary.is_file() and os.access(development_binary, os.X_OK):
        return str(development_binary)

    installed = shutil.which("shiori-feed-batch")
    if installed:
        return installed

    raise HTTPException(
        status_code=503,
        detail=(
            "Article analysis runner is not available. "
            "Run `cargo build --manifest-path batch/Cargo.toml` first."
        ),
    )


def _batch_command() -> list[str]:
    return [_batch_binary(), "--article-analysis-only"]


def _batch_command_for_article(source_type: str, article_id: int) -> list[str]:
    return [_batch_binary(), f"--reanalyze-article={source_type}:{article_id}"]


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
        conn.execute(
            "DELETE FROM app_settings WHERE key = ? AND value = ?", (_CANCEL_KEY, value)
        )


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
            conn.execute(
                "DELETE FROM app_settings WHERE key = ? AND value = ?",
                (_CANCEL_KEY, value),
            )


class ArticleAnalysisService:
    def clear_results(self) -> SettingsAIArticleAnalysisClearResponse:
        if self.status().running:
            raise HTTPException(
                status_code=409,
                detail="Article analysis is running. Wait for it to finish before clearing results.",
            )
        with get_db() as conn:
            row = conn.execute("SELECT COUNT(*) AS total FROM article_ai_analyses").fetchone()
            cleared_count = int(row["total"]) if row else 0
            conn.execute("DELETE FROM article_ai_analyses")
            # article_ai_embeddings has no FK/trigger tying it to
            # article_ai_analyses (see the migration comment), so orphaned
            # vectors are swept up explicitly here, the one place that bulk
            # deletes analyses.
            load_vec_extension(conn)
            conn.execute(
                "DELETE FROM article_ai_embeddings "
                "WHERE analysis_id NOT IN (SELECT id FROM article_ai_analyses)"
            )
        return SettingsAIArticleAnalysisClearResponse(cleared_count=cleared_count)

    def _status_response(self, running: bool) -> SettingsAIArticleAnalysisStatusResponse:
        if not running:
            return SettingsAIArticleAnalysisStatusResponse(running=False)
        with get_db() as conn:
            row = conn.execute(
                "SELECT value FROM app_settings WHERE key = ?", (_PROGRESS_KEY,)
            ).fetchone()
            cancel_row = conn.execute(
                "SELECT value FROM app_settings WHERE key = ?", (_CANCEL_KEY,)
            ).fetchone()
            lock_row = conn.execute(
                "SELECT value FROM app_settings WHERE key = ?", (_RUN_LOCK_KEY,)
            ).fetchone()
        stopping = bool(
            cancel_row
            and lock_row
            and str(cancel_row["value"]) == str(lock_row["value"])
        )
        if row is None:
            return SettingsAIArticleAnalysisStatusResponse(running=True, stopping=stopping)
        try:
            progress = json.loads(str(row["value"]))
            return SettingsAIArticleAnalysisStatusResponse(
                running=True,
                stopping=stopping,
                **progress,
            )
        except (TypeError, ValueError, ValidationError):
            return SettingsAIArticleAnalysisStatusResponse(running=True, stopping=stopping)

    def request_cancel(self) -> SettingsAIArticleAnalysisCancelResponse:
        if not self.status().running:
            raise HTTPException(status_code=409, detail="Article analysis is not running")
        with get_db() as conn:
            row = conn.execute(
                "SELECT value FROM app_settings WHERE key = ?", (_RUN_LOCK_KEY,)
            ).fetchone()
            if row is None:
                raise HTTPException(status_code=409, detail="Article analysis is not running")
            token = str(row["value"])
            conn.execute(
                """
                INSERT INTO app_settings (key, value) VALUES (?, ?)
                ON CONFLICT(key) DO UPDATE SET value = excluded.value
                """,
                (_CANCEL_KEY, token),
            )
        return SettingsAIArticleAnalysisCancelResponse(cancellation_requested=True)

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
        return self._execute(_batch_command(), _RUN_TIMEOUT_SECONDS)

    def run_single(
        self, source_type: str, article_id: int
    ) -> SettingsAIArticleAnalysisRunResponse:
        return self._execute(
            _batch_command_for_article(source_type, article_id),
            _SINGLE_ARTICLE_RUN_TIMEOUT_SECONDS,
        )

    def _execute(
        self, command: list[str], timeout_seconds: int
    ) -> SettingsAIArticleAnalysisRunResponse:
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
                    command,
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

            timeout = threading.Timer(timeout_seconds, terminate_on_timeout)
            timeout.start()
            output_lines: list[str] = []
            report: SettingsAIArticleAnalysisRunResponse | None = None
            _logger.info("Starting AI article analysis: %s", command)
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
                "AI article analysis completed: processed=%d succeeded=%d failed=%d skipped=%d",
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
