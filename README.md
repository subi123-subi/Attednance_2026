# WorkPulse - Python Attendance Management System

A full-stack, responsive Attendance Management System built with **Python**, **Flask**, and **SQLite**.

---

## 🌟 Key Features

### 1. 🛡️ Admin Portal
- **Secure Administrator Login**: Pre-configured admin dashboard.
- **Employee Registration & Password Creation**:
  - Admin registers employee details: *Employee Code, Full Name, Username, Email, Department, Designation, Phone, and Joining Date*.
  - **Admin assigns the login password** for each employee.
  - Password visibility toggle (show/hide) for easy admin reference and credential recovery.
  - Ability to edit details or reset employee passwords anytime.
- **Live Attendance Monitoring**:
  - Real-time tracker for on-duty employees currently checked in.
  - KPI metric cards: Total Employees, Present Today, Currently Checked In, Total Hours Logged Today, Attendance Rate.
- **Comprehensive Attendance Logs & Working Hours Calculation**:
  - Full company logs with exact Check-In, Check-Out, and calculated working duration ($H:M$ format & decimal hours).
  - Multi-criteria filters: Employee, Department, Date Range (Start/End Date), and Status.
  - **Admin Force Clock-Out**: Ability for the admin to manually clock out any employee who forgot to check out.
  - **CSV / Excel Export**: One-click download of attendance logs for payroll and auditing.

### 2. 👤 Employee Portal
- **Employee Authentication**:
  - Log in using Username or Employee Code along with the **password assigned by the Admin**.
- **Interactive Check-In & Check-Out**:
  - One-click **Check-In** button when arriving at work.
  - Live real-time counter showing the active session duration ($HH:MM:SS$).
  - One-click **Check-Out** button upon shift completion.
  - Optional shift notes (e.g., "Remote work", "Shift end").
- **Exact Working Hours Calculation**:
  - Automatically calculates exact working hours between Check-In and Check-Out.
  - Supports multiple check-ins per day (e.g. lunch breaks or split shifts) and aggregates daily totals.
- **Personal Dashboard Metrics**:
  - Today's Total Working Hours.
  - This Month's Total Logged Hours.
  - Days Worked this Month.
  - Daily Average Working Hours.
  - Detailed personal attendance history table.

---

## 🚀 Quick Start Guide

### Prerequisites
- Python 3.8+ (Python 3.14+ supported)
- Flask (`pip install Flask`)

### Running the Application

1. Navigate to the project directory:
   ```bash
   cd C:\Users\Admin\.gemini\antigravity\scratch\attendance_system
   ```

2. Start the Flask server:
   ```bash
   python app.py
   ```

3. Open your browser and visit:
   ```
   http://127.0.0.1:5000
   ```

---

## 🔑 Default Demo Credentials

| Role | Username / Code | Password | Access Level |
| :--- | :--- | :--- | :--- |
| **Admin** | `admin` (or `ADM001`) | `admin123` | Full administrative control, employee management, system logs |
| **Employee 1** | `john.doe` (or `EMP101`) | `emp123` | Personal check-in/out, hours tracking, history |
| **Employee 2** | `sarah.smith` (or `EMP102`) | `welcome2026` | Personal check-in/out, hours tracking, history |

> *Tip: You can also register brand new employees through the Admin portal with any password you choose!*

---

## 📂 Project Architecture

```
attendance_system/
│
├── app.py                  # Flask Application Routes & Authentication Logic
├── database.py             # SQLite Schema, Models, and Working Hours Calculation
├── test_system.py          # Automated Test Suite (Unit & Integration Tests)
├── attendance.db           # SQLite Database (Auto-generated on first run)
├── README.md               # Documentation & Setup Guide
│
└── templates/
    ├── base.html           # Base layout with Tailwind CSS & Live Digital Clock
    ├── login.html          # Dual portal Sign-In page with demo autofill
    ├── admin_dashboard.html# Admin overview with KPI cards & live active monitors
    ├── admin_employees.html# Employee directory, registration & password manager
    ├── admin_attendance.html# Detailed attendance logs, filters & CSV export
    └── employee_dashboard.html# Employee personal portal with live Check-In/Out timer
```

---

## ⚙️ How Working Hours Calculation Works

1. **Check-In**: When an employee clicks "Check In", a record is created with `check_in = CURRENT_TIMESTAMP` and status `Checked In`.
2. **Check-Out**: When the employee clicks "Check Out", the system:
   - Fetches the active check-in timestamp.
   - Computes:
     $$\text{Duration (seconds)} = \text{Check Out Timestamp} - \text{Check In Timestamp}$$
   - Formats the duration into human-readable format:
     $$\text{Hours} = \lfloor \text{seconds} / 3600 \rfloor, \quad \text{Minutes} = \lfloor (\text{seconds} \pmod{3600}) / 60 \rfloor \implies \mathbf{X\text{h } Y\text{m}}$$
   - Calculates decimal hours for payroll:
     $$\text{Decimal Hours} = \frac{\text{seconds}}{3600} \implies \mathbf{8.25\text{ hrs}}$$
3. **Daily Aggregation**: Sums all completed sessions for that date plus any currently active session in real-time.
