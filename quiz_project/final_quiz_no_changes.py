import json
import os
import time
import random
from datetime import datetime
from rapidfuzz import fuzz
from PIL import Image
from tabulate import tabulate
import speech_recognition as sr
import pyttsx3
from gtts import gTTS
import pygame


# Initialize pygame mixer for sound playback with error handling
def init_mixer():
    try:
        pygame.mixer.init()
    except pygame.error as e:
        print(f"Error initializing mixer: {e}")


def play_sound(sound_file):
    """Plays a sound to notify the user that the system is ready to listen."""
    if not pygame.mixer.get_init():  # Check if the mixer is initialized
        init_mixer()

    pygame.mixer.music.load(sound_file)
    pygame.mixer.music.play()
    while pygame.mixer.music.get_busy():
        pygame.time.Clock().tick(5)  # Ensures the sound completes before moving on
def play_audio_with_pygame(file_path):
    """Plays the audio file using pygame to avoid opening external applications."""
    pygame.mixer.init()
    pygame.mixer.music.load(file_path)
    pygame.mixer.music.play()
    while pygame.mixer.music.get_busy():
        pygame.time.Clock().tick(5)  # Keeps sound playing until finished

    # Ensure pygame finishes using the file before deletion
    pygame.mixer.music.stop()
    pygame.mixer.quit()

    # Remove the mp3 file after playing to prevent permission issues
    if os.path.exists(file_path):
        try:
            os.remove(file_path)
        except Exception as e:
            print(f"Error deleting file {file_path}: {e}")


# Speak text using gTTS and play it using pygame
# Speak text using gTTS and play it using pygame
def speak_text_gtts(text, language='en'):
    """Converts text to speech using gTTS and plays it using pygame."""
    try:
        # Use a unique filename for each audio file to avoid conflicts
        filename = f"speech_{int(time.time())}.mp3"
        tts = gTTS(text=text, lang=language)
        tts.save(filename)
        play_audio_with_pygame(filename)
    except Exception as e:
        print(f"Error with gTTS: {e}")

# Speak text in Hindi
def speak_text(text):
    try:
        speak_text_gtts(text, language='en')  # Set language to 'hi' for Hindi
    except Exception as e:
        print(f"Error with gTTS: {e}")

# Function to handle speech recognition
def listen_to_user():
    recognizer = sr.Recognizer()
    mic = sr.Microphone()

    with mic as source:
        # Minimize the time for ambient noise adjustment to speed up listening
        recognizer.adjust_for_ambient_noise(source, duration=0.5)  # Reduced duration for faster adjustment

        # Play sound to alert the user to start speaking
        play_sound("beep.mp3")  # Ensure you have a beep.mp3 sound file in your project directory

        print("-------")

        try:
            # Listen with a phrase time limit to stop after you've finished talking
            audio = recognizer.listen(source, timeout=5, phrase_time_limit=4)  # Timeout after 5 seconds of silence
        except sr.WaitTimeoutError:
            print("Timeout: No speech detected.")
            return ""  # Return an empty string if no input was detected

    try:
        # Convert speech to text using Google's Speech API
        user_input = recognizer.recognize_google(audio, language="en")
        print(f"You said: {user_input}")
        return user_input.lower()
    except sr.UnknownValueError:
        print("Sorry, I could not understand what you said.")
        return ""  # Return empty string if speech is unintelligible
    except sr.RequestError as e:
        print(f"Could not request results from Google Speech Recognition service; {e}")
        return "Error with Google API."
    except Exception as e:
        print(f"An error occurred: {e}")
        return "Something went wrong."


