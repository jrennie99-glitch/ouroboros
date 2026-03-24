# ============================
# Ouroboros — Local launcher (replaces colab_launcher.py for local execution)
# ============================
# Runs Ouroboros on macOS/Linux without Google Colab or Google Drive.
# State is persisted to a local directory instead of Drive.

import logging
import os, sys, json, time, uuid, pathlib, subprocess, datetime, threading, queue as _queue_mod
from typing import Any, Dict, List, Optional, Set, Tuple

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(name)s] %(levelname)s: %(message)s")
log = logging.getLogger(__name__)

# ----------------------------
# 0) Load .env file
# ----------------------------
_env_path = pathlib.Path(__file__).parent / ".env"
if _env_path.exists():
    for line in _env_path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" in line:
            key, _, val = line.partition("=")
            key, val = key.strip(), val.strip()
            if key and key not in os.environ:
                os.environ[key] = val

# ----------------------------
# 0.1) Install deps
# ----------------------------
if __name__ == "__main__":
    subprocess.run(
        [sys.executable, "-m", "pip", "install", "-q", "openai>=1.0.0", "requests"],
        check=True,
    )

def ensure_claude_code_cli() -> bool:
    local_bin = str(pathlib.Path.home() / ".local" / "bin")
    if local_bin not in os.environ.get("PATH", ""):
        os.environ["PATH"] = f"{local_bin}:{os.environ.get('PATH', '')}"
    has_cli = subprocess.run(["bash", "-lc", "command -v claude >/dev/null 2>&1"], check=False).returncode == 0
    return has_cli

if __name__ != "__main__":
    sys.exit(0)

from ouroboros.apply_patch import install as install_apply_patch
from ouroboros.llm import DEFAULT_LIGHT_MODEL
install_apply_patch()

# ----------------------------
# 0.2) Voice helpers (STT + TTS for Telegram voice notes)
# ----------------------------
import tempfile

def transcribe_voice(ogg_bytes: bytes) -> str:
    """Transcribe voice note bytes to text using OpenAI Whisper via OpenRouter or local."""
    try:
        tmp_ogg = tempfile.NamedTemporaryFile(suffix=".ogg", delete=False)
        tmp_ogg.write(ogg_bytes)
        tmp_ogg.close()
        # Convert ogg to wav for whisper
        tmp_wav = tmp_ogg.name.replace(".ogg", ".wav")
        subprocess.run(["ffmpeg", "-y", "-i", tmp_ogg.name, "-ar", "16000", "-ac", "1", tmp_wav],
                       capture_output=True, timeout=30)
        # Try OpenAI whisper API via openai SDK
        from openai import OpenAI
        base_url = os.environ.get("OUROBOROS_LLM_BASE_URL", "https://openrouter.ai/api/v1")
        api_key = os.environ.get("OPENROUTER_API_KEY", "")
        # Use Groq for free whisper if available, otherwise try openai compatible
        try:
            groq_client = OpenAI(base_url="https://api.groq.com/openai/v1",
                                 api_key=os.environ.get("GROQ_API_KEY", "dummy"))
            with open(tmp_wav, "rb") as f:
                result = groq_client.audio.transcriptions.create(model="whisper-large-v3", file=f)
            return result.text
        except Exception:
            pass
        # Fallback: use local whisper via command line if available
        try:
            r = subprocess.run(["whisper", tmp_wav, "--model", "tiny", "--output_format", "txt",
                                "--output_dir", tempfile.gettempdir()],
                               capture_output=True, timeout=60, text=True)
            txt_file = tmp_wav.replace(".wav", ".txt")
            if os.path.exists(txt_file):
                text = open(txt_file).read().strip()
                os.unlink(txt_file)
                return text
        except Exception:
            pass
        # Fallback: use macOS speech recognition
        try:
            r = subprocess.run(
                ["python3", "-c", f"""
import speech_recognition as sr
r = sr.Recognizer()
with sr.AudioFile("{tmp_wav}") as source:
    audio = r.record(source)
print(r.recognize_google(audio))
"""],
                capture_output=True, timeout=30, text=True)
            if r.returncode == 0 and r.stdout.strip():
                return r.stdout.strip()
        except Exception:
            pass
        return "[Voice note received but transcription unavailable. Install: pip3 install SpeechRecognition]"
    except Exception as e:
        log.warning("Voice transcription failed: %s", e)
        return f"[Voice note received, transcription error: {e}]"
    finally:
        for f in [tmp_ogg.name, tmp_ogg.name.replace(".ogg", ".wav")]:
            try:
                os.unlink(f)
            except Exception:
                pass

