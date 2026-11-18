# VIVA_PREPARATION

## What ParkEase does
Manages 50 parking spots: dashboard, register vehicle (auto-allocate), change spot, search, release.

## Who does what
- **Frontend** (templates, CSS, JS): shows data, sends forms. 
- **Backend** (`app.py`): receives requests, validates, calls database functions, chooses the page/message.
- **Database** (`database.py`, `schema.sql`): stores data, enforces rules.

## Core ideas, in our implementation
- **Flask route**: `@app.get("/search")` maps a URL to a Python function that returns a page.
- **GET vs POST**: GET only reads (dashboard, search, confirmation page). POST changes data (register, reassign, release). Refreshing a GET never changes data.
- **Post/Redirect/Get**: after a successful POST we redirect, so pressing refresh cannot register the vehicle twice.
- **SQLite**: a database stored in one file (`parkease.db`), used through Python's `sqlite3`.
- **Primary key**: `id` uniquely identifies a row. **Foreign key**: `vehicles.spot_id` must be an existing `parking_spots.id` (enforced because we run `PRAGMA foreign_keys=ON` on each connection).
- **UNIQUE / NOT NULL**: UNIQUE on registration, mobile, spot_id stops duplicates; NOT NULL stops missing data.
- **Parameterized SQL**: `execute("... WHERE mobile_number = ?", (mobile,))` - input is passed separately, so SQL injection is not possible.

## Flows
- **Automatic allocation**: in one transaction we check duplicates, run `SELECT` for the lowest-id spot with no vehicle, then `INSERT` the vehicle with that spot_id.
- **Manual reassignment**: user picks from a list of free spots; in one transaction we check the vehicle exists, the spot exists and is free, then run one `UPDATE vehicles SET spot_id=?`. If anything fails, rollback and the old spot stays.
- **Release**: confirmation page -> POST -> `DELETE FROM vehicles WHERE id=?`. The spot becomes free automatically because nothing references it; the registration and mobile numbers become reusable.
- **Dashboard counts**: spots LEFT JOIN vehicles; occupied = spots that have a vehicle; available = 50 - occupied. Nothing is stored or counted in JavaScript.
- **Two vehicles, one spot?** Impossible: `BEGIN IMMEDIATE` serializes writers, and UNIQUE(spot_id) rejects it even if code were wrong.
- **Duplicates**: we check first (clear message), and the UNIQUE constraints catch races.
- **Why transactions**: all-or-nothing; no half-finished operation, no double allocation.
- **Normalization**: `dl 8c-ab 1234` and `DL8CAB1234` are the same vehicle; mobile `+91 98765 43210` is stored as `9876543210`.

## Testing
`python -m unittest discover -s tests -v`. 29 tests cover init, allocation, duplicates, validation, full capacity, reassign, search, release, counts, missing records. They use temporary database files, so real data is safe.

## Likely questions
1. *Why no status column?* Two sources of truth could disagree; occupancy is derived from vehicle rows.
2. *What stops SQL injection?* Parameterized queries with `?`.
3. *What if two users register at the same time?* `BEGIN IMMEDIATE` makes them take turns; the second sees the first's spot as taken.
4. *Why delete instead of marking released?* Requirement: no history; deleting frees all unique values automatically.
5. *Why validate in backend if the form has hints?* Anyone can bypass the browser; the backend and database are the real protection.
6. *Difference between a primary and a foreign key?* Primary identifies a row in its own table; foreign refers to another table's primary key.
7. *What happens when all 50 spots are full?* Registration returns a clear message and inserts nothing.

## Limitations
Single facility, no login or roles, no history/reports, SQLite suits light local use only, Flask dev server is not for production, no real-time auto-refresh (page reloads show latest data).
