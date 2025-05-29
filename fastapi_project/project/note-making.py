import os
from dotenv import load_dotenv
from fastapi import FastAPI, Request, Form, HTTPException, Depends
from fastapi.responses import HTMLResponse, RedirectResponse, StreamingResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from passlib.context import CryptContext
import io
from datetime import datetime, date
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from reportlab.lib.units import inch
from starlette.middleware.sessions import SessionMiddleware
import smtplib
from email.mime.text import MIMEText
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from pathlib import Path
from sqlalchemy.orm import Session
from models import Base, User, Note, engine, SessionLocal

# Load environment variables from .env file
load_dotenv()

app = FastAPI()
app.add_middleware(SessionMiddleware, secret_key=os.getenv("SESSION_SECRET"))

# ...existing code...
BASE_DIR = Path(__file__).resolve().parent
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))
# ...existing code...
app.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static")

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Dependency to get database session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Email configuration
SMTP_SERVER = os.getenv("SMTP_SERVER")
SMTP_PORT = int(os.getenv("SMTP_PORT"))
SMTP_USERNAME = os.getenv("SMTP_USERNAME")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD")

def send_reminder_email(to_email, note_title, note_content):
    msg = MIMEText(f"Reminder: Your note '{note_title}' is due today!\n\nContent: {note_content}")
    msg["Subject"] = f"Reminder: {note_title}"
    msg["From"] = SMTP_USERNAME
    msg["To"] = to_email
    try:
        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.starttls()
            server.login(SMTP_USERNAME, SMTP_PASSWORD)
            server.sendmail(SMTP_USERNAME, to_email, msg.as_string())
        print(f"Email sent to {to_email} for note: {note_title}")
        return True
    except Exception as e:
        print(f"Failed to send email to {to_email}: {e}")
        return False

# Check for reminders and send emails using SQLAlchemy
async def check_reminders(db: Session):
    today = date.today()
    try:
        notes = (db.query(Note, User.email)
                .join(User, Note.user_id == User.user_id)
                .filter(Note.reminder_date == today, Note.email_sent == False)
                .all())
        
        for note, email in notes:
            email_sent = send_reminder_email(email, note.title, note.content)
            if email_sent:
                note.email_sent = True
        db.commit()
    except Exception as e:
        db.rollback()
        print(f"Error checking reminders: {str(e)}")

# Schedule the check_reminders function to run daily
@app.on_event("startup")
async def start_scheduler():
    scheduler = AsyncIOScheduler()
    db = SessionLocal()  # Create a single session for the scheduler
    scheduler.add_job(check_reminders, "interval", days=1, args=[db])
    scheduler.start()
    await check_reminders(db)

# Root GET endpoint
@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})

# Login GET endpoint
@app.get("/login", response_class=HTMLResponse)
async def read_login(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})

# Login POST endpoint
@app.post("/login", response_class=HTMLResponse)
async def login_user(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db)
):
    try:
        user = db.query(User).filter(User.username == username).first()
        if not user or not pwd_context.verify(password, user.password_hash):
            return templates.TemplateResponse(
                "login.html",
                {"request": request, "error": "Invalid username or password"}
            )
        
        notes = db.query(Note).filter(Note.user_id == user.user_id).order_by(Note.created_at.desc()).all()
        response = templates.TemplateResponse(
            "home.html",
            {
                "request": request,
                "username": username,
                "user_id": user.user_id,
                "notes": notes,
                "message": "Login successful!",
                "selected_tag": ""
            }
        )
        request.session["user_id"] = user.user_id
        request.session["username"] = user.username
        return response
    except Exception as e:
        print(f"Error during login: {str(e)}")
        return templates.TemplateResponse(
            "login.html",
            {"request": request, "error": "An error occurred"}
        )

# Signup GET endpoint
@app.get("/signup", response_class=HTMLResponse)
async def read_signup(request: Request):
    return templates.TemplateResponse("signup.html", {"request": request})