def text_to_voice_ogg(text: str, voice: str = "Samantha") -> Optional[bytes]:
    """Convert text to .ogg opus voice note using macOS say + ffmpeg."""
    try:
        # Clean text for speech
        import re as _re
        clean = text
        clean = _re.sub(r'```[\s\S]*?```', 'Code block omitted.', clean)
        clean = _re.sub(r'`([^`]+)`', r'\1', clean)
        clean = _re.sub(r'\*\*?([^*]+)\*\*?', r'\1', clean)
        clean = _re.sub(r'#{1,6}\s', '', clean)
        clean = _re.sub(r'\[([^\]]+)\]\([^)]+\)', r'\1', clean)
        clean = _re.sub(r'[|_~]', ' ', clean)
        # Limit length for voice
        if len(clean) > 3000:
            clean = clean[:3000] + "... message truncated for voice."
        tmp_aiff = tempfile.NamedTemporaryFile(suffix=".aiff", delete=False)
        tmp_aiff.close()
        tmp_ogg = tmp_aiff.name.replace(".aiff", ".ogg")
        # macOS say -> AIFF
        subprocess.run(["say", "-v", voice, "-o", tmp_aiff.name, clean],
                       capture_output=True, timeout=60)
        # AIFF -> OGG Opus (Telegram requires opus codec)
        subprocess.run(["ffmpeg", "-y", "-i", tmp_aiff.name, "-c:a", "libopus",
                        "-b:a", "32k", "-ar", "48000", "-ac", "1", tmp_ogg],
                       capture_output=True, timeout=60)
        if os.path.exists(tmp_ogg):
            with open(tmp_ogg, "rb") as f:
                ogg_data = f.read()
            return ogg_data if len(ogg_data) > 100 else None
        return None
    except Exception as e:
        log.warning("TTS failed: %s", e)
        return None
    finally:
        for f in [tmp_aiff.name, tmp_aiff.name.replace(".aiff", ".ogg")]:
            try:
                os.unlink(f)
            except Exception:
                pass

# ----------------------------
# 1) Secrets + runtime config (from env vars / .env file)
# ----------------------------
def get_secret(name: str, default: Optional[str] = None, required: bool = False) -> Optional[str]:
    v = os.environ.get(name, default)
    if required:
        assert v is not None and str(v).strip() != "", f"Missing required secret: {name}"
    return v

def get_cfg(name: str, default: Optional[str] = None) -> Optional[str]:
    v = os.environ.get(name)
    if v is not None and str(v).strip() != "":
        return v
    return default

def _parse_int_cfg(raw: Optional[str], default: int, minimum: int = 0) -> int:
    try:
        val = int(str(raw))
    except Exception:
        val = default
    return max(minimum, val)

OPENROUTER_API_KEY = get_secret("OPENROUTER_API_KEY", required=True)
TELEGRAM_BOT_TOKEN = get_secret("TELEGRAM_BOT_TOKEN", required=True)
TOTAL_BUDGET_DEFAULT = get_secret("TOTAL_BUDGET", required=True)
GITHUB_TOKEN = get_secret("GITHUB_TOKEN", required=False) or ""

import re
_raw_budget = str(TOTAL_BUDGET_DEFAULT or "")
_clean_budget = re.sub(r'[^0-9.\-]', '', _raw_budget)
TOTAL_BUDGET_LIMIT = float(_clean_budget) if _clean_budget else 0.0

