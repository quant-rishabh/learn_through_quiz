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
        with open(config_file, 'r') as f:
            self.config = json.load(f)
        self.learning_section_directory = self.config['learning_section_directory']
        self.image_directory = self.config['image_directory']
        self.practice_attempts = self.config['practice_attempts']
        self.results_directory = self.config['results_directory']
        self.fuzzy_search_threshold = self.config.get('fuzzy_search_threshold', 80)  # Default to 80 if not set
        os.makedirs(self.results_directory, exist_ok=True)

    def list_json_files(self):
        """Lists all JSON files in the learning section directory."""
        json_files = [f.replace('.json', '') for f in os.listdir(self.learning_section_directory) if f.endswith('.json')]
        return json_files

    def load_data(self, data_file):
        """Loads the selected JSON file's content."""
        data_file_path = os.path.join(self.learning_section_directory, data_file + '.json')
        with open(data_file_path, 'r') as f:
            self.data = json.load(f)
        self.data_file = data_file

    def show_image(self, image_name, topic):
        """Displays the image associated with the question, checking for the correct topic and file."""
        image_path = os.path.join(self.image_directory, self.data_file, topic, image_name)
        if os.path.exists(image_path):
            img = Image.open(image_path)
            img.show()
        else:
            print(f"Image {image_name} not found in directory {image_path}.")

    def print_red(self, text):
        """Prints the text in red color."""
        red_code = "\033[91m"
        reset_code = "\033[0m"
        print(f"{red_code}{text}{reset_code}")

    def handle_question(self, question_data, topic):
        """Handles the process of asking a question and checking the answer."""
        question = question_data.get('question', '')
        question_type = question_data.get('type', 'text')
        correct = True

        # Display the question in red
        self.print_red(f"\nQuestion: {question}")

        if question_type == 'text':
            correct = self.handle_single_answer_question(question_data)
        elif question_type == 'multi':
            correct = self.handle_multi_answer_question(question_data)
        elif question_type == 'image':
            image = question_data.get('image')
            if image:
                self.show_image(image, topic)
            correct = self.handle_single_answer_question(question_data)

        if not correct:
            if 'answer' in question_data:
                correct_answer = question_data['answer'].split('@')[0]
                print(f"\nYour answer was incorrect. The correct answer is: {correct_answer}")
                print("Let's practice the correct answer.")
                self.practice_wrong_answer(correct_answer, question)
            else:
                print("\nYour answers were incorrect.")
                for key, value in question_data.items():
                    if key in ['question', 'type', 'image']:
                        continue
                    correct_answer = value.split('@')[0]
                    print(f"The correct answer for '{key}' is: {correct_answer}")
                print("Let's practice the correct answers.")
                for key, value in question_data.items():
                    if key in ['question', 'type', 'image']:
                        continue
                    correct_answer = value.split('@')[0]
                    self.practice_wrong_answer(correct_answer, key)
            self.results.append({"question": question, "result": "correct after practice"})
        else:
            self.results.append({"question": question, "result": "correct"})

    def handle_single_answer_question(self, question_data):
        """Handles single-answer questions."""
        answer = question_data['answer']
        return self.ask_and_check(question_data['question'], answer)

    def handle_multi_answer_question(self, question_data):
        """Handles multi-answer questions."""
        correct = True
        for key, value in question_data.items():
            if key in ['question', 'type', 'image']:
                continue
            if not self.ask_and_check(key, value):
                correct = False
        return correct

    def ask_and_check(self, prompt, answer):
        """Asks the question and checks if the answer is correct."""
        parts = answer.split('@')
        correct_answers = [ans.strip().lower() for ans in parts[0].split(';')]
        additional_info = parts[1].strip() if len(parts) > 1 else ""

        remaining_answers = set(correct_answers)
        while remaining_answers:
            # Prompt for answer without repeating the full question
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
                return False  # If incorrect, return False to trigger practice mode

        if additional_info:
            print(f"Information: {additional_info}")
        return True

    def practice_wrong_answer(self, correct_answer, prompt):
        """Handles practicing of incorrect answers."""
        for attempt in range(self.practice_attempts):
            user_input = input(f"Practice {attempt + 1}/{self.practice_attempts} - {prompt}: ").strip().lower()
            if fuzz.ratio(user_input, correct_answer.lower()) >= self.fuzzy_search_threshold:
                print("Correct!")
            else:
                print(f"Incorrect. The correct answer is: {correct_answer}. Please try again.")
        print("Practice completed.")

    def record_result(self, topic, time_taken):
        """Records the results of the quiz."""
        result_file_name = os.path.join(self.results_directory,
                                        f"{os.path.splitext(self.data_file)[0]}_{topic}_result.json")
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

        questions = self.data[topic]

        if mode == "test":
            random.shuffle(questions)
            start_time = time.time()
            for question_data in questions:
                self.handle_question(question_data, topic)
            end_time = time.time()
            time_taken = (end_time - start_time) / 60
            self.record_result(topic, time_taken)
            self.display_results(topic)

        elif mode == "learn":
            self.display_learning_mode(questions, topic)

    def display_learning_mode(self, questions, topic):
        """Displays all questions and answers for learning."""
        table_data = []
        for question_data in questions:
            question = question_data.get('question', '')
            question_type = question_data.get('type', 'text')
            if 'answer' in question_data:
                answer = question_data['answer'].split('@')[0]
            else:
                answer = ", ".join([value.split('@')[0] for key, value in question_data.items() if key not in ['question', 'type', 'image']])

            table_data.append([question, answer])

            if question_type == 'image' and 'image' in question_data:
                self.show_image(question_data['image'], topic)

        headers = ["Question", "Answer"]
        print(tabulate(table_data, headers=headers, tablefmt="grid"))


def main():
    config_file = "config.json"
    quiz_master = QuizMaster(config_file)

    # Ask the user whether they want to take a test or learn
    mode = input("Do you want to give a test or learn? (test/learn): ").strip().lower()
    if mode not in ["test", "learn"]:
        print("Invalid option. Please enter 'test' or 'learn'.")
        return

    # List all available JSON files in the learning section directory
    available_files = quiz_master.list_json_files()
    quiz_master.print_red(f"Available files: {', '.join(available_files)}")

    data_file = input("Enter the name of the JSON file (without .json): ")
    quiz_master.load_data(data_file)

    # Show available topics in the selected file
    available_topics = list(quiz_master.data.keys())
    quiz_master.print_red(f"\nAvailable topics: {', '.join(available_topics)}")

    topic = input("Enter the topic (e.g., dbms): ")

    quiz_master.run_quiz(topic, mode)


if __name__ == "__main__":
    main()
