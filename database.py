"""
ParkEase - database layer (Person 4 area, shared by everyone).

ALL SQL lives in this file. app.py only calls the functions below.

Key ideas
---------
* A spot is occupied iff a row in `vehicles` has spot_id = that spot's id.
* Every connection enables PRAGMA foreign_keys = ON.
* Every write runs inside BEGIN IMMEDIATE ... COMMIT, so two simultaneous
  requests cannot both grab the same free spot.
* All SQL is parameterized (the ? placeholders). User input is never pasted
  into SQL strings.
* Functions expect ALREADY-VALIDATED, ALREADY-NORMALIZED input (see app.py).
"""
import os
import sqlite3
from contextlib import closing, contextmanager

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.environ.get("PARKEASE_DB", os.path.join(BASE_DIR, "parkease.db"))
SCHEMA_PATH = os.path.join(BASE_DIR, "schema.sql")
TOTAL_SPOTS = 50


# ---- Errors the routes can turn into friendly messages --------------------
class ParkEaseError(Exception):
    """Base class for expected, user-facing problems."""


class DuplicateRegistration(ParkEaseError):
    pass


class DuplicateMobile(ParkEaseError):
    pass


class NoSpotAvailable(ParkEaseError):
    pass


class SpotNotAvailable(ParkEaseError):
    pass


class VehicleNotFound(ParkEaseError):
    pass


class SpotNotFound(ParkEaseError):
    pass


# ---- Connections and transactions -----------------------------------------
def get_connection(db_path=None):
    """Open a connection with foreign keys ON. isolation_level=None means we
    control transactions ourselves (explicit BEGIN/COMMIT)."""
    conn = sqlite3.connect(db_path or DB_PATH, timeout=10, isolation_level=None)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


@contextmanager
def transaction(db_path=None):
    """BEGIN IMMEDIATE takes the write lock up front, so the 'find a free spot'
    check and the INSERT happen as one indivisible step. Any exception rolls
    everything back."""
    conn = get_connection(db_path)
    try:
        conn.execute("BEGIN IMMEDIATE")
        yield conn
        conn.execute("COMMIT")
    except BaseException:
        try:
            conn.execute("ROLLBACK")
        except sqlite3.Error:
            pass
        raise
    finally:
        conn.close()


# ---- Initialization --------------------------------------------------------
def init_db(db_path=None):
    """Create tables and seed P01..P50. Safe to run on every start:
    CREATE TABLE IF NOT EXISTS + INSERT OR IGNORE never create duplicates."""
    with closing(get_connection(db_path)) as conn:
        with open(SCHEMA_PATH, encoding="utf-8") as f:
            conn.executescript(f.read())
        conn.execute("BEGIN IMMEDIATE")
        conn.executemany(
            "INSERT OR IGNORE INTO parking_spots (id, spot_number) VALUES (?, ?)",
            [(i, f"P{i:02d}") for i in range(1, TOTAL_SPOTS + 1)],
        )
        conn.execute("COMMIT")


# ---- Reading ---------------------------------------------------------------
_VEHICLE_SELECT = """
    SELECT v.id, v.registration_number, v.owner_name, v.mobile_number,
           s.spot_number
    FROM vehicles v JOIN parking_spots s ON s.id = v.spot_id
"""


def get_dashboard_data(db_path=None):
    """Return every spot (with vehicle_id if occupied) and the three counts.
    Counts come straight from the tables, never from stored counters."""
    with closing(get_connection(db_path)) as conn:
        spots = [dict(r) for r in conn.execute(
            """SELECT s.id, s.spot_number, v.id AS vehicle_id
               FROM parking_spots s LEFT JOIN vehicles v ON v.spot_id = s.id
               ORDER BY s.id""")]
    occupied = sum(1 for s in spots if s["vehicle_id"] is not None)
    return {"spots": spots, "total": len(spots),
            "occupied": occupied, "available": len(spots) - occupied}


def get_available_spots(db_path=None):
    """Spot numbers with no vehicle, in numerical order."""
    with closing(get_connection(db_path)) as conn:
        return [r["spot_number"] for r in conn.execute(
            """SELECT s.spot_number FROM parking_spots s
               WHERE NOT EXISTS (SELECT 1 FROM vehicles v WHERE v.spot_id = s.id)
               ORDER BY s.id""")]


def get_vehicle(vehicle_id, db_path=None):
    with closing(get_connection(db_path)) as conn:
        row = conn.execute(_VEHICLE_SELECT + " WHERE v.id = ?", (vehicle_id,)).fetchone()
    return dict(row) if row else None


