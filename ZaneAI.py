import customtkinter as ctk
import subprocess
import threading
import os
import re
import time
from dotenv import load_dotenv

load_dotenv()

try:
    from openai import OpenAI
except ImportError:
    OpenAI = None


def _get_env(key: str, default: str = "") -> str:
    val = os.getenv(key, default)
    if val and val.startswith("__") and val.endswith("__"):
        return ""
    return val or default


class ZaneGUI(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Zane AI Terminal Helper")
        self.geometry("900x650")
        
        # Determine OS for the prompt
        self.os_type = "Windows PowerShell" if os.name == 'nt' else "Linux/Mac Bash"
        self.history = [{"role": "system", "content": f"You are a terminal expert on {self.os_type}. Return PowerShell commands on Windows. Output ONLY the raw command. No markdown, no backticks, no explanations."}]
        self.client = None
        self.model = _get_env("OPENAI_MODEL", "gpt-4o-mini")
        self._init_client()

        # --- UI Components ---
        self.output_area = ctk.CTkTextbox(self, font=("Roboto Mono", 14))
        self.output_area.pack(padx=20, pady=20, fill="both", expand=True)

        self.input_field = ctk.CTkEntry(self, placeholder_text="Ask to do something...", height=40)
        self.input_field.pack(padx=20, pady=(0, 10), fill="x")
        self.input_field.bind("<Return>", lambda e: self.process_input())

        # Execute Button for safety
        self.pending_command = ""
        self.exec_button = ctk.CTkButton(self, text="Execute Suggested Command", state="disabled", command=self.run_shell_task, fg_color="green")
        self.exec_button.pack(padx=20, pady=(0, 20))

    def log(self, text):
        self.output_area.insert("end", text + "\n")
        self.output_area.see("end")

    def process_input(self):
        user_text = self.input_field.get()
        if not user_text: return
        self.log(f"\nUser: {user_text}")
        self.input_field.delete(0, 'end')
        threading.Thread(target=self.ai_logic, args=(user_text,), daemon=True).start()

    def _init_client(self):
        api_key = _get_env("OPENAI_API_KEY") or _get_env("OPENROUTER_API_KEY")
        base_url = _get_env("OPENAI_BASE_URL")
        if not base_url and "/" in self.model:
            base_url = "https://openrouter.ai/api/v1"
        if api_key and OpenAI:
            kwargs = {"api_key": api_key}
            if base_url:
                kwargs["base_url"] = base_url
            self.client = OpenAI(**kwargs)

    def ai_logic(self, user_text):
        if not self.client:
            self.log("Error: No API key. Add OPENROUTER_API_KEY or OPENAI_API_KEY to .env")
            return
        try:
            self.history.append({"role": "user", "content": user_text})
            raw_content = self._call_ai_with_retry()
            clean_command = re.sub(r'^`+|`+$', '', raw_content)
            self.pending_command = clean_command
            self.log(f"Zane Suggests: {clean_command}")
            self.exec_button.configure(state="normal")
        except Exception as e:
            self.log(f"Error: {str(e)}")

    def _call_ai_with_retry(self, max_retries=3):
        for attempt in range(max_retries + 1):
            try:
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=self.history,
                    temperature=0.3,
                )
                return response.choices[0].message.content.strip()
            except Exception as e:
                if "429" in str(e) or "rate" in str(e).lower():
                    if attempt < max_retries:
                        wait = 2 ** (attempt + 1)
                        self.log(f"Rate limited. Retrying in {wait}s...")
                        time.sleep(wait)
                    else:
                        raise RuntimeError(
                            "Rate limit exceeded. Wait a minute and try again, or add your key at "
                            "https://openrouter.ai/settings/integrations for higher limits."
                        ) from e
                else:
                    raise

    def run_shell_task(self):
        """Actually executes the command when the user clicks the button."""
        try:
            self.log(f"Executing: {self.pending_command}...")
            if os.name == "nt":
                result = subprocess.run(
                    ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", self.pending_command],
                    capture_output=True, text=True, timeout=300
                )
            else:
                result = subprocess.run(self.pending_command, shell=True, capture_output=True, text=True, timeout=300)
            output = result.stdout if result.returncode == 0 else result.stderr
            self.log(f"--- Output ---\n{output}")
            self.exec_button.configure(state="disabled")  # Reset
        except Exception as e:
            self.log(f"System Error: {e}")

if __name__ == "__main__":
    app = ZaneGUI()
    app.mainloop()
