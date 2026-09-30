"""
Database module for WorkPulse Enterprise Attendance & HR Management System.
Handles complete schema for Admin (15 modules) and Employee (10 modules).
"""

import sqlite3
import os
import json
from datetime import datetime, date, timedelta
from werkzeug.security import generate_password_hash, check_password_hash

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'attendance.db')

def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # 1. Users table (Admin & Employee details)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            emp_code TEXT UNIQUE NOT NULL,
            full_name TEXT NOT NULL,
            username TEXT UNIQUE NOT NULL,
            email TEXT,
            password_hash TEXT NOT NULL,
            raw_password_hint TEXT,
            role TEXT NOT NULL DEFAULT 'employee', -- 'admin' or 'employee'
            department TEXT DEFAULT 'Engineering',
            designation TEXT DEFAULT 'Software Engineer',
            phone TEXT,
            joining_date TEXT,
            salary_type TEXT DEFAULT 'Monthly', -- 'Monthly' or 'Hourly'
            basic_salary REAL DEFAULT 3500.0,
            hourly_rate REAL DEFAULT 25.0,
            allowance REAL DEFAULT 300.0,
            deductions REAL DEFAULT 150.0,
            bank_account TEXT DEFAULT 'ACC-987654321',
            status TEXT DEFAULT 'Active',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Add missing columns to users table if upgrading an existing db
    cursor.execute("PRAGMA table_info(users)")
    existing_user_cols = [col[1] for col in cursor.fetchall()]
    
    user_cols_to_add = [
        ("salary_type", "TEXT DEFAULT 'Monthly'"),
        ("basic_salary", "REAL DEFAULT 3500.0"),
        ("hourly_rate", "REAL DEFAULT 25.0"),
        ("allowance", "REAL DEFAULT 300.0"),
        ("deductions", "REAL DEFAULT 150.0"),
        ("bank_account", "TEXT DEFAULT 'ACC-987654321'")
    ]
    for col_name, col_def in user_cols_to_add:
        if col_name not in existing_user_cols:
            cursor.execute(f"ALTER TABLE users ADD COLUMN {col_name} {col_def}")

    # 2. Attendance Records table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS attendance (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            date TEXT NOT NULL, -- YYYY-MM-DD
            check_in TIMESTAMP NOT NULL,
            check_out TIMESTAMP,
            work_duration_seconds INTEGER DEFAULT 0,
            work_duration_formatted TEXT DEFAULT '0h 0m',
            status TEXT DEFAULT 'Checked In', -- 'Checked In', 'Completed', 'Late', 'Half Day'
            notes TEXT,
            ip_address TEXT DEFAULT '127.0.0.1',
            device_name TEXT DEFAULT 'Web Portal',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
        )
    ''')

    # Add missing columns to attendance table if upgrading
    cursor.execute("PRAGMA table_info(attendance)")
    existing_att_cols = [col[1] for col in cursor.fetchall()]
    att_cols_to_add = [
        ("ip_address", "TEXT DEFAULT '127.0.0.1'"),
        ("device_name", "TEXT DEFAULT 'Web Portal'")
    ]
    for col_name, col_def in att_cols_to_add:
        if col_name not in existing_att_cols:
            cursor.execute(f"ALTER TABLE attendance ADD COLUMN {col_name} {col_def}")



    # 3. Leaves table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS leaves (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            leave_type TEXT NOT NULL, -- 'Casual', 'Sick', 'Annual', 'Maternity', 'Unpaid'
            start_date TEXT NOT NULL,
            end_date TEXT NOT NULL,
            days INTEGER DEFAULT 1,
            reason TEXT NOT NULL,
            status TEXT DEFAULT 'Pending', -- 'Pending', 'Approved', 'Rejected'
            admin_comment TEXT,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            reviewed_at TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
        )
    ''')

    # 4. Permissions table (Short hours leave / late arrival / early exit)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS permissions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            date TEXT NOT NULL,
            start_time TEXT NOT NULL,
            end_time TEXT NOT NULL,
            hours REAL DEFAULT 1.5,
            reason TEXT NOT NULL,
            status TEXT DEFAULT 'Pending', -- 'Pending', 'Approved', 'Rejected'
            admin_comment TEXT,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
        )
    ''')

    # 5. Attendance Corrections table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS corrections (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            attendance_id INTEGER,
            date TEXT NOT NULL,
            requested_check_in TEXT NOT NULL,
            requested_check_out TEXT NOT NULL,
            reason TEXT NOT NULL,
            status TEXT DEFAULT 'Pending', -- 'Pending', 'Approved', 'Rejected'
            admin_comment TEXT,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
        )
    ''')

    # 6. HR Departments, Designations, Shifts, Holidays
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS hr_departments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE NOT NULL,
            head_of_dept TEXT,
            description TEXT
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS hr_designations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT UNIQUE NOT NULL,
            department TEXT,
            description TEXT
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS hr_shifts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            start_time TEXT NOT NULL,
            end_time TEXT NOT NULL,
            grace_period_mins INTEGER DEFAULT 15
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS hr_holidays (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            date TEXT NOT NULL,
            holiday_type TEXT DEFAULT 'Public Holiday'
        )
    ''')

    # 7. Payroll & Payslips table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS payroll (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            month_year TEXT NOT NULL, -- 'YYYY-MM'
            days_worked INTEGER DEFAULT 0,
            total_hours REAL DEFAULT 0.0,
            basic_pay REAL DEFAULT 0.0,
            allowances REAL DEFAULT 0.0,
            overtime_pay REAL DEFAULT 0.0,
            deductions REAL DEFAULT 0.0,
            net_salary REAL DEFAULT 0.0,
            payment_status TEXT DEFAULT 'Pending', -- 'Pending', 'Paid', 'Processing'
            payment_date TEXT,
            payment_method TEXT DEFAULT 'Bank Transfer',
            reference_no TEXT,
            generated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE,
            UNIQUE(user_id, month_year)
        )
    ''')

    # 8. Device Management table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS devices (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            device_type TEXT NOT NULL DEFAULT 'Biometric Scanner', -- 'Biometric Scanner', 'RFID Reader', 'Facial Recognition'
            ip_address TEXT NOT NULL,
            location TEXT DEFAULT 'Main Gate',
            status TEXT DEFAULT 'Online', -- 'Online', 'Offline'
            last_sync TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # 9. Company Settings table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS company_settings (
            id INTEGER PRIMARY KEY,
            company_name TEXT DEFAULT 'WorkPulse Enterprise Corp.',
            standard_work_hours REAL DEFAULT 8.0,
            grace_period_mins INTEGER DEFAULT 15,
            currency TEXT DEFAULT '$',
            overtime_rate_multiplier REAL DEFAULT 1.5,
            tax_percentage REAL DEFAULT 5.0,
            address TEXT DEFAULT '100 Innovation Way, Tech Park, CA',
            contact_email TEXT DEFAULT 'hr@workpulse.com',
            contact_phone TEXT DEFAULT '+1 (800) 555-0199'
        )
    ''')

    # 10. Audit Logs table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS audit_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            user_name TEXT,
            action TEXT NOT NULL,
            details TEXT,
            ip_address TEXT DEFAULT '127.0.0.1',
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # 11. Notifications table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS notifications (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            title TEXT NOT NULL,
            message TEXT NOT NULL,
            type TEXT DEFAULT 'info', -- 'info', 'success', 'warning', 'danger'
            is_read INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
        )
    ''')

    # Seed Default Settings if empty
    cursor.execute("SELECT COUNT(*) as c FROM company_settings")
    if cursor.fetchone()['c'] == 0:
        cursor.execute('''
            INSERT INTO company_settings (id, company_name, standard_work_hours, grace_period_mins, currency, overtime_rate_multiplier, tax_percentage, address, contact_email, contact_phone)
            VALUES (1, 'WorkPulse Enterprise Corp.', 8.0, 15, '$', 1.5, 5.0, '100 Innovation Way, Tech Park, CA', 'hr@workpulse.com', '+1 (800) 555-0199')
        ''')

    # Seed Admin User
    cursor.execute("SELECT id FROM users WHERE role = 'admin'")
    if not cursor.fetchone():
        admin_pass = "admin123"
        cursor.execute('''
            INSERT INTO users (emp_code, full_name, username, email, password_hash, raw_password_hint, role, department, designation, joining_date, basic_salary, hourly_rate)
            VALUES (?, ?, ?, ?, ?, ?, 'admin', 'Management', 'System Administrator', ?, 6000.0, 45.0)
        ''', ('ADM001', 'System Administrator', 'admin', 'admin@workpulse.com', generate_password_hash(admin_pass), admin_pass, date.today().strftime('%Y-%m-%d')))

    # Seed Sample Employees
    cursor.execute("SELECT COUNT(*) as c FROM users WHERE role = 'employee'")
    if cursor.fetchone()['c'] == 0:
        sample_employees = [
            ('EMP101', 'John Doe', 'john.doe', 'john@workpulse.com', 'emp123', 'Engineering', 'Senior Developer', 4800.0, 32.0, 400.0, 200.0),
            ('EMP102', 'Sarah Smith', 'sarah.smith', 'sarah@workpulse.com', 'welcome2026', 'Human Resources', 'HR Manager', 4200.0, 28.0, 350.0, 180.0),
            ('EMP103', 'Michael Brown', 'michael.b', 'michael@workpulse.com', 'pass456', 'Marketing', 'Marketing Lead', 3900.0, 26.0, 300.0, 150.0),
            ('EMP104', 'Emily Davis', 'emily.d', 'emily@workpulse.com', 'emily2026', 'Finance', 'Financial Analyst', 4100.0, 27.0, 350.0, 160.0)
        ]
        for emp_code, name, uname, email, pwd, dept, desig, basic, hourly, allow, deduct in sample_employees:
            cursor.execute('''
                INSERT INTO users (emp_code, full_name, username, email, password_hash, raw_password_hint, role, department, designation, joining_date, basic_salary, hourly_rate, allowance, deductions)
                VALUES (?, ?, ?, ?, ?, ?, 'employee', ?, ?, ?, ?, ?, ?, ?)
            ''', (emp_code, name, uname, email, generate_password_hash(pwd), pwd, dept, desig, date.today().strftime('%Y-%m-%d'), basic, hourly, allow, deduct))

    # Seed Sample Departments & Designations & Shifts & Holidays
    cursor.execute("SELECT COUNT(*) as c FROM hr_departments")
    if cursor.fetchone()['c'] == 0:
        depts = [
            ('Engineering', 'John Doe', 'Software Development & IT Infrastructure'),
            ('Human Resources', 'Sarah Smith', 'Talent Acquisition & Employee Engagement'),
            ('Marketing', 'Michael Brown', 'Growth, Brand, and Digital Marketing'),
            ('Finance', 'Emily Davis', 'Accounting, Payroll, and Budgeting'),
            ('Operations', 'General', 'Facility and Daily Business Operations')
        ]
        cursor.executemany("INSERT INTO hr_departments (name, head_of_dept, description) VALUES (?, ?, ?)", depts)

    cursor.execute("SELECT COUNT(*) as c FROM hr_designations")
    if cursor.fetchone()['c'] == 0:
        desigs = [
            ('Senior Developer', 'Engineering', 'Leads architecture & core development'),
            ('HR Manager', 'Human Resources', 'Oversees workforce & benefits'),
            ('Marketing Lead', 'Marketing', 'Manages outreach & campaigns'),
            ('Financial Analyst', 'Finance', 'Handles accounting & financial reports'),
            ('QA Engineer', 'Engineering', 'Test automation & quality assurance')
        ]
        cursor.executemany("INSERT INTO hr_designations (title, department, description) VALUES (?, ?, ?)", desigs)

    cursor.execute("SELECT COUNT(*) as c FROM hr_shifts")
    if cursor.fetchone()['c'] == 0:
        shifts = [
            ('Morning Shift (Standard)', '09:00', '18:00', 15),
            ('Early Shift', '07:00', '16:00', 15),
            ('Night Shift', '21:00', '06:00', 20)
        ]
        cursor.executemany("INSERT INTO hr_shifts (name, start_time, end_time, grace_period_mins) VALUES (?, ?, ?, ?)", shifts)

    cursor.execute("SELECT COUNT(*) as c FROM hr_holidays")
    if cursor.fetchone()['c'] == 0:
        holidays = [
            ('New Year Day', f"{date.today().year}-01-01", 'National Holiday'),
            ('Labor Day', f"{date.today().year}-05-01", 'Public Holiday'),
            ('Independence Day', f"{date.today().year}-07-04", 'National Holiday'),
            ('Thanksgiving Day', f"{date.today().year}-11-26", 'Public Holiday'),
            ('Christmas Holiday', f"{date.today().year}-12-25", 'National Holiday')
        ]
        cursor.executemany("INSERT INTO hr_holidays (name, date, holiday_type) VALUES (?, ?, ?)", holidays)

    # Seed Sample Devices
    cursor.execute("SELECT COUNT(*) as c FROM devices")
    if cursor.fetchone()['c'] == 0:
        devices = [
            ('Main Reception Biometric-1', 'Biometric Scanner', '192.168.1.120', 'Ground Floor Entrance', 'Online'),
            ('Engineering Lab RFID-2', 'RFID Reader', '192.168.1.121', 'Building B, Floor 2', 'Online'),
            ('Executive Suite Facial-3', 'Facial Recognition', '192.168.1.122', 'Building A, Floor 5', 'Online')
        ]
        cursor.executemany("INSERT INTO devices (name, device_type, ip_address, location, status) VALUES (?, ?, ?, ?, ?)", devices)

    # Seed Sample Notifications
    cursor.execute("SELECT COUNT(*) as c FROM notifications")
    if cursor.fetchone()['c'] == 0:
        cursor.execute('''
            INSERT INTO notifications (user_id, title, message, type)
            VALUES (2, 'Welcome to WorkPulse', 'Your employee portal account has been configured by Admin.', 'success')
        ''')

    conn.commit()
    conn.close()

