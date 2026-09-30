"""
WorkPulse Enterprise Attendance & HR Management System
Full implementations for:
- 15 Admin Modules
- 10 Employee Modules
- Automated Payroll, Live Timers, Calendar, Payslips, and ZIP Archiver
"""

import os
import csv
import io
import zipfile
import shutil
from datetime import datetime, date, timedelta
from functools import wraps
from flask import (
    Flask, render_template, request, redirect, url_for, 
    flash, session, jsonify, Response, send_file, make_response
)
import database as db

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'workpulse-enterprise-supersecret-2026')

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# ----------------- Decorators & Context Processors ----------------- #

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash("Please sign in to access the portal.", "warning")
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash("Please sign in to access this page.", "warning")
            return redirect(url_for('login'))
        if session.get('role') != 'admin':
            flash("Access denied. Administrator privileges required.", "danger")
            return redirect(url_for('employee_dashboard'))
        return f(*args, **kwargs)
    return decorated_function

@app.context_processor
def inject_global_data():
    user = None
    unread_notifs = 0
    if 'user_id' in session:
        user = db.get_user_by_id(session['user_id'])
        if user:
            conn = db.get_db_connection()
            c = conn.cursor()
            c.execute("SELECT COUNT(*) as c FROM notifications WHERE user_id = ? AND is_read = 0", (user['id'],))
            unread_notifs = c.fetchone()['c']
            conn.close()

    settings = db.get_company_settings()
    return {
        'current_user': user,
        'company_settings': settings,
        'current_year': datetime.now().year,
        'today_date': date.today().strftime('%Y-%m-%d'),
        'current_month': date.today().strftime('%Y-%m'),
        'unread_notifs_count': unread_notifs
    }

# ----------------- Auth Routes ----------------- #

@app.route('/')
def index():
    if 'user_id' in session:
        if session.get('role') == 'admin':
            return redirect(url_for('admin_dashboard'))
        return redirect(url_for('employee_dashboard'))
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if 'user_id' in session:
        if session.get('role') == 'admin':
            return redirect(url_for('admin_dashboard'))
        return redirect(url_for('employee_dashboard'))
        
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '').strip()
        
        if not username or not password:
            flash("Please enter both username/employee code and password.", "danger")
            return render_template('login.html')
            
        user = db.authenticate_user(username, password)
        if user:
            session['user_id'] = user['id']
            session['username'] = user['username']
            session['full_name'] = user['full_name']
            session['role'] = user['role']
            session['emp_code'] = user['emp_code']
            
            db.log_audit(user['id'], user['full_name'], "User Login", f"Logged in via {request.remote_addr}", request.remote_addr)
            
            flash(f"Welcome back, {user['full_name']}!", "success")
            if user['role'] == 'admin':
                return redirect(url_for('admin_dashboard'))
            return redirect(url_for('employee_dashboard'))
        else:
            flash("Invalid Employee ID / Username or Password. Please contact Administrator.", "danger")
            
    return render_template('login.html')

@app.route('/logout')
def logout():
    if 'user_id' in session:
        db.log_audit(session['user_id'], session.get('full_name', 'User'), "User Logout", "Logged out", request.remote_addr)
    session.clear()
    flash("You have successfully signed out.", "info")
    return redirect(url_for('login'))


# =========================================================================
# 🛡️ ADMIN PORTAL ROUTES (15 Complete Modules)
# =========================================================================

# 1. Dashboard
@app.route('/admin/dashboard')
@admin_required
def admin_dashboard():
    stats = db.get_admin_dashboard_stats()
    departments = db.get_departments()
    recent_records = db.get_all_attendance_records(limit=10)
    active_records = [r for r in recent_records if r['status'] == 'Checked In' or r['check_out'] is None]
    
    return render_template(
        'admin/dashboard.html',
        stats=stats,
        recent_records=recent_records,
        active_records=active_records,
        departments=departments
    )

