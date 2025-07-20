from __future__ import annotations

import datetime as _dt
import json
import os
import tempfile
from pathlib import Path
from typing import Optional, Tuple
from io import BytesIO

import streamlit as st
from gtts import gTTS
from googletrans import Translator as _GoogleTranslator, LANGUAGES as GOOGLE_LANGUAGES
import speech_recognition as sr

HISTORY_FILE = Path.home() / ".translator_history.json"
SUPPORTED_PROVIDERS = ("Google", "OpenAI")
LANGUAGE_OPTIONS = {v.title(): k for k, v in GOOGLE_LANGUAGES.items()}
TTS_LANG_MAP = {
    "zh-cn": "zh",
    "zh-tw": "zh-TW",
    "pt-br": "pt",
    "en-us": "en",
    "en-gb": "en",
    "es": "es",
    "fr": "fr",
    "de": "de",
    "hi": "hi",
    "ja": "ja",
    "ko": "ko",
    "ru": "ru",
    "it": "it",
    "ar": "ar"
}

class GoogleProvider:
    def __init__(self):
        self.translator = _GoogleTranslator()

    def translate(self, text: str, dest_lang: str) -> Tuple[str, str]:
        result = self.translator.translate(text, src='auto', dest=dest_lang)
        return result.src, result.text


class OpenAIProvider:
    def __init__(self, api_key: str, model: str = "gpt-4o"):
        import openai
        openai.api_key = api_key
        self.model = model
        self.client = openai

    def translate(self, text: str, dest_lang: str) -> Tuple[str, str]:
        prompt = (
            f"Translate the following text to {dest_lang}. Do not explain, just reply with the translated text:\n\n{text}"
        )
        response = self.client.ChatCompletion.create(
            model=self.model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.2,
        )
        translated = response.choices[0].message.content.strip()
        return "auto", translated


def speak_text_bytes(text: str, lang: str = "en") -> Optional[BytesIO]:
    try:
        tts_lang = TTS_LANG_MAP.get(lang.lower(), lang[:2])
        tts = gTTS(text=text, lang=tts_lang)
        audio_bytes = BytesIO()
        tts.write_to_fp(audio_bytes)
        audio_bytes.seek(0)
        return audio_bytes
    except Exception:
        return None

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

def listen_microphone(lang_code: str = "en") -> str:
    recognizer = sr.Recognizer()
    try:
        with sr.Microphone() as source:
            st.info("🎙️ Listening... Speak now")
            recognizer.adjust_for_ambient_noise(source)
            audio = recognizer.listen(source, timeout=5)
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
    except Exception as e:
        return f"Microphone error: {e}"

st.set_page_config(page_title="AI Translator", page_icon="🌍", layout="centered")
st.title("🌍 AI Language Translator ")

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

st.subheader("Text or Mic Input")

col1, col2 = st.columns([2, 1])

with col1:
    input_text = st.text_area("Text to translate", value="")

with col2:
    if st.button("🎤 Speak"):
        mic_text = listen_microphone()
        if mic_text:
            st.success("Mic captured:")
            st.write(mic_text)
            input_text = mic_text
        else:
            st.error("Could not understand audio.")

lang_display_names = sorted(LANGUAGE_OPTIONS.keys())
selected_lang_display = st.selectbox("Target Language", lang_display_names, index=lang_display_names.index("English"))
target_lang = LANGUAGE_OPTIONS[selected_lang_display]

if st.button("Translate"):
    if not input_text.strip():
        st.error("Please enter or speak text to translate.")
    elif not target_lang.strip():
        st.error("Please select a target language.")
    else:
        with st.spinner("Translating..."):
            try:
                src_lang, translated_text = translator.translate(input_text, target_lang)
                st.success("Translation complete!")
                st.write(f"**Detected language:** `{src_lang}`")
                st.write("**Translated text:**")
                st.write(translated_text)
                save_history(src_lang, target_lang, input_text, translated_text, provider)
                audio_bytes = speak_text_bytes(translated_text, lang=target_lang)
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

st.caption("© 2025 AI Translator – Accessible Speech & Text Translator built with Python.")
st.caption("Author:- Pranay Nigam and Abhishek Maurya")