# ----------------- Helpers ----------------- #

def log_audit(user_id, user_name, action, details="", ip_address="127.0.0.1"):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO audit_logs (user_id, user_name, action, details, ip_address)
            VALUES (?, ?, ?, ?, ?)
        ''', (user_id, user_name, action, details, ip_address))
        conn.commit()
        conn.close()
    except Exception as e:
        print("Audit log error:", e)

def create_notification(user_id, title, message, n_type='info'):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO notifications (user_id, title, message, type)
            VALUES (?, ?, ?, ?)
        ''', (user_id, title, message, n_type))
        conn.commit()
        conn.close()
    except Exception as e:
        print("Notification error:", e)

def get_company_settings():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM company_settings WHERE id = 1")
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else {
        'company_name': 'WorkPulse Enterprise Corp.',
        'standard_work_hours': 8.0,
        'grace_period_mins': 15,
        'currency': '$',
        'overtime_rate_multiplier': 1.5,
        'tax_percentage': 5.0,
        'address': '100 Innovation Way, Tech Park, CA',
        'contact_email': 'hr@workpulse.com',
        'contact_phone': '+1 (800) 555-0199'
    }

def update_company_settings(company_name, work_hours, grace_period, currency, ot_mult, tax_pct, address, email, phone):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        UPDATE company_settings 
        SET company_name = ?, standard_work_hours = ?, grace_period_mins = ?, currency = ?, 
            overtime_rate_multiplier = ?, tax_percentage = ?, address = ?, contact_email = ?, contact_phone = ?
        WHERE id = 1
    ''', (company_name, work_hours, grace_period, currency, ot_mult, tax_pct, address, email, phone))
    conn.commit()
    conn.close()
    return True

# ----------------- User Management ----------------- #

def authenticate_user(username_or_code, password):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT * FROM users 
        WHERE (LOWER(username) = LOWER(?) OR LOWER(emp_code) = LOWER(?) OR LOWER(email) = LOWER(?))
        AND status = 'Active'
    ''', (username_or_code, username_or_code, username_or_code))
    user = cursor.fetchone()
    conn.close()
    
    if user and check_password_hash(user['password_hash'], password):
        return dict(user)
    return None

