"""
ParkEase - Flask app: routes, validation, user messages.
Database work is delegated to database.py (no SQL in this file).
"""
import os
import re

from flask import (Flask, flash, jsonify, redirect, render_template, request,
                   url_for)

import database as db


# ---- Validation / normalization helpers -----------------------------------
def normalize_registration(raw):
    """'dl 8c-ab 1234' -> 'DL8CAB1234' (used for storing AND searching)."""
    return re.sub(r"[\s-]+", "", (raw or "").strip()).upper()


def validate_registration(raw):
    """Return (normalized, error). Deliberately lenient so old, new and BH-series
    plates all pass: 6-12 letters/digits with at least one of each."""
    raw = (raw or "").strip()
    if not raw:
        return None, "Vehicle registration number is required."
    if not re.fullmatch(r"[A-Za-z0-9 \-]+", raw):
        return None, ("Registration number may contain only letters, digits, "
                      "spaces and hyphens (example: DL 8C AB 1234).")
    norm = normalize_registration(raw)
    if not 6 <= len(norm) <= 12 or not re.search(r"[A-Z]", norm) or not re.search(r"\d", norm):
        return None, ("Enter the number printed on the vehicle's number plate, "
                      "for example DL 8C AB 1234 or MH 12 AB 1234.")
    return norm, None


def validate_owner_name(raw):
    name = re.sub(r"\s+", " ", (raw or "").strip())
    if not name:
        return None, "Owner's name is required."
    if len(name) < 2 or len(name) > 60:
        return None, "Owner's name must be between 2 and 60 characters."
    if not all(c.isalpha() or c in " .'-" for c in name) or sum(c.isalpha() for c in name) < 2:
        return None, "Owner's name may contain only letters, spaces, dots, apostrophes and hyphens."
    return name, None


def normalize_mobile(raw):
    """Return canonical 10 digits or None. Accepts +91 / 91 prefix and spaces/hyphens."""
    s = re.sub(r"[\s-]+", "", (raw or "").strip())
    if s.startswith("+91"):
        s = s[3:]
    elif len(s) == 12 and s.startswith("91"):
        s = s[2:]
    return s if re.fullmatch(r"[6-9]\d{9}", s) else None


def validate_mobile(raw):
    if not (raw or "").strip():
        return None, "Mobile number is required."
    m = normalize_mobile(raw)
    if m is None:
        return None, ("Enter a valid 10-digit Indian mobile number starting with 6-9 "
                      "(optional +91, e.g. +91 98765 43210).")
    return m, None


# ---- App factory -----------------------------------------------------------
def create_app(db_path=None):
    app = Flask(__name__)
    app.config["SECRET_KEY"] = os.environ.get("PARKEASE_SECRET", "dev-only-change-me")
    app.config["DATABASE"] = db_path or db.DB_PATH
    db.init_db(app.config["DATABASE"])

    def path():
        return app.config["DATABASE"]

    # -- Dashboard
    @app.get("/")
    def index():
        return render_template("index.html", data=db.get_dashboard_data(path()))

    # -- Spot information (JSON, used by the dashboard pop-up)
    @app.get("/spot/<spot_number>")
    def spot_info(spot_number):
        exists, vehicle = db.get_vehicle_by_spot(spot_number.upper(), path())
        if not exists:
            return jsonify(error="Spot not found"), 404
        return jsonify(spot_number=spot_number.upper(), occupied=vehicle is not None,
                       vehicle=vehicle)

    # -- Registration
    @app.route("/register", methods=["GET", "POST"])
    def register():
        if request.method == "GET":
            return render_template("register.html", form={}, errors={})
        form = {k: request.form.get(k, "").strip() for k in ("registration_number", "owner_name", "mobile_number")}
        reg, e1 = validate_registration(form["registration_number"])
        name, e2 = validate_owner_name(form["owner_name"])
        mobile, e3 = validate_mobile(form["mobile_number"])
        errors = {k: e for k, e in (("registration_number", e1), ("owner_name", e2), ("mobile_number", e3)) if e}
        if errors:
            return render_template("register.html", form=form, errors=errors), 400
        try:
            vehicle = db.register_vehicle(reg, name, mobile, path())
        except db.DuplicateRegistration as e:
            return render_template("register.html", form=form, errors={"registration_number": str(e)}), 409
        except db.DuplicateMobile as e:
            return render_template("register.html", form=form, errors={"mobile_number": str(e)}), 409
        except db.NoSpotAvailable as e:
            return render_template("register.html", form=form, errors={"general": str(e)}), 409
        flash(f"Registration successful! Spot {vehicle['spot_number']} has been allocated "
              f"to {vehicle['registration_number']}.", "success")
        return redirect(url_for("vehicle_detail", vehicle_id=vehicle["id"]))  # Post/Redirect/Get

    # -- Vehicle detail page (reassignment + release entry point)
    @app.get("/vehicle/<int:vehicle_id>")
    def vehicle_detail(vehicle_id):
        vehicle = db.get_vehicle(vehicle_id, path())
        if vehicle is None:
            return render_template("error.html", message="That vehicle is not registered."), 404
        return render_template("vehicle.html", vehicle=vehicle,
                               available=db.get_available_spots(path()))

    @app.post("/vehicle/<int:vehicle_id>/reassign")
    def reassign(vehicle_id):
        new_spot = request.form.get("spot_number", "").strip().upper()
        try:
            vehicle = db.reassign_spot(vehicle_id, new_spot, path())
        except db.VehicleNotFound as e:
            return render_template("error.html", message=str(e)), 404
        except db.ParkEaseError as e:
            flash(str(e), "error")
            return redirect(url_for("vehicle_detail", vehicle_id=vehicle_id))
        flash(f"Spot changed. {vehicle['registration_number']} is now in {vehicle['spot_number']}.", "success")
        return redirect(url_for("vehicle_detail", vehicle_id=vehicle_id))

    # -- Search (GET: it only reads data)
    @app.get("/search")
    def search():
        raw = request.args.get("registration_number")
        if raw is None:
            return render_template("search.html", query="", searched=False, vehicle=None, error=None)
        norm, error = validate_registration(raw)
        if error:
            return render_template("search.html", query=raw, searched=True, vehicle=None, error=error), 400
        vehicle = db.find_vehicle_by_registration(norm, path())
        return render_template("search.html", query=raw, searched=True, vehicle=vehicle, error=None)

    # -- Release: GET shows the confirmation page, POST does the deletion
    @app.get("/vehicle/<int:vehicle_id>/release")
    def release_confirm(vehicle_id):
        vehicle = db.get_vehicle(vehicle_id, path())
        if vehicle is None:
            return render_template("error.html", message="That vehicle is not registered."), 404
        return render_template("confirm_release.html", vehicle=vehicle)

    @app.post("/vehicle/<int:vehicle_id>/release")
    def release(vehicle_id):
        if request.form.get("confirm") != "yes":
            flash("Release was not confirmed, so nothing was changed.", "warning")
            return redirect(url_for("vehicle_detail", vehicle_id=vehicle_id))
        try:
            v = db.release_vehicle(vehicle_id, path())
        except db.VehicleNotFound as e:
            return render_template("error.html", message=str(e)), 404
        flash(f"Vehicle {v['registration_number']} released. Spot {v['spot_number']} is available again.", "success")
        return redirect(url_for("index"))

    @app.errorhandler(404)
    def not_found(_):
        return render_template("error.html", message="Page not found."), 404

    return app


if __name__ == "__main__":
    create_app().run(debug=True)
