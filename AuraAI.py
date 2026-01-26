import customtkinter as ctk
import subprocess
import ollama
import threading
import os
import re

class AuraGUI(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Zane AI Terminal Helper")
        self.geometry("900x650")
        
        # Determine OS for the prompt
        self.os_type = "Windows PowerShell" if os.name == 'nt' else "Linux/Mac Bash"
        self.history = [{"role": "system", "content": f"You are a terminal expert on {self.os_type}. Translate English to shell commands. Output ONLY the raw command. No markdown, no backticks, no explanations."}]

        # --- UI Components ---
        self.output_area = ctk.CTkTextbox(self, font=("Roboto Mono", 14))
        self.output_area.pack(padx=20, pady=20, fill="both", expand=True)

        self.input_field = ctk.CTkEntry(self, placeholder_text="Ask to do something...", height=40)
        self.input_field.pack(padx=20, pady=(0, 10), fill="x")
        self.input_field.bind("<Return>", lambda e: self.process_input())

        # ADDED: Execute Button for safety
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

    def ai_logic(self, user_text):
        try:
            self.history.append({"role": "user", "content": user_text})
            # Change 'llama3' to your specific model (e.g., 'llama3.2')
            response = ollama.chat(model='llama3.2', messages=self.history)
            raw_content = response['message']['content'].strip()
            
            # Regex to remove backticks if the AI includes them
            clean_command = re.sub(r'^`+|`+$', '', raw_content)
            
            self.pending_command = clean_command
            self.log(f"Aura Suggests: {clean_command}")
            
            # Enable button only if it looks like a command
            self.exec_button.configure(state="normal")
                
        except Exception as e:
            self.log(f"Error: {str(e)}")

    def run_shell_task(self):
        """Actually executes the command when the user clicks the button."""
        try:
            self.log(f"Executing: {self.pending_command}...")
            result = subprocess.run(self.pending_command, shell=True, capture_output=True, text=True)
            output = result.stdout if result.returncode == 0 else result.stderr
            self.log(f"--- Output ---\n{output}")
            self.exec_button.configure(state="disabled") # Reset
        except Exception as e:
            self.log(f"System Error: {e}")

if __name__ == "__main__":
    app = AuraGUI()
    app.mainloop() # This line keeps the window alive!