def get_user_by_id(user_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM users WHERE id = ?', (user_id,))
    user = cursor.fetchone()
    conn.close()
    return dict(user) if user else None

def get_all_employees(search=None, department=None):
    conn = get_db_connection()
    cursor = conn.cursor()
    query = "SELECT * FROM users WHERE role = 'employee'"
    params = []
    
    if search:
        query += " AND (full_name LIKE ? OR emp_code LIKE ? OR username LIKE ? OR email LIKE ?)"
        term = f"%{search}%"
        params.extend([term, term, term, term])
        
    if department and department != 'All':
        query += " AND department = ?"
        params.append(department)
        
    query += " ORDER BY id DESC"
    cursor.execute(query, params)
    employees = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return employees

def create_employee(emp_code, full_name, username, email, password, department, designation, phone, joining_date, basic_salary=3500.0, hourly_rate=25.0, allowance=300.0, deductions=150.0, salary_type='Monthly'):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        password_hash = generate_password_hash(password)
        cursor.execute('''
            INSERT INTO users (emp_code, full_name, username, email, password_hash, raw_password_hint, role, department, designation, phone, joining_date, basic_salary, hourly_rate, allowance, deductions, salary_type)
            VALUES (?, ?, ?, ?, ?, ?, 'employee', ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (emp_code.strip(), full_name.strip(), username.strip().lower(), email.strip() if email else '', password_hash, password, department, designation, phone, joining_date, basic_salary, hourly_rate, allowance, deductions, salary_type))
        conn.commit()
        user_id = cursor.lastrowid
        conn.close()
        create_notification(user_id, "Welcome to WorkPulse", "Your employee account has been created by Administrator.", "success")
        return True, user_id
    except sqlite3.IntegrityError as e:
        conn.close()
        if 'emp_code' in str(e).lower():
            return False, "Employee Code already exists."
        elif 'username' in str(e).lower():
            return False, "Username already exists."
        return False, f"Database error: {str(e)}"
    except Exception as e:
        conn.close()
        return False, str(e)

def update_employee(user_id, emp_code, full_name, username, email, password, department, designation, phone, status, basic_salary=None, hourly_rate=None, allowance=None, deductions=None, salary_type=None):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        fields = [
            ("emp_code", emp_code.strip()),
            ("full_name", full_name.strip()),
            ("username", username.strip().lower()),
            ("email", email.strip()),
            ("department", department),
            ("designation", designation),
            ("phone", phone),
            ("status", status)
        ]
        if password and password.strip():
            fields.append(("password_hash", generate_password_hash(password.strip())))
            fields.append(("raw_password_hint", password.strip()))
        if basic_salary is not None:
            fields.append(("basic_salary", float(basic_salary)))
        if hourly_rate is not None:
            fields.append(("hourly_rate", float(hourly_rate)))
        if allowance is not None:
            fields.append(("allowance", float(allowance)))
        if deductions is not None:
            fields.append(("deductions", float(deductions)))
        if salary_type is not None:
            fields.append(("salary_type", salary_type))

        set_clause = ", ".join([f"{k} = ?" for k, _ in fields])
        params = [v for _, v in fields]
        params.append(user_id)

        cursor.execute(f"UPDATE users SET {set_clause} WHERE id = ?", params)
        conn.commit()
        conn.close()
        return True, "Employee updated successfully."
    except Exception as e:
        conn.close()
        return False, str(e)

def delete_employee(user_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM users WHERE id = ? AND role != 'admin'", (user_id,))
    deleted = cursor.rowcount > 0
    conn.commit()
    conn.close()
    return deleted

# ----------------- Attendance & Time Engine ----------------- #

def format_seconds(seconds):
    if not seconds or seconds < 0:
        return "0h 0m"
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    return f"{hours}h {minutes}m"

def format_hours_decimal(seconds):
    if not seconds:
        return 0.0
    return round(seconds / 3600.0, 2)

def get_active_session(user_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT * FROM attendance 
        WHERE user_id = ? AND check_out IS NULL 
        ORDER BY id DESC LIMIT 1
    ''', (user_id,))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None

def record_check_in(user_id, notes="", ip_address="127.0.0.1", device_name="Web Portal"):
    active = get_active_session(user_id)
    if active:
        return False, "You are already checked in. Please check out first."
    
    now = datetime.now()
    today_str = now.strftime('%Y-%m-%d')
    now_str = now.strftime('%Y-%m-%d %H:%M:%S')
    
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO attendance (user_id, date, check_in, status, notes, ip_address, device_name)
        VALUES (?, ?, ?, 'Checked In', ?, ?, ?)
    ''', (user_id, today_str, now_str, notes, ip_address, device_name))
    conn.commit()
    att_id = cursor.lastrowid
    conn.close()
    return True, {"attendance_id": att_id, "check_in": now_str}

def record_check_out(user_id, notes="", ip_address="127.0.0.1"):
    active = get_active_session(user_id)
    if not active:
        return False, "No active check-in found. Please check in first."
    
    now = datetime.now()
    now_str = now.strftime('%Y-%m-%d %H:%M:%S')
    check_in_dt = datetime.strptime(active['check_in'], '%Y-%m-%d %H:%M:%S')
    
    duration = max(0, int((now - check_in_dt).total_seconds()))
    formatted_duration = format_seconds(duration)
    
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        UPDATE attendance 
        SET check_out = ?, work_duration_seconds = ?, work_duration_formatted = ?, status = 'Completed', notes = CASE WHEN ? != '' THEN ? ELSE notes END
        WHERE id = ?
    ''', (now_str, duration, formatted_duration, notes, notes, active['id']))
    conn.commit()
    conn.close()
    
    return True, {
        "attendance_id": active['id'],
        "check_in": active['check_in'],
        "check_out": now_str,
        "duration": formatted_duration,
        "duration_seconds": duration,
        "hours_decimal": format_hours_decimal(duration)
    }

