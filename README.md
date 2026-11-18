# ParkEase

A local parking management web app: view availability of 50 spots, register vehicles (automatic spot allocation, optional manual change), search by number plate, and release vehicles with confirmation.

## Features
- Dashboard with 50 spots (P01-P50): green = available, red = occupied; total / available / occupied counts read from SQLite
- Register a vehicle (official number-plate registration number, owner's name, mobile number) with automatic first-free-spot allocation
- Move a vehicle to another currently available spot
- Search by registration number (case, spaces and hyphens ignored)
- Release by search result or by clicking an occupied spot; always asks for confirmation; the vehicle record is deleted (no history kept)

## Technology
Python 3.9+, Flask, SQLite (built-in `sqlite3`), Jinja templates, HTML, CSS, vanilla JavaScript.

## Structure
```
ParkEase/
├── app.py            routes, validation, messages
├── database.py       ALL SQL, transactions, shared DB functions
├── schema.sql        tables + constraints
├── requirements.txt  Flask
├── templates/        base, index, register, search, vehicle, confirm_release, error
├── static/           style.css, script.js
├── tests/            test_database.py, test_routes.py
└── PROJECT_CONTEXT.md, DESIGN_DECISIONS.md, VIVA_PREPARATION.md
```

## Setup and run
```bash
cd ParkEase
python -m venv venv
venv\Scripts\activate          # Windows   (macOS/Linux: source venv/bin/activate)
pip install -r requirements.txt
python app.py
```
Open http://127.0.0.1:5000 . The file `parkease.db` is created automatically on first run (it is git-ignored).

## Run the tests
```bash
python -m unittest discover -s tests -v
```
Tests use temporary databases, never `parkease.db`.

## Notes
- Registration numbers are stored normalized (uppercase, no spaces/hyphens), e.g. `DL8CAB1234`; mobile numbers as 10 digits.
- To start fresh, stop the app and delete `parkease.db`.
- Set `PARKEASE_SECRET` to a random string if you ever deploy beyond a laptop.