# 2. Live Attendance
@app.route('/admin/live-attendance')
@admin_required
def admin_live_attendance():
    all_records = db.get_all_attendance_records(limit=200)
    live_records = [r for r in all_records if r['check_out'] is None]
    completed_today = [r for r in all_records if r['date'] == date.today().strftime('%Y-%m-%d') and r['check_out'] is not None]
    stats = db.get_admin_dashboard_stats()
    
    return render_template(
        'admin/live_attendance.html',
        live_records=live_records,
        completed_today=completed_today,
        stats=stats
    )

# 3. Employees Management (CRUD & Passwords)
@app.route('/admin/employees')
@admin_required
def admin_employees():
    search = request.args.get('search', '').strip()
    department = request.args.get('department', 'All')
    employees = db.get_all_employees(search=search, department=department)
    departments = db.get_departments()
    designations = db.get_designations()
    
    return render_template(
        'admin/employees.html',
        employees=employees,
        departments=departments,
        designations=designations,
        current_dept=department,
        search_query=search
    )

@app.route('/admin/employees/add', methods=['POST'])
@admin_required
def admin_add_employee():
    emp_code = request.form.get('emp_code', '').strip()
    full_name = request.form.get('full_name', '').strip()
    username = request.form.get('username', '').strip()
    email = request.form.get('email', '').strip()
    password = request.form.get('password', '').strip()
    department = request.form.get('department', 'Engineering')
    designation = request.form.get('designation', 'Staff')
    phone = request.form.get('phone', '').strip()
    joining_date = request.form.get('joining_date', date.today().strftime('%Y-%m-%d'))
    salary_type = request.form.get('salary_type', 'Monthly')
    basic_salary = float(request.form.get('basic_salary') or 3500.0)
    hourly_rate = float(request.form.get('hourly_rate') or 25.0)
    allowance = float(request.form.get('allowance') or 300.0)
    deductions = float(request.form.get('deductions') or 150.0)
    
    if not emp_code or not full_name or not username or not password:
        flash("Employee Code, Full Name, Username, and Password are required.", "danger")
        return redirect(url_for('admin_employees'))
        
    success, result = db.create_employee(
        emp_code, full_name, username, email, password, department, designation, phone, joining_date,
        basic_salary, hourly_rate, allowance, deductions, salary_type
    )
    
    if success:
        db.log_audit(session['user_id'], session['full_name'], "Create Employee", f"Registered {full_name} ({emp_code})", request.remote_addr)
        flash(f"Employee {full_name} ({emp_code}) registered successfully with designated password!", "success")
    else:
        flash(f"Error registering employee: {result}", "danger")
        
    return redirect(url_for('admin_employees'))

@app.route('/admin/employees/edit/<int:user_id>', methods=['POST'])
@admin_required
def admin_edit_employee(user_id):
    emp_code = request.form.get('emp_code', '').strip()
    full_name = request.form.get('full_name', '').strip()
    username = request.form.get('username', '').strip()
    email = request.form.get('email', '').strip()
    password = request.form.get('password', '').strip()
    department = request.form.get('department', 'Engineering')
    designation = request.form.get('designation', 'Staff')
    phone = request.form.get('phone', '').strip()
    status = request.form.get('status', 'Active')
    basic_salary = request.form.get('basic_salary')
    hourly_rate = request.form.get('hourly_rate')
    allowance = request.form.get('allowance')
    deductions = request.form.get('deductions')
    salary_type = request.form.get('salary_type')
    
    success, message = db.update_employee(
        user_id, emp_code, full_name, username, email, password, department, designation, phone, status,
        basic_salary, hourly_rate, allowance, deductions, salary_type
    )
    
    if success:
        db.log_audit(session['user_id'], session['full_name'], "Edit Employee", f"Updated details for ID {user_id}", request.remote_addr)
        flash(f"Employee {full_name} profile updated.", "success")
    else:
        flash(f"Failed to update employee: {message}", "danger")
        
    return redirect(url_for('admin_employees'))

@app.route('/admin/employees/delete/<int:user_id>', methods=['POST'])
@admin_required
def admin_delete_employee(user_id):
    success = db.delete_employee(user_id)
    if success:
        db.log_audit(session['user_id'], session['full_name'], "Delete Employee", f"Removed Employee ID {user_id}", request.remote_addr)
        flash("Employee record removed successfully.", "success")
    else:
        flash("Unable to delete employee.", "danger")
    return redirect(url_for('admin_employees'))