def get_employee_attendance_history(user_id, start_date=None, end_date=None, limit=100):
    conn = get_db_connection()
    cursor = conn.cursor()
    query = '''
        SELECT a.*, u.full_name, u.emp_code 
        FROM attendance a
        JOIN users u ON a.user_id = u.id
        WHERE a.user_id = ?
    '''
    params = [user_id]
    if start_date:
        query += " AND a.date >= ?"
        params.append(start_date)
    if end_date:
        query += " AND a.date <= ?"
        params.append(end_date)
    query += " ORDER BY a.id DESC LIMIT ?"
    params.append(limit)
    
    cursor.execute(query, params)
    records = [dict(row) for row in cursor.fetchall()]
    conn.close()
    
    now = datetime.now()
    for rec in records:
        if rec['check_out'] is None:
            c_in = datetime.strptime(rec['check_in'], '%Y-%m-%d %H:%M:%S')
            live_sec = max(0, int((now - c_in).total_seconds()))
            rec['work_duration_seconds'] = live_sec
            rec['work_duration_formatted'] = format_seconds(live_sec) + " (Active)"
            rec['hours_decimal'] = format_hours_decimal(live_sec)
        else:
            rec['hours_decimal'] = format_hours_decimal(rec['work_duration_seconds'])
    return records