OPENAI_API_KEY = get_secret("OPENAI_API_KEY", default="")
ANTHROPIC_API_KEY = get_secret("ANTHROPIC_API_KEY", default="")
GITHUB_USER = get_cfg("GITHUB_USER")
GITHUB_REPO = get_cfg("GITHUB_REPO", default="ouroboros")
assert GITHUB_USER and str(GITHUB_USER).strip(), "GITHUB_USER not set. Add it to .env file."
assert GITHUB_REPO and str(GITHUB_REPO).strip(), "GITHUB_REPO not set. Add it to .env file."
MAX_WORKERS = int(get_cfg("OUROBOROS_MAX_WORKERS", default="2") or "2")
MODEL_MAIN = get_cfg("OUROBOROS_MODEL", default="meta-llama/llama-3.3-70b-instruct:free")
MODEL_CODE = get_cfg("OUROBOROS_MODEL_CODE", default="meta-llama/llama-3.3-70b-instruct:free")
MODEL_LIGHT = get_cfg("OUROBOROS_MODEL_LIGHT", default="meta-llama/llama-3.3-70b-instruct:free")

BUDGET_REPORT_EVERY_MESSAGES = 10
SOFT_TIMEOUT_SEC = max(60, int(get_cfg("OUROBOROS_SOFT_TIMEOUT_SEC", default="600") or "600"))
HARD_TIMEOUT_SEC = max(120, int(get_cfg("OUROBOROS_HARD_TIMEOUT_SEC", default="1800") or "1800"))
DIAG_HEARTBEAT_SEC = _parse_int_cfg(get_cfg("OUROBOROS_DIAG_HEARTBEAT_SEC", default="30"), default=30, minimum=0)
DIAG_SLOW_CYCLE_SEC = _parse_int_cfg(get_cfg("OUROBOROS_DIAG_SLOW_CYCLE_SEC", default="20"), default=20, minimum=0)

os.environ["OPENROUTER_API_KEY"] = str(OPENROUTER_API_KEY)
os.environ["OPENAI_API_KEY"] = str(OPENAI_API_KEY or "")
os.environ["ANTHROPIC_API_KEY"] = str(ANTHROPIC_API_KEY or "")
os.environ["GITHUB_USER"] = str(GITHUB_USER)
os.environ["GITHUB_REPO"] = str(GITHUB_REPO)
os.environ["OUROBOROS_MODEL"] = str(MODEL_MAIN)
os.environ["OUROBOROS_MODEL_CODE"] = str(MODEL_CODE)
if MODEL_LIGHT:
    os.environ["OUROBOROS_MODEL_LIGHT"] = str(MODEL_LIGHT)
os.environ["OUROBOROS_DIAG_HEARTBEAT_SEC"] = str(DIAG_HEARTBEAT_SEC)
os.environ["OUROBOROS_DIAG_SLOW_CYCLE_SEC"] = str(DIAG_SLOW_CYCLE_SEC)
os.environ["TELEGRAM_BOT_TOKEN"] = str(TELEGRAM_BOT_TOKEN)

if str(ANTHROPIC_API_KEY or "").strip():
    ensure_claude_code_cli()

# ----------------------------
# 2) Local state directory (replaces Google Drive)
# ----------------------------
LOCAL_STATE_DIR = pathlib.Path(get_cfg("OUROBOROS_STATE_DIR", default=str(pathlib.Path(__file__).parent / "local_state")))
DRIVE_ROOT = LOCAL_STATE_DIR.resolve()
REPO_DIR = pathlib.Path(__file__).parent.resolve()

os.environ["DRIVE_ROOT"] = str(DRIVE_ROOT)
os.environ["OUROBOROS_REPO_DIR"] = str(REPO_DIR)

for sub in ["state", "logs", "memory", "index", "locks", "archive"]:
    (DRIVE_ROOT / sub).mkdir(parents=True, exist_ok=True)

# Clear stale owner mailbox files from previous session
try:
    from ouroboros.owner_inject import get_pending_path
    _stale_inject = get_pending_path(DRIVE_ROOT)
    if _stale_inject.exists():
        _stale_inject.unlink(missing_ok=True)
    _mailbox_dir = DRIVE_ROOT / "memory" / "owner_mailbox"
    if _mailbox_dir.exists():
        for _f in _mailbox_dir.iterdir():
            _f.unlink(missing_ok=True)
except Exception:
    pass