# Signup POST endpoint
@app.post("/signup", response_class=HTMLResponse)
async def create_user(
    request: Request,
    username: str = Form(...),
    email: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db)
):
    try:
        if len(username) < 3:
            return templates.TemplateResponse(
                "signup.html",
                {"request": request, "error": "Username must be at least 3 characters long"}
            )
        if "@" not in email or "." not in email:
            return templates.TemplateResponse(
                "signup.html",
                {"request": request, "error": "Invalid email format"}
            )
        if len(password) < 6:
            return templates.TemplateResponse(
                "signup.html",
                {"request": request, "error": "Password must be at least 6 characters long"}
            )

        hashed_password = pwd_context.hash(password)
        new_user = User(username=username, email=email, password_hash=hashed_password)
        db.add(new_user)
        db.commit()
        db.refresh(new_user)

        response = templates.TemplateResponse(
            "home.html",
            {
                "request": request,
                "username": username,
                "user_id": new_user.user_id,
                "notes": [],
                "message": "Sign up successful!",
                "selected_tag": ""
            }
        )
        request.session["user_id"] = new_user.user_id
        request.session["username"] = new_user.username
        return response
    except Exception as e:
        db.rollback()
        print(f"Error during signup: {str(e)}")
        return templates.TemplateResponse(
            "signup.html",
            {"request": request, "error": "An error occurred"}
        )

# Notes GET endpoint
@app.get("/notes", response_class=HTMLResponse)
async def read_notes(request: Request, db: Session = Depends(get_db)):
    user_id = request.session.get("user_id")
    if not user_id:
        return RedirectResponse(url="/login", status_code=303)
    try:
        notes = db.query(Note).filter(Note.user_id == user_id).order_by(Note.created_at.desc()).all()
        return templates.TemplateResponse(
            "home.html",
            {
                "request": request,
                "username": request.session.get("username"),
                "user_id": int(user_id),
                "notes": notes,
                "selected_tag": ""
            }
        )
    except Exception as e:
        print(f"Error fetching notes: {str(e)}")
        return templates.TemplateResponse(
            "home.html",
            {
                "request": request,
                "username": request.session.get("username", ""),
                "user_id": int(user_id),
                "notes": [],
                "error": "An error occurred",
                "selected_tag": ""
            }
        )

# Notes Filter GET endpoint
@app.get("/notes/filter", response_class=HTMLResponse)
async def filter_notes(request: Request, db: Session = Depends(get_db)):
    user_id = request.session.get("user_id")
    if not user_id:
        return RedirectResponse(url="/login", status_code=303)
    try:
        selected_tag = request.query_params.get("tag", "")
        if selected_tag:
            notes = db.query(Note).filter(Note.user_id == user_id, Note.tags == selected_tag).order_by(Note.created_at.desc()).all()
        else:
            notes = db.query(Note).filter(Note.user_id == user_id).order_by(Note.created_at.desc()).all()
        return templates.TemplateResponse(
            "home.html",
            {
                "request": request,
                "username": request.session.get("username"),
                "user_id": int(user_id),
                "notes": notes,
                "selected_tag": selected_tag
            }
        )
    except Exception as e:
        print(f"Error filtering notes: {str(e)}")
        return templates.TemplateResponse(
            "home.html",
            {
                "request": request,
                "username": request.session.get("username", ""),
                "user_id": int(user_id),
                "notes": [],
                "error": "An error occurred while filtering notes",
                "selected_tag": ""
            }
        )

# Notes POST endpoint (Create Note)
@app.post("/notes", response_class=HTMLResponse)
async def write_notes(
    request: Request,
    title: str = Form(...),
    content: str = Form(...),
    set_reminder: str = Form(...),
    reminder_date: str = Form(None),
    tag: str = Form(None),
    user_id: int = Form(...),
    db: Session = Depends(get_db)
):
    try:
        if set_reminder == "on":
            if not reminder_date:
                raise HTTPException(status_code=400, detail="Reminder date is required when set_reminder is on")
            try:
                final_reminder_date = datetime.strptime(reminder_date, "%Y-%m-%d").date()
            except ValueError:
                raise HTTPException(status_code=400, detail="Invalid date format for reminder")
        else:
            final_reminder_date = None
        final_tag = tag if tag else None

        new_note = Note(
            user_id=user_id,
            title=title,
            content=content,
            reminder_date=final_reminder_date,
            tags=final_tag,
            email_sent=False  # Ensure default is set
        )
        db.add(new_note)
        db.commit()
        return RedirectResponse(url="/notes", status_code=303)
    except Exception as e:
        db.rollback()
        print(f"Error during note creation: {str(e)}")
        return templates.TemplateResponse(
            "home.html",
            {
                "request": request,
                "username": request.session.get("username", ""),
                "user_id": user_id,
                "notes": [],
                "error": "An error occurred while saving the note",
                "selected_tag": ""
            }
        )