def get_employee_stats(user_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    today_str = date.today().strftime('%Y-%m-%d')
    first_of_month = date.today().replace(day=1).strftime('%Y-%m-%d')
    
    # Today's total hours
    cursor.execute('''
        SELECT SUM(work_duration_seconds) as total_sec 
        FROM attendance 
        WHERE user_id = ? AND date = ? AND check_out IS NOT NULL
    ''', (user_id, today_str))
    today_row = cursor.fetchone()
    today_seconds = today_row['total_sec'] or 0
    
    # Active session check
    active = get_active_session(user_id)
    is_checked_in = False
    current_session_duration = 0
    if active:
        is_checked_in = True
        c_in = datetime.strptime(active['check_in'], '%Y-%m-%d %H:%M:%S')
        current_session_duration = max(0, int((datetime.now() - c_in).total_seconds()))
        today_seconds += current_session_duration
        
    # Month's total hours and distinct days
    cursor.execute('''
        SELECT SUM(work_duration_seconds) as month_sec, COUNT(DISTINCT date) as days_worked
        FROM attendance 
        WHERE user_id = ? AND date >= ? AND check_out IS NOT NULL
    ''', (user_id, first_of_month))
    month_row = cursor.fetchone()
    month_seconds = (month_row['month_sec'] or 0) + (current_session_duration if is_checked_in else 0)
    days_worked = month_row['days_worked'] or (1 if is_checked_in else 0)
    
    # Pending leaves and permissions count
    cursor.execute("SELECT COUNT(*) as c FROM leaves WHERE user_id = ? AND status = 'Pending'", (user_id,))
    pending_leaves = cursor.fetchone()['c']
    
    cursor.execute("SELECT COUNT(*) as c FROM permissions WHERE user_id = ? AND status = 'Pending'", (user_id,))
    pending_permissions = cursor.fetchone()['c']

    cursor.execute("SELECT COUNT(*) as c FROM notifications WHERE user_id = ? AND is_read = 0", (user_id,))
    unread_notifs = cursor.fetchone()['c']

    conn.close()
    
    avg_hours_day = round((month_seconds / 3600.0) / max(days_worked, 1), 1) if days_worked > 0 else 0.0
    
    return {
        "is_checked_in": is_checked_in,
        "active_session": active,
        "today_seconds": today_seconds,
        "today_formatted": format_seconds(today_seconds),
        "today_hours_decimal": format_hours_decimal(today_seconds),
        "month_seconds": month_seconds,
        "month_formatted": format_seconds(month_seconds),
        "month_hours_decimal": format_hours_decimal(month_seconds),
        "days_worked_this_month": days_worked,
        "avg_daily_hours": avg_hours_day,
        "pending_leaves": pending_leaves,
        "pending_permissions": pending_permissions,
        "unread_notifications": unread_notifs
    }

def get_admin_dashboard_stats():
    conn = get_db_connection()
    cursor = conn.cursor()
    today_str = date.today().strftime('%Y-%m-%d')
    first_of_month = date.today().replace(day=1).strftime('%Y-%m-%d')
    
    cursor.execute("SELECT COUNT(*) as total FROM users WHERE role = 'employee' AND status = 'Active'")
    total_employees = cursor.fetchone()['total']
    
    cursor.execute("SELECT COUNT(DISTINCT user_id) as present FROM attendance WHERE date = ?", (today_str,))
    present_today = cursor.fetchone()['present']
    
    cursor.execute("SELECT COUNT(*) as live_count FROM attendance WHERE check_out IS NULL")
    currently_active = cursor.fetchone()['live_count']
    
    cursor.execute("SELECT SUM(work_duration_seconds) as total_sec FROM attendance WHERE date = ?", (today_str,))
    total_today_sec = cursor.fetchone()['total_sec'] or 0
    
    cursor.execute("SELECT check_in FROM attendance WHERE check_out IS NULL AND date = ?", (today_str,))
    for row in cursor.fetchall():
        c_in = datetime.strptime(row['check_in'], '%Y-%m-%d %H:%M:%S')
        total_today_sec += max(0, int((datetime.now() - c_in).total_seconds()))

    cursor.execute("SELECT COUNT(*) as c FROM leaves WHERE status = 'Pending'")
    pending_leaves = cursor.fetchone()['c']

    cursor.execute("SELECT COUNT(*) as c FROM permissions WHERE status = 'Pending'")
    pending_permissions = cursor.fetchone()['c']

    cursor.execute("SELECT COUNT(*) as c FROM corrections WHERE status = 'Pending'")
    pending_corrections = cursor.fetchone()['c']

    cursor.execute("SELECT COUNT(*) as c FROM payroll WHERE payment_status = 'Pending'")
    pending_payroll = cursor.fetchone()['c']
        
    conn.close()
    
    absent_today = max(0, total_employees - present_today)
    
    return {
        "total_employees": total_employees,
        "present_today": present_today,
        "currently_active": currently_active,
        "absent_today": absent_today,
        "total_hours_today_formatted": format_seconds(total_today_sec),
        "total_hours_today_decimal": format_hours_decimal(total_today_sec),
        "attendance_rate": round((present_today / max(total_employees, 1)) * 100, 1),
        "pending_leaves": pending_leaves,
        "pending_permissions": pending_permissions,
        "pending_corrections": pending_corrections,
        "pending_payroll": pending_payroll
    }

def get_all_attendance_records(user_id=None, department=None, start_date=None, end_date=None, status=None, limit=500):
    conn = get_db_connection()
    cursor = conn.cursor()
    query = '''
        SELECT a.*, u.full_name, u.emp_code, u.department, u.designation, u.raw_password_hint
        FROM attendance a
        JOIN users u ON a.user_id = u.id
        WHERE 1=1
    '''
    params = []
    if user_id:
        query += " AND a.user_id = ?"
        params.append(user_id)
    if department and department != 'All':
        query += " AND u.department = ?"
        params.append(department)
    if start_date:
        query += " AND a.date >= ?"
        params.append(start_date)
    if end_date:
        query += " AND a.date <= ?"
        params.append(end_date)
    if status and status != 'All':
        query += " AND a.status = ?"
        params.append(status)
        
    query += " ORDER BY a.date DESC, a.id DESC LIMIT ?"
    params.append(limit)
    
    cursor.execute(query, params)
    records = [dict(row) for row in cursor.fetchall()]
    conn.close()
    
    now = datetime.now()
    for rec in records:
        if rec['check_out'] is None:
            c_in = datetime.strptime(rec['check_in'], '%Y-%m-%d %H:%M:%S')
            live_sec = max(0, int((now - c_in).total_seconds()))
            rec['work_duration_seconds'] = live_sec
            rec['work_duration_formatted'] = format_seconds(live_sec) + " (Ongoing)"
            rec['hours_decimal'] = format_hours_decimal(live_sec)
        else:
            rec['hours_decimal'] = format_hours_decimal(rec['work_duration_seconds'])
    return records

def admin_manual_clock_out(attendance_id, check_out_time=None, notes="Clocked out by Admin"):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM attendance WHERE id = ?", (attendance_id,))
    record = cursor.fetchone()
    if not record or record['check_out']:
        conn.close()
        return False, "Record already checked out or not found."
    
    check_out_str = check_out_time or datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    c_in = datetime.strptime(record['check_in'], '%Y-%m-%d %H:%M:%S')
    c_out = datetime.strptime(check_out_str, '%Y-%m-%d %H:%M:%S')
    duration = max(0, int((c_out - c_in).total_seconds()))
    formatted = format_seconds(duration)
    
    cursor.execute('''
        UPDATE attendance 
        SET check_out = ?, work_duration_seconds = ?, work_duration_formatted = ?, status = 'Completed', notes = ?
        WHERE id = ?
    ''', (check_out_str, duration, formatted, notes, attendance_id))
    conn.commit()
    conn.close()
    return True, "Successfully updated attendance record."

# ----------------- Leaves & Permissions ----------------- #

def apply_leave(user_id, leave_type, start_date, end_date, reason):
    d1 = datetime.strptime(start_date, '%Y-%m-%d')
    d2 = datetime.strptime(end_date, '%Y-%m-%d')
    days = max(1, (d2 - d1).days + 1)
    
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO leaves (user_id, leave_type, start_date, end_date, days, reason, status)
        VALUES (?, ?, ?, ?, ?, ?, 'Pending')
    ''', (user_id, leave_type, start_date, end_date, days, reason))
    conn.commit()
    conn.close()
    return True

def get_leaves(user_id=None, status=None):
    conn = get_db_connection()
    cursor = conn.cursor()
    query = '''
        SELECT l.*, u.full_name, u.emp_code, u.department 
        FROM leaves l
        JOIN users u ON l.user_id = u.id
        WHERE 1=1
    '''
    params = []
    if user_id:
        query += " AND l.user_id = ?"
        params.append(user_id)
    if status and status != 'All':
        query += " AND l.status = ?"
        params.append(status)
    query += " ORDER BY l.id DESC"
    cursor.execute(query, params)
    rows = [dict(r) for r in cursor.fetchall()]
    conn.close()
    return rows

def review_leave(leave_id, status, admin_comment=""):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT user_id, leave_type FROM leaves WHERE id = ?", (leave_id,))
    l_row = cursor.fetchone()
    if not l_row:
        conn.close()
        return False
    
    cursor.execute('''
        UPDATE leaves 
        SET status = ?, admin_comment = ?, reviewed_at = CURRENT_TIMESTAMP
        WHERE id = ?
    ''', (status, admin_comment, leave_id))
    conn.commit()
    conn.close()
    
    n_type = 'success' if status == 'Approved' else 'danger'
    create_notification(l_row['user_id'], f"Leave Request {status}", f"Your {l_row['leave_type']} leave has been {status.lower()} by HR. Note: {admin_comment}", n_type)
    return True

def apply_permission(user_id, req_date, start_time, end_time, reason):
    t1 = datetime.strptime(start_time, '%H:%M')
    t2 = datetime.strptime(end_time, '%H:%M')
    hours = round(max(0.5, (t2 - t1).total_seconds() / 3600.0), 1)
    
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO permissions (user_id, date, start_time, end_time, hours, reason, status)
        VALUES (?, ?, ?, ?, ?, ?, 'Pending')
    ''', (user_id, req_date, start_time, end_time, hours, reason))
    conn.commit()
    conn.close()
    return True

