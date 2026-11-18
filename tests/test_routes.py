"""Route/validation tests using Flask's test client and a temporary database."""
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import app as parkease
import database as db

GOOD = {"registration_number": "DL 8C AB 1234", "owner_name": "Aarav Sharma", "mobile_number": "+91 98765-43210"}


class RouteTests(unittest.TestCase):
    def setUp(self):
        fd, self.path = tempfile.mkstemp(suffix=".db")
        os.close(fd)
        self.app = parkease.create_app(self.path)
        self.app.config["TESTING"] = True
        self.client = self.app.test_client()

    def tearDown(self):
        os.remove(self.path)

    def register(self, **over):
        data = dict(GOOD, **over)
        return self.client.post("/register", data=data)

    def test_dashboard_shows_50_spots_and_counts(self):
        r = self.client.get("/")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.data.count(b'class="spot available"'), 50)
        self.assertIn(b"P50", r.data)

    def test_register_success_and_normalization(self):
        r = self.register()
        self.assertEqual(r.status_code, 302)  # Post/Redirect/Get
        page = self.client.get(r.headers["Location"]).data
        self.assertIn(b"DL8CAB1234", page)
        self.assertIn(b"9876543210", page)
        self.assertIn(b"P01", page)
        self.assertEqual(db.get_dashboard_data(self.path)["occupied"], 1)

    def test_register_page_has_number_plate_hint(self):
        self.assertIn(b"number plate", self.client.get("/register").data)

    def test_invalid_and_missing_fields(self):
        for over in ({"registration_number": ""}, {"registration_number": "!!"}, {"registration_number": "ABC"},
                     {"owner_name": ""}, {"owner_name": "R2D2"}, {"mobile_number": ""},
                     {"mobile_number": "12345"}, {"mobile_number": "5876543210"}):
            r = self.register(**over)
            self.assertEqual(r.status_code, 400, over)
        self.assertEqual(db.get_dashboard_data(self.path)["occupied"], 0)

    def test_duplicates_rejected(self):
        self.register()
        r = self.register(registration_number="dl-8c-ab-1234", mobile_number="9000000000")
        self.assertEqual(r.status_code, 409)
        self.assertIn(b"already parked", r.data)
        r = self.register(registration_number="MH12AB9999")  # same mobile
        self.assertEqual(r.status_code, 409)
        self.assertIn(b"mobile number already", r.data)

    def test_full_capacity_graceful(self):
        for i in range(50):
            self.register(registration_number=f"MH12AB{1000 + i}", mobile_number=f"9{i:09d}")
        r = self.register(registration_number="KA01ZZ9999", mobile_number="9111111111")
        self.assertEqual(r.status_code, 409)
        self.assertIn(b"All 50 parking spots are occupied", r.data)
        self.assertEqual(db.get_dashboard_data(self.path)["occupied"], 50)

    def test_search_case_space_hyphen_insensitive(self):
        self.register()
        r = self.client.get("/search", query_string={"registration_number": "dl-8c ab-1234"})
        self.assertIn(b"Aarav Sharma", r.data)
        r = self.client.get("/search", query_string={"registration_number": "MH12AB0000"})
        self.assertIn(b"No currently parked vehicle", r.data)

    def test_spot_info_endpoint(self):
        self.register()
        j = self.client.get("/spot/P01").get_json()
        self.assertTrue(j["occupied"])
        self.assertEqual(j["vehicle"]["owner_name"], "Aarav Sharma")
        self.assertFalse(self.client.get("/spot/P02").get_json()["occupied"])
        self.assertEqual(self.client.get("/spot/P99").status_code, 404)

    def test_reassign_flow(self):
        self.register()
        vid = db.find_vehicle_by_registration("DL8CAB1234", self.path)["id"]
        self.client.post(f"/vehicle/{vid}/reassign", data={"spot_number": "P08"})
        self.assertEqual(db.get_vehicle(vid, self.path)["spot_number"], "P08")
        self.register(registration_number="MH12AB1111", mobile_number="9000000001")  # takes P01
        self.client.post(f"/vehicle/{vid}/reassign", data={"spot_number": "P01"})  # occupied now
        self.assertEqual(db.get_vehicle(vid, self.path)["spot_number"], "P08")
        self.assertEqual(self.client.post("/vehicle/999/reassign", data={"spot_number": "P05"}).status_code, 404)

    def test_release_requires_confirmation(self):
        self.register()
        vid = db.find_vehicle_by_registration("DL8CAB1234", self.path)["id"]
        self.assertEqual(self.client.get(f"/vehicle/{vid}/release").status_code, 200)  # GET only asks
        self.assertIsNotNone(db.get_vehicle(vid, self.path))
        self.client.post(f"/vehicle/{vid}/release", data={})  # not confirmed
        self.assertIsNotNone(db.get_vehicle(vid, self.path))
        r = self.client.post(f"/vehicle/{vid}/release", data={"confirm": "yes"})
        self.assertEqual(r.status_code, 302)
        self.assertIsNone(db.get_vehicle(vid, self.path))
        self.assertEqual(db.get_dashboard_data(self.path)["available"], 50)
        self.assertEqual(self.register().status_code, 302)  # can register again

    def test_release_missing_vehicle(self):
        self.assertEqual(self.client.post("/vehicle/999/release", data={"confirm": "yes"}).status_code, 404)
        self.assertEqual(self.client.get("/vehicle/999/release").status_code, 404)


if __name__ == "__main__":
    unittest.main()