class QuizMaster:
    def __init__(self, config_file):
        self.load_config(config_file)
        self.data = {}
        self.results = []

    def load_config(self, config_file):
        """Load the configuration from the specified JSON file."""
        with open(config_file, 'r') as f:
            self.config = json.load(f)

        # Set up paths and other config options
        self.learning_section_directory = self.config['learning_section_directory']
        self.image_directory = self.config['image_directory']
        self.practice_attempts = self.config['practice_attempts']
        self.results_directory = self.config['results_directory']
        self.fuzzy_search_threshold = self.config.get('fuzzy_search_threshold', 80)  # Default to 80 if not set

        # Ensure the directories exist
        os.makedirs(self.results_directory, exist_ok=True)

    def show_test_results(self, category, lesson, topic):
        """Displays all test results in a sorted tabular manner based on time_taken_minutes."""
        lesson = lesson.replace(".json", "").strip()
        category = category.strip()
        topic = topic.strip()

        # Path to the result file
        result_file_name = os.path.join(self.results_directory, category, lesson, topic, "result.json")

        # Check if the result file exists
        if not os.path.exists(result_file_name):
            print(f"No results found for {category}/{lesson}/{topic}")
            return

        # Load the results from the file
        try:
            with open(result_file_name, 'r', encoding='utf-8') as result_file:
                all_results = json.load(result_file)
        except json.JSONDecodeError:
            print(f"Error reading the result file {result_file_name}")
            return

        # Sort results by time_taken_minutes
        all_results_sorted = sorted(all_results, key=lambda x: x['time_taken_minutes'])

        # ANSI color codes
        RED = '\033[91m'
        RESET = '\033[0m'

        # Prepare the headers with red color
        headers = [
            f"{RED}Date{RESET}",
            f"{RED}Time Taken (minutes){RESET}",
            f"{RED}Correct Answers{RESET}",
            f"{RED}Wrong Answers{RESET}",
            f"{RED}Wrong Questions with Answers{RESET}"
        ]

        # Prepare the data for tabulation
        table_data = [
            [
                result['date_time'],
                result['time_taken_minutes'],
                result['correct_answers'],
                result['wrong_answers'],
                # Use .get() to provide a default empty list if 'wrong_questions_with_answers' key is missing
                "\n".join([f"{idx + 1}. {q['question']} -> {q['correct_answer']}" for idx, q in
                           enumerate(result.get('wrong_questions_with_answers', []))])
            ]
            for result in all_results_sorted
        ]

        # Display the results in a tabular format with red headers
        print(tabulate(table_data, headers, tablefmt="grid"))

    def load_learning_data(self):
        """Load the persistent learning data from file, initialize if not present."""
        learning_data_file = "learning_data.json"

        # If the file doesn't exist, initialize and save learning data
        if not os.path.exists(learning_data_file):
            learning_data = self.initialize_learning_data_from_json_files()
            self.save_learning_data(learning_data)
            return learning_data

        # If the file exists, load the data
        with open(learning_data_file, 'r') as f:
            learning_data = json.load(f)

        # Update learning data with any new topics
        self.update_learning_data_with_new_topics(learning_data)
        return learning_data

    def initialize_learning_data_from_json_files(self):
        """Initialize the learning data from all available JSON files."""
        learning_data = {}

        # Loop through all JSON files in categorized folders
        for category in os.listdir(self.learning_section_directory):
            category_path = os.path.join(self.learning_section_directory, category)
            if os.path.isdir(category_path):
                learning_data[category] = {}
                for json_file in self.list_json_files_in_category(category_path):
                    self.load_data(os.path.splitext(os.path.basename(json_file))[0], category_path)
                    lesson = os.path.splitext(os.path.basename(json_file))[0]
                    learning_data[category][lesson] = {topic: 0 for topic in self.data.keys()}  # Initialize all topics with 0

        return learning_data

    def list_json_files_in_category(self, category_path):
        """List all JSON files in a given category folder."""
        return [os.path.join(category_path, f) for f in os.listdir(category_path) if f.endswith('.json')]

    def update_learning_data(self, category, lesson, topic):
        """Update the learning count for a given topic in a given category and lesson."""
        # Load existing learning data
        learning_data = self.load_learning_data()

        # Strip any leading/trailing spaces from category, lesson, and topic
        category = category.strip()
        lesson = lesson.strip()
        topic = topic.strip()

        # Ensure category exists in learning data
        if category not in learning_data:
            learning_data[category] = {}

        # Ensure lesson exists in the category
        if lesson not in learning_data[category]:
            learning_data[category][lesson] = {}

        # Ensure topic exists and increment the count
        if topic not in learning_data[category][lesson]:
            learning_data[category][lesson][topic] = 0
        learning_data[category][lesson][topic] += 1

        # Save the updated learning data
        self.save_learning_data(learning_data)

    def update_learning_data_with_new_topics(self, learning_data):
        """Update the learning data to add new topics from JSON files, without modifying existing data."""
        # Strip any leading/trailing spaces from category, lesson, and topic

        for category in os.listdir(self.learning_section_directory):
            category = category.strip()
            category_path = os.path.join(self.learning_section_directory, category)
            if os.path.isdir(category_path):
                if category not in learning_data:
                    learning_data[category] = {}
                for json_file in self.list_json_files_in_category(category_path):
                    self.load_data(os.path.splitext(os.path.basename(json_file))[0], category_path)
                    lesson = os.path.splitext(os.path.basename(json_file))[0]
                    lesson = lesson.strip()
                    if lesson not in learning_data[category]:
                        learning_data[category][lesson] = {}
                    for topic in self.data.keys():
                        if topic not in learning_data[category][lesson]:
                            topic = topic.strip()
                            learning_data[category][lesson][topic] = 0

        self.save_learning_data(learning_data)

    def save_learning_data(self, learning_data):
        """Save the learning data to file."""
        learning_data_file = "learning_data.json"
        with open(learning_data_file, 'w') as f:
            json.dump(learning_data, f, indent=4)

    def load_data(self, lesson, category_path):
        """Loads the selected JSON file's content from its category."""
        data_file_path = os.path.join(category_path, lesson + '.json')

        # Open the file using UTF-8 encoding to handle special characters
        with open(data_file_path, 'r', encoding='utf-8') as f:
            self.data = json.load(f)
        self.data_file = lesson  # Store the relative path (e.g., "Science/Physics")

    def display_learning_data(self):
        """Display the hierarchical learning data in a tree format with color."""
        learning_data = self.load_learning_data()

        # ANSI color codes
        colors = {
            'category': '\033[96m',  # Cyan for categories
            'lesson': '\033[92m',  # Green for lessons
            'topic': '\033[93m',  # Yellow for topics
            'reset': '\033[0m'  # Reset color
        }

        for category, lessons in learning_data.items():
            print(f"{colors['category']}{category}/{colors['reset']}")
            for lesson, topics in lessons.items():
                print(f"{colors['lesson']}├── Lesson: {lesson}{colors['reset']}")
                for topic, count in topics.items():
                    print(f"{colors['topic']}│   ├── Topic: {topic} ({count} tests taken){colors['reset']}")
            print("")

    def list_json_files(self):
        """Recursively lists all JSON files in the learning section directory."""
        json_files = []
        for root, dirs, files in os.walk(self.learning_section_directory):
            for file in files:
                if file.endswith('.json'):
                    relative_path = os.path.relpath(os.path.join(root, file), self.learning_section_directory)
                    json_file = relative_path.replace('.json', '').replace('\\', '/')
                    json_files.append(json_file)
        return sorted(json_files)

    def show_image(self, image_name, category, lesson, topic):
        """Displays the image associated with the question, dynamically building the path."""
        # Remove .json extension from lesson name if present
        lesson = lesson.replace(".json", "")  # Ensure no .json extension is used

        # Adjust the path to reflect the correct folder structure:
        # images/<category>/<lesson>/<topic>/<image_name>
        image_path = os.path.join(self.image_directory, category, lesson, topic, image_name)

        # Convert to absolute path for better file resolution
        image_path = os.path.abspath(image_path)

        # Debugging: Print the full image path
        print(f"Looking for image at: {image_path}")

        if os.path.exists(image_path):
            img = Image.open(image_path)
            img.show()
            print(f"Image {image_name} displayed successfully.")
        else:
            print(f"Image {image_name} not found in directory {image_path}.")

    def print_red(self, text):
        """Prints the text in red color."""
        red_code = "\033[91m"
        reset_code = "\033[0m"
        print(f"{red_code}{text}{reset_code}")

    def handle_question(self, question_data, category, lesson, topic):
        """Handles the process of asking a question and checking the answer."""
        correct = True
        image_shown = False

        # Check if the question contains an image to show at the start
        if "type" in question_data and question_data["type"] == "image" and "image" in question_data:
            self.show_image(question_data["image"], category, lesson, topic)
            image_shown = True  # Mark that the image has been shown

        # Iterate over all key-value pairs in question_data
        for key, value in question_data.items():
            # Skip "type" and "image" keys when displaying the question (these are metadata)
            if key == "type" or key == "image":
                continue

            # Display the question
            self.print_red(f"\nQuestion: {key}")

            # Handle the answer
            correct = self.handle_single_answer_question(key, value)

            if not correct:
                correct_answer = value.split('@')[0]
                print(f"\nYour answer was incorrect. The correct answer is: {correct_answer}")
                print("Let's practice the correct answer.")
                self.practice_wrong_answer(correct_answer, key)
                # Store the wrong question and the correct answer
                self.results.append({"question": key, "result": "wrong", "correct_answer": correct_answer})
            else:
                # Append the result with an empty correct_answer for correct responses
                self.results.append({"question": key, "result": "correct", "correct_answer": ""})

        # If there was no image at the start but the question has an image, show it now
        if not image_shown and "image" in question_data:
            self.show_image(question_data["image"], category, lesson, topic)

    def handle_single_answer_question(self, question, answer):
        """Handles single-answer questions."""
        return self.ask_and_check(question, answer)

    def ask_and_check(self, prompt, answer):
        parts = answer.split('@')
        correct_answers = [ans.strip().lower() for ans in parts[0].split(';')]
        additional_info = parts[1].strip() if len(parts) > 1 else ""
        remaining_answers = set(correct_answers)

        while remaining_answers:
            user_input = input(": ").strip().lower()
            if user_input == "skip":
                print("Skipped this question.")
                return False

            matched_answers = [ans for ans in remaining_answers if fuzz.ratio(user_input, ans) >= self.fuzzy_search_threshold]
            if matched_answers:
                for matched in matched_answers:
                    print(f"Correct! '{matched}' matched.")
                    remaining_answers.remove(matched)
            else:
                print("Incorrect. Try again.")
                return False

        if additional_info:
            print(f"Information: {additional_info}")
        return True

    def practice_wrong_answer(self, correct_answer, prompt):
        for attempt in range(self.practice_attempts):
            user_input = input(f"Practice {attempt + 1}/{self.practice_attempts} - {prompt}: ").strip().lower()
            if fuzz.ratio(user_input, correct_answer.lower()) >= self.fuzzy_search_threshold:
                print("Correct!")
            else:
                print(f"Incorrect. The correct answer is: {correct_answer}. Please try again.")
        print("Practice completed.")

    def record_result(self, category, lesson, topic, time_taken):
        """Save the result in a structured directory format and append new results to the same file."""
        # Remove `.json` from lesson name if it's present and strip any leading/trailing spaces
        lesson = lesson.replace(".json", "").strip()
        category = category.strip()
        topic = topic.strip()

        # Create the directory structure if it doesn't exist
        result_dir = os.path.join(self.results_directory, category, lesson, topic)
        os.makedirs(result_dir, exist_ok=True)

        # Collect wrong questions and their correct answers
        wrong_questions_with_answers = [
            {"question": r['question'], "correct_answer": r['correct_answer']}
            for r in self.results if r['result'] == 'wrong'
        ]

        # File path for the result JSON file
        result_file_name = os.path.join(result_dir, "result.json")

        # Prepare result data to save
        new_result_data = {
            "date_time": datetime.now().strftime("%H:%M:%S %d-%m-%Y"),
            "time_taken_minutes": round(time_taken, 2),
            "correct_answers": len([r for r in self.results if r['result'] == 'correct']),
            "wrong_answers": len([r for r in self.results if r['result'] == 'wrong']),
            "wrong_questions_with_answers": wrong_questions_with_answers
            # Add the wrong questions and correct answers here
        }

        # Check if the file exists; if it does, load existing data, else create a new list
        if os.path.exists(result_file_name):
            with open(result_file_name, 'r', encoding='utf-8') as result_file:
                all_results = json.load(result_file)
        else:
            all_results = []

        # Append the new result to the list
        all_results.append(new_result_data)

        # Save the updated list of results back to the file
        with open(result_file_name, 'w', encoding='utf-8') as result_file:
            json.dump(all_results, result_file, indent=4)

        print(f"Results recorded in {result_file_name}")

    def run_quiz(self, topic, mode):
        """Runs the quiz or learn mode for the selected topic."""
        if topic not in self.data:
            print(f"Topic '{topic}' not found.")
            return

        # Get the list of questions for the given topic
        questions = self.data[topic]

        self.results = []

        # Shuffle the list of questions directly
        random.shuffle(questions)

        start_time = time.time()

        if mode == "test" or mode == "speak":
            for q in questions:
                if mode == "test":
                    # For test mode, ask via text input
                    self.handle_question(q, self.current_category, self.current_lesson, topic)
                elif mode == "speak":
                    # For speak mode, ask via speech
                    self.handle_question_speak(q, self.current_category, self.current_lesson, topic)

            end_time = time.time()
            time_taken = (end_time - start_time) / 60

            # Strip the '.json' from current_lesson
            self.current_lesson = self.current_lesson.replace(".json", "").strip()

            # Record the result after finishing the quiz
            self.record_result(self.current_category, self.current_lesson, topic, time_taken)

            # Now call update_learning_data to increment the count
            self.update_learning_data(self.current_category, self.current_lesson, topic)

            # Show test results immediately after completing the test
            self.show_test_results(self.current_category, self.current_lesson, topic)

        elif mode == "learn":
            self.display_learning_mode(questions, topic)

    def handle_question_speak(self, question_data, category, lesson, topic):
        """Handles the process of asking a question and checking the answer in speak mode."""
        correct = True
        image_shown = False

        # Check if the question contains an image to show at the start
        if "type" in question_data and question_data["type"] == "image" and "image" in question_data:
            self.show_image(question_data["image"], category, lesson, topic)
            image_shown = True  # Mark that the image has been shown

        # Iterate over all key-value pairs in question_data
        for key, value in question_data.items():
            # Skip "type" and "image" keys when displaying the question (these are metadata)
            if key == "type" or key == "image":
                continue

            # Display the question
            self.print_red(f"\nQuestion: {key}")
            speak_text(f"Question: {key}")  # Speak the question

            # Handle the answer by listening to user speech
            correct = self.handle_single_answer_question_speak(key, value)

            if not correct:
                correct_answer = value.split('@')[0]
                speak_text(f"Your answer was incorrect. The correct answer is: {correct_answer}")
                print(f"\nYour answer was incorrect. The correct answer is: {correct_answer}")
                print("Let's practice the correct answer.")
                self.practice_wrong_answer(correct_answer, key)
                self.results.append({"question": key, "result": "wrong", "correct_answer": correct_answer})
            else:
                self.results.append({"question": key, "result": "correct"})

        # If there was no image at the start but the question has an image, show it now
        if not image_shown and "image" in question_data:
            self.show_image(question_data["image"], category, lesson, topic)

    def handle_single_answer_question_speak(self, prompt, answer):
        """Handles single-answer questions in speak mode."""
        return self.ask_and_check_speak(prompt, answer)



    def ask_and_check_speak(self, prompt, answer):
        """Asks the question and checks if the answer is correct in speak mode."""
        parts = answer.split('@')
        correct_answers = [ans.strip().lower() for ans in parts[0].split(';')]
        additional_info = parts[1].strip() if len(parts) > 1 else ""

        remaining_answers = set(correct_answers)
        while remaining_answers:
            user_input = listen_to_user().strip().lower()  # Capture user input via speech

            if user_input == "skip":
                print("Skipped this question.")
                return False

            matched_answers = [ans for ans in remaining_answers if
                               fuzz.ratio(user_input, ans) >= self.fuzzy_search_threshold]
            if matched_answers:
                for matched in matched_answers:
                    print(f"Correct! '{matched}' matched.")
                    remaining_answers.remove(matched)
            else:
                print("Incorrect. Try again.")
                return False

        if additional_info:
            print(f"Information: {additional_info}")
        return True


