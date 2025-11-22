📘 Event Scheduling & Resource Allocation System

A Flask-based web application for managing events, resources, and resource allocations with built-in conflict detection and custom user authentication.

🚀 Features

🔐 User signup & login (custom session-based auth)

📅 Create, edit, delete events

🏢 Manage resources (rooms, labs, halls, equipment)

🔗 Allocate resources to events

❌ Prevent double booking using time-overlap conflict detection

📊 Resource utilization report

🎨 Bootstrap-based UI (no static folder required)

🛠 Tech Stack

Backend: Flask
Database: MySQL (PyMySQL)
Validation: WTForms + Flask-WTF
Security: Werkzeug password hashing
Templating: Jinja2 (inside templates/)

📁 Project Structure
EventHandler/
│── app.py                  # Main Flask application
│── forms.py                # All WTForms classes
│── templates/              # HTML templates (Bootstrap UI)
│── requirements.txt        # Dependencies


(No static folder used)

⚙️ Setup Instructions
1️⃣ Install dependencies
pip install -r requirements.txt

2️⃣ Configure database

Update DB credentials inside get_db() in app.py.

3️⃣ Run the app
python app.py


Open in browser:

http://localhost:5000/

🔍 Conflict Detection Logic

A resource cannot be allocated if times overlap:

(start_time < existing_end_time) AND
(end_time > existing_start_time)


If true → conflict detected → allocation blocked.

📊 Utilization Report

The system shows:

Total hours a resource was used

Overlapping events within date range

Upcoming bookings

✔ Summary

This project demonstrates:

Flask CRUD operations

Custom login system using sessions

MySQL integration

Resource allocation logic

Conflict detection algorithm

Clean Bootstrap UI without static assets

WTForms-based validation
