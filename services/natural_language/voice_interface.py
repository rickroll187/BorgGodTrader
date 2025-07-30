import speech_recognition as sr

class VoiceInterface:
    """
    Voice to text for natural bot control.
    """
    def __init__(self):
        self.recognizer = sr.Recognizer()
        self.mic = sr.Microphone()

    def listen_and_recognize(self):
        with self.mic as source:
            print("Listening for command...")
            audio = self.recognizer.listen(source)
        text = self.recognizer.recognize_google(audio)
        print(f"Recognized: {text}")
        return text