CHAT_LOG_PATH = DRIVE_ROOT / "logs" / "chat.jsonl"
if not CHAT_LOG_PATH.exists():
    CHAT_LOG_PATH.write_text("", encoding="utf-8")

# ----------------------------
# 3) Git constants
# ----------------------------
BRANCH_DEV = "ouroboros"
BRANCH_STABLE = "ouroboros-stable"
if GITHUB_TOKEN:
    REMOTE_URL = f"https://{GITHUB_TOKEN}:x-oauth-basic@github.com/{GITHUB_USER}/{GITHUB_REPO}.git"
else:
    REMOTE_URL = f"https://github.com/{GITHUB_USER}/{GITHUB_REPO}.git"

# ----------------------------
# 4) Initialize supervisor modules
# ----------------------------
from supervisor.state import (
    init as state_init, load_state, save_state, append_jsonl,
    update_budget_from_usage, status_text, rotate_chat_log_if_needed,
    init_state,
)
state_init(DRIVE_ROOT, TOTAL_BUDGET_LIMIT)
init_state()

from supervisor.telegram import (
    init as telegram_init, TelegramClient, send_with_budget, log_chat,
)
TG = TelegramClient(str(TELEGRAM_BOT_TOKEN))
telegram_init(
    drive_root=DRIVE_ROOT,
    total_budget_limit=TOTAL_BUDGET_LIMIT,
    budget_report_every=BUDGET_REPORT_EVERY_MESSAGES,
    tg_client=TG,
)

from supervisor.git_ops import (
    init as git_ops_init, ensure_repo_present, checkout_and_reset,
    sync_runtime_dependencies, import_test, safe_restart,
)
git_ops_init(
    repo_dir=REPO_DIR, drive_root=DRIVE_ROOT, remote_url=REMOTE_URL,
    branch_dev=BRANCH_DEV, branch_stable=BRANCH_STABLE,
)

from supervisor.queue import (
    enqueue_task, enforce_task_timeouts, enqueue_evolution_task_if_needed,
    persist_queue_snapshot, restore_pending_from_snapshot,
    cancel_task_by_id, queue_review_task, sort_pending,
)

from supervisor.workers import (
    init as workers_init, get_event_q, WORKERS, PENDING, RUNNING,
    spawn_workers, kill_workers, assign_tasks, ensure_workers_healthy,
    handle_chat_direct, _get_chat_agent, auto_resume_after_restart,
)
workers_init(
    repo_dir=REPO_DIR, drive_root=DRIVE_ROOT, max_workers=MAX_WORKERS,
    soft_timeout=SOFT_TIMEOUT_SEC, hard_timeout=HARD_TIMEOUT_SEC,
    total_budget_limit=TOTAL_BUDGET_LIMIT,
    branch_dev=BRANCH_DEV, branch_stable=BRANCH_STABLE,
)

from supervisor.events import dispatch_event

# Initialize inter-agent messaging system
from supervisor import messaging as _messaging
_messaging.init(DRIVE_ROOT)

# ----------------------------
# 5) Bootstrap repo
# ----------------------------
ensure_repo_present()
ok, msg = safe_restart(reason="bootstrap", unsynced_policy="rescue_and_reset")
assert ok, f"Bootstrap failed: {msg}"

# ----------------------------
# 6) Start workers
# ----------------------------
kill_workers()
spawn_workers(MAX_WORKERS)
restored_pending = restore_pending_from_snapshot()
persist_queue_snapshot(reason="startup")
if restored_pending > 0:
    st_boot = load_state()
    if st_boot.get("owner_chat_id"):
        send_with_budget(int(st_boot["owner_chat_id"]),
                         f"Restored pending queue from snapshot: {restored_pending} tasks.")

append_jsonl(DRIVE_ROOT / "logs" / "supervisor.jsonl", {
    "ts": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    "type": "launcher_start",
    "branch": load_state().get("current_branch"),
    "sha": load_state().get("current_sha"),
    "max_workers": MAX_WORKERS,
    "model_default": MODEL_MAIN, "model_code": MODEL_CODE, "model_light": MODEL_LIGHT,
    "soft_timeout_sec": SOFT_TIMEOUT_SEC, "hard_timeout_sec": HARD_TIMEOUT_SEC,
    "diag_heartbeat_sec": DIAG_HEARTBEAT_SEC,
    "diag_slow_cycle_sec": DIAG_SLOW_CYCLE_SEC,
})

