"""
Student Performance Analysis System

An introductory, menu-driven Python application for managing student marks.
Student records are stored in students.csv beside this file.
"""

import csv
from pathlib import Path


# A tuple is used because the subject list is fixed for every student.
SUBJECTS = ("Python", "Mathematics", "English", "Computer Science")
CSV_PATH = Path(__file__).resolve().parent / "students.csv"
CSV_COLUMNS = ("roll_number", "name", *SUBJECTS)


def find_student(students, roll_number):
    """Find one student by roll number, ignoring letter case and spaces."""
    searched_roll = roll_number.strip().casefold()
    for student in students:
        if student["roll_number"].casefold() == searched_roll:
            return student
    return None


def is_valid_mark(mark):
    """Return True when mark can be represented as a number from 0 to 100."""
    try:
        value = float(mark)
    except (TypeError, ValueError):
        return False
    return 0 <= value <= 100


def ensure_csv_file(csv_path=CSV_PATH):
    """Create the CSV file with column headings when it does not exist."""
    csv_path = Path(csv_path)
    if not csv_path.exists():
        try:
            csv_path.parent.mkdir(parents=True, exist_ok=True)
            with csv_path.open("w", newline="", encoding="utf-8") as file:
                writer = csv.writer(file)
                writer.writerow(CSV_COLUMNS)
        except OSError as error:
            print(f"Could not create the CSV file: {error}")
            return False
    return True


def load_students(csv_path=CSV_PATH):
    """Load valid records from CSV and skip malformed or duplicate rows."""
    csv_path = Path(csv_path)
    if not csv_path.exists():
        ensure_csv_file(csv_path)
        return []

    students = []
    seen_roll_numbers = set()

    try:
        with csv_path.open("r", newline="", encoding="utf-8") as file:
            reader = csv.DictReader(file)
            if not reader.fieldnames or not set(CSV_COLUMNS).issubset(
                reader.fieldnames
            ):
                print("The CSV file does not have the expected column headings.")
                return []

            for row_number, row in enumerate(reader, start=2):
                roll_number = (row.get("roll_number") or "").strip()
                name = (row.get("name") or "").strip()

                try:
                    marks = {
                        subject: float(row[subject])
                        for subject in SUBJECTS
                    }
                except (KeyError, TypeError, ValueError):
                    print(f"Skipped invalid CSV record on row {row_number}.")
                    continue

                roll_key = roll_number.casefold()
                if (
                    not roll_number
                    or not name
                    or roll_key in seen_roll_numbers
                    or not all(is_valid_mark(mark) for mark in marks.values())
                ):
                    print(f"Skipped invalid CSV record on row {row_number}.")
                    continue

                students.append(
                    {
                        "roll_number": roll_number,
                        "name": name,
                        "marks": marks,
                    }
                )
                seen_roll_numbers.add(roll_key)
    except OSError as error:
        print(f"Could not read the CSV file: {error}")

    return students


def save_students(students, csv_path=CSV_PATH):
    """Save all current records while preserving every student in the list."""
    csv_path = Path(csv_path)
    try:
        csv_path.parent.mkdir(parents=True, exist_ok=True)
        with csv_path.open("w", newline="", encoding="utf-8") as file:
            writer = csv.DictWriter(file, fieldnames=CSV_COLUMNS)
            writer.writeheader()
            for student in students:
                row = {
                    "roll_number": student["roll_number"],
                    "name": student["name"],
                }
                row.update(student["marks"])
                writer.writerow(row)
    except OSError as error:
        print(f"Could not save student records: {error}")
        return False
    return True


def calculate_statistics(student):
    """Calculate total, average, percentage, and grade for one student."""
    total = sum(student["marks"].values())
    average = total / len(SUBJECTS)
    percentage = (total / (len(SUBJECTS) * 100)) * 100

    if average >= 90:
        grade = "A+"
    elif average >= 80:
        grade = "A"
    elif average >= 70:
        grade = "B"
    elif average >= 60:
        grade = "C"
    elif average >= 50:
        grade = "D"
    else:
        grade = "F"

    return {
        "total": total,
        "average": average,
        "percentage": percentage,
        "grade": grade,
    }


def print_student_report(student):
    """Display a readable report for one student."""
    statistics = calculate_statistics(student)
    print("\n" + "-" * 48)
    print(f"Name       : {student['name']}")
    print(f"Roll number: {student['roll_number']}")
    print("Subject marks:")
    for subject in SUBJECTS:
        print(f"  {subject:<22} {student['marks'][subject]:>7.2f}")
    print(f"Total      : {statistics['total']:.2f} / 400")
    print(f"Average    : {statistics['average']:.2f} / 100")
    print(f"Percentage : {statistics['percentage']:.2f}%")
    print(f"Grade      : {statistics['grade']}")
    print("-" * 48)


