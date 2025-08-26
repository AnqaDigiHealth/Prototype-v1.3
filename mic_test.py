import speech_recognition as sr

recognizer = sr.Recognizer()

with sr.Microphone() as source:
    print("🎙️ Say something...")
    audio = recognizer.listen(source)

    try:
        text = recognizer.recognize_google(audio)
        print("📝 You said:", text)
    except sr.UnknownValueError:
        print("😕 Sorry, couldn't understand the audio.")
    except sr.RequestError as e:
        print("❌ Could not request results; check your internet. Error:", e)
