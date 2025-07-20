from __future__ import annotations

import datetime as _dt
import json
import os
import tempfile
from pathlib import Path
from typing import Optional, Tuple

import langdetect
import streamlit as st
from gtts import gTTS
from googletrans import Translator as _GoogleTranslator, LANGUAGES as GOOGLE_LANGUAGES
from langdetect import detect
import speech_recognition as sr
import sounddevice as sd
import numpy as np
import scipy.io.wavfile as wav

# ---------- Constants ----------
HISTORY_FILE = Path.home() / ".translator_history.json"
SUPPORTED_PROVIDERS = ("Google", "OpenAI")
UPLOAD_DIR = Path(tempfile.gettempdir()) / "translator_uploads"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

# ---------- Helper Classes ----------
class GoogleProvider:
    def __init__(self):
        self.translator = _GoogleTranslator()

    def translate(self, text: str, dest_lang: str) -> Tuple[str, str]:
        src_lang = detect(text)
        if dest_lang not in GOOGLE_LANGUAGES:
            raise ValueError(f"Language not supported: {dest_lang}")
        result = self.translator.translate(text, src=src_lang, dest=dest_lang)
        return src_lang, result.text


class OpenAIProvider:
    def __init__(self, api_key: str, model: str = "gpt-4o"):
        import openai
        openai.api_key = api_key
        self.model = model
        self.client = openai

    def translate(self, text: str, dest_lang: str) -> Tuple[str, str]:
        src_lang = detect(text)
        prompt = (
            f"Translate the following text from {src_lang} to {dest_lang}. "
            "Do not explain, just reply with the translated text.\n\n"
            f"{text}"
        )
        response = self.client.ChatCompletion.create(
            model=self.model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.2,
        )
        translated = response.choices[0].message.content.strip()
        return src_lang, translated


# ---------- Services ----------
def speak_text(text: str, lang: str = "en") -> bytes:
    try:
        tts = gTTS(text=text, lang=lang)
        with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as tmp:
            tts.save(tmp.name)
            tmp.seek(0)
            audio_bytes = tmp.read()
        os.unlink(tmp.name)
        return audio_bytes
    except Exception:
        return b""


def save_history(src_lang: str, dest_lang: str, src_text: str, dest_text: str, provider: str):
    HISTORY_FILE.touch(exist_ok=True)
    entry = {
        "timestamp": _dt.datetime.utcnow().isoformat() + "Z",
        "src_lang": src_lang,
        "dest_lang": dest_lang,
        "src_text": src_text,
        "dest_text": dest_text,
        "provider": provider,
    }
    try:
        content = HISTORY_FILE.read_text(encoding="utf-8")
        data = json.loads(content) if content else []
    except (json.JSONDecodeError, OSError):
        data = []

    data.append(entry)
    HISTORY_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def load_history(limit: int = 20):
    if not HISTORY_FILE.exists():
        return []
    try:
        content = HISTORY_FILE.read_text(encoding="utf-8")
        return json.loads(content)[-limit:]
    except (json.JSONDecodeError, OSError):
        return []


def transcribe_audio(file_path: str, lang_code: str = "en") -> str:
    recognizer = sr.Recognizer()
    with sr.AudioFile(file_path) as source:
        audio = recognizer.record(source)
        try:
            lang_map = {
                "en": "en-US", "hi": "hi-IN", "es": "es-ES", "fr": "fr-FR", "de": "de-DE",
                "zh": "zh-CN", "ja": "ja-JP", "ko": "ko-KR", "it": "it-IT", "ru": "ru-RU"
            }
            recog_lang = lang_map.get(lang_code.lower(), "en-US")
            return recognizer.recognize_google(audio, language=recog_lang)
        except sr.UnknownValueError:
            return ""
        except sr.RequestError as e:
            return f"Speech recognition failed: {e}"


def record_microphone(duration: int = 5, samplerate: int = 16000) -> Optional[str]:
    try:
        st.info("🎙️ Recording... Please speak clearly.")
        audio = sd.rec(int(duration * samplerate), samplerate=samplerate, channels=1, dtype='int16')
        sd.wait()
        file_path = str(UPLOAD_DIR / "mic_input.wav")
        wav.write(file_path, samplerate, audio)
        return file_path
    except Exception as e:
        st.error(f"Microphone recording failed: {e}")
        return None


