# DESIGN_DECISIONS

Each entry: chosen / why / alternative / why chosen fits.

**Flask.** Small, readable, routes are plain Python functions. Alternative: Django (more files, admin, ORM, too heavy). Fits a four-person college project that must be explained in a viva.

**SQLite.** One file, no server, built into Python (`sqlite3`). Alternative: MySQL/PostgreSQL (separate server to install). Fits a single-laptop app with a handful of users.

**Two tables.** `parking_spots` (the 50 fixed places) and `vehicles` (currently parked vehicles). Alternative: separate owners, allocations and history tables. Every extra table adds joins and ways to become inconsistent; the requirements only need current state.

**Occupancy derived from vehicles (no status column).** A spot is occupied iff some vehicle row has its `spot_id`. Alternative: `status` column kept in sync. That creates two sources of truth that can disagree (spot says free, vehicle says P05). Deriving makes disagreement impossible.

**Database constraints.** UNIQUE on registration, mobile and spot_id; NOT NULL; FOREIGN KEY with `PRAGMA foreign_keys=ON`. Alternative: only Python checks. Python checks give friendly messages but can be bypassed by bugs or simultaneous requests; constraints are the final guarantee. We use both.

**Transactions (`BEGIN IMMEDIATE`).** "Find free spot, then insert" is two steps; without a transaction two requests could both pick P01. `BEGIN IMMEDIATE` takes the write lock first, so they run one after another; on any error everything rolls back. Alternative: no transaction and hope. Not acceptable for allocation.

**Delete on release.** The vehicle row is deleted, which automatically frees spot, registration number and mobile number. Alternative: `released` flag. That would need partial unique indexes and filtering everywhere.

**No parking history.** Explicit requirement; also keeps the schema minimal and avoids storing personal data longer than needed. A history table could be added later without changing the current tables.

**Other choices.** Search uses GET (read-only); state changes use POST then redirect (Post/Redirect/Get). Release confirmation is a server-side page, so it works even without JavaScript. Release is GET-confirm then POST. `create_app(db_path)` lets tests use a temporary database. All SQL is parameterized.