# 4. HR Management (Departments, Designations, Shifts, Holidays)
@app.route('/admin/hr-management')
@admin_required
def admin_hr_management():
    depts = db.get_departments()
    desigs = db.get_designations()
    shifts = db.get_shifts()
    holidays = db.get_holidays()
    return render_template(
        'admin/hr_management.html',
        departments=depts,
        designations=desigs,
        shifts=shifts,
        holidays=holidays
    )

@app.route('/admin/hr/dept/add', methods=['POST'])
@admin_required
def admin_add_department():
    name = request.form.get('name', '').strip()
    head = request.form.get('head_of_dept', '').strip()
    desc = request.form.get('description', '').strip()
    if name:
        conn = db.get_db_connection()
        try:
            conn.cursor().execute("INSERT INTO hr_departments (name, head_of_dept, description) VALUES (?, ?, ?)", (name, head, desc))
            conn.commit()
            flash(f"Department '{name}' added successfully.", "success")
        except:
            flash("Department name already exists.", "danger")
        conn.close()
    return redirect(url_for('admin_hr_management'))

@app.route('/admin/hr/holiday/add', methods=['POST'])
@admin_required
def admin_add_holiday():
    name = request.form.get('name', '').strip()
    h_date = request.form.get('date', '').strip()
    h_type = request.form.get('holiday_type', 'Public Holiday')
    if name and h_date:
        conn = db.get_db_connection()
        conn.cursor().execute("INSERT INTO hr_holidays (name, date, holiday_type) VALUES (?, ?, ?)", (name, h_date, h_type))
        conn.commit()
        conn.close()
        flash(f"Holiday '{name}' scheduled for {h_date}.", "success")
    return redirect(url_for('admin_hr_management'))

# 5. Master Attendance Logs
@app.route('/admin/attendance')
@admin_required
def admin_attendance():
    user_id = request.args.get('user_id', '')
    department = request.args.get('department', 'All')
    start_date = request.args.get('start_date', '')
    end_date = request.args.get('end_date', '')
    status = request.args.get('status', 'All')
    
    u_id = int(user_id) if user_id and user_id.isdigit() else None
    records = db.get_all_attendance_records(
        user_id=u_id, department=department, start_date=start_date, end_date=end_date, status=status, limit=500
    )
    
    total_seconds = sum(r['work_duration_seconds'] for r in records)
    total_hours = db.format_seconds(total_seconds)
    decimal_hours = db.format_hours_decimal(total_seconds)
    
    employees = db.get_all_employees()
    departments = db.get_departments()
    
    return render_template(
        'admin/attendance.html',
        records=records,
        employees=employees,
        departments=departments,
        selected_user=u_id,
        selected_dept=department,
        start_date=start_date,
        end_date=end_date,
        selected_status=status,
        total_hours=total_hours,
        decimal_hours=decimal_hours,
        total_records_count=len(records)
    )

@app.route('/admin/attendance/clock_out/<int:att_id>', methods=['POST'])
@admin_required
def admin_force_clock_out(att_id):
    notes = request.form.get('notes', 'Admin Manual Clock Out')
    success, msg = db.admin_manual_clock_out(att_id, notes=notes)
    if success:
        flash("Attendance record clocked out successfully.", "success")
    else:
        flash(f"Error: {msg}", "danger")
    return redirect(request.referrer or url_for('admin_attendance'))

# 6. Leaves & Permissions Review
@app.route('/admin/leaves-permissions')
@admin_required
def admin_leaves_permissions():
    leaves = db.get_leaves()
    permissions = db.get_permissions()
    return render_template(
        'admin/leaves_permissions.html',
        leaves=leaves,
        permissions=permissions
    )

@app.route('/admin/leave/review/<int:leave_id>', methods=['POST'])
@admin_required
def admin_review_leave(leave_id):
    status = request.form.get('status')
    comment = request.form.get('admin_comment', '')
    db.review_leave(leave_id, status, comment)
    flash(f"Leave request marked as {status}.", "success")
    return redirect(url_for('admin_leaves_permissions'))

