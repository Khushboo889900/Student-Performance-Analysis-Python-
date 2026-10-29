"""
Browser interface and Python API for the Student Performance Analysis System.

The website reads and writes the same students.csv file as main.py.
"""

from io import BytesIO
import os
from pathlib import Path

import matplotlib

# The website creates chart images on the server, so it does not need a desktop.
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from flask import Flask, jsonify, redirect, render_template, request, send_file

from main import (
    SUBJECTS,
    calculate_statistics,
    calculate_subject_averages,
    find_student,
    is_valid_mark,
    load_students,
    save_students,
)


API_PREFIX = "/students-api"
PROJECT_ZIP_PATH = Path(__file__).resolve().parent.parent / "student_performance_analysis.zip"
app = Flask(__name__, template_folder="templates", static_folder="static")

# Create the CSV file if it is missing, then use the shared CSV for all requests.
load_students()


def get_current_students():
    """Read the latest records so terminal and browser changes stay in sync."""
    return load_students()


def student_as_json(student):
    """Add calculated results to a student record for the website."""
    result = {
        "roll_number": student["roll_number"],
        "name": student["name"],
        "marks": student["marks"],
    }
    result.update(calculate_statistics(student))
    return result


def json_error(message, status_code):
    """Return a consistent JSON error response."""
    return jsonify({"error": message}), status_code


def validate_mark_values(marks):
    """Check that every provided mark is numeric and between 0 and 100."""
    if not isinstance(marks, dict):
        return "Marks must be supplied as a subject-to-mark object."

    for subject, value in marks.items():
        if subject not in SUBJECTS:
            return f"Unknown subject: {subject}."
        if isinstance(value, bool) or not is_valid_mark(value):
            return f"{subject} must be a number from 0 to 100."
    return None


def save_or_error(students):
    """Save a changed list and return an error response if saving fails."""
    if not save_students(students):
        return json_error("The student records could not be saved.", 500)
    return None


@app.after_request
def disable_stale_browser_cache(response):
    """Ensure refreshed student data and chart images are shown immediately."""
    response.headers["Cache-Control"] = "no-store"
    return response


@app.get("/")
def home():
    """Serve the single-page student management website."""
    return render_template("index.html", api_base=API_PREFIX)


@app.get("/download")
def download_project_zip():
    """Download the clean project archive for a local setup."""
    if not PROJECT_ZIP_PATH.is_file():
        return json_error("The project ZIP is not available.", 404)
    return send_file(
        PROJECT_ZIP_PATH,
        mimetype="application/zip",
        as_attachment=True,
        download_name=PROJECT_ZIP_PATH.name,
    )


@app.get("/favicon.ico")
def favicon():
    """Send older browsers to the Chandigarh University mark."""
    return redirect("/static/chandigarh-university-mark.png")


@app.get(f"{API_PREFIX}/students")
def list_students():
    """Return every saved student with calculated marks and grade."""
    students = get_current_students()
    return jsonify(
        {
            "students": [student_as_json(student) for student in students],
            "count": len(students),
        }
    )


@app.get(f"{API_PREFIX}/summary")
def get_summary():
    """Return class counts, top and bottom performers, and subject averages."""
    students = get_current_students()
    if not students:
        return jsonify(
            {
                "count": 0,
                "highest": [],
                "lowest": [],
                "subject_averages": {},
            }
        )

    totals = [
        calculate_statistics(student)["total"]
        for student in students
    ]
    highest_total = max(totals)
    lowest_total = min(totals)

    return jsonify(
        {
            "count": len(students),
            "highest": [
                student_as_json(student)
                for student in students
                if calculate_statistics(student)["total"] == highest_total
            ],
            "lowest": [
                student_as_json(student)
                for student in students
                if calculate_statistics(student)["total"] == lowest_total
            ],
            "subject_averages": calculate_subject_averages(students),
        }
    )


@app.get(f"{API_PREFIX}/students/<path:roll_number>")
def get_student(roll_number):
    """Return one student's full report."""
    student = find_student(get_current_students(), roll_number)
    if not student:
        return json_error("No student found with that roll number.", 404)
    return jsonify({"student": student_as_json(student)})


@app.post(f"{API_PREFIX}/students")
def create_student():
    """Validate and add a student, then persist the complete record list."""
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return json_error("Send student details as a JSON object.", 400)

    roll_number = data.get("roll_number")
    name = data.get("name")
    marks = data.get("marks")

    if not isinstance(roll_number, str) or not roll_number.strip():
        return json_error("Roll number cannot be empty.", 400)
    if not isinstance(name, str) or not name.strip():
        return json_error("Student name cannot be empty.", 400)
    if not isinstance(marks, dict) or set(marks) != set(SUBJECTS):
        return json_error("Enter a mark for each of the four subjects.", 400)

    marks_error = validate_mark_values(marks)
    if marks_error:
        return json_error(marks_error, 400)

    students = get_current_students()
    clean_roll_number = roll_number.strip()
    if find_student(students, clean_roll_number):
        return json_error("That roll number already exists.", 409)

    student = {
        "roll_number": clean_roll_number,
        "name": name.strip(),
        "marks": {subject: float(marks[subject]) for subject in SUBJECTS},
    }
    students.append(student)

    save_error = save_or_error(students)
    if save_error:
        return save_error
    return jsonify({"student": student_as_json(student)}), 201


