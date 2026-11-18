-- ParkEase schema. Two tables only. There is deliberately NO "status" column:
-- a spot is occupied exactly when a vehicle row references its id.

CREATE TABLE IF NOT EXISTS parking_spots (
    id          INTEGER PRIMARY KEY,
    spot_number TEXT UNIQUE NOT NULL            -- P01 ... P50
);

CREATE TABLE IF NOT EXISTS vehicles (
    id                  INTEGER PRIMARY KEY,
    registration_number TEXT UNIQUE NOT NULL,   -- normalized: uppercase, no spaces/hyphens
    owner_name          TEXT NOT NULL CHECK (length(trim(owner_name)) > 0),
    mobile_number       TEXT UNIQUE NOT NULL,   -- canonical 10 digits
    spot_id             INTEGER UNIQUE NOT NULL -- UNIQUE => one vehicle per spot
                        REFERENCES parking_spots(id)
);