@app.route('/admin/permission/review/<int:perm_id>', methods=['POST'])
@admin_required
def admin_review_permission(perm_id):
    status = request.form.get('status')
    comment = request.form.get('admin_comment', '')
    db.review_permission(perm_id, status, comment)
    flash(f"Permission request marked as {status}.", "success")
    return redirect(url_for('admin_leaves_permissions'))

# 7. Attendance Corrections
@app.route('/admin/corrections')
@admin_required
def admin_corrections():
    corrections = db.get_corrections()
    return render_template('admin/corrections.html', corrections=corrections)

@app.route('/admin/corrections/review/<int:corr_id>', methods=['POST'])
@admin_required
def admin_review_correction(corr_id):
    status = request.form.get('status')
    comment = request.form.get('admin_comment', '')
    db.review_correction(corr_id, status, comment)
    flash(f"Attendance correction request {status}.", "success")
    return redirect(url_for('admin_corrections'))

# 8. Salary Configuration
@app.route('/admin/salary-config')
@admin_required
def admin_salary_config():
    employees = db.get_all_employees()
    return render_template('admin/salary_config.html', employees=employees)

@app.route('/admin/salary-config/update/<int:user_id>', methods=['POST'])
@admin_required
def admin_update_salary_config(user_id):
    basic = float(request.form.get('basic_salary') or 0)
    hourly = float(request.form.get('hourly_rate') or 0)
    allowance = float(request.form.get('allowance') or 0)
    deductions = float(request.form.get('deductions') or 0)
    sal_type = request.form.get('salary_type', 'Monthly')
    bank = request.form.get('bank_account', '').strip()
    
    conn = db.get_db_connection()
    conn.cursor().execute('''
        UPDATE users 
        SET basic_salary = ?, hourly_rate = ?, allowance = ?, deductions = ?, salary_type = ?, bank_account = ?
        WHERE id = ?
    ''', (basic, hourly, allowance, deductions, sal_type, bank, user_id))
    conn.commit()
    conn.close()
    
    flash("Employee salary structure updated successfully.", "success")
    return redirect(url_for('admin_salary_config'))

# 9. Payroll Processing
@app.route('/admin/payroll')
@admin_required
def admin_payroll():
    month = request.args.get('month', date.today().strftime('%Y-%m'))
    status = request.args.get('status', 'All')
    records = db.get_payroll_records(month_year=month, status=status)
    
    total_payout = sum(r['net_salary'] for r in records)
    paid_payout = sum(r['net_salary'] for r in records if r['payment_status'] == 'Paid')
    pending_payout = sum(r['net_salary'] for r in records if r['payment_status'] == 'Pending')
    
    return render_template(
        'admin/payroll.html',
        records=records,
        current_month=month,
        selected_status=status,
        total_payout=total_payout,
        paid_payout=paid_payout,
        pending_payout=pending_payout
    )

@app.route('/admin/payroll/generate', methods=['POST'])
@admin_required
def admin_generate_payroll():
    month = request.form.get('month_year', date.today().strftime('%Y-%m'))
    count = db.generate_monthly_payroll(month)
    db.log_audit(session['user_id'], session['full_name'], "Payroll Run", f"Generated {count} payroll records for {month}", request.remote_addr)
    flash(f"Generated automated payroll for {count} active employees for month {month}.", "success")
    return redirect(url_for('admin_payroll', month=month))

# 10. Payments
@app.route('/admin/payments')
@admin_required
def admin_payments():
    records = db.get_payroll_records()
    return render_template('admin/payments.html', records=records)

@app.route('/admin/payments/disburse/<int:payroll_id>', methods=['POST'])
@admin_required
def admin_disburse_payment(payroll_id):
    method = request.form.get('payment_method', 'Bank Transfer')
    ref = request.form.get('reference_no', '')
    db.mark_payroll_paid(payroll_id, method, ref)
    flash("Payment recorded and employee notified.", "success")
    return redirect(url_for('admin_payments'))

# 11. Payslips / Receipts
@app.route('/admin/payslips')
@admin_required
def admin_payslips():
    records = db.get_payroll_records()
    return render_template('admin/payslips.html', records=records)