@app.put(f"{API_PREFIX}/students/<path:roll_number>")
def update_student(roll_number):
    """Update a student's name and/or marks without changing the roll number."""
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return json_error("Send the changes as a JSON object.", 400)
    if "name" not in data and "marks" not in data:
        return json_error("Provide a new name, marks, or both.", 400)

    students = get_current_students()
    student = find_student(students, roll_number)
    if not student:
        return json_error("No student found with that roll number.", 404)

    if "name" in data:
        name = data["name"]
        if not isinstance(name, str) or not name.strip():
            return json_error("Student name cannot be empty.", 400)
        student["name"] = name.strip()

    if "marks" in data:
        marks = data["marks"]
        marks_error = validate_mark_values(marks)
        if marks_error:
            return json_error(marks_error, 400)
        if not marks:
            return json_error("Provide at least one subject mark to update.", 400)
        for subject, value in marks.items():
            student["marks"][subject] = float(value)

    save_error = save_or_error(students)
    if save_error:
        return save_error
    return jsonify({"student": student_as_json(student)})


@app.delete(f"{API_PREFIX}/students/<path:roll_number>")
def delete_student(roll_number):
    """Delete one record after the website has asked the user to confirm."""
    students = get_current_students()
    student = find_student(students, roll_number)
    if not student:
        return json_error("No student found with that roll number.", 404)

    students.remove(student)
    save_error = save_or_error(students)
    if save_error:
        return save_error
    return jsonify({"message": f"Deleted {student['name']}."})


def chart_as_png(draw_chart):
    """Render one Matplotlib chart into an in-memory PNG response."""
    image = BytesIO()
    figure = draw_chart()
    figure.savefig(image, format="png", dpi=140, bbox_inches="tight")
    plt.close(figure)
    image.seek(0)
    return send_file(image, mimetype="image/png")


@app.get(f"{API_PREFIX}/charts/student/<path:roll_number>.png")
def student_chart(roll_number):
    """Create a bar chart of one student's subject marks."""
    student = find_student(get_current_students(), roll_number)
    if not student:
        return json_error("No student found with that roll number.", 404)

    def draw():
        figure, axis = plt.subplots(figsize=(9, 5))
        values = [student["marks"][subject] for subject in SUBJECTS]
        bars = axis.bar(SUBJECTS, values, color="#ce1a19")
        axis.set_title(
            f"Subject-wise Marks: {student['name']} "
            f"(Roll {student['roll_number']})"
        )
        axis.set_xlabel("Subject")
        axis.set_ylabel("Marks (out of 100)")
        axis.set_ylim(0, 110)
        axis.tick_params(axis="x", labelrotation=15)
        axis.bar_label(bars, fmt="%.1f", padding=3)
        figure.tight_layout()
        return figure

    return chart_as_png(draw)


@app.get(f"{API_PREFIX}/charts/averages.png")
def average_chart():
    """Create a chart comparing the average marks for all students."""
    students = get_current_students()
    if not students:
        return json_error("Add a student before creating a chart.", 404)

    def draw():
        names = [
            f"{student['name']}\n({student['roll_number']})"
            for student in students
        ]
        averages = [
            calculate_statistics(student)["average"]
            for student in students
        ]
        figure, axis = plt.subplots(figsize=(max(8, len(students) * 0.9), 5))
        bars = axis.bar(names, averages, color="#332f2b")
        axis.set_title("Average Marks by Student")
        axis.set_xlabel("Student")
        axis.set_ylabel("Average marks (out of 100)")
        axis.set_ylim(0, 110)
        axis.tick_params(axis="x", labelrotation=20)
        axis.bar_label(bars, fmt="%.1f", padding=3)
        figure.tight_layout()
        return figure

    return chart_as_png(draw)


@app.get(f"{API_PREFIX}/charts/subjects.png")
def subject_chart():
    """Create a chart of the class average for every subject."""
    students = get_current_students()
    if not students:
        return json_error("Add a student before creating a chart.", 404)

    def draw():
        averages = calculate_subject_averages(students)
        values = [averages[subject] for subject in SUBJECTS]
        figure, axis = plt.subplots(figsize=(9, 5))
        bars = axis.bar(
            SUBJECTS,
            values,
            color=["#ce1a19", "#332f2b", "#a9131a", "#827a7b"],
        )
        axis.set_title("Class Average by Subject")
        axis.set_xlabel("Subject")
        axis.set_ylabel("Average marks (out of 100)")
        axis.set_ylim(0, 110)
        axis.tick_params(axis="x", labelrotation=15)
        axis.bar_label(bars, fmt="%.1f", padding=3)
        figure.tight_layout()
        return figure

    return chart_as_png(draw)


if __name__ == "__main__":
    port = int(os.environ.get("PORT", "5000"))
    app.run(host="0.0.0.0", port=port, debug=False)