# Edit Note GET endpoint
@app.get("/notes/edit/{note_id}", response_class=HTMLResponse)
async def get_edit_note(request: Request, note_id: int, db: Session = Depends(get_db)):
    user_id = request.session.get("user_id")
    if not user_id:
        return RedirectResponse(url="/login", status_code=303)
    try:
        notes = db.query(Note).filter(Note.user_id == user_id).order_by(Note.created_at.desc()).all()
        note = db.query(Note).filter(Note.note_id == note_id, Note.user_id == user_id).first()
        if not note:
            return templates.TemplateResponse(
                "home.html",
                {
                    "request": request,
                    "username": request.session.get("username"),
                    "user_id": int(user_id),
                    "notes": notes,
                    "error": "Note not found or you don't have permission to edit it",
                    "selected_tag": ""
                }
            )
        return templates.TemplateResponse(
            "home.html",
            {
                "request": request,
                "username": request.session.get("username"),
                "user_id": int(user_id),
                "notes": notes,
                "editing_note_id": note_id,
                "note": note,
                "selected_tag": ""
            }
        )
    except Exception as e:
        print(f"Error fetching note for editing: {str(e)}")
        return templates.TemplateResponse(
            "home.html",
            {
                "request": request,
                "username": request.session.get("username", ""),
                "user_id": int(user_id),
                "notes": [],
                "error": "An error occurred while loading the edit form",
                "selected_tag": ""
            }
        )

# Edit Note POST endpoint
@app.post("/notes/edit/{note_id}", response_class=HTMLResponse)
async def edit_note(
    request: Request,
    note_id: int,
    title: str = Form(...),
    content: str = Form(...),
    set_reminder: str = Form(...),
    reminder_date: str = Form(None),
    user_id: int = Form(...),
    db: Session = Depends(get_db)
):
    try:
        print(f"Editing note_id: {note_id}, set_reminder: {set_reminder}, reminder_date: {reminder_date}")
        if set_reminder == "on":
            if not reminder_date:
                raise HTTPException(status_code=400, detail="Reminder date is required when set_reminder is on")
            try:
                final_reminder_date = datetime.strptime(reminder_date, "%Y-%m-%d").date()
                print(f"Parsed reminder_date: {final_reminder_date}")
            except ValueError as ve:
                print(f"Invalid date format for reminder: {ve}")
                raise HTTPException(status_code=400, detail="Invalid date format for reminder")
        else:
            final_reminder_date = None

        note = db.query(Note).filter(Note.note_id == note_id, Note.user_id == user_id).first()
        if not note:
            raise HTTPException(status_code=404, detail="Note not found or you don't have permission to edit it")
        
        note.title = title
        note.content = content
        note.reminder_date = final_reminder_date
        db.commit()
        print(f"Note {note_id} updated successfully with reminder_date: {final_reminder_date}")
        return RedirectResponse(url="/notes", status_code=303)
    except Exception as e:
        db.rollback()
        print(f"Error during note editing: {str(e)}")
        return templates.TemplateResponse(
            "home.html",
            {
                "request": request,
                "username": request.session.get("username", ""),
                "user_id": user_id,
                "notes": [],
                "error": f"An error occurred while updating the note: {str(e)}",
                "selected_tag": ""
            }
        )

# Set Tag Endpoint
@app.post("/notes/tag/{note_id}", response_class=HTMLResponse)
async def set_tag(
    request: Request,
    note_id: int,
    tag: str = Form(None),
    user_id: int = Form(...),
    db: Session = Depends(get_db)
):
    try:
        note = db.query(Note).filter(Note.note_id == note_id, Note.user_id == user_id).first()
        if not note:
            raise HTTPException(status_code=404, detail="Note not found or you don't have permission to edit it")
        
        note.tags = tag if tag else None
        db.commit()
        return RedirectResponse(url="/notes", status_code=303)
    except Exception as e:
        db.rollback()
        print(f"Error during setting tag: {str(e)}")
        return templates.TemplateResponse(
            "home.html",
            {
                "request": request,
                "username": request.session.get("username", ""),
                "user_id": user_id,
                "notes": [],
                "error": "An error occurred while setting the tag",
                "selected_tag": ""
            }
        )

