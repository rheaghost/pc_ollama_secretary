//install libs needed below
//worked on 2025/12/31 add or modify according to your preferences
  

import os, sys, time, requests, cv2, pyttsx3, PyPDF2, tkinter as tk

from datetime import datetime

from tkinter import filedialog

from bs4 import BeautifulSoup

from ollama import Client

from docx2pdf import convert

import youtube_transcript_api

​

# --- Initialization ---

client = Client(host='http://localhost:11434')

chat_history = []

speaker_on = True

MEMORY_FILE = "secretary_learning_log.txt"

​

def get_timestamp():

    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

​

def speak(text):

    if not speaker_on: return

    engine = pyttsx3.init()

    voices = engine.getProperty('voices')

    for v in voices:

        if "EN" in v.id.upper(): engine.setProperty('voice', v.id); break

    engine.setProperty('rate', 170)

    engine.say(text)

    engine.runAndWait()

​

# --- Core Brain ---

def process_chat(model_name, prompt_type="General"):

    start_time = time.time()

    try:

        res = client.chat(model=model_name, messages=chat_history[-10:])

        ans = res['message']['content']

        elapsed = round(time.time() - start_time, 2)

        

        print(f"\nSecretary ({elapsed}s) | {prompt_type}: {ans}")

        chat_history.append({'role': 'assistant', 'content': ans})

        

        with open(MEMORY_FILE, "a", encoding="utf-8") as f:

            f.write(f"[{get_timestamp()}] {prompt_type}: {ans[:100]}...\n")

        

        if speaker_on: speak(ans)

    except Exception as e:

        print(f" Error: {e}")

​

# --- Tools ---

def handle_document():

    root = tk.Tk(); root.withdraw(); root.attributes('-topmost', True)

    path = filedialog.askopenfilename(filetypes=[("Docs", "*.pdf *.docx *.doc")])

    root.destroy()

    if not path: return

    path = os.path.abspath(path)

​

    if path.lower().endswith(('.docx', '.doc')):

        print("📄 Word detected. Converting...")

        pdf_path = os.path.splitext(path)[0] + ".pdf"

        convert(path, pdf_path)

        path = pdf_path

​

    reader = PyPDF2.PdfReader(path)

    text = " ".join([p.extract_text() for p in reader.pages[:10]])

    chat_history.append({'role': 'user', 'content': f"Context: {text[:4000]}"})

    process_chat("llama3.2", "Document Analysis")

​

def handle_youtube():

    url = input("\n[Y] YouTube URL: ")

    try:

        v_id = url.split("v=")[1].split("&")[0] if "v=" in url else url.split("/")[-1]

        print(f"📺 Fetching transcript for {v_id}...")

        # Direct call to module to avoid 'Type Object' error

        ts = youtube_transcript_api.YouTubeTranscriptApi.get_transcript(v_id)

        text = " ".join([t['text'] for t in ts])

        chat_history.append({'role': 'user', 'content': f"Summarize: {text[:4000]}"})

        process_chat("llama3.2", "YouTube Summary")

    except Exception as e:

        print(f"❌ YouTube Error: {e}")

​

def morning_briefing():

    print("🌅 Initializing Secretary 2026...")

    

    # 1. Prepare the Greeting

    hour = datetime.now().hour

    greeting = "Good morning" if hour < 12 else "Good afternoon"

    if hour > 17: greeting = "Good evening"

    

    msg = f"{greeting}. Your local brain is online and ready for 2026."

    

    # 2. Try to remember the last session

    if os.path.exists(MEMORY_FILE):

        try:

            with open(MEMORY_FILE, "r", encoding="utf-8") as f:

                lines = f.readlines()

                if lines:

                    last_action = lines[-1].strip()

                    msg += f" I have restored your memory. Your last recorded action was: {last_action[:50]}."

        except:

            pass

            

    print(f"🤖 {msg}")

    speak(msg)

​

# --- Updated Start Function ---

def start():

    morning_briefing() # This runs once at launch

    while True:

        # ... rest of your menu logic ...

​

​

​

def handle_quit():

    ts = datetime.now().strftime("%Y%m%d_%H%M")

    with open(f"Report_{ts}.txt", "w", encoding="utf-8") as f:

        f.write(f"Final Report {get_timestamp()}\n" + "="*20 + "\n")

        for m in chat_history: f.write(f"{m['role'].upper()}: {m['content']}\n\n")

    print("✅ Report Saved. Goodbye!")

    sys.exit()

​

# --- Main Loop ---

def start():

    morning_briefing() # This runs once at launch

    while True:

        print(f"\n--- 🤖 SECRETARY 2026 | {get_timestamp()} ---")

        print("[T] Text [M] Mic [P] Doc/PDF [Y] YouTube [Q] Quit")

        c = input("Choice: ").lower()

        if c == 't':

            chat_history.append({'role': 'user', 'content': input("Ask: ")})

            process_chat("llama3.2")

        elif c == 'p': handle_document()

        elif c == 'y': handle_youtube()

        elif c == 'q': handle_quit()

​

if __name__ == "__main__":

    try:

        client.list()

        print("Connection Successful")

        start()

    except Exception as e:

        print(f"Crash: {e}")

​