# ----------------------------
# 6.1) Auto-resume after restart
# ----------------------------
auto_resume_after_restart()

# ----------------------------
# 6.2) Direct-mode watchdog
# ----------------------------
def _chat_watchdog_loop():
    soft_warned = False
    while True:
        time.sleep(30)
        try:
            agent = _get_chat_agent()
            if not agent._busy:
                soft_warned = False
                continue
            now = time.time()
            idle_sec = now - agent._last_progress_ts
            total_sec = now - agent._task_started_ts
            if idle_sec >= HARD_TIMEOUT_SEC:
                st = load_state()
                if st.get("owner_chat_id"):
                    send_with_budget(int(st["owner_chat_id"]),
                                     f"Task stuck ({int(total_sec)}s). Restarting agent.")
                reset_chat_agent()
                soft_warned = False
                continue
            if idle_sec >= SOFT_TIMEOUT_SEC and not soft_warned:
                soft_warned = True
                st = load_state()
                if st.get("owner_chat_id"):
                    send_with_budget(int(st["owner_chat_id"]),
                                     f"Task running for {int(total_sec)}s, last progress {int(idle_sec)}s ago.")
        except Exception:
            pass

_watchdog_thread = threading.Thread(target=_chat_watchdog_loop, daemon=True)
_watchdog_thread.start()

# ----------------------------
# 6.3) Background consciousness
# ----------------------------
from ouroboros.consciousness import BackgroundConsciousness

def _get_owner_chat_id() -> Optional[int]:
    try:
        st = load_state()
        cid = st.get("owner_chat_id")
        return int(cid) if cid else None
    except Exception:
        return None

_consciousness = BackgroundConsciousness(
    drive_root=DRIVE_ROOT,
    repo_dir=REPO_DIR,
    event_queue=get_event_q(),
    owner_chat_id_fn=_get_owner_chat_id,
)

def reset_chat_agent():
    import supervisor.workers as _w
    _w._chat_agent = None

# ----------------------------
# 7) Main loop
# ----------------------------
import types
_event_ctx = types.SimpleNamespace(
    DRIVE_ROOT=DRIVE_ROOT,
    REPO_DIR=REPO_DIR,
    BRANCH_DEV=BRANCH_DEV,
    BRANCH_STABLE=BRANCH_STABLE,
    TG=TG,
    WORKERS=WORKERS,
    PENDING=PENDING,
    RUNNING=RUNNING,
    MAX_WORKERS=MAX_WORKERS,
    send_with_budget=send_with_budget,
    load_state=load_state,
    save_state=save_state,
    update_budget_from_usage=update_budget_from_usage,
    append_jsonl=append_jsonl,
    enqueue_task=enqueue_task,
    cancel_task_by_id=cancel_task_by_id,
    queue_review_task=queue_review_task,
    persist_queue_snapshot=persist_queue_snapshot,
    safe_restart=safe_restart,
    kill_workers=kill_workers,
    spawn_workers=spawn_workers,
    sort_pending=sort_pending,
    consciousness=_consciousness,
)


def _safe_qsize(q: Any) -> int:
    try:
        return int(q.qsize())
    except Exception:
        return -1