def find_vehicle_by_registration(normalized_reg, db_path=None):
    """Only active vehicles exist in the table, so released ones never match."""
    with closing(get_connection(db_path)) as conn:
        row = conn.execute(_VEHICLE_SELECT + " WHERE v.registration_number = ?",
                           (normalized_reg,)).fetchone()
    return dict(row) if row else None


def get_vehicle_by_spot(spot_number, db_path=None):
    """Return (spot_exists, vehicle_or_None) for a spot number like 'P05'."""
    with closing(get_connection(db_path)) as conn:
        spot = conn.execute("SELECT id FROM parking_spots WHERE spot_number = ?",
                            (spot_number,)).fetchone()
        if spot is None:
            return False, None
        row = conn.execute(_VEHICLE_SELECT + " WHERE v.spot_id = ?",
                           (spot["id"],)).fetchone()
    return True, (dict(row) if row else None)


# ---- Writing ---------------------------------------------------------------
def register_vehicle(registration_number, owner_name, mobile_number, db_path=None):
    """Check duplicates, pick the FIRST free spot, insert - all in one
    transaction. Returns the new vehicle dict (with spot_number)."""
    with transaction(db_path) as conn:
        if conn.execute("SELECT 1 FROM vehicles WHERE registration_number = ?",
                        (registration_number,)).fetchone():
            raise DuplicateRegistration(
                "This vehicle registration number is already parked in ParkEase.")
        if conn.execute("SELECT 1 FROM vehicles WHERE mobile_number = ?",
                        (mobile_number,)).fetchone():
            raise DuplicateMobile(
                "This mobile number already has an active vehicle in ParkEase.")
        spot = conn.execute(
            """SELECT s.id FROM parking_spots s
               WHERE NOT EXISTS (SELECT 1 FROM vehicles v WHERE v.spot_id = s.id)
               ORDER BY s.id LIMIT 1""").fetchone()
        if spot is None:
            raise NoSpotAvailable("All 50 parking spots are occupied. "
                                  "Please try again after a vehicle is released.")
        try:
            cur = conn.execute(
                "INSERT INTO vehicles (registration_number, owner_name, mobile_number, spot_id) "
                "VALUES (?, ?, ?, ?)",
                (registration_number, owner_name, mobile_number, spot["id"]))
        except sqlite3.IntegrityError as e:  # constraint is the last line of defence
            raise _translate_integrity_error(e)
        vehicle_id = cur.lastrowid
    return get_vehicle(vehicle_id, db_path)


def reassign_spot(vehicle_id, new_spot_number, db_path=None):
    """Move a vehicle to another FREE spot with a single UPDATE. If anything
    fails the transaction rolls back and the vehicle keeps its old spot."""
    with transaction(db_path) as conn:
        vehicle = conn.execute("SELECT id, spot_id FROM vehicles WHERE id = ?",
                               (vehicle_id,)).fetchone()
        if vehicle is None:
            raise VehicleNotFound("That vehicle is not registered (it may already have been released).")
        spot = conn.execute("SELECT id FROM parking_spots WHERE spot_number = ?",
                            (new_spot_number,)).fetchone()
        if spot is None:
            raise SpotNotFound("That parking spot does not exist.")
        if spot["id"] == vehicle["spot_id"]:
            raise SpotNotAvailable("The vehicle is already in that spot.")
        if conn.execute("SELECT 1 FROM vehicles WHERE spot_id = ?", (spot["id"],)).fetchone():
            raise SpotNotAvailable(f"Spot {new_spot_number} is occupied. Please choose an available spot.")
        try:
            conn.execute("UPDATE vehicles SET spot_id = ? WHERE id = ?", (spot["id"], vehicle_id))
        except sqlite3.IntegrityError as e:
            raise _translate_integrity_error(e)
    return get_vehicle(vehicle_id, db_path)


def release_vehicle(vehicle_id, db_path=None):
    """DELETE the vehicle row. That alone frees the spot, the registration
    number and the mobile number. No history is kept. Returns the deleted
    vehicle's details (for the success message)."""
    with transaction(db_path) as conn:
        row = conn.execute(_VEHICLE_SELECT + " WHERE v.id = ?", (vehicle_id,)).fetchone()
        if row is None:
            raise VehicleNotFound("That vehicle is not registered (it may already have been released).")
        conn.execute("DELETE FROM vehicles WHERE id = ?", (vehicle_id,))
    return dict(row)


def _translate_integrity_error(err):
    msg = str(err)
    if "registration_number" in msg:
        return DuplicateRegistration("This vehicle registration number is already parked in ParkEase.")
    if "mobile_number" in msg:
        return DuplicateMobile("This mobile number already has an active vehicle in ParkEase.")
    return SpotNotAvailable("That parking spot was just taken. Please choose another.")


if __name__ == "__main__":
    init_db()
    print(f"Database ready at {DB_PATH}")