def get_permissions(user_id=None, status=None):
    conn = get_db_connection()
    cursor = conn.cursor()
    query = '''
        SELECT p.*, u.full_name, u.emp_code, u.department 
        FROM permissions p
        JOIN users u ON p.user_id = u.id
        WHERE 1=1
    '''
    params = []
    if user_id:
        query += " AND p.user_id = ?"
        params.append(user_id)
    if status and status != 'All':
        query += " AND p.status = ?"
        params.append(status)
    query += " ORDER BY p.id DESC"
    cursor.execute(query, params)
    rows = [dict(r) for r in cursor.fetchall()]
    conn.close()
    return rows

def review_permission(perm_id, status, admin_comment=""):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT user_id, date FROM permissions WHERE id = ?", (perm_id,))
    p_row = cursor.fetchone()
    if not p_row:
        conn.close()
        return False
    
    cursor.execute('''
        UPDATE permissions 
        SET status = ?, admin_comment = ?
        WHERE id = ?
    ''', (status, admin_comment, perm_id))
    conn.commit()
    conn.close()
    
    n_type = 'success' if status == 'Approved' else 'danger'
    create_notification(p_row['user_id'], f"Permission Request {status}", f"Your short leave permission for {p_row['date']} was {status.lower()}.", n_type)
    return True

