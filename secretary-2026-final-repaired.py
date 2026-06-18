import tkinter as tk
from tkinter import filedialog
from bs4 import BeautifulSoup
import cv2
import time
import requests
from datetime import datetime
import os
import sys
import pyttsx3
from ollama import Client
import io
import PyPDF2
import speech_recognition as sr
from youtube_transcript_api import YouTubeTranscriptApi
from docx2pdf import convert

MEMORY_FILE = "secretary_learning_log.txt"

# --- Initialization & Connection Shield ---
os.environ['no_proxy'] = '*'

try:
    client = Client(host='http://localhost:11434')
    client.list()  # Test the connection immediately
    print("✅ Connection to Ollama Successful")
except:
    # If localhost fails, fall back to the IP
    client = Client(host='http://127.0.0.1:11434')
    print("⚠️ Localhost failed, using IP address instead.")

# Global State
speaker_on = True
chat_history = []  # Memory storage
MEMORY_LIMIT = 10  # Sliding window size (last 10 messages)

def get_timestamp():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

def speak(text):
    if not speaker_on: return
    engine = pyttsx3.init()
    voices = engine.getProperty('voices')
    
    # Find an English voice specifically
    for voice in voices:
        if "EN" in voice.id.upper() or "ZIRA" in voice.id.upper() or "DAVID" in voice.id.upper():
            engine.setProperty('voice', voice.id)
            break
    
    engine.setProperty('rate', 170) 
    engine.say(text)
    engine.runAndWait()

# --- Tools ---
def handle_text():
    global chat_history
    print("\n--- [T] TEXT QUERY MODE ---")
    query = input("Ask Secretary: ")
    if not query.strip(): return

    chat_history.append({'role': 'user', 'content': query})

    try:
        context = chat_history[-MEMORY_LIMIT:]
        response = client.chat(model='llama3.2', messages=context)
        answer = response['message']['content']
        
        print(f"\nSecretary: {answer}")
        chat_history.append({'role': 'assistant', 'content': answer})
        speak(answer)
    except Exception as e:
        print(f"❌ Connection Error: {e}")

def handle_image_folder():
    root = tk.Tk()
    root.withdraw() 
    root.attributes('-topmost', True) 
    
    file_path = filedialog.askopenfilename(
        title="Select Medical Document or Image",
        filetypes=[("Image files", "*.jpg *.jpeg *.png *.bmp")]
    )
    root.destroy() 

    if not file_path:
        print("Selection cancelled.")
        return

    print(f"🧐 Analyzing: {os.path.basename(file_path)}...")

    try:
        with open(file_path, 'rb') as img_file:
            response = client.generate(
                model='llava',
                prompt="You are a medical secretary. Describe this image accurately, focusing on medications, dosages, or key medical data. Keep it concise.",
                images=[img_file.read()]
            )
            
            description = response['response']
            print(f"\nSecretary's Analysis:\n{description}")
            chat_history.append({'role': 'user', 'content': f"Context from image ({os.path.basename(file_path)}): {description}"})
            speak(description)
    except Exception as e:
        print(f"❌ Image Analysis Error: {e}")

def handle_web_summary():
    url = input("\n[Web Summary] Paste URL: ")
    if not url.startswith('http'):
        print("⚠️ Invalid URL. Must start with http or https.")
        return

    print("🌐 Fetching content...")
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code != 200:
            print(f"❌ Site blocked us. Status: {response.status_code}")
            return

        soup = BeautifulSoup(response.content, 'html.parser')
        for tag in soup(["script", "style", "nav", "footer", "header"]):
            tag.decompose()
            
        text = soup.get_text(separator=' ', strip=True)
        clean_text = text[:3000]

        prompt = f"Summarize the following webpage content in 3-5 sentences for a medical secretary:\n\n{clean_text}"
        chat_history.append({'role': 'user', 'content': prompt})
        res = client.chat(model='llama3.2', messages=chat_history[-MEMORY_LIMIT:])
        
        answer = res['message']['content']
        print(f"\nSecretary's Web Summary:\n{answer}")
        chat_history.append({'role': 'assistant', 'content': answer})
        speak(answer)
    except Exception as e:
        print(f"❌ Web Error: {e}")

