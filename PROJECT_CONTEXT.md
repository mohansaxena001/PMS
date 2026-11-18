# PROJECT_CONTEXT - ParkEase (canonical reference)

## Purpose
Local parking management app for one facility with exactly 50 spots. No login, no history, no external services.

## Confirmed requirements (summary)
- Spots P01-P50 auto-created at DB initialization, never duplicated on restart.
- Dashboard: grid + total/available/occupied from the database. Available = green, occupied = red. Available spots are not clickable; occupied spots show the vehicle and offer release.
- Registration: registration number (official number plate), owner's name, mobile number. All mandatory. First free spot assigned automatically. Rejected if registration number or mobile number is already active, or if no spot is free (no row inserted).
- Reassignment: only to a currently available spot; vehicle never loses its spot if it fails.
- Search: by normalized registration number; active vehicles only.
- Release: two entry points (search result, dashboard spot) -> confirmation page -> POST deletes the row.

## Business rules (enforced by database + backend)
1. Exactly 50 spots. 2. One vehicle per spot (UNIQUE spot_id). 3. One active vehicle per mobile (UNIQUE). 4. One active record per registration number (UNIQUE). 5. No vehicle without a spot (spot_id NOT NULL). 6. Reassign only to a free spot. 7. Release deletes the row. 8. Released numbers can register again. 9. Counts derived from DB state. 10. No history. 11. No authentication.

## Normalization
- Registration: strip, remove spaces/hyphens, uppercase. Valid: letters/digits only, 6-12 chars, at least one letter and one digit (accepts old, new and BH-series plates).
- Mobile: remove spaces/hyphens, optional +91 (or 91 before 10 digits), must match `[6-9]\d{9}`; stored as 10 digits.
- Owner name: collapsed whitespace, 2-60 chars, letters plus space . ' -

## Database
`parking_spots(id PK, spot_number UNIQUE NOT NULL)` and `vehicles(id PK, registration_number UNIQUE NOT NULL, owner_name NOT NULL, mobile_number UNIQUE NOT NULL, spot_id UNIQUE NOT NULL -> parking_spots.id)`.
No status column: a spot is occupied iff a vehicle references it. `PRAGMA foreign_keys=ON` on every connection. Writes use `BEGIN IMMEDIATE`.

## Routes
| Method | Path | Purpose |
|---|---|---|
| GET | `/` | Dashboard |
| GET | `/spot/<spot_number>` | JSON spot info (404 if unknown) |
| GET/POST | `/register` | Form / register (400 invalid, 409 duplicate or full, 302 on success) |
| GET | `/vehicle/<id>` | Vehicle details, change-spot form, release button |
| POST | `/vehicle/<id>/reassign` | Move to another available spot |
| GET | `/search?registration_number=` | Search (read-only) |
| GET | `/vehicle/<id>/release` | Confirmation page (changes nothing) |
| POST | `/vehicle/<id>/release` | Deletes vehicle if `confirm=yes` |

## File responsibilities
- `database.py`: connections, `transaction()`, `init_db`, `get_dashboard_data`, `get_available_spots`, `get_vehicle`, `find_vehicle_by_registration`, `get_vehicle_by_spot`, `register_vehicle`, `reassign_spot`, `release_vehicle`, custom exceptions (`DuplicateRegistration`, `DuplicateMobile`, `NoSpotAvailable`, `SpotNotAvailable`, `SpotNotFound`, `VehicleNotFound`).
- `app.py`: `create_app(db_path)`, validators, routes, flash messages. No SQL.
- `templates/`, `static/`: UI. `script.js` only adds a pop-up for occupied spots (page works without it).
- `tests/`: unittest suites on temporary databases.

## Team areas (one shared codebase)
Person 1 dashboard/UI (index.html, style.css, script.js) · Person 2 allocation/reassign/release (database.py write functions) · Person 3 registration/search/validation (app.py validators + routes, register/search templates) · Person 4 schema, init, shared DB functions, integration, tests (schema.sql, database.py, tests/).
