# ParkEase
### Smart Parking Management System

ParkEase is a web-based parking management application built using Python, Flask, and SQLite. It helps manage parking availability, vehicle registration, parking allocation, vehicle search, and spot release through a simple and interactive dashboard.

The application is designed to run locally on a computer through a web browser.

---

## Features

- **Interactive Dashboard:** Displays all 50 parking spots with real-time availability information.
- **Visual Parking Status:** Green indicates available spots, while red indicates occupied spots.
- **Parking Statistics:** Displays total, available, and occupied parking spots.
- **Vehicle Registration:** Register vehicles using their official number-plate registration number, owner's name, and mobile number.
- **Automatic Allocation:** Automatically assigns the first available parking spot.
- **Manual Reassignment:** Allows users to change the allocated spot to another available spot.
- **Vehicle Search:** Search for parked vehicles using their registration number.
- **Vehicle Information:** View vehicle details and assigned parking location.
- **Vehicle Release:** Release vehicles through either the search page or the dashboard.
- **Database Management:** Stores active vehicle and parking allocation information using SQLite.

## Technology Stack

| Technology | Purpose |
|---|---|
| Python | Backend logic and validation |
| Flask | Web application framework |
| SQLite | Database management |
| HTML | Webpage structure |
| CSS | Styling and responsive design |
| JavaScript | Frontend interactions |
| Jinja | Dynamic HTML rendering |

## Project Structure

```text
ParkEase/
│
├── app.py
├── database.py
├── schema.sql
├── requirements.txt
├── .gitignore
│
├── templates/
│   ├── base.html
│   ├── index.html
│   ├── register.html
│   └── search.html
│
├── static/
│   ├── style.css
│   └── script.js
│
├── tests/
│   ├── test_database.py
│   └── test_routes.py
│
├── README.md
├── PROJECT_CONTEXT.md
├── DESIGN_DECISIONS.md
└── VIVA_PREPARATION.md
```

## How to Use ParkEase

1. Open the dashboard to view all 50 parking spots.
2. Navigate to **Register Vehicle** to register a vehicle.
3. Enter the vehicle's official number-plate registration number, owner's name, and mobile number.
4. The application automatically allocates the first available parking spot.
5. If needed, select another available spot.
6. Use **Search Vehicle** to find a currently parked vehicle.
7. Click an occupied parking spot to view its associated vehicle.
8. Release a vehicle after confirming the action.

Once a vehicle is released, its parking spot becomes available again.

## Database Design

ParkEase uses SQLite with two primary tables:

**parking_spots**
- Stores the 50 parking spot identifiers.
- Each spot has a unique identifier.

**vehicles**
- Stores currently registered vehicles.
- Contains the vehicle registration number, owner's name, mobile number, and assigned parking spot.

Parking occupancy is derived from vehicle allocations rather than maintained using a separate status column.

Database constraints help prevent:
- Duplicate active vehicle registration numbers.
- Multiple active allocations for one mobile number.
- Multiple vehicles occupying the same parking spot.

Released vehicle records are deleted. The application does not maintain parking history.

## Data and Application Scope

- Parking capacity is fixed at 50 spots.
- Only one active vehicle can be associated with a mobile number.
- Each active vehicle has exactly one parking spot.
- Released vehicles can register again.
- No login or authentication system is included.
- No payment system or parking history is maintained.
- The application is intended for local use.

## Project Objective

The objective of ParkEase is to demonstrate how a simple full-stack web application can combine frontend development, backend programming, database management, and software testing to solve a practical parking management problem.

---