def _handle_supervisor_command(text: str, chat_id: int, tg_offset: int = 0):
    lowered = text.strip().lower()
    if lowered.startswith("/panic"):
        send_with_budget(chat_id, "PANIC: stopping everything now.")
        kill_workers()
        st2 = load_state()
        st2["tg_offset"] = tg_offset
        save_state(st2)
        raise SystemExit("PANIC")
    if lowered.startswith("/restart"):
        st2 = load_state()
        st2["session_id"] = uuid.uuid4().hex
        st2["tg_offset"] = tg_offset
        save_state(st2)
        send_with_budget(chat_id, "Restarting (soft).")
        ok, msg = safe_restart(reason="owner_restart", unsynced_policy="rescue_and_reset")
        if not ok:
            send_with_budget(chat_id, f"Restart cancelled: {msg}")
            return True
        kill_workers()
        os.execv(sys.executable, [sys.executable, __file__])
    if lowered.startswith("/status"):
        status = status_text(WORKERS, PENDING, RUNNING, SOFT_TIMEOUT_SEC, HARD_TIMEOUT_SEC)
        send_with_budget(chat_id, status, force_budget=True)
        return "[Supervisor handled /status]\n"
    if lowered.startswith("/review"):
        queue_review_task(reason="owner:/review", force=True)
        return "[Supervisor handled /review]\n"
    if lowered.startswith("/evolve"):
        parts = lowered.split()
        action = parts[1] if len(parts) > 1 else "on"
        turn_on = action not in ("off", "stop", "0")
        st2 = load_state()
        st2["evolution_mode_enabled"] = bool(turn_on)
        save_state(st2)
        if not turn_on:
            PENDING[:] = [t for t in PENDING if str(t.get("type")) != "evolution"]
            sort_pending()
            persist_queue_snapshot(reason="evolve_off")
        state_str = "ON" if turn_on else "OFF"
        send_with_budget(chat_id, f"Evolution: {state_str}")
        return f"[Supervisor handled /evolve — {state_str}]\n"
    if lowered.startswith("/bg"):
        parts = lowered.split()
        action = parts[1] if len(parts) > 1 else "status"
        if action in ("start", "on", "1"):
            result = _consciousness.start()
            send_with_budget(chat_id, result)
        elif action in ("stop", "off", "0"):
            result = _consciousness.stop()
            send_with_budget(chat_id, result)
        else:
            bg_status = "running" if _consciousness.is_running else "stopped"
            send_with_budget(chat_id, f"Background consciousness: {bg_status}")
        return f"[Supervisor handled /bg {action}]\n"
    return ""


offset = int(load_state().get("tg_offset") or 0)
_last_diag_heartbeat_ts = 0.0
_last_message_ts: float = time.time()
_ACTIVE_MODE_SEC: int = 300

# Auto-start background consciousness (unless disabled)
if os.environ.get("OUROBOROS_DISABLE_BG") != "1":
    try:
        _consciousness.start()
        log.info("Background consciousness auto-started")
    except Exception as e:
        log.warning("consciousness auto-start failed: %s", e)
else:
    log.info("Background consciousness DISABLED (OUROBOROS_DISABLE_BG=1)")

print(f"\n{'='*60}")
print(f"  Ouroboros LOCAL launcher running")
print(f"  Model: {MODEL_MAIN}")
print(f"  LLM Base URL: {os.environ.get('OUROBOROS_LLM_BASE_URL', 'https://openrouter.ai/api/v1')}")
print(f"  Workers: {MAX_WORKERS}")
print(f"  Budget: ${TOTAL_BUDGET_LIMIT}")
print(f"  State dir: {DRIVE_ROOT}")
print(f"  Send a message to your Telegram bot to start!")
print(f"  Web chat: http://localhost:8765")
print(f"{'='*60}\n")

# Start web chat server with voice support
try:
    import threading
    from web_chat import ChatHandler
    from http.server import HTTPServer as _HTTPServer
    _web_server = _HTTPServer(("0.0.0.0", 8765), ChatHandler)
    threading.Thread(target=_web_server.serve_forever, daemon=True).start()
    log.info("Web chat with voice started at http://localhost:8765")
except Exception as _e:
    log.warning("Failed to start web chat: %s", _e)

