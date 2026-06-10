"""
main.py — ConstitutionAI unified launcher.

Run this file from the project root to start BOTH the backend (FastAPI/Uvicorn)
and the frontend (Vite/Vue) dev server in parallel.

Usage:
    python main.py

Press Ctrl+C to stop both servers.
"""

import os
import sys
import subprocess
import signal
import threading
import time
from pathlib import Path

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

ROOT_DIR     = Path(__file__).parent.resolve()
BACKEND_DIR  = ROOT_DIR / "backend"
FRONTEND_DIR = ROOT_DIR / "frontend"

# ---------------------------------------------------------------------------
# ANSI colors for pretty terminal output
# ---------------------------------------------------------------------------

RESET  = "\033[0m"
BOLD   = "\033[1m"
CYAN   = "\033[96m"
GREEN  = "\033[92m"
YELLOW = "\033[93m"
RED    = "\033[91m"
BLUE   = "\033[94m"
MAGENTA = "\033[95m"

def banner():
    print(f"""
{CYAN}{BOLD}╔══════════════════════════════════════════════════════╗
║        ConstitutionAI — Unified Launcher             ║
║   AI-powered tutor for the Indian Constitution 🇮🇳    ║
╚══════════════════════════════════════════════════════╝{RESET}
""")

def log(tag: str, color: str, message: str):
    print(f"  {color}{BOLD}[{tag}]{RESET} {message}")

# ---------------------------------------------------------------------------
# Stream subprocess output with a colored prefix
# ---------------------------------------------------------------------------

def stream_output(proc: subprocess.Popen, tag: str, color: str):
    """Read lines from a subprocess and print them with a colored tag."""
    for line in iter(proc.stdout.readline, b""):
        text = line.decode("utf-8", errors="replace").rstrip()
        if text:
            print(f"  {color}[{tag}]{RESET} {text}")
    # Process ended
    proc.stdout.close()

# ---------------------------------------------------------------------------
# Pre-flight checks
# ---------------------------------------------------------------------------

def check_node_modules():
    """Install frontend dependencies if node_modules is missing."""
    nm = FRONTEND_DIR / "node_modules"
    if not nm.exists():
        log("SETUP", YELLOW, "node_modules not found — running npm install...")
        result = subprocess.run(
            ["npm", "install"],
            cwd=FRONTEND_DIR,
            shell=True,
        )
        if result.returncode != 0:
            log("ERROR", RED, "npm install failed. Make sure Node.js 18+ is installed.")
            sys.exit(1)
        log("SETUP", GREEN, "npm install complete ✅")
    else:
        log("SETUP", GREEN, "node_modules found ✅")


def check_env_file():
    """Warn if .env is missing in the backend directory."""
    env_file = BACKEND_DIR / ".env"
    example  = BACKEND_DIR / ".env.example"
    if not env_file.exists():
        log("SETUP", YELLOW, ".env not found in backend/ — copying from .env.example")
        if example.exists():
            import shutil
            shutil.copy(example, env_file)
            log("SETUP", YELLOW,
                "Created backend/.env — please edit it with your API keys before restarting!")
        else:
            log("SETUP", RED, "No .env.example found. Create backend/.env manually.")


# ---------------------------------------------------------------------------
# Main launcher
# ---------------------------------------------------------------------------

def main():
    banner()

    # ── Pre-flight ──────────────────────────────────────────────────────────
    log("CHECK", CYAN, "Running pre-flight checks…")
    check_env_file()
    check_node_modules()
    print()

    # ── Resolve python / npm executables ────────────────────────────────────
    python_exe = sys.executable          # use the same Python that ran this script
    npm_cmd    = "npm"

    # ── Start Backend ───────────────────────────────────────────────────────
    log("BACKEND", BLUE, f"Starting FastAPI on http://localhost:8000  (Ctrl+C to stop all)")

    backend_env = os.environ.copy()
    backend_env["PYTHONUNBUFFERED"] = "1"   # ensure unbuffered stdout

    backend_proc = subprocess.Popen(
        [
            python_exe, "-m", "uvicorn",
            "main:app",
            "--reload",
            "--port", "8000",
            "--host", "0.0.0.0",
        ],
        cwd=BACKEND_DIR,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        env=backend_env,
    )

    # ── Start Frontend ──────────────────────────────────────────────────────
    log("FRONTEND", MAGENTA, "Starting Vite dev server on http://localhost:5173")

    frontend_proc = subprocess.Popen(
        [npm_cmd, "run", "dev"],
        cwd=FRONTEND_DIR,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        shell=True,                       # required on Windows for npm
    )

    # ── Stream output in background threads ─────────────────────────────────
    t_back  = threading.Thread(target=stream_output, args=(backend_proc,  "BACKEND",  BLUE),    daemon=True)
    t_front = threading.Thread(target=stream_output, args=(frontend_proc, "FRONTEND", MAGENTA), daemon=True)
    t_back.start()
    t_front.start()

    print()
    log("INFO", GREEN, "Both servers are starting — please wait a few seconds…")
    log("INFO", GREEN, "  Backend  → http://localhost:8000")
    log("INFO", GREEN, "  API Docs → http://localhost:8000/docs")
    log("INFO", GREEN, "  Frontend → http://localhost:5173")
    print(f"\n  {YELLOW}Press Ctrl+C to stop both servers.{RESET}\n")

    # ── Wait and handle Ctrl+C ───────────────────────────────────────────────
    def shutdown(signum=None, frame=None):
        print(f"\n{YELLOW}{BOLD}  Shutting down ConstitutionAI…{RESET}")
        for proc in (backend_proc, frontend_proc):
            try:
                proc.terminate()
            except Exception:
                pass
        # Give them a moment to exit gracefully
        time.sleep(1)
        for proc in (backend_proc, frontend_proc):
            try:
                proc.kill()
            except Exception:
                pass
        log("INFO", GREEN, "All servers stopped. Goodbye! 👋")
        sys.exit(0)

    # Register SIGINT / SIGTERM
    signal.signal(signal.SIGINT,  shutdown)
    signal.signal(signal.SIGTERM, shutdown)

    # Keep main thread alive; monitor child processes
    while True:
        # If backend exits unexpectedly, report it
        if backend_proc.poll() is not None and backend_proc.returncode != 0:
            log("BACKEND", RED, f"Backend exited with code {backend_proc.returncode}!")
            shutdown()

        # If frontend exits unexpectedly
        if frontend_proc.poll() is not None and frontend_proc.returncode not in (None, 0):
            log("FRONTEND", RED, f"Frontend exited with code {frontend_proc.returncode}!")
            shutdown()

        time.sleep(2)


if __name__ == "__main__":
    main()