def get_selection_from_list(options, prompt):
        """Display options and get user selection as a number."""
        for idx, option in enumerate(options, 1):
            print(f"{idx}. {option}")

        while True:
            try:
                selection = int(input(f"{prompt} (Enter number): ")) - 1
                if 0 <= selection < len(options):
                    return options[selection]
                else:
                    print(f"Please select a number between 1 and {len(options)}.")
            except ValueError:
                print("Invalid input. Please enter a number.")
def main():
    config_file = "/Users/macbookpro/Documents/Developer/learn_through_quiz/quiz_project/config.json"
    quiz_master = QuizMaster(config_file)

    while True:


        # Display learning data at the start
        quiz_master.display_learning_data()

        # List available categories (folders)
        categories = [folder for folder in os.listdir(quiz_master.learning_section_directory) if os.path.isdir(os.path.join(quiz_master.learning_section_directory, folder))]
        quiz_master.print_red("Available categories:")
        selected_category = get_selection_from_list(categories, "Enter the category")
        quiz_master.current_category = selected_category  # Store the current category
        category_path = os.path.join(quiz_master.learning_section_directory, selected_category)

        # List lessons in the category
        lessons = quiz_master.list_json_files_in_category(category_path)
        if not lessons:
            print(f"No lessons found in category '{selected_category}'.")
            return
        quiz_master.print_red("Available lessons:")
        selected_lesson = get_selection_from_list([os.path.basename(lesson) for lesson in lessons], "Enter the lesson")
        quiz_master.current_lesson = selected_lesson  # Store the current lesson
        quiz_master.load_data(os.path.splitext(selected_lesson)[0], category_path)

        # Show available topics in the selected lesson
        available_topics = list(quiz_master.data.keys())
        quiz_master.print_red("Available topics:")
        selected_topic = get_selection_from_list(available_topics, "Enter the topic")

        # List available modes (test/speak/learn/show results)
        modes = ["test", "speak", "learn", "show test results"]
        quiz_master.print_red("Select mode:")
        selected_mode = get_selection_from_list(modes, "Do you want to give a test, speak, learn, or show test results (Enter number)")

        if selected_mode == "show test results":
            # Show the test results
            quiz_master.show_test_results(selected_category, selected_lesson, selected_topic)
        else:
            # Run the quiz based on the selected mode
            quiz_master.run_quiz(selected_topic, selected_mode)

        # Ask the user if they want to start over or exit
        restart = input("Press enter to start again: ").strip().lower()
        if restart == 'no':
            print("Exiting the quiz application. Goodbye!")
            break

if __name__ == "__main__":
    main()