while True:
    loop_started_ts = time.time()
    rotate_chat_log_if_needed(DRIVE_ROOT)
    ensure_workers_healthy()

    event_q = get_event_q()
    while True:
        try:
            evt = event_q.get_nowait()
        except _queue_mod.Empty:
            break
        dispatch_event(evt, _event_ctx)

    enforce_task_timeouts()
    enqueue_evolution_task_if_needed()
    assign_tasks()
    persist_queue_snapshot(reason="main_loop")

    _now = time.time()
    _active = (_now - _last_message_ts) < _ACTIVE_MODE_SEC
    _poll_timeout = 0 if _active else 10
    try:
        updates = TG.get_updates(offset=offset, timeout=_poll_timeout)
    except Exception as e:
        append_jsonl(DRIVE_ROOT / "logs" / "supervisor.jsonl", {
            "ts": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "type": "telegram_poll_error", "offset": offset, "error": repr(e),
        })
        time.sleep(1.5)
        continue

    for upd in updates:
        offset = int(upd["update_id"]) + 1
        msg = upd.get("message") or upd.get("edited_message") or {}
        if not msg:
            continue
        chat_id = int(msg["chat"]["id"])
        from_user = msg.get("from") or {}
        user_id = int(from_user.get("id") or 0)
        text = str(msg.get("text") or "")
        caption = str(msg.get("caption") or "")
        now_iso = datetime.datetime.now(datetime.timezone.utc).isoformat()

        # Handle voice notes — transcribe to text
        _is_voice_msg = False
        if msg.get("voice"):
            voice_file_id = msg["voice"].get("file_id")
            if voice_file_id:
                _is_voice_msg = True
                voice_bytes = TG.download_file_bytes(voice_file_id)
                if voice_bytes:
                    transcribed = transcribe_voice(voice_bytes)
                    if transcribed:
                        text = transcribed
                        log.info("Voice transcribed: %s", text[:100])
                elif not text:
                    text = "[Voice note received but download failed]"

        image_data = None
        if msg.get("photo"):
            best_photo = msg["photo"][-1]
            file_id = best_photo.get("file_id")
            if file_id:
                b64, mime = TG.download_file_base64(file_id)
                if b64:
                    image_data = (b64, mime, caption)
        elif msg.get("document"):
            doc = msg["document"]
            mime_type = str(doc.get("mime_type") or "")
            if mime_type.startswith("image/"):
                file_id = doc.get("file_id")
                if file_id:
                    b64, mime = TG.download_file_base64(file_id)
                    if b64:
                        image_data = (b64, mime, caption)

        st = load_state()
        if st.get("owner_id") is None:
            st["owner_id"] = user_id
            st["owner_chat_id"] = chat_id
            st["last_owner_message_at"] = now_iso
            save_state(st)
            log_chat("in", chat_id, user_id, text)
            send_with_budget(chat_id, "Owner registered. Ouroboros online.")
            continue

        if user_id != int(st.get("owner_id")):
            continue

        log_chat("in", chat_id, user_id, text)
        st["last_owner_message_at"] = now_iso
        _last_message_ts = time.time()
        save_state(st)

        if text.strip().lower().startswith("/"):
            try:
                result = _handle_supervisor_command(text, chat_id, tg_offset=offset)
                if result is True:
                    continue
                elif result:
                    text = result + text
            except SystemExit:
                raise
            except Exception:
                log.warning("Supervisor command handler error", exc_info=True)

        if not text and not image_data:
            continue

        _consciousness.inject_observation(f"Owner message: {text[:100]}")
        agent = _get_chat_agent()

        if agent._busy:
            if image_data:
                if text:
                    agent.inject_message(text)
                send_with_budget(chat_id, "Photo received, but a task is in progress. Send again when I'm free.")
            elif text:
                agent.inject_message(text)
        else:
            _BATCH_WINDOW_SEC = 1.5
            _EARLY_EXIT_SEC = 0.15
            _batch_start = time.time()
            _batch_deadline = _batch_start + _BATCH_WINDOW_SEC
            _batched_texts = [text] if text else []
            _batched_image = image_data

            _batch_state = load_state()
            _batch_state_dirty = False
            while time.time() < _batch_deadline:
                time.sleep(0.1)
                try:
                    _extra_updates = TG.get_updates(offset=offset, timeout=0) or []
                except Exception:
                    _extra_updates = []
                if not _extra_updates and (time.time() - _batch_start) < _EARLY_EXIT_SEC:
                    break
                for _upd in _extra_updates:
                    offset = max(offset, int(_upd.get("update_id", offset - 1)) + 1)
                    _msg2 = _upd.get("message") or _upd.get("edited_message") or {}
                    _uid2 = (_msg2.get("from") or {}).get("id")
                    _cid2 = (_msg2.get("chat") or {}).get("id")
                    _txt2 = _msg2.get("text") or _msg2.get("caption") or ""
                    if _uid2 and _batch_state.get("owner_id") and _uid2 == int(_batch_state["owner_id"]):
                        log_chat("in", _cid2, _uid2, _txt2)
                        _batch_state["last_owner_message_at"] = datetime.datetime.now(datetime.timezone.utc).isoformat()
                        _batch_state_dirty = True
                        if _txt2.strip().lower().startswith("/"):
                            try:
                                _cmd_result = _handle_supervisor_command(_txt2, _cid2, tg_offset=offset)
                                if _cmd_result is True:
                                    continue
                                elif _cmd_result:
                                    _txt2 = _cmd_result + _txt2
                            except SystemExit:
                                raise
                            except Exception:
                                log.warning("Supervisor command in batch failed", exc_info=True)
                        if _txt2:
                            _batched_texts.append(_txt2)
                            _batch_deadline = max(_batch_deadline, time.time() + 0.3)
                        if not _batched_image:
                            _doc2 = _msg2.get("document") or {}
                            _photo2 = (_msg2.get("photo") or [None])[-1] or {}
                            _fid2 = _photo2.get("file_id") or _doc2.get("file_id")
                            if _fid2:
                                _b642, _mime2 = TG.download_file_base64(_fid2)
                                if _b642:
                                    _batched_image = (_b642, _mime2, _txt2)

            if _batch_state_dirty:
                save_state(_batch_state)

            if len(_batched_texts) > 1:
                final_text = "\n\n".join(_batched_texts)
            elif _batched_texts:
                final_text = _batched_texts[0]
            else:
                final_text = text

            if agent._busy:
                if final_text:
                    agent.inject_message(final_text)
                if _batched_image:
                    send_with_budget(chat_id, "Photo received, but a task is in progress.")
            else:
                _consciousness.pause()
                _voice_reply = _is_voice_msg
                def _run_task_and_resume(cid, txt, img, voice_reply):
                    try:
                        handle_chat_direct(cid, txt, img, reply_as_voice=voice_reply)
                    finally:
                        _consciousness.resume()
                _t = threading.Thread(
                    target=_run_task_and_resume,
                    args=(chat_id, final_text, _batched_image, _voice_reply),
                    daemon=True,
                )
                try:
                    _t.start()
                except Exception as _te:
                    log.error("Failed to start chat thread: %s", _te)
                    _consciousness.resume()

    st = load_state()
    st["tg_offset"] = offset
    save_state(st)

    now_epoch = time.time()
    loop_duration_sec = now_epoch - loop_started_ts

    if DIAG_SLOW_CYCLE_SEC > 0 and loop_duration_sec >= float(DIAG_SLOW_CYCLE_SEC):
        append_jsonl(DRIVE_ROOT / "logs" / "supervisor.jsonl", {
            "ts": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "type": "main_loop_slow_cycle",
            "duration_sec": round(loop_duration_sec, 3),
            "pending_count": len(PENDING),
            "running_count": len(RUNNING),
        })

    if DIAG_HEARTBEAT_SEC > 0 and (now_epoch - _last_diag_heartbeat_ts) >= float(DIAG_HEARTBEAT_SEC):
        workers_total = len(WORKERS)
        workers_alive = sum(1 for w in WORKERS.values() if w.proc.is_alive())
        append_jsonl(DRIVE_ROOT / "logs" / "supervisor.jsonl", {
            "ts": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "type": "main_loop_heartbeat",
            "offset": offset,
            "workers_total": workers_total,
            "workers_alive": workers_alive,
            "pending_count": len(PENDING),
            "running_count": len(RUNNING),
            "event_q_size": _safe_qsize(event_q),
            "running_task_ids": list(RUNNING.keys())[:5],
            "spent_usd": st.get("spent_usd"),
        })
        _last_diag_heartbeat_ts = now_epoch

    _loop_sleep = 0.1 if (_now - _last_message_ts) < _ACTIVE_MODE_SEC else 0.5
    time.sleep(_loop_sleep)