def handle_webcam():
    print("\n📸 Opening Webcam... Press SPACE to capture, ESC to exit.")
    cam = cv2.VideoCapture(0)
    
    while True:
        ret, frame = cam.read()
        if not ret:
            print("❌ Failed to grab frame.")
            break
        
        cv2.imshow("Secretary 2026 - Webcam (Space=Capture)", frame)
        key = cv2.waitKey(1)
        if key % 256 == 27:  # ESC
            print("Closing webcam...")
            break
        elif key % 256 == 32:  # SPACE
            img_name = "webcam_capture.png"
            cv2.imwrite(img_name, frame)
            print(f"✅ Image saved as {img_name}")
            cam.release()
            cv2.destroyAllWindows()
            process_captured_image(img_name)
            break

    cam.release()
    cv2.destroyAllWindows()

def process_captured_image(path):
    print("🧐 Analyzing webcam capture...")
    try:
        with open(path, 'rb') as img_file:
            response = client.generate(
                model='llava',
                prompt="You are a medical secretary. Describe this webcam image, focusing on medicine labels or documents.",
                images=[img_file.read()]
            )
            description = response['response']
            print(f"\nSecretary's Analysis:\n{description}")
            chat_history.append({'role': 'user', 'content': f"Context from webcam: {description}"})
            speak(description)
    except Exception as e:
        print(f"❌ Analysis Error: {e}")

def handle_image_url():
    url = input("\n[U] Paste DIRECT Image URL (must end in .jpg, .png): ")
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36',
        'Accept': 'image/avif,image/webp,image/apng,image/svg+xml,image/*,*/*;q=0.8'
    }

    print("🌐 Downloading image...")
    try:
        response = requests.get(url, headers=headers, timeout=15, stream=True)
        if response.status_code == 200:
            content_type = response.headers.get('content-type', '')
            if 'image' not in content_type:
                print(f"⚠️ Error: The URL provided is a {content_type}, not an image file.")
                return

            img_bytes = response.content
            print("🧐 Analyzing with LLaVA...")
            res = client.generate(
                model='llava',
                prompt="Describe this medical image. What medications or labels do you see?",
                images=[img_bytes]
            )
            
            description = res['response']
            print(f"\nSecretary: {description}")
            chat_history.append({'role': 'user', 'content': f"Context from URL image: {description}"})
            speak(description)
        else:
            print(f"❌ Blocked! Status: {response.status_code}.")
    except Exception as e:
        print(f"❌ Analysis Error: {e}")

def process_chat(model_name, prompt_type="General"):
    start_time = time.time() 
    try:
        response = client.chat(model=model_name, messages=chat_history[-10:])
        ans = response['message']['content']
        elapsed = round(time.time() - start_time, 2)
        print(f"\nSecretary ({elapsed}s) | {prompt_type}: {ans}")
        
        chat_history.append({'role': 'assistant', 'content': ans})
        with open("secretary_permanent_log.txt", "a", encoding="utf-8") as f:
            f.write(f"\n[{get_timestamp()}] Task: {prompt_type} | Speed: {elapsed}s\nOutput: {ans[:200]}...\n")
            
        if speaker_on: speak(ans)
    except Exception as e:
        print(f"❌ Error in process_chat: {e}")

def handle_mic():
    recognizer = sr.Recognizer()
    with sr.Microphone() as source:
        print("\n🎤 Listening... (Speak now)")
        try:
            audio = recognizer.listen(source, timeout=5)
            text = recognizer.recognize_google(audio)
            print(f"🗨️ You said: {text}")
            return text
        except Exception:
            print("⚠️ Could not hear you clearly.")
            return None

def handle_document():
    root = tk.Tk(); root.withdraw(); root.attributes('-topmost', True)
    path = filedialog.askopenfilename(filetypes=[("Documents", "*.pdf *.docx *.doc")])
    root.destroy()
    if not path: return

    path = os.path.abspath(path)

    if path.lower().endswith(('.docx', '.doc')):
        print(f"📄 Word detected. Converting to PDF...")
        pdf_path = os.path.splitext(path)[0] + ".pdf"
        try:
            convert(path, pdf_path)
            path = pdf_path 
            print("✅ Conversion successful.")
        except Exception as e:
            print(f"❌ Conversion Error: {e}")
            return

    try:
        print(f"📖 Analyzing: {os.path.basename(path)}...")
        reader = PyPDF2.PdfReader(path)
        text = ""
        num_pages = min(len(reader.pages), 10)
        for i in range(num_pages):
            text += reader.pages[i].extract_text()
        
        chat_history.append({'role': 'user', 'content': f"Context from document: {text[:4000]}"})
        process_chat("llama3.2", "Document Analysis")
    except Exception as e:
        print(f"❌ PDF Reading Error: {e}")