@app.route('/payslip/view/<int:payroll_id>')
@login_required
def view_payslip(payroll_id):
    slip = db.get_payslip(payroll_id)
    if not slip:
        flash("Payslip not found.", "danger")
        return redirect(url_for('index'))
    # Security check: employee can only view their own
    if session.get('role') != 'admin' and slip['user_id'] != session['user_id']:
        flash("Unauthorized access to payslip.", "danger")
        return redirect(url_for('employee_dashboard'))
        
    return render_template('payslip_detail.html', slip=slip)

# 12. Reports & Analytics
@app.route('/admin/reports')
@admin_required
def admin_reports():
    stats = db.get_admin_dashboard_stats()
    employees = db.get_all_employees()
    records = db.get_all_attendance_records(limit=100)
    payroll_all = db.get_payroll_records()
    
    return render_template(
        'admin/reports.html',
        stats=stats,
        employees=employees,
        records=records,
        payroll=payroll_all
    )

# 13. Device Management
@app.route('/admin/devices')
@admin_required
def admin_devices():
    devices = db.get_devices()
    return render_template('admin/devices.html', devices=devices)

@app.route('/admin/devices/add', methods=['POST'])
@admin_required
def admin_add_device():
    name = request.form.get('name', '').strip()
    d_type = request.form.get('device_type', 'Biometric Scanner')
    ip = request.form.get('ip_address', '').strip()
    loc = request.form.get('location', 'Main Gate')
    
    if name and ip:
        conn = db.get_db_connection()
        conn.cursor().execute('''
            INSERT INTO devices (name, device_type, ip_address, location, status)
            VALUES (?, ?, ?, ?, 'Online')
        ''', (name, d_type, ip, loc))
        conn.commit()
        conn.close()
        flash(f"Device '{name}' configured successfully.", "success")
    return redirect(url_for('admin_devices'))

@app.route('/admin/devices/sync/<int:dev_id>', methods=['POST'])
@admin_required
def admin_sync_device(dev_id):
    conn = db.get_db_connection()
    conn.cursor().execute("UPDATE devices SET last_sync = CURRENT_TIMESTAMP WHERE id = ?", (dev_id,))
    conn.commit()
    conn.close()
    flash("Device synchronized successfully with central attendance database.", "success")
    return redirect(url_for('admin_devices'))

# 14. Company Settings
@app.route('/admin/company-settings', methods=['GET', 'POST'])
@admin_required
def admin_company_settings():
    if request.method == 'POST':
        c_name = request.form.get('company_name', '').strip()
        work_hours = float(request.form.get('standard_work_hours') or 8.0)
        grace = int(request.form.get('grace_period_mins') or 15)
        currency = request.form.get('currency', '$').strip()
        ot_mult = float(request.form.get('overtime_rate_multiplier') or 1.5)
        tax = float(request.form.get('tax_percentage') or 5.0)
        address = request.form.get('address', '').strip()
        email = request.form.get('contact_email', '').strip()
        phone = request.form.get('contact_phone', '').strip()
        
        db.update_company_settings(c_name, work_hours, grace, currency, ot_mult, tax, address, email, phone)
        flash("Company policies and attendance parameters updated.", "success")
        return redirect(url_for('admin_company_settings'))
        
    settings = db.get_company_settings()
    return render_template('admin/company_settings.html', settings=settings)

# 15. Audit Logs
@app.route('/admin/audit-logs')
@admin_required
def admin_audit_logs():
    logs = db.get_audit_logs(limit=300)
    return render_template('admin/audit_logs.html', logs=logs)

# CSV Export
@app.route('/admin/export/csv')
@admin_required
def admin_export_csv():
    records = db.get_all_attendance_records(limit=2000)
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['Record ID', 'Employee Code', 'Full Name', 'Department', 'Designation', 'Date', 'Check In', 'Check Out', 'Duration (H:M)', 'Decimal Hours', 'Status', 'Notes'])
    for r in records:
        writer.writerow([
            r['id'], r['emp_code'], r['full_name'], r['department'], r['designation'],
            r['date'], r['check_in'], r['check_out'] or 'Active', r['work_duration_formatted'],
            r['hours_decimal'], r['status'], r['notes'] or ''
        ])
    output.seek(0)
    return Response(
        output.getvalue(),
        mimetype="text/csv",
        headers={"Content-Disposition": f"attachment;filename=attendance_master_report_{date.today().strftime('%Y%m%d')}.csv"}
    )


