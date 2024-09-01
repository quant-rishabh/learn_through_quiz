import speech_recognition as sr

def test_microphone():
    recognizer = sr.Recognizer()

    with sr.Microphone() as mic:
        print("Adjusting for ambient noise... Please wait.")
        recognizer.adjust_for_ambient_noise(mic, duration=1)
        print("Listening... Please speak into the microphone.")

        # Listen to the microphone input
        audio = recognizer.listen(mic)

        try:
            # Recognize speech using Google Web API
            text = recognizer.recognize_google(audio)
            print(f"Recognized text: {text}")
        except sr.UnknownValueError:
            print("Could not understand the audio.")
        except sr.RequestError as e:
            print(f"Could not request results from Google Speech Recognition service; {e}")

if __name__ == "__main__":
    test_microphone()