# ----------------- Attendance Corrections ----------------- #

def apply_correction(user_id, att_date, req_check_in, req_check_out, reason):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO corrections (user_id, date, requested_check_in, requested_check_out, reason, status)
        VALUES (?, ?, ?, ?, ?, 'Pending')
    ''', (user_id, att_date, req_check_in, req_check_out, reason))
    conn.commit()
    conn.close()
    return True

def get_corrections(user_id=None, status=None):
    conn = get_db_connection()
    cursor = conn.cursor()
    query = '''
        SELECT c.*, u.full_name, u.emp_code, u.department 
        FROM corrections c
        JOIN users u ON c.user_id = u.id
        WHERE 1=1
    '''
    params = []
    if user_id:
        query += " AND c.user_id = ?"
        params.append(user_id)
    if status and status != 'All':
        query += " AND c.status = ?"
        params.append(status)
    query += " ORDER BY c.id DESC"
    cursor.execute(query, params)
    rows = [dict(r) for r in cursor.fetchall()]
    conn.close()
    return rows

def review_correction(corr_id, status, admin_comment=""):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM corrections WHERE id = ?", (corr_id,))
    c_row = cursor.fetchone()
    if not c_row:
        conn.close()
        return False
        
    cursor.execute('''
        UPDATE corrections 
        SET status = ?, admin_comment = ?
        WHERE id = ?
    ''', (status, admin_comment, corr_id))
    
    # If approved, update or insert into attendance
    if status == 'Approved':
        c_in_str = f"{c_row['date']} {c_row['requested_check_in']}:00"
        c_out_str = f"{c_row['date']} {c_row['requested_check_out']}:00"
        dt1 = datetime.strptime(c_in_str, '%Y-%m-%d %H:%M:%S')
        dt2 = datetime.strptime(c_out_str, '%Y-%m-%d %H:%M:%S')
        dur = max(0, int((dt2 - dt1).total_seconds()))
        dur_fmt = format_seconds(dur)
        
        cursor.execute('''
            INSERT INTO attendance (user_id, date, check_in, check_out, work_duration_seconds, work_duration_formatted, status, notes)
            VALUES (?, ?, ?, ?, ?, ?, 'Completed', 'Corrected by HR approval')
        ''', (c_row['user_id'], c_row['date'], c_in_str, c_out_str, dur, dur_fmt))
        
    conn.commit()
    conn.close()
    
    n_type = 'success' if status == 'Approved' else 'danger'
    create_notification(c_row['user_id'], f"Attendance Correction {status}", f"Your correction request for {c_row['date']} was {status.lower()}.", n_type)
    return True

# ----------------- Payroll & Salary Calculation Engine ----------------- #

def generate_monthly_payroll(month_year):
    """
    Computes accurate monthly payroll for all active employees.
    Month format: YYYY-MM
    Calculates: Days worked, total hours, overtime hours, allowances, deductions, and Net Salary.
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    
    settings = get_company_settings()
    std_hours = settings.get('standard_work_hours', 8.0)
    ot_multiplier = settings.get('overtime_rate_multiplier', 1.5)
    tax_pct = settings.get('tax_percentage', 5.0)
    
    cursor.execute("SELECT * FROM users WHERE role = 'employee' AND status = 'Active'")
    employees = [dict(r) for r in cursor.fetchall()]
    
    generated_count = 0
    for emp in employees:
        user_id = emp['id']
        start_date = f"{month_year}-01"
        end_date = f"{month_year}-31"
        
        # Calculate hours & days worked in month
        cursor.execute('''
            SELECT SUM(work_duration_seconds) as total_sec, COUNT(DISTINCT date) as days_count
            FROM attendance 
            WHERE user_id = ? AND date >= ? AND date <= ? AND check_out IS NOT NULL
        ''', (user_id, start_date, end_date))
        att_row = cursor.fetchone()
        
        total_sec = att_row['total_sec'] or 0
        days_worked = att_row['days_count'] or 0
        total_hours = round(total_sec / 3600.0, 2)
        
        basic = float(emp['basic_salary'] or 3500.0)
        hourly_rate = float(emp['hourly_rate'] or 25.0)
        allowance = float(emp['allowance'] or 300.0)
        deductions = float(emp['deductions'] or 150.0)
        
        # Overtime calculation (Standard working days ~ 22 days * 8 hrs = 176 hrs)
        expected_standard_hours = max(days_worked * std_hours, 1)
        overtime_hours = max(0.0, total_hours - expected_standard_hours)
        overtime_pay = round(overtime_hours * hourly_rate * ot_multiplier, 2)
        
        # If hourly employee, basic = total_hours * hourly_rate
        if emp['salary_type'] == 'Hourly':
            calculated_basic = round(min(total_hours, expected_standard_hours) * hourly_rate, 2)
        else:
            # Pro-rate monthly salary if needed or full monthly
            calculated_basic = basic
            
        tax_amount = round((calculated_basic + allowance + overtime_pay) * (tax_pct / 100.0), 2)
        total_deductions = deductions + tax_amount
        net_salary = round(max(0.0, calculated_basic + allowance + overtime_pay - total_deductions), 2)
        
        cursor.execute('''
            INSERT INTO payroll (user_id, month_year, days_worked, total_hours, basic_pay, allowances, overtime_pay, deductions, net_salary, payment_status)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'Pending')
            ON CONFLICT(user_id, month_year) DO UPDATE SET
                days_worked = excluded.days_worked,
                total_hours = excluded.total_hours,
                basic_pay = excluded.basic_pay,
                allowances = excluded.allowances,
                overtime_pay = excluded.overtime_pay,
                deductions = excluded.deductions,
                net_salary = excluded.net_salary
        ''', (user_id, month_year, days_worked, total_hours, calculated_basic, allowance, overtime_pay, total_deductions, net_salary))
        generated_count += 1
        
    conn.commit()
    conn.close()
    return generated_count

def get_payroll_records(month_year=None, user_id=None, status=None):
    conn = get_db_connection()
    cursor = conn.cursor()
    query = '''
        SELECT p.*, u.full_name, u.emp_code, u.department, u.designation, u.bank_account, u.email
        FROM payroll p
        JOIN users u ON p.user_id = u.id
        WHERE 1=1
    '''
    params = []
    if month_year:
        query += " AND p.month_year = ?"
        params.append(month_year)
    if user_id:
        query += " AND p.user_id = ?"
        params.append(user_id)
    if status and status != 'All':
        query += " AND p.payment_status = ?"
        params.append(status)
        
    query += " ORDER BY p.month_year DESC, p.id DESC"
    cursor.execute(query, params)
    rows = [dict(r) for r in cursor.fetchall()]
    conn.close()
    return rows

def get_payslip(payroll_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT p.*, u.full_name, u.emp_code, u.department, u.designation, u.bank_account, u.email, u.phone, u.joining_date
        FROM payroll p
        JOIN users u ON p.user_id = u.id
        WHERE p.id = ?
    ''', (payroll_id,))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None

