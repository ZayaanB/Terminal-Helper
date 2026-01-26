import customtkinter as ctk
import subprocess
import ollama
import threading
import os

class AuraGUI(ctk.CTk):
    def __init__(self):
        super().__init__()

        # --- Window Setup ---
        self.title("Aura AI Terminal")
        self.geometry("900x600")
        ctk.set_appearance_mode("dark")
        
        # --- Context State ---
        self.history = [{"role": "system", "content": f"You are a terminal expert on {os.name}. Translate English to shell commands. Output ONLY the raw command. If conversation, be brief."}]

        # --- Layout ---
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # Terminal Output Area
        self.output_area = ctk.CTkTextbox(self, font=("Roboto Mono", 14), fg_color="#1a1a1a", text_color="#d1d1d1")
        self.output_area.grid(row=0, column=0, padx=20, pady=20, sticky="nsew")
        self.output_area.insert("0.0", "--- Aura AI Shell Activated ---\nAsk me to do something (e.g., 'List all files' or 'Create a python script')\n\n")

        # Input Area
        self.input_field = ctk.CTkEntry(self, placeholder_text="Enter English command...", font=("Inter", 14), height=40)
        self.input_field.grid(row=1, column=0, padx=20, pady=(0, 20), sticky="ew")
        self.input_field.bind("<Return>", lambda e: self.process_input())

    def log(self, text, color_tag=None):
        self.output_area.insert("end", text + "\n")
        self.output_area.see("end")

    def process_input(self):
        user_text = self.input_field.get()
        if not user_text: return
        
        self.log(f"\nUser: {user_text}")
        self.input_field.delete(0, 'end')
        
        # Run AI logic in a thread to keep GUI responsive
        threading.Thread(target=self.ai_logic, args=(user_text,), daemon=True).start()

    def ai_logic(self, user_text):
        try:
            # 1. Get AI response
            self.history.append({"role": "user", "content": user_text})
            response = ollama.chat(model='llama3', messages=self.history)
            ai_command = response['message']['content'].strip()

            # 2. Safety/Execution
            if ai_command and not any(x in ai_command.lower() for x in ["hello", "sorry", "i am"]):
                self.log(f"AI Suggestion: {ai_command}")
                # For safety, we'll auto-execute but you can add a button here
                result = subprocess.run(ai_command, shell=True, capture_output=True, text=True)
                output = result.stdout if result.returncode == 0 else result.stderr
                self.log(f"Output:\n{output}")
                self.history.append({"role": "assistant", "content": f"Command output: {output}"})
            else:
                self.log(f"Aura: {ai_command}")
                
        except Exception as e:
            self.log(f"Error: {str(e)}")

if __name__ == "__main__":
    app = AuraGUI()
    app.mainloop()