def get_non_empty_text(prompt, current_value=None):
    """Ask until the user enters text; Enter keeps the current value if given."""
    while True:
        value = input(prompt).strip()
        if current_value is not None and not value:
            return current_value
        if value:
            return value
        print("This field cannot be empty. Please try again.")


def get_mark_from_user(subject, current_value=None):
    """Ask for a valid subject mark; a blank entry keeps an existing mark."""
    while True:
        prompt = f"{subject} mark (0-100"
        if current_value is not None:
            prompt += f", Enter to keep {current_value:g}"
        prompt += "): "

        value = input(prompt).strip()
        if current_value is not None and not value:
            return current_value

        if not value:
            print("A mark is required.")
            continue

        if not is_valid_mark(value):
            print("Enter a numeric mark from 0 to 100.")
            continue

        return float(value)


def add_student(students):
    """Collect and add a student, then save the updated list."""
    print("\nAdd a new student")
    while True:
        roll_number = get_non_empty_text("Roll number: ")
        if find_student(students, roll_number):
            print("That roll number already exists. Enter a unique roll number.")
            continue
        break

    name = get_non_empty_text("Student name: ")
    marks = {
        subject: get_mark_from_user(subject)
        for subject in SUBJECTS
    }
    students.append(
        {
            "roll_number": roll_number,
            "name": name,
            "marks": marks,
        }
    )

    if save_students(students):
        print(f"Student {name} was added and saved successfully.")


def view_all_students(students):
    """Display a short summary for every student."""
    if not students:
        print("\nNo student records are available.")
        return

    print("\nSTUDENT RECORDS")
    print("=" * 76)
    print(f"{'Roll number':<16}{'Name':<26}{'Total / 400':>16}{'Average':>12}{'Grade':>8}")
    print("-" * 76)
    for student in students:
        statistics = calculate_statistics(student)
        print(
            f"{student['roll_number']:<16}"
            f"{student['name'][:24]:<26}"
            f"{statistics['total']:>16.2f}"
            f"{statistics['average']:>12.2f}"
            f"{statistics['grade']:>8}"
        )
    print("=" * 76)


def search_student(students):
    """Search by roll number and show the full report when found."""
    roll_number = input("Enter the roll number to search: ").strip()
    student = find_student(students, roll_number)
    if student:
        print_student_report(student)
    else:
        print(f"No student found with roll number '{roll_number}'.")


def update_student(students):
    """Update a student's name and/or marks; blank values keep old details."""
    roll_number = input("Enter the roll number to update: ").strip()
    student = find_student(students, roll_number)
    if not student:
        print(f"No student found with roll number '{roll_number}'.")
        return

    print(f"Updating {student['name']}. Press Enter to keep a current value.")
    student["name"] = get_non_empty_text(
        f"Name [{student['name']}]: ", current_value=student["name"]
    )
    for subject in SUBJECTS:
        student["marks"][subject] = get_mark_from_user(
            subject, current_value=student["marks"][subject]
        )

    if save_students(students):
        print("Student details were updated and saved successfully.")


def delete_student(students):
    """Delete one student only after explicit confirmation."""
    roll_number = input("Enter the roll number to delete: ").strip()
    student = find_student(students, roll_number)
    if not student:
        print(f"No student found with roll number '{roll_number}'.")
        return

    confirmation = input(
        f"Delete {student['name']} (roll {student['roll_number']})? (y/n): "
    ).strip().casefold()
    if confirmation not in ("y", "yes"):
        print("Deletion cancelled.")
        return

    students.remove(student)
    if save_students(students):
        print("Student record deleted and saved successfully.")


def show_student_statistics(students):
    """Ask for a roll number and display calculated marks and grade."""
    roll_number = input("Enter the roll number: ").strip()
    student = find_student(students, roll_number)
    if student:
        print_student_report(student)
    else:
        print(f"No student found with roll number '{roll_number}'.")


def show_extreme_student(students, highest=True):
    """Show the student or students with the highest or lowest total."""
    if not students:
        print("\nNo student records are available.")
        return

    totals = [calculate_statistics(student)["total"] for student in students]
    target_total = max(totals) if highest else min(totals)
    label = "Highest-scoring" if highest else "Lowest-scoring"
    print(f"\n{label} student(s):")
    for student in students:
        if calculate_statistics(student)["total"] == target_total:
            print_student_report(student)


def get_pyplot():
    """Import Matplotlib only when a chart is requested."""
    try:
        import matplotlib.pyplot as plt
    except ImportError:
        print("Matplotlib is not installed. Run: pip install -r requirements.txt")
        return None
    return plt


