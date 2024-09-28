import json
import os
import time
import random
from datetime import datetime
from rapidfuzz import fuzz
from PIL import Image
from tabulate import tabulate

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
        for category in os.listdir(self.learning_section_directory):
            category_path = os.path.join(self.learning_section_directory, category)
            if os.path.isdir(category_path):
                if category not in learning_data:
                    learning_data[category] = {}
                for json_file in self.list_json_files_in_category(category_path):
                    self.load_data(os.path.splitext(os.path.basename(json_file))[0], category_path)
                    lesson = os.path.splitext(os.path.basename(json_file))[0]
                    if lesson not in learning_data[category]:
                        learning_data[category][lesson] = {}
                    for topic in self.data.keys():
                        if topic not in learning_data[category][lesson]:
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
                self.results.append({"question": key, "result": "correct after practice"})
            else:
                self.results.append({"question": key, "result": "correct"})

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

    def record_result(self, topic, time_taken):
        result_file_name = os.path.join(self.results_directory,
                                        f"{os.path.splitext(self.data_file.replace('/', '_'))[0]}_{topic}_result.json")
        result_data = {
            "date_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "time_taken_minutes": round(time_taken, 2),
            "correct_answers": len([r for r in self.results if r['result'] == 'correct']),
            "wrong_answers": len([r for r in self.results if r['result'] == 'wrong']),
            "practice_sessions": len(self.results)
        }
        if os.path.exists(result_file_name):
            with open(result_file_name, 'r', encoding='utf-8') as result_file:
                all_results = json.load(result_file)
        else:
            all_results = []

        all_results.append(result_data)
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

        # Shuffle the list of questions directly
        random.shuffle(questions)

        # Now use shuffled_questions in the quiz
        if mode == "test":
            start_time = time.time()
            for q in questions:
                # Pass the entire question (q) to handle_question, along with category and lesson
                self.handle_question(q, self.current_category, self.current_lesson, topic)
            end_time = time.time()
            time_taken = (end_time - start_time) / 60
            self.record_result(topic, time_taken)

            # Update the learning data for the current topic in the current JSON file
            self.update_learning_data(self.current_category, self.current_lesson, topic)

        elif mode == "learn":
            self.display_learning_mode(questions, topic)


def main():
    config_file = "config.json"
    quiz_master = QuizMaster(config_file)

    # Load and update learning data (this will initialize or update if needed)
    learning_data = quiz_master.load_learning_data()

    # Display learning data at the start
    quiz_master.display_learning_data()

    # List available categories (folders)
    categories = [folder for folder in os.listdir(quiz_master.learning_section_directory) if os.path.isdir(os.path.join(quiz_master.learning_section_directory, folder))]
    quiz_master.print_red(f"Available categories: {', '.join(categories)}")

    # Ask user for category
    category = input("Enter the category: ").strip()
    category_path = os.path.join(quiz_master.learning_section_directory, category)
    if not os.path.exists(category_path):
        print(f"Category '{category}' not found.")
        return

    quiz_master.current_category = category  # Store the current category

    # List lessons in the category
    lessons = quiz_master.list_json_files_in_category(category_path)
    if not lessons:
        print(f"No lessons found in category '{category}'.")
        return
    quiz_master.print_red(f"Available lessons: {', '.join([os.path.basename(lesson) for lesson in lessons])}")

    # Ask user for lesson
    lesson = input("Enter the lesson: ").strip() + ".json"
    if lesson not in [os.path.basename(l) for l in lessons]:
        print(f"Lesson '{lesson}' not found.")
        return

    quiz_master.current_lesson = lesson  # Store the current lesson
    quiz_master.load_data(os.path.splitext(lesson)[0], category_path)

    # Show available topics in the selected file
    available_topics = list(quiz_master.data.keys())
    quiz_master.print_red(f"Available topics: {', '.join(available_topics)}")

    topic = input("Enter the topic: ").strip()

    # Ask user for mode (test/learn)
    mode = input("Do you want to give a test or learn? (test/learn): ").strip().lower()

    quiz_master.run_quiz(topic, mode)



if __name__ == "__main__":
    main()
