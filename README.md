# Book It – Doctor Appointment Booking App

Simple web app built with:
- Python + Flask (backend)
- HTML, CSS, JavaScript (frontend)
- SQLite (local) / PostgreSQL (Vercel)

## Features
- Home page
- User registration and login
- Appointment booking with doctor selection
- Admin dashboard to view all appointments and update status
- **Doctor management**: Add, edit, and remove doctors (admin only)

## Run locally
1. Create and activate virtual environment:
   - Windows PowerShell:
     - `python -m venv .venv`
     - `.venv\Scripts\Activate.ps1`
2. Install dependencies:
   - `pip install -r requirements.txt`
3. Start the app:
   - `python app.py`
4. Open:
   - `http://127.0.0.1:5000`

## Quick start (Windows)
- Command Prompt:
  - `run.bat`
- PowerShell:
  - `.\run.ps1`

## Default admin account
- Email: `admin@clinic.com`
- Password: `admin123`

Change this password after first login in a real-world setup.

## If it does not run
- If `ModuleNotFoundError: No module named 'flask'`:
  - `python -m pip install -r requirements.txt`
- If PowerShell blocks activation scripts:
  - Use `run.bat`, or run directly without activation:
  - `.\.venv\Scripts\python.exe -m pip install -r requirements.txt`
  - `.\.venv\Scripts\python.exe app.py`
- If port 5000 is already in use:
  - `python -m flask --app app run --port 5001`
  - then open `http://127.0.0.1:5001`

## Deploy on Vercel

1. Push this repo to GitHub and [import it on Vercel](https://vercel.com/new).
2. Add a **Postgres** database:
   - In your Vercel project, go to **Storage** → **Create Database** → **Postgres**
   - This sets `POSTGRES_URL` automatically.
3. Add environment variable (if not using Vercel Postgres):
   - `SECRET_KEY` – a random string for session security
4. Deploy. Vercel will detect the Flask app and build it.

**Note:** Locally the app uses SQLite. On Vercel it uses PostgreSQL via `POSTGRES_URL`.