def plot_student_marks(students):
    """Plot the subject-wise marks for a selected student."""
    if not students:
        print("\nNo student records are available to chart.")
        return

    roll_number = input("Enter the student's roll number: ").strip()
    student = find_student(students, roll_number)
    if not student:
        print(f"No student found with roll number '{roll_number}'.")
        return

    plt = get_pyplot()
    if plt is None:
        return

    marks = [student["marks"][subject] for subject in SUBJECTS]
    plt.figure(figsize=(9, 5))
    bars = plt.bar(SUBJECTS, marks, color="#3478c7")
    plt.title(f"Subject-wise Marks: {student['name']} (Roll {student['roll_number']})")
    plt.xlabel("Subject")
    plt.ylabel("Marks (out of 100)")
    plt.ylim(0, 110)
    plt.xticks(rotation=15, ha="right")
    plt.bar_label(bars, fmt="%.1f", padding=3)
    plt.tight_layout()
    print("Displaying the chart. Close its window to return to the menu.")
    plt.show()


def plot_student_averages(students):
    """Compare the average marks of all students in a bar chart."""
    if not students:
        print("\nNo student records are available to chart.")
        return

    plt = get_pyplot()
    if plt is None:
        return

    names = [
        f"{student['name']}\n({student['roll_number']})"
        for student in students
    ]
    averages = [
        calculate_statistics(student)["average"]
        for student in students
    ]
    width = max(8, len(students) * 0.9)
    plt.figure(figsize=(width, 5))
    bars = plt.bar(names, averages, color="#45a17b")
    plt.title("Average Marks by Student")
    plt.xlabel("Student")
    plt.ylabel("Average marks (out of 100)")
    plt.ylim(0, 110)
    plt.xticks(rotation=20, ha="right")
    plt.bar_label(bars, fmt="%.1f", padding=3)
    plt.tight_layout()
    print("Displaying the chart. Close its window to return to the menu.")
    plt.show()


def calculate_subject_averages(students):
    """Return a dictionary with the class average for each subject."""
    if not students:
        return {}
    return {
        subject: sum(student["marks"][subject] for student in students)
        / len(students)
        for subject in SUBJECTS
    }


def show_subject_averages(students):
    """Display and chart the average mark for each subject in the class."""
    if not students:
        print("\nNo student records are available to calculate class averages.")
        return

    averages = calculate_subject_averages(students)
    print("\nSUBJECT-WISE CLASS AVERAGES")
    for subject in SUBJECTS:
        print(f"{subject:<22} {averages[subject]:.2f}")

    plt = get_pyplot()
    if plt is None:
        return

    values = [averages[subject] for subject in SUBJECTS]
    plt.figure(figsize=(9, 5))
    bars = plt.bar(SUBJECTS, values, color="#dd8b42")
    plt.title("Class Average by Subject")
    plt.xlabel("Subject")
    plt.ylabel("Average marks (out of 100)")
    plt.ylim(0, 110)
    plt.xticks(rotation=15, ha="right")
    plt.bar_label(bars, fmt="%.1f", padding=3)
    plt.tight_layout()
    print("Displaying the chart. Close its window to return to the menu.")
    plt.show()


def print_menu():
    """Display the application's numbered options."""
    print(
        """
1.  Add a new student
2.  View all student records
3.  Search for a student by roll number
4.  Update student details or marks
5.  Delete a student record
6.  Calculate total, average, percentage, and grade
7.  Display the highest-scoring student
8.  Display the lowest-scoring student
9.  Generate an individual student's subject-wise bar chart
10. Compare average marks of all students
11. Save student records to CSV
12. Reload saved records from CSV
13. Display subject-wise class averages and chart
14. Exit
"""
    )


def main():
    """Load saved data and run the menu until the user chooses to exit."""
    print("=" * 56)
    print("       STUDENT PERFORMANCE ANALYSIS SYSTEM")
    print("=" * 56)
    students = load_students()
    if students:
        print(f"Loaded {len(students)} student record(s) from {CSV_PATH.name}.")
    else:
        print("No saved student records found. You can add the first student.")

    while True:
        print_menu()
        try:
            choice = input("Choose an option (1-14): ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nInput ended. Saving records before exit.")
            save_students(students)
            print("Goodbye.")
            break

        if choice == "1":
            add_student(students)
        elif choice == "2":
            view_all_students(students)
        elif choice == "3":
            search_student(students)
        elif choice == "4":
            update_student(students)
        elif choice == "5":
            delete_student(students)
        elif choice == "6":
            show_student_statistics(students)
        elif choice == "7":
            show_extreme_student(students, highest=True)
        elif choice == "8":
            show_extreme_student(students, highest=False)
        elif choice == "9":
            plot_student_marks(students)
        elif choice == "10":
            plot_student_averages(students)
        elif choice == "11":
            if save_students(students):
                print("Student records saved successfully.")
        elif choice == "12":
            students = load_students()
            print(f"Reloaded {len(students)} student record(s) from CSV.")
        elif choice == "13":
            show_subject_averages(students)
        elif choice == "14":
            if save_students(students):
                print("Student records saved successfully.")
            print("Thank you for using the Student Performance Analysis System.")
            print("Goodbye.")
            break
        else:
            print("Invalid choice. Enter a number from 1 to 14.")


if __name__ == "__main__":
    main()
