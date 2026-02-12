"""
Terminal Helper AI - A local AI agent that suggests and executes terminal commands.
Uses natural language; provides commands with descriptions and prerequisites.
Executes only with user permission. Includes program update scanner.
"""

import customtkinter as ctk
import subprocess
import threading
import os
import re
import json
import sys
import time
# Load environment variables
from dotenv import load_dotenv
load_dotenv()

# OpenAI client
try:
    from openai import OpenAI
except ImportError:
    OpenAI = None


def get_env(key: str, default: str = "") -> str:
    """Get env var, replacing placeholder __...__ with empty."""
    val = os.getenv(key, default)
    if val and val.startswith("__") and val.endswith("__"):
        return ""
    return val or default


class UpdateScanner:
    """Scans for outdated packages on Windows or Linux."""

    def __init__(self):
        self.is_windows = os.name == "nt"

    def get_outdated_packages(self) -> list[dict]:
        """Returns list of {source, name, current, available}."""
        results = []

        if self.is_windows:
            # Windows: winget (columns: Name, Id, Version, Available)
            try:
                proc = subprocess.run(
                    ["winget", "list", "--outdated"],
                    capture_output=True, text=True, timeout=30
                )
                if proc.returncode == 0:
                    for line in proc.stdout.splitlines()[3:]:
                        parts = [p.strip() for p in re.split(r"\s{2,}", line) if p.strip()]
                        if len(parts) >= 3:
                            # Name, Id, Version, Available (Id needed for upgrade)
                            results.append({
                                "source": "winget",
                                "name": parts[1] if len(parts) > 1 else parts[0],
                                "id": parts[1] if len(parts) > 1 else parts[0],
                                "current": parts[2] if len(parts) > 2 else "?",
                                "available": parts[3] if len(parts) > 3 else "?",
                            })
            except (subprocess.TimeoutExpired, FileNotFoundError):
                pass

            # pip (Windows)
            try:
                proc = subprocess.run(
                    [sys.executable, "-m", "pip", "list", "--outdated"],
                    capture_output=True, text=True, timeout=15
                )
                if proc.returncode == 0:
                    for line in proc.stdout.splitlines()[2:]:
                        parts = line.split()
                        if len(parts) >= 3:
                            results.append({
                                "source": "pip",
                                "name": parts[0],
                                "id": parts[0],
                                "current": parts[1],
                                "available": parts[2],
                            })
            except Exception:
                pass

            # npm (if package.json in common locations)
            try:
                proc = subprocess.run(
                    ["npm", "outdated", "--json"],
                    capture_output=True, text=True, timeout=15, cwd=os.getcwd()
                )
                if proc.returncode == 0 and proc.stdout.strip():
                    data = json.loads(proc.stdout)
                    for name, info in data.items():
                        if isinstance(info, dict) and "current" in info and "latest" in info:
                            results.append({
                                "source": "npm",
                                "name": name,
                                "id": name,
                                "current": info.get("current", "?"),
                                "available": info.get("latest", "?"),
                            })
            except Exception:
                pass
        else:
            # Linux: apt
            try:
                proc = subprocess.run(
                    ["apt", "list", "--upgradable"],
                    capture_output=True, text=True, timeout=15
                )
                if proc.returncode == 0:
                    for line in proc.stdout.splitlines()[1:]:
                        if "/" in line:
                            name_ver = line.split("/")[0]
                            if " " in name_ver:
                                name, current = name_ver.rsplit(" ", 1)
                            else:
                                name, current = name_ver, "?"
                            results.append({
                                "source": "apt",
                                "name": name,
                                "id": name,
                                "current": current,
                                "available": "?",
                            })
            except (subprocess.TimeoutExpired, FileNotFoundError):
                pass

            # pip (Linux)
            try:
                proc = subprocess.run(
                    [sys.executable, "-m", "pip", "list", "--outdated"],
                    capture_output=True, text=True, timeout=15
                )
                if proc.returncode == 0:
                    for line in proc.stdout.splitlines()[2:]:
                        parts = line.split()
                        if len(parts) >= 3:
                            results.append({
                                "source": "pip",
                                "name": parts[0],
                                "id": parts[0],
                                "current": parts[1],
                                "available": parts[2],
                            })
            except Exception:
                pass

        return results

    def run_update(self, source: str, pkg_id: str) -> tuple[bool, str]:
        """Run update for a package. Returns (success, output)."""
        try:
            if source == "winget":
                proc = subprocess.run(
                    ["winget", "upgrade", "--id", pkg_id, "--accept-package-agreements", "--accept-source-agreements"],
                    capture_output=True, text=True, timeout=120
                )
            elif source == "pip":
                proc = subprocess.run(
                    [sys.executable, "-m", "pip", "install", "--upgrade", pkg_id],
                    capture_output=True, text=True, timeout=120
                )
            elif source == "apt":
                proc = subprocess.run(
                    ["sudo", "apt", "install", "--only-upgrade", "-y", pkg_id],
                    capture_output=True, text=True, timeout=120
                )
            elif source == "npm":
                proc = subprocess.run(
                    ["npm", "install", f"{pkg_id}@latest"],
                    capture_output=True, text=True, timeout=120, cwd=os.getcwd()
                )
            else:
                return False, f"Unknown source: {source}"

            out = proc.stdout or proc.stderr or ""
            return proc.returncode == 0, out
        except Exception as e:
            return False, str(e)


class TerminalHelperApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Terminal Helper AI")
        self.geometry("950x720")
        self.minsize(700, 500)

        # Theme
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")

        self.os_type = "Windows PowerShell" if os.name == "nt" else "Linux/Mac Bash"
        self.client = None
        self.model = get_env("OPENAI_MODEL", "gpt-4o-mini")
        self._init_openai()

        self.history = [
            {"role": "system", "content": self._system_prompt()}
        ]
        self.pending_commands: list[dict] = []
        self.pending_updates: list[dict] = []
        self.update_scanner = UpdateScanner()

        self._build_ui()

    def _init_openai(self):
        api_key = get_env("OPENROUTER_API_KEY") or get_env("OPENAI_API_KEY")
        base_url = get_env("OPENAI_BASE_URL")
        # Use OpenRouter when OPENROUTER_API_KEY is set, model has provider prefix, or base_url indicates OpenRouter
        if not base_url and (get_env("OPENROUTER_API_KEY") or "/" in self.model):
            base_url = "https://openrouter.ai/api/v1"
        if api_key and OpenAI:
            kwargs = {"api_key": api_key}
            if base_url:
                kwargs["base_url"] = base_url
            self.client = OpenAI(**kwargs)
        else:
            self.client = None

    def _system_prompt(self) -> str:
        return f"""You are a terminal expert on {self.os_type}. The user asks in natural language.
Respond with valid JSON only, no other text. Use this exact structure:
{{
  "description": "Plain-language summary",
  "prerequisites": ["What user needs first"],
  "commands": ["command1", "command2"]
}}
- description: Short, simple words. No jargon. E.g. "Downloads and installs Ollama" or "Lists files in folder"
- prerequisites: Simple items, e.g. "Internet" or "Admin rights". Use empty [] if none.
- commands: Shell commands for {self.os_type}. On Windows use PowerShell only.
Output ONLY the JSON object, no markdown code blocks, no explanations."""

    def _build_ui(self):
        # Main container
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        # Header
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.grid(row=0, column=0, padx=20, pady=(20, 10), sticky="ew")
        header.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(header, text="Terminal Helper AI", font=("Segoe UI", 24, "bold")).grid(row=0, column=0, sticky="w")
        ctk.CTkLabel(header, text=self.os_type, font=("Segoe UI", 12), text_color="gray").grid(row=1, column=0, sticky="w")

        # Tabs
        self.tabview = ctk.CTkTabview(self)
        self.tabview.grid(row=1, column=0, padx=20, pady=(0, 10), sticky="nsew")
        self.tabview.add("Commands")
        self.tabview.add("Updates")

        # --- Commands tab ---
        cmd_frame = self.tabview.tab("Commands")
        cmd_frame.grid_columnconfigure(0, weight=1)
        cmd_frame.grid_rowconfigure(1, weight=1)

        self.output_area = ctk.CTkTextbox(cmd_frame, font=("Consolas", 13), wrap="word")
        self.output_area.grid(row=1, column=0, padx=0, pady=(0, 10), sticky="nsew")

        input_row = ctk.CTkFrame(cmd_frame, fg_color="transparent")
        input_row.grid(row=2, column=0, sticky="ew")
        input_row.grid_columnconfigure(0, weight=1)
        self.input_field = ctk.CTkEntry(input_row, placeholder_text="Ask in natural language (e.g. 'list files in current folder')...", height=40)
        self.input_field.grid(row=0, column=0, padx=(0, 10), pady=(0, 10), sticky="ew")
        self.input_field.bind("<Return>", lambda e: self._process_input())

        ctk.CTkButton(input_row, text="Ask", width=80, command=self._process_input).grid(row=0, column=1, pady=(0, 10))

        self.exec_button = ctk.CTkButton(cmd_frame, text="Execute Command(s)", state="disabled", command=self._run_commands, fg_color="#2d7d46", hover_color="#246b3a")
        self.exec_button.grid(row=3, column=0, pady=(0, 20))

        # --- Updates tab ---
        up_frame = self.tabview.tab("Updates")
        up_frame.grid_columnconfigure(0, weight=1)
        up_frame.grid_rowconfigure(1, weight=1)

        up_btns = ctk.CTkFrame(up_frame, fg_color="transparent")
        up_btns.grid(row=0, column=0, sticky="ew")
        up_btns.grid_columnconfigure(0, weight=1)
        ctk.CTkButton(up_btns, text="Scan for Updates", command=self._scan_updates).grid(row=0, column=0, padx=(0, 10))
        self.update_all_btn = ctk.CTkButton(up_btns, text="Update All", state="disabled", command=self._run_updates, fg_color="#2d7d46")
        self.update_all_btn.grid(row=0, column=1)

        self.updates_listbox = ctk.CTkTextbox(up_frame, font=("Consolas", 12), wrap="word")
        self.updates_listbox.grid(row=1, column=0, padx=0, pady=10, sticky="nsew")

        self._log("Ready. Enter a task in natural language, or switch to Updates to scan for outdated packages.")
        if not self.client:
            self._log("\n⚠ Add your OPENROUTER_API_KEY (or OPENAI_API_KEY) to .env to use the AI agent.")

    def _log(self, text: str):
        self.output_area.insert("end", text + "\n")
        self.output_area.see("end")

    def _log_updates(self, text: str):
        self.updates_listbox.insert("end", text + "\n")
        self.updates_listbox.see("end")

    def _process_input(self):
        user_text = self.input_field.get().strip()
        if not user_text:
            return
        self._log(f"\nYou: {user_text}")
        self.input_field.delete(0, "end")
        self.exec_button.configure(state="disabled")
        threading.Thread(target=self._ai_logic, args=(user_text,), daemon=True).start()

    def _ai_logic(self, user_text: str):
        if not self.client:
            self._log("Error: No API key. Add OPENROUTER_API_KEY or OPENAI_API_KEY to .env")
            return
        try:
            self.history.append({"role": "user", "content": user_text})
            raw = self._call_ai_with_retry()
            # Strip markdown code blocks if present
            raw = re.sub(r"^```(?:json)?\s*", "", raw)
            raw = re.sub(r"\s*```$", "", raw)
            data = json.loads(raw)

            desc = data.get("description", "No description.")
            prereqs = data.get("prerequisites", [])
            commands = data.get("commands", [])

            if not commands:
                self._log("No commands suggested.")
                return

            self.pending_commands = [{"cmd": c, "desc": desc} for c in commands]
            self._log(f"\n📋 {desc}")
            if prereqs:
                self._log("Prerequisites: " + "; ".join(prereqs))
            for i, c in enumerate(commands, 1):
                self._log(f"  {i}. {c}")
            self._log("")
            self.exec_button.configure(state="normal")
        except json.JSONDecodeError as e:
            self._log(f"Failed to parse AI response: {e}")
        except Exception as e:
            self._log(f"Error: {e}")

    def _call_ai_with_retry(self, max_retries: int = 3) -> str:
        """Call AI API with retry on 429."""
        last_exc = None
        for attempt in range(max_retries + 1):
            try:
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=self.history,
                    temperature=0.3,
                )
                return response.choices[0].message.content.strip()
            except Exception as e:
                last_exc = e
                err_str = str(e).lower()
                if "429" in err_str or "rate" in err_str:
                    if attempt < max_retries:
                        wait = 2 ** (attempt + 1)
                        self._log(f"⏳ Rate limited. Retrying in {wait}s...")
                        time.sleep(wait)
                    else:
                        msg = self._format_rate_limit_error(e)
                        raise RuntimeError(msg) from e
                else:
                    raise
        raise last_exc

    def _format_rate_limit_error(self, e: Exception) -> str:
        """Extract friendly message from rate limit error."""
        s = str(e)
        if "rate-limited" in s or "rate limit" in s:
            return (
                "Rate limit exceeded. The free model is temporarily overloaded. "
                "Wait a minute and try again, or add your own provider key at "
                "https://openrouter.ai/settings/integrations for higher limits."
            )
        return s

    def _run_commands(self):
        if not self.pending_commands:
            return
        for item in self.pending_commands:
            cmd = item["cmd"]
            self._log(f"▶ Executing: {cmd}")
            try:
                result = self._run_shell_command(cmd)
                out = result.stdout or result.stderr or "(no output)"
                self._log(out)
            except Exception as e:
                self._log(f"Error: {e}")
        self.pending_commands = []
        self.exec_button.configure(state="disabled")

    def _run_shell_command(self, cmd: str) -> subprocess.CompletedProcess:
        """Run command in PowerShell on Windows, shell on Linux/Mac."""
        if os.name == "nt":
            return subprocess.run(
                ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", cmd],
                capture_output=True, text=True, cwd=os.getcwd(), timeout=300
            )
        return subprocess.run(cmd, shell=True, capture_output=True, text=True, cwd=os.getcwd(), timeout=300)

    def _scan_updates(self):
        self.updates_listbox.delete("1.0", "end")
        self._log_updates("Scanning for outdated packages...\n")
        threading.Thread(target=self._do_scan, daemon=True).start()

    def _do_scan(self):
        try:
            pkgs = self.update_scanner.get_outdated_packages()
            self.pending_updates = pkgs
            self.after(0, lambda: self._show_updates(pkgs))
        except Exception as e:
            self.after(0, lambda: self._log_updates(f"Error: {e}"))

    def _show_updates(self, pkgs: list):
        self.updates_listbox.delete("1.0", "end")
        if not pkgs:
            self._log_updates("No outdated packages found.")
            return
        self._log_updates(f"Found {len(pkgs)} outdated package(s):\n")
        for p in pkgs:
            self._log_updates(f"  [{p['source']}] {p['name']}  {p['current']} → {p['available']}")
        self._log_updates("\nClick 'Update All' to apply updates (with your permission).")
        self.update_all_btn.configure(state="normal")

    def _run_updates(self):
        if not self.pending_updates:
            return
        self.update_all_btn.configure(state="disabled")
        self._log_updates("\n--- Updating packages ---\n")
        pkgs = list(self.pending_updates)
        self.pending_updates = []
        threading.Thread(target=self._do_run_updates, args=(pkgs,), daemon=True).start()

    def _do_run_updates(self, pkgs: list):
        """Run updates in background thread to avoid blocking the UI."""
        try:
            for p in pkgs:
                self.after(0, lambda p=p: self._log_updates(f"Updating {p['name']} ({p['source']})..."))
                ok, out = self.update_scanner.run_update(p["source"], p.get("id", p["name"]))
                status = "✓" if ok else "✗"
                summary = self._summarize_update_output(p["source"], ok, out)
                self.after(0, lambda s=status, sm=summary: self._log_updates(f"  {s} {sm}"))
        except Exception as e:
            self.after(0, lambda: self._log_updates(f"Error: {e}"))
        finally:
            self.after(0, self._finish_updates)

    def _summarize_update_output(self, source: str, success: bool, out: str) -> str:
        """Show a clear summary instead of raw verbose output."""
        if success:
            out_lower = out.lower()
            if "requirement already satisfied" in out_lower or "already up-to-date" in out_lower:
                return "Already up to date"
            if "successfully installed" in out_lower:
                return "Installed successfully"
            if "defaulting to user installation" in out_lower:
                return "Updated (user install)"
            return "Success"
        return out.strip()[:300] if out else "Failed"

    def _finish_updates(self):
        self.update_all_btn.configure(state="disabled")
        self._log_updates("\nDone.")


def main():
    app = TerminalHelperApp()
    app.mainloop()


if __name__ == "__main__":
    main()