# =========================================================================
# 👤 EMPLOYEE PORTAL ROUTES (10 Complete Modules)
# =========================================================================

# 1. Dashboard (Live Check-In / Out, Timer, Today Status, Working Hours)
@app.route('/employee/dashboard')
@login_required
def employee_dashboard():
    user_id = session['user_id']
    stats = db.get_employee_stats(user_id)
    history = db.get_employee_attendance_history(user_id, limit=10)
    leaves = db.get_leaves(user_id=user_id)[:3]
    notifs = db.get_notifications(user_id, limit=5)
    
    return render_template(
        'employee/dashboard.html',
        stats=stats,
        history=history,
        leaves=leaves,
        notifications=notifs
    )

@app.route('/employee/check_in', methods=['POST'])
@login_required
def employee_check_in():
    user_id = session['user_id']
    notes = request.form.get('notes', '').strip()
    success, res = db.record_check_in(user_id, notes=notes, ip_address=request.remote_addr)
    if success:
        flash(f"Check-in recorded at {res['check_in']}. Have a productive day!", "success")
    else:
        flash(res, "warning")
    return redirect(url_for('employee_dashboard'))

@app.route('/employee/check_out', methods=['POST'])
@login_required
def employee_check_out():
    user_id = session['user_id']
    notes = request.form.get('notes', '').strip()
    success, res = db.record_check_out(user_id, notes=notes, ip_address=request.remote_addr)
    if success:
        flash(f"Check-out recorded at {res['check_out']}! Total session: {res['duration']} ({res['hours_decimal']} hrs).", "success")
    else:
        flash(res, "warning")
    return redirect(url_for('employee_dashboard'))

# 2. My Attendance
@app.route('/employee/my-attendance')
@login_required
def employee_my_attendance():
    user_id = session['user_id']
    start_date = request.args.get('start_date', '')
    end_date = request.args.get('end_date', '')
    history = db.get_employee_attendance_history(user_id, start_date=start_date, end_date=end_date, limit=150)
    stats = db.get_employee_stats(user_id)
    return render_template('employee/my_attendance.html', history=history, stats=stats, start_date=start_date, end_date=end_date)

# 3. Attendance Calendar (Visual Monthly Calendar)
@app.route('/employee/attendance-calendar')
@login_required
def employee_attendance_calendar():
    user_id = session['user_id']
    month = request.args.get('month', date.today().strftime('%Y-%m'))
    history = db.get_employee_attendance_history(user_id, start_date=f"{month}-01", end_date=f"{month}-31", limit=100)
    holidays = db.get_holidays()
    
    # Map attendance by date
    att_by_date = {r['date']: r for r in history}
    
    return render_template(
        'employee/attendance_calendar.html',
        att_by_date=att_by_date,
        current_month=month,
        holidays=holidays
    )

# 4. Leave Application & History
@app.route('/employee/leave', methods=['GET', 'POST'])
@login_required
def employee_leave():
    user_id = session['user_id']
    if request.method == 'POST':
        l_type = request.form.get('leave_type', 'Casual')
        s_date = request.form.get('start_date')
        e_date = request.form.get('end_date')
        reason = request.form.get('reason', '').strip()
        if s_date and e_date and reason:
            db.apply_leave(user_id, l_type, s_date, e_date, reason)
            flash("Leave request submitted for review.", "success")
            return redirect(url_for('employee_leave'))
            
    leaves = db.get_leaves(user_id=user_id)
    return render_template('employee/leaves.html', leaves=leaves)

# 5. Permission Application
@app.route('/employee/permission', methods=['GET', 'POST'])
@login_required
def employee_permission():
    user_id = session['user_id']
    if request.method == 'POST':
        req_date = request.form.get('date')
        s_time = request.form.get('start_time')
        e_time = request.form.get('end_time')
        reason = request.form.get('reason', '').strip()
        if req_date and s_time and e_time and reason:
            db.apply_permission(user_id, req_date, s_time, e_time, reason)
            flash("Short leave permission request submitted.", "success")
            return redirect(url_for('employee_permission'))
            
    permissions = db.get_permissions(user_id=user_id)
    return render_template('employee/permissions.html', permissions=permissions)