def mark_payroll_paid(payroll_id, method='Bank Transfer', ref_no=''):
    conn = get_db_connection()
    cursor = conn.cursor()
    today_str = date.today().strftime('%Y-%m-%d')
    ref = ref_no or f"TXN-{int(datetime.now().timestamp())}"
    
    cursor.execute('''
        UPDATE payroll 
        SET payment_status = 'Paid', payment_date = ?, payment_method = ?, reference_no = ?
        WHERE id = ?
    ''', (today_str, method, ref, payroll_id))
    
    cursor.execute("SELECT user_id, month_year, net_salary FROM payroll WHERE id = ?", (payroll_id,))
    p = cursor.fetchone()
    conn.commit()
    conn.close()
    
    if p:
        create_notification(p['user_id'], "Salary Disbursed", f"Your payslip for {p['month_year']} of amount ${p['net_salary']:,.2f} has been marked as Paid via {method}.", "success")
    return True

# ----------------- HR Masters & Devices ----------------- #

def get_departments():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM hr_departments ORDER BY name ASC")
    rows = [dict(r) for r in cursor.fetchall()]
    conn.close()
    return rows

def get_designations():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM hr_designations ORDER BY title ASC")
    rows = [dict(r) for r in cursor.fetchall()]
    conn.close()
    return rows

def get_shifts():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM hr_shifts ORDER BY id ASC")
    rows = [dict(r) for r in cursor.fetchall()]
    conn.close()
    return rows

def get_holidays():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM hr_holidays ORDER BY date ASC")
    rows = [dict(r) for r in cursor.fetchall()]
    conn.close()
    return rows

def get_devices():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM devices ORDER BY id ASC")
    rows = [dict(r) for r in cursor.fetchall()]
    conn.close()
    return rows

def get_audit_logs(limit=200):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM audit_logs ORDER BY id DESC LIMIT ?", (limit,))
    rows = [dict(r) for r in cursor.fetchall()]
    conn.close()
    return rows

def get_notifications(user_id, limit=50):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM notifications WHERE user_id = ? ORDER BY id DESC LIMIT ?", (user_id, limit))
    rows = [dict(r) for r in cursor.fetchall()]
    cursor.execute("UPDATE notifications SET is_read = 1 WHERE user_id = ?", (user_id,))
    conn.commit()
    conn.close()
    return rows

# Initialize on import
init_db()
