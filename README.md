# 🌍 AI Language Translator: Accessible, Multi-Functional Speech & Translation App

AI Language Translator is an intuitive and inclusive application designed to assist people — especially those who are mute or visually impaired — in breaking language barriers using advanced translation, speech recognition, and speech synthesis technologies. Built using Python, Streamlit, Google Translate API, OpenAI GPT, and gTTS, this tool delivers real-time multilingual support with a user-friendly interface.

---

## 🚀 Features

### 1. **Multilingual Translation (Text & Speech)**

- Translate typed text or recognized speech into over **100+ languages**.
- Auto-detects source language.
- Supports both **Google Translate** and **OpenAI GPT (context-aware)**.
- Output translated speech in real-time.

### 2. **Speech-to-Text (STT)**

- 🎤 Record speech directly using the system microphone.
- 📂 Upload `.wav` audio files for transcription.
- Converts voice input into editable text for translation.

### 3. **Text-to-Speech (TTS)**

- Synthesizes translated text into speech using `gTTS`.
- Auto-plays the result for immediate listening.
- Option to disable autoplay for custom control.

### 4. **Translation History**

- Saves all translations with timestamps, source/target languages, and providers.
- Easily review and reuse previous translations.

---

## ⚙️ How It Works

### 1. **Installation**

Make sure you have **Python 3.8+** installed.

Install the dependencies using pip:

```bash
pip install streamlit gTTS googletrans==4.0.0-rc1 langdetect openai SpeechRecognition sounddevice scipy
```
### 2. **Running the Application**
Run the app using Streamlit:

```bash
Copy
Edit
streamlit run advanced_translator.py
```


