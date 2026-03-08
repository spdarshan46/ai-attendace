# ==========================================
#  VOICE.PY — AI Voice Assistant
#
#  Offline TTS using pyttsx3 (no API key).
#  Install:  pip install pyttsx3
#
#  Speaks in a background thread so the
#  GUI / camera never freezes.
# ==========================================

import threading

_engine = None
_lock   = threading.Lock()


def _get_engine():
    """Lazy-init pyttsx3 engine (one per process)."""
    global _engine
    if _engine is None:
        try:
            import pyttsx3
            _engine = pyttsx3.init("sapi5")
            # Rate: 150 wpm feels natural (default ~200 is too fast)
            _engine.setProperty("rate", 155)
            # Volume: 0.0 – 1.0
            _engine.setProperty("volume", 0.95)
            # Pick first available voice (usually Microsoft Zira / David on Windows)
            voices = _engine.getProperty("voices")
            if voices:
                _engine.setProperty("voice", voices[0].id)
        except Exception as e:
            print(f"[voice] pyttsx3 init failed: {e}")
            _engine = None
    return _engine


def speak(text: str, blocking: bool = False):
    def _run():
        try:
            import pyttsx3
            engine = pyttsx3.init("sapi5")
            engine.setProperty("rate", 155)
            engine.setProperty("volume", 0.95)

            voices = engine.getProperty("voices")
            if voices:
                engine.setProperty("voice", voices[0].id)

            engine.say(text)
            engine.runAndWait()
            engine.stop()

        except Exception as e:
            print(f"[voice] speak error: {e}")

    if blocking:
        _run()
    else:
        t = threading.Thread(target=_run, daemon=True)
        t.start()

# ── Pre-built message helpers ─────────────────────────────────────────────────
def greet_login(name: str):
    speak(f"Welcome, {name}. Attendance marked successfully. Have a productive day.")

def greet_logout(name: str):
    speak(f"Goodbye, {name}. Logout recorded. See you tomorrow.")

def say_error(msg: str = "Face not recognised. Please try again."):
    speak(msg)

def say_spoof():
    speak("Spoof attempt detected. Please move slightly and try again.")

def say_already_in(name: str):
    speak(f"{name}, you are already logged in today.")

def say_already_out(name: str):
    speak(f"{name}, you have already logged out today.")

def say_scanning():
    speak("Scanning. Please look at the camera.")

def say_identified(name: str, confidence: float):
    speak(f"Face identified. {name}, {confidence:.0f} percent confidence. "
          f"Press Enter to confirm.")


# ── Quick test ────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    speak("AI Face Attendance System is ready.", blocking=True)
    greet_login("Darshan")