def handle_youtube():
    url = input("\n[Y] Paste YouTube URL: ")
    try:
        if "v=" in url: video_id = url.split("v=")[1].split("&")[0]
        elif "youtu.be/" in url: video_id = url.split("youtu.be/")[1].split("?")[0]
        else: video_id = url

        print(f"📺 Fetching transcript for ID: {video_id}...")
        transcript = YouTubeTranscriptApi.get_transcript(video_id)
        text = " ".join([t['text'] for t in transcript])
        print(f"✅ Success! ({len(text)} characters found)")
        
        prompt = f"Summarize this YouTube video transcript:\n\n{text[:4000]}"
        chat_history.append({'role': 'user', 'content': prompt})
        process_chat("llama3.2", "YouTube Summary")
    except Exception as e:
        print(f"❌ YouTube Error: {e}")

def handle_quit():
    print("\n📝 Generating Daily Summary Report...")
    if chat_history:
        try:
            summary_prompt = "Summarize all our activities today into a 5-sentence professional report for my records."
            chat_history.append({'role': 'user', 'content': summary_prompt})
            res = client.chat(model='llama3.2', messages=chat_history)
            report = res['message']['content']
            
            with open("Daily_Report.txt", "w", encoding="utf-8") as f:
                f.write(f"SECRETARY 2026 - DAILY REPORT\nDate: {time.strftime('%Y-%m-%d')}\n")
                f.write("-" * 30 + "\n")
                f.write(report)
            print("✅ Daily_Report.txt has been saved. Goodbye!")
        except Exception as e:
            print(f"⚠️ Could not generate report text: {e}")
    else:
        print("No activity to report. Goodbye!")
    sys.exit()

def load_permanent_memory():
    global chat_history
    if os.path.exists(MEMORY_FILE):
        try:
            with open(MEMORY_FILE, "r", encoding="utf-8") as f:
                lines = f.readlines()
                past_context = "".join(lines[-20:])
                chat_history.append({
                    'role': 'system', 
                    'content': f"Here is context from previous sessions: {past_context}"
                })
            print("📜 Past memory loaded successfully.")
        except Exception as e:
            print(f"⚠️ Could not load past memory: {e}")

def morning_briefing():
    print("🌅 Initializing Secretary 2026...")
    hour = datetime.now().hour
    greeting = "Good morning" if hour < 12 else "Good afternoon"
    if hour > 17: greeting = "Good evening"
    
    msg = f"{greeting}. Your local brain is online and ready for 2026."
    
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

# --- Master Execution Routine ---
def start():
    load_permanent_memory()
    morning_briefing()
    run_secretary()

def run_secretary():
    global speaker_on
    while True:
        status = "ON" if speaker_on else "OFF"
        print(f"\n{'='*40}")
        print(f"🤖 SECRETARY 2026 | Speaker: {status}")
        print(f"{'='*40}")
        print("[T] Text Query      [W] Web Summary (URL)")
        print("[I] Image (Folder)  [K] Image (Webcam)")
        print("[U] Image (URL)     [S] Toggle Speaker")
        print("[Y] Youtube (URL)   [P] Word/PDF Read")
        print("[Q] Quit")            
        
        choice = input("\nSelection: ").lower()

        if choice == 't':
            handle_text()
        elif choice == 'w':
            handle_web_summary()
        elif choice == 'i':
            handle_image_folder()
        elif choice == 'k':
            handle_webcam()
        elif choice == 'u':
            handle_image_url()
        elif choice == 's':
            speaker_on = not speaker_on
            print(f"📢 Speaker toggled {'ON' if speaker_on else 'OFF'}")
        elif choice == 'y':
            handle_youtube()
        elif choice == 'p':
            handle_document()
        elif choice == 'q':
            handle_quit()
        else:
            print("⚠️ Invalid selection.")

if __name__ == "__main__":
    try:
        client.list()
        print("✅ Connection to Ollama Successful")
    except Exception as e:
        print(f"❌ Actual Connection Error: {e}")
        sys.exit()

    try:
        start()
    except Exception as e:
        print(f"💥 Secretary App Crash: {e}")
