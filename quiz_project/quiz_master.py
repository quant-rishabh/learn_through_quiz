import sys
import json
import os
import random
import time
from datetime import datetime
from collections import defaultdict
from PyQt5.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QLabel, QPushButton, QComboBox,
    QMessageBox, QHBoxLayout, QScrollArea, QLineEdit, QInputDialog
)
from PyQt5.QtGui import (QFont,QPixmap)
from PyQt5.QtCore import Qt
from tabulate import tabulate
from rapidfuzz import fuzz


class QuizMaster(QWidget):
    def __init__(self):
        super().__init__()
        self.config = self.load_config("config.json")
        self.results_directory = self.config.get('results_directory', 'results')
        self.initUI()
        self.load_subjects()

    def initUI(self):
        self.setWindowTitle('Quiz Master')
        self.setGeometry(300, 100, 600, 800)

        main_layout = QVBoxLayout()

        # Overview Button
        overview_button = QPushButton("Learning Overview")
        overview_button.clicked.connect(self.show_learning_overview)
        overview_button.setStyleSheet("background-color: #f0ad4e; color: white; font-size: 16px; padding: 10px;")
        main_layout.addWidget(overview_button)

        # Subject and Topic Selection
        self.subject_label = QLabel("Select Subject:")
        self.subject_dropdown = QComboBox()
        self.subject_dropdown.currentTextChanged.connect(self.load_topics)
        self.topic_label = QLabel("Select Topic:")
        self.topic_dropdown = QComboBox()

        subject_layout = QHBoxLayout()
        subject_layout.addWidget(self.subject_label)
        subject_layout.addWidget(self.subject_dropdown)

        topic_layout = QHBoxLayout()
        topic_layout.addWidget(self.topic_label)
        topic_layout.addWidget(self.topic_dropdown)

        main_layout.addLayout(subject_layout)
        main_layout.addLayout(topic_layout)

        # Start Buttons
        self.learn_button = QPushButton("Learn")
        self.learn_button.clicked.connect(self.on_learn_clicked)
        self.test_button = QPushButton("Test")
        self.test_button.clicked.connect(self.on_test_clicked)
        self.learn_button.setStyleSheet("background-color: #5bc0de; color: white; font-size: 16px; padding: 10px;")
        self.test_button.setStyleSheet("background-color: #5cb85c; color: white; font-size: 16px; padding: 10px;")

        button_layout = QHBoxLayout()
        button_layout.addWidget(self.learn_button)
        button_layout.addWidget(self.test_button)

        main_layout.addLayout(button_layout)

        # Scrollable Area for Questions and Answers
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.content_widget = QWidget()
        self.scroll_area.setWidget(self.content_widget)
        self.content_layout = QVBoxLayout(self.content_widget)

        main_layout.addWidget(self.scroll_area)
        self.setLayout(main_layout)

        # Set font size for question label
        self.question_font = QFont("Arial", 18, QFont.Bold)

    def load_config(self, config_file):
        with open(config_file, 'r') as f:
            return json.load(f)

    def load_subjects(self):
        learning_section_directory = self.config['learning_section_directory']
        json_files = [f.replace('.json', '') for f in os.listdir(learning_section_directory) if f.endswith('.json')]
        self.subject_dropdown.addItems(json_files)

    def load_topics(self):
        selected_subject = self.subject_dropdown.currentText()
        learning_section_directory = self.config['learning_section_directory']
        data_file_path = os.path.join(learning_section_directory, selected_subject + '.json')
        with open(data_file_path, 'r') as f:
            self.data = json.load(f)
        topics = list(self.data.keys())
        self.topic_dropdown.clear()
        self.topic_dropdown.addItems(topics)

    def show_learning_overview(self):
        learning_counts_file = os.path.join(self.results_directory, "learning_counts.json")

        if os.path.exists(learning_counts_file):
            with open(learning_counts_file, 'r', encoding='utf-8') as f:
                learning_counts = json.load(f)
        else:
            learning_counts = {}

        # Load all topics from the learning section
        all_topics = defaultdict(list)
        learning_section_directory = self.config['learning_section_directory']
        for file_name in os.listdir(learning_section_directory):
            if file_name.endswith('.json'):
                subject = file_name.replace('.json', '')
                with open(os.path.join(learning_section_directory, file_name), 'r') as f:
                    data = json.load(f)
                    all_topics[subject].extend(data.keys())

        # Build the overview message
        overview_message = ""
        sr_no = 1
        for subject, topics in all_topics.items():
            overview_message += f"{sr_no}. {subject}\n"
            for topic in sorted(topics):
                count = learning_counts.get(subject, {}).get(topic, 0)
                overview_message += f"       |----- {topic:<15} --->  {count}\n"
            sr_no += 1

        if not overview_message:
            overview_message = "No topics have been learned yet."

        QMessageBox.information(self, "Learning Overview", overview_message)

    def on_learn_clicked(self):
        self.mode = "learn"
        self.start_quiz()

    def on_test_clicked(self):
        self.mode = "test"
        self.start_quiz()

    def start_quiz(self):
        self.selected_subject = self.subject_dropdown.currentText()
        self.selected_topic = self.topic_dropdown.currentText()

        self.questions = self.data[self.selected_topic]
        random.shuffle(self.questions)  # Shuffle questions for unbiased learning
        self.current_question_index = 0

        self.correct_answers = 0
        self.incorrect_answers = 0
        self.start_time = time.time()

        self.display_question()

    def display_question(self):
        if self.mode == "learn":
            self.display_all_content()
        elif self.mode == "test":
            self.display_test_content()

    def display_all_content(self):
        self.clear_content()
        serial_number = 1
        for question_data in self.questions:
            question_label = QLabel(f"{serial_number}. {question_data.get('question', '')}")
            question_label.setFont(self.question_font)
            self.content_layout.addWidget(question_label)

            if 'image' in question_data:
                image_path = os.path.join(self.config['image_directory'], self.selected_subject, self.selected_topic, question_data['image'])
                if os.path.exists(image_path):
                    image_label = QLabel()
                    pixmap = QPixmap(image_path)
                    image_label.setPixmap(pixmap.scaled(300, 300, Qt.KeepAspectRatio))
                    self.content_layout.addWidget(image_label)
                else:
                    image_label = QLabel("Image not found")
                    self.content_layout.addWidget(image_label)

            for key, value in question_data.items():
                if key not in ['question', 'type', 'image']:
                    answer_label = QLabel(f"{key}: {value.split('@')[0]}")
                    self.content_layout.addWidget(answer_label)
                    if '@' in value:
                        info_label = QLabel(f"   Info: {value.split('@')[1]}")
                        self.content_layout.addWidget(info_label)

            serial_number += 1

    def display_test_content(self):
        self.clear_content()
        self.current_question_data = self.questions[self.current_question_index]
        self.current_answer_list = None
        self.display_next_part_of_question()

    def display_next_part_of_question(self):
        self.clear_content()

        if not self.current_answer_list:
            if not self.current_question_data:
                self.current_question_index += 1
                if self.current_question_index < len(self.questions):
                    self.display_test_content()
                else:
                    self.end_quiz()
                return

            # Get the next part of the question
            next_parts = [(k, v) for k, v in self.current_question_data.items()
                          if k not in ['question', 'type', 'image'] and not k.startswith('_') and v]
            if not next_parts:
                self.current_question_index += 1
                if self.current_question_index < len(self.questions):
                    self.display_test_content()
                else:
                    self.end_quiz()
                return
            self.current_question_part_key, self.current_question_part_value = next_parts[0]
            self.current_answer_list = [ans.strip().lower() for ans in self.current_question_part_value.split('@')[0].split(';')]

            # Display the main question if available
            main_question = self.current_question_data.get('question', '')
            if main_question:
                question_label = QLabel(main_question)
                question_label.setFont(self.question_font)
                self.content_layout.addWidget(question_label)

        # Display the current part of the question
        question_part_label = QLabel(f"{self.current_question_part_key} ({len(self.current_answer_list)} answers remaining)")
        question_part_label.setFont(self.question_font)
        self.content_layout.addWidget(question_part_label)

        if 'image' in self.current_question_data:
            image_path = os.path.join(self.config['image_directory'], self.selected_subject, self.selected_topic, self.current_question_data['image'])
            if os.path.exists(image_path):
                image_label = QLabel()
                pixmap = QPixmap(image_path)
                image_label.setPixmap(pixmap.scaled(300, 300, Qt.KeepAspectRatio))
                self.content_layout.addWidget(image_label)

        # Answer input field
        self.answer_input = QLineEdit()
        self.answer_input.setPlaceholderText(f"Answer for {self.current_question_part_key}")
        self.content_layout.addWidget(self.answer_input)
        self.answer_input.setFocus()

        # Submit button
        submit_button = QPushButton("Submit Answer")
        submit_button.setStyleSheet("background-color: #4CAF50; color: white; padding: 10px;")
        submit_button.clicked.connect(self.submit_part_answer)
        self.content_layout.addWidget(submit_button)

        # Connect Enter key to submit answer
        self.answer_input.returnPressed.connect(self.submit_part_answer)

    def submit_part_answer(self):
        user_answer = self.answer_input.text().strip().lower()
        matched = any(
            fuzz.ratio(user_answer, ans) >= self.config['fuzzy_search_threshold'] for ans in self.current_answer_list)

        if matched:
            matched_answer = next(ans for ans in self.current_answer_list if
                                  fuzz.ratio(user_answer, ans) >= self.config['fuzzy_search_threshold'])
            self.current_answer_list.remove(matched_answer)
            QMessageBox.information(self, "Correct", f"'{matched_answer}' is correct!")
            self.correct_answers += 1

            if not self.current_answer_list:
                self.current_question_data[self.current_question_part_key] = ""  # Mark this part as answered

                # Move to the next part of the question or to the next question
                self.display_next_part_of_question()
            else:
                # Still more answers remaining for this question part
                self.display_next_part_of_question()
        else:
            correct_answer = "; ".join(self.current_answer_list)
            QMessageBox.warning(self, "Incorrect", f"Incorrect. The correct answer is: {correct_answer}")
            self.incorrect_answers += 1
            self.practice_wrong_answer(correct_answer, self.current_question_part_key)

        # Clear the input field and set focus back to it
        self.answer_input.clear()
        self.answer_input.setFocus()  # Ensure focus is on the input field after dialog

    def practice_wrong_answer(self, correct_answer, key):
        for attempt in range(self.config['practice_attempts']):
            answer, ok = QInputDialog.getText(
                self,
                f"Practice {attempt + 1}/{self.config['practice_attempts']}",
                f"Practice: {key}"
            )

            if ok and fuzz.ratio(answer.strip().lower(), correct_answer.lower()) >= self.config[
                'fuzzy_search_threshold']:
                QMessageBox.information(self, "Correct", "Correct!")
            else:
                QMessageBox.warning(self, "Incorrect",
                                    f"Incorrect. The correct answer is: {correct_answer}. Please try again.")

        # Show a message that practice is complete
        QMessageBox.information(self, "Practice Complete",
                                f"You have completed {self.config['practice_attempts']} practice attempts.")

        # Continue to the next part of the question or the next question
        self.display_next_part_of_question()

    def clear_content(self):
        for i in reversed(range(self.content_layout.count())):
            widget_to_remove = self.content_layout.itemAt(i).widget()
            self.content_layout.removeWidget(widget_to_remove)
            widget_to_remove.deleteLater()

    def end_quiz(self):
        end_time = time.time()
        time_taken = round((end_time - self.start_time) / 60, 2)  # Time taken in minutes
        result_data = {
            "date_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "correct_answers": self.correct_answers,
            "incorrect_answers": self.incorrect_answers,
            "time_taken": time_taken
        }

        result_file_name = f"{self.selected_subject}_{self.selected_topic}_results.json"
        result_file_path = os.path.join(self.results_directory, result_file_name)

        if os.path.exists(result_file_path):
            with open(result_file_path, 'r') as f:
                results = json.load(f)
        else:
            results = []

        results.append(result_data)

        with open(result_file_path, 'w') as f:
            json.dump(results, f, indent=4)

        # Ensure learning count is updated
        self.record_result(self.selected_topic, time_taken)
        self.display_results(results)

    def display_results(self, results):
        headers = ["Date Time", "Correct Answers", "Incorrect Answers", "Time Taken (minutes)"]
        table_data = [[r["date_time"], r["correct_answers"], r["incorrect_answers"], r["time_taken"]] for r in results]

        results_table = tabulate(table_data, headers, tablefmt="grid")
        QMessageBox.information(self, "Quiz Results", results_table)

    def record_result(self, topic, time_taken):
        result_file_name = os.path.join(self.results_directory, f"{self.selected_subject}_{topic}_results.json")
        result_data = {
            "date_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "correct_answers": self.correct_answers,
            "incorrect_answers": self.incorrect_answers,
            "time_taken": time_taken
        }

        if os.path.exists(result_file_name):
            with open(result_file_name, 'r', encoding='utf-8') as result_file:
                all_results = json.load(result_file)
        else:
            all_results = []

        all_results.append(result_data)

        with open(result_file_name, 'w', encoding='utf-8') as result_file:
            json.dump(all_results, result_file, indent=4)

        # Update learning count
        self.update_learning_count(self.selected_subject, topic)

    def update_learning_count(self, subject, topic):
        learning_counts_file = os.path.join(self.config['results_directory'], "learning_counts.json")

        os.makedirs(self.config['results_directory'], exist_ok=True)

        if os.path.exists(learning_counts_file):
            with open(learning_counts_file, 'r', encoding='utf-8') as f:
                learning_counts = json.load(f)
        else:
            learning_counts = {}

        if subject not in learning_counts:
            learning_counts[subject] = {}

        if topic not in learning_counts[subject]:
            learning_counts[subject][topic] = 0

        learning_counts[subject][topic] += 1

        with open(learning_counts_file, 'w', encoding='utf-8') as f:
            json.dump(learning_counts, f, indent=4)


def main():
    app = QApplication(sys.argv)
    quiz_master = QuizMaster()
    quiz_master.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