# 6. Attendance Correction Request
@app.route('/employee/corrections', methods=['GET', 'POST'])
@login_required
def employee_corrections():
    user_id = session['user_id']
    if request.method == 'POST':
        c_date = request.form.get('date')
        c_in = request.form.get('requested_check_in')
        c_out = request.form.get('requested_check_out')
        reason = request.form.get('reason', '').strip()
        if c_date and c_in and c_out and reason:
            db.apply_correction(user_id, c_date, c_in, c_out, reason)
            flash("Attendance correction request submitted to HR.", "success")
            return redirect(url_for('employee_corrections'))
            
    corrections = db.get_corrections(user_id=user_id)
    return render_template('employee/corrections.html', corrections=corrections)

# 7. My Salary
@app.route('/employee/my-salary')
@login_required
def employee_my_salary():
    user_id = session['user_id']
    user = db.get_user_by_id(user_id)
    payroll_history = db.get_payroll_records(user_id=user_id)
    return render_template('employee/my_salary.html', user=user, payroll_history=payroll_history)

# 8. Payslips
@app.route('/employee/payslips')
@login_required
def employee_payslips():
    user_id = session['user_id']
    payslips = db.get_payroll_records(user_id=user_id)
    return render_template('employee/payslips.html', payslips=payslips)

# 9. Notifications
@app.route('/employee/notifications')
@login_required
def employee_notifications():
    user_id = session['user_id']
    notifs = db.get_notifications(user_id, limit=100)
    return render_template('employee/notifications.html', notifications=notifs)

# 10. Profile
@app.route('/employee/profile', methods=['GET', 'POST'])
@login_required
def employee_profile():
    user_id = session['user_id']
    if request.method == 'POST':
        phone = request.form.get('phone', '').strip()
        email = request.form.get('email', '').strip()
        bank = request.form.get('bank_account', '').strip()
        new_pass = request.form.get('new_password', '').strip()
        
        conn = db.get_db_connection()
        if new_pass:
            p_hash = db.generate_password_hash(new_pass)
            conn.cursor().execute('''
                UPDATE users SET phone = ?, email = ?, bank_account = ?, password_hash = ?, raw_password_hint = ?
                WHERE id = ?
            ''', (phone, email, bank, p_hash, new_pass, user_id))
        else:
            conn.cursor().execute('''
                UPDATE users SET phone = ?, email = ?, bank_account = ?
                WHERE id = ?
            ''', (phone, email, bank, user_id))
        conn.commit()
        conn.close()
        
        flash("Profile updated successfully.", "success")
        return redirect(url_for('employee_profile'))
        
    user = db.get_user_by_id(user_id)
    return render_template('employee/profile.html', user=user)


# =========================================================================
# 📦 ZIP DOWNLOAD ROUTE (Instant Download of Whole Project)
# =========================================================================

@app.route('/download-zip')
def download_project_zip():
    """Generates an in-memory ZIP archive of the whole application and serves it."""
    memory_file = io.BytesIO()
    with zipfile.ZipFile(memory_file, 'w', zipfile.ZIP_DEFLATED) as zf:
        for root, dirs, files in os.walk(BASE_DIR):
            # Ignore cache & git folders
            if '__pycache__' in root or '.git' in root or 'venv' in root:
                continue
            for file in files:
                if file.endswith('.pyc') or file.endswith('.zip'):
                    continue
                file_path = os.path.join(root, file)
                rel_path = os.path.relpath(file_path, BASE_DIR)
                zf.write(file_path, arcname=os.path.join('attendance_system', rel_path))
                
    memory_file.seek(0)
    return send_file(
        memory_file,
        mimetype='application/zip',
        as_attachment=True,
        download_name='attendance_management_system.zip'
    )


if __name__ == '__main__':
    app.run(debug=True, host='127.0.0.1', port=5000)