# ---------- Streamlit UI ----------
st.set_page_config(page_title="AI Translator", page_icon="🌍", layout="centered")
st.title("🌍 AI Language Translator (Accessible & Advanced)")

with st.sidebar:
    st.header("Settings")
    provider = st.selectbox("Translation Engine", SUPPORTED_PROVIDERS)
    if provider == "OpenAI":
        openai_key = st.text_input("OpenAI API Key", value=os.getenv("OPENAI_API_KEY", ""), type="password")
        if not openai_key:
            st.warning("OpenAI key required for OpenAI provider.")
    else:
        openai_key = ""

    st.markdown("### Output")
    auto_play_audio = st.checkbox("🔊 Auto‑play translated speech", value=True)

if provider == "Google":
    translator = GoogleProvider()
elif provider == "OpenAI":
    translator = OpenAIProvider(api_key=openai_key)

st.subheader("Enter, Upload, or Speak Text")
input_text = st.text_area("Text to translate", value="")
target_lang = st.text_input("Target language code (e.g., en, es, fr, hi)", value="en")

# Audio Upload Option
uploaded_audio = st.file_uploader("Upload a speech file (WAV format)", type=["wav"])
if uploaded_audio:
    file_path = str(UPLOAD_DIR / uploaded_audio.name)
    with open(file_path, "wb") as f:
        f.write(uploaded_audio.read())
    transcribed = transcribe_audio(file_path, target_lang)
    if transcribed:
        st.success("Audio transcribed successfully!")
        st.text_area("Recognized speech:", transcribed, key="recognized")
        input_text = transcribed
    else:
        st.error("Could not transcribe audio.")

# Microphone Recording Option
if st.button("🎤 Record from Microphone"):
    mic_path = record_microphone(duration=5)
    if mic_path:
        transcribed = transcribe_audio(mic_path, target_lang)
        if transcribed:
            st.success("Microphone input transcribed successfully!")
            st.text_area("Recognized speech:", transcribed, key="mic_text")
            input_text = transcribed
        else:
            st.error("Could not transcribe microphone input.")

if st.button("Translate"):
    if not input_text.strip():
        st.error("Please enter, upload, or record text.")
    elif not target_lang.strip():
        st.error("Please enter a target language code.")
    else:
        with st.spinner("Translating..."):
            try:
                src_lang, translated_text = translator.translate(input_text, target_lang)
                st.success("Translation complete!")
                st.write(f"**Detected language:** `{src_lang}`")
                st.write("**Translated text:**")
                st.write(translated_text)
                save_history(src_lang, target_lang, input_text, translated_text, provider)
                audio_bytes = speak_text(translated_text, lang=target_lang)
                if audio_bytes and auto_play_audio:
                    st.audio(audio_bytes, format="audio/mp3", start_time=0)
            except Exception as e:
                st.error(f"Translation failed: {e}")

with st.expander("📜 Translation History"):
    history = load_history()
    if not history:
        st.info("No history yet.")
    else:
        for item in reversed(history):
            st.markdown(f"*{item['timestamp']}* &nbsp; **{item['src_lang']} ➔ {item['dest_lang']}** (*{item['provider']}*)")
            st.write(f"**Input:** {item['src_text']}")
            st.write(f"**Output:** {item['dest_text']}")
            st.markdown("---")

st.caption("© 2025 AI Translator – Built for accessibility and real-world impact 🧠💬")

"""
An AI‑powered language translator with these enhanced features:

• Translate between 100+ languages using:
    – Google Translate
    – OpenAI GPT (context‑aware, requires API key)

• Upload and transcribe audio (WAV) or speak directly via microphone – supports visually impaired users

• Text‑to-speech output (auto-play enabled by default, can be toggled off)

• Translation history (stored locally in JSON)

• Streamlit web UI (Run via: streamlit run advanced_translator.py)

• Accessible design: no typing needed if speech input is used

Tested on Python 3.11.7.

Authors: Pranay Nigam & Abhishek Maurya (Enhanced by ChatGPT) – July 2025
"""
