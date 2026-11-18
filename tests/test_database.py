"""Database-layer tests. Each test uses its own temporary database file."""
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import database as db


def make_vehicle(i):
    return (f"MH12AB{1000 + i}", f"Owner {i}", f"9{i:09d}")


class DatabaseTests(unittest.TestCase):
    def setUp(self):
        fd, self.path = tempfile.mkstemp(suffix=".db")
        os.close(fd)
        db.init_db(self.path)

    def tearDown(self):
        os.remove(self.path)

    def reg(self, i):
        return db.register_vehicle(*make_vehicle(i), db_path=self.path)

    def counts(self):
        d = db.get_dashboard_data(self.path)
        self.assertEqual(d["total"], 50)
        self.assertEqual(d["available"] + d["occupied"], 50)
        return d["available"], d["occupied"]

    def test_01_exactly_50_spots(self):
        d = db.get_dashboard_data(self.path)
        self.assertEqual(len(d["spots"]), 50)
        self.assertEqual(d["spots"][0]["spot_number"], "P01")
        self.assertEqual(d["spots"][-1]["spot_number"], "P50")

    def test_02_init_twice_no_duplicates(self):
        db.init_db(self.path)
        db.init_db(self.path)
        self.assertEqual(db.get_dashboard_data(self.path)["total"], 50)

    def test_03_initial_counts(self):
        self.assertEqual(self.counts(), (50, 0))

    def test_04_register_valid(self):
        v = self.reg(1)
        self.assertEqual(v["owner_name"], "Owner 1")
        self.assertEqual(self.counts(), (49, 1))

    def test_05_first_available_spot(self):
        self.assertEqual(self.reg(1)["spot_number"], "P01")
        self.assertEqual(self.reg(2)["spot_number"], "P02")
        db.release_vehicle(self.reg(3)["id"] - 2, self.path)  # release first vehicle (P01)
        self.assertEqual(self.reg(4)["spot_number"], "P01")   # lowest free spot reused

    def test_06_duplicate_registration(self):
        self.reg(1)
        with self.assertRaises(db.DuplicateRegistration):
            db.register_vehicle("MH12AB1001", "Other", "9999999999", self.path)
        self.assertEqual(self.counts(), (49, 1))

    def test_07_duplicate_mobile(self):
        self.reg(1)
        with self.assertRaises(db.DuplicateMobile):
            db.register_vehicle("KA01XY9999", "Other", make_vehicle(1)[2], self.path)
        self.assertEqual(self.counts(), (49, 1))

    def test_09_full_capacity(self):
        for i in range(1, 51):
            self.reg(i)
        self.assertEqual(self.counts(), (0, 50))
        with self.assertRaises(db.NoSpotAvailable):
            self.reg(51)
        self.assertEqual(self.counts(), (0, 50))  # nothing inserted

    def test_10_reassign_to_available(self):
        v = self.reg(1)
        out = db.reassign_spot(v["id"], "P08", self.path)
        self.assertEqual(out["spot_number"], "P08")
        self.assertIn("P01", db.get_available_spots(self.path))
        self.assertNotIn("P08", db.get_available_spots(self.path))

    def test_11_reassign_to_occupied_rejected(self):
        a, b = self.reg(1), self.reg(2)
        with self.assertRaises(db.SpotNotAvailable):
            db.reassign_spot(a["id"], b["spot_number"], self.path)
        self.assertEqual(db.get_vehicle(a["id"], self.path)["spot_number"], "P01")  # unchanged

    def test_12_reassign_no_duplicate_records(self):
        v = self.reg(1)
        db.reassign_spot(v["id"], "P20", self.path)
        self.assertEqual(self.counts(), (49, 1))

    def test_13_search_existing(self):
        self.reg(1)
        v = db.find_vehicle_by_registration("MH12AB1001", self.path)
        self.assertEqual((v["owner_name"], v["spot_number"]), ("Owner 1", "P01"))

    def test_14_search_missing(self):
        self.assertIsNone(db.find_vehicle_by_registration("NOPE000000", self.path))

    def test_15_release_deletes(self):
        v = self.reg(1)
        db.release_vehicle(v["id"], self.path)
        self.assertIsNone(db.get_vehicle(v["id"], self.path))
        self.assertIsNone(db.find_vehicle_by_registration("MH12AB1001", self.path))

    def test_16_release_frees_spot(self):
        v = self.reg(1)
        db.release_vehicle(v["id"], self.path)
        self.assertIn("P01", db.get_available_spots(self.path))
        self.assertEqual(self.counts(), (50, 0))

    def test_17_reuse_after_release(self):
        v = self.reg(1)
        db.release_vehicle(v["id"], self.path)
        again = self.reg(1)  # same registration AND mobile
        self.assertEqual(again["spot_number"], "P01")

    def test_19_nonexistent_records(self):
        with self.assertRaises(db.VehicleNotFound):
            db.release_vehicle(999, self.path)
        with self.assertRaises(db.VehicleNotFound):
            db.reassign_spot(999, "P05", self.path)
        v = self.reg(1)
        with self.assertRaises(db.SpotNotFound):
            db.reassign_spot(v["id"], "P99", self.path)
        self.assertEqual(db.get_vehicle(v["id"], self.path)["spot_number"], "P01")

    def test_db_constraints_enforced_directly(self):
        """The database itself rejects a second vehicle on the same spot."""
        import sqlite3
        v = self.reg(1)
        conn = db.get_connection(self.path)
        with self.assertRaises(sqlite3.IntegrityError):
            conn.execute("INSERT INTO vehicles (registration_number, owner_name, mobile_number, spot_id) "
                         "VALUES ('ZZ99ZZ9999','X','9000000000',1)")
        with self.assertRaises(sqlite3.IntegrityError):  # foreign key: spot 999 does not exist
            conn.execute("INSERT INTO vehicles (registration_number, owner_name, mobile_number, spot_id) "
                         "VALUES ('ZZ99ZZ9998','X','9000000001',999)")
        conn.close()


if __name__ == "__main__":
    unittest.main()
