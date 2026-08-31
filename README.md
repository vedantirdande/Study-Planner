# Study Portal

A Flask + SQLite student resource portal for notes, previous-year question papers and shared academic PDFs.

## Features

- Student registration and login
- Secure password hashing
- Search and filter notes/PYQs by branch and semester
- PDF uploads with a 10 MB limit
- Unique server-generated upload filenames
- Student profile and resource management
- Edit/delete only your own resources
- Admin panel for user roles and resource moderation
- CSRF protection for all POST actions
- Responsive mobile-friendly UI

## Run locally (Windows PowerShell)

```powershell
cd "C:\Users\ASUS\Documents\GHRCEM_Study_Portal_Perfected"
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python database/init_db.py
python app.py
```

Open: `http://127.0.0.1:5000`

If PowerShell blocks activation, you can run the environment's Python directly:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe app.py
```

## Create an admin account

There is no public admin sign-up form. Register an account from the portal first, then promote that account from PowerShell using its exact registration number:

```powershell
python database\create_admin.py YOUR_ACTUAL_REGISTRATION_NUMBER
```

For example:

```powershell
python database\create_admin.py 2526CTFBTITE016
```

The command prints an error if the account does not exist. After a successful promotion, log out and log in again. The **Admin** link will appear in the navigation and on the dashboard.

## Important before deployment

Set a strong secret key in the environment:

```powershell
$env:SECRET_KEY="your-long-random-secret"
$env:FLASK_DEBUG="0"
python app.py
```

For production, use a production WSGI server such as Gunicorn on Linux/hosting rather than Flask's development server.

## Upload policy

Only PDF files are accepted and the maximum upload size is 10 MB.