# Delete Note Endpoint
@app.post("/notes/delete/{note_id}", response_class=HTMLResponse)
async def delete_note(
    request: Request,
    note_id: int,
    user_id: int = Form(...),
    db: Session = Depends(get_db)
):
    try:
        note = db.query(Note).filter(Note.note_id == note_id, Note.user_id == user_id).first()
        if not note:
            raise HTTPException(status_code=404, detail="Note not found or you don't have permission to delete it")
        
        db.delete(note)
        db.commit()
        return RedirectResponse(url="/notes", status_code=303)
    except Exception as e:
        db.rollback()
        print(f"Error during note deletion: {str(e)}")
        return templates.TemplateResponse(
            "home.html",
            {
                "request": request,
                "username": request.session.get("username", ""),
                "user_id": user_id,
                "notes": [],
                "error": "An error occurred while deleting the note",
                "selected_tag": ""
            }
        )

# Export Notes as PDF Endpoint using ReportLab
@app.post("/notes/export-pdf", response_class=StreamingResponse)
async def export_notes_pdf(request: Request, selected_tag: str = Form(None), db: Session = Depends(get_db)):
    user_id = request.session.get("user_id")
    if not user_id:
        return RedirectResponse(url="/login", status_code=303)
    
    try:
        if selected_tag:
            notes = db.query(Note).filter(Note.user_id == user_id, Note.tags == selected_tag).order_by(Note.created_at.desc()).all()
        else:
            notes = db.query(Note).filter(Note.user_id == user_id).order_by(Note.created_at.desc()).all()

        if not notes:
            return templates.TemplateResponse(
                "home.html",
                {
                    "request": request,
                    "username": request.session.get("username"),
                    "user_id": int(user_id),
                    "notes": [],
                    "error": "No notes available to export",
                    "selected_tag": selected_tag
                }
            )

        buffer = io.BytesIO()
        c = canvas.Canvas(buffer, pagesize=letter)
        width, height = letter
        margin = inch
        y_position = height - margin

        c.setFont("Helvetica-Bold", 16)
        c.drawCentredString(width / 2, y_position, "Your Notes")
        y_position -= 0.5 * inch

        c.setFont("Helvetica", 10)
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        c.drawCentredString(width / 2, y_position, f"Exported on {timestamp}")
        y_position -= 0.5 * inch

        c.setFont("Helvetica", 12)
        for note in notes:
            if y_position < margin + 1.5 * inch:
                c.showPage()
                y_position = height - margin
                c.setFont("Helvetica", 12)

            c.setFont("Helvetica-Bold", 14)
            c.drawString(margin, y_position, note.title)
            y_position -= 0.3 * inch

            c.setFont("Helvetica", 12)
            content_lines = note.content.split('\n')
            for line in content_lines:
                c.drawString(margin + 0.2 * inch, y_position, line[:80])
                y_position -= 0.2 * inch
                if y_position < margin:
                    c.showPage()
                    y_position = height - margin
                    c.setFont("Helvetica", 12)

            if note.reminder_date:
                c.drawString(margin + 0.2 * inch, y_position, f"Reminder: {note.reminder_date}")
                y_position -= 0.2 * inch

            if note.tags:
                c.drawString(margin + 0.2 * inch, y_position, f"Tag: {note.tags}")
                y_position -= 0.2 * inch

            y_position -= 0.3 * inch
            c.line(margin, y_position, width - margin, y_position)
            y_position -= 0.5 * inch

        c.save()
        buffer.seek(0)
        timestamp = datetime.now().strftime("%Y-%m-%d_%H%M%S")
        filename = f"notes_export_{timestamp}.pdf"

        return StreamingResponse(
            buffer,
            media_type="application/pdf",
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )
    except Exception as e:
        print(f"Error during PDF export: {str(e)}")
        return templates.TemplateResponse(
            "home.html",
            {
                "request": request,
                "username": request.session.get("username", ""),
                "user_id": int(user_id),
                "notes": [],
                "error": "An error occurred while exporting to PDF",
                "selected_tag": selected_tag
            }
        )

# Logout endpoint
@app.get("/logout", response_class=HTMLResponse)
async def logout(request: Request):
    request.session.clear()
    return RedirectResponse(url="/login", status_code=303)