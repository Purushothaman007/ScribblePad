ScribblePad 📝
ScribblePad is a fast and simple web-based note-taking API built with FastAPI. Create, edit, and manage your notes effortlessly! 🚀
Features ✨

Create, update, and delete notes using a RESTful API.
User-specific note management.
Store notes securely with SQLite and SQLAlchemy.
Hosted on Render for easy access.

Technologies 🛠️

Python 🐍
FastAPI ⚡
SQLAlchemy 📊
SQLite 💾
Uvicorn 🌟

Installation 🔧

Clone the repository:git clone https://github.com/your-username/scribblepad.git
cd scribblepad


Create and activate a virtual environment:python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate


Install dependencies:pip install -r requirements.txt


Set up SQLite:
Ensure the database file (e.g., test.db) is set in fastapi_project/project/models.py.



Usage 📚

Start the server:uvicorn fastapi_project.main:app --host 0.0.0.0 --port 8000


Explore the API:
Open http://localhost:8000/docs for interactive API documentation.
Try these endpoints:
POST /notes: Add a note.
GET /notes: View all notes for a user.





