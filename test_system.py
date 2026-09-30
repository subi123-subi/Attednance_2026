"""
Comprehensive integration test suite covering all 15 Admin modules and 10 Employee modules.
"""

import unittest
from datetime import datetime, timedelta, date
import database as db
from app import app

class ComprehensiveSystemTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        db.init_db()
        cls.client = app.test_client()
        app.config['TESTING'] = True

    def test_01_admin_full_modules(self):
        """Test authentication and all 15 Admin modules."""
        # 1. Login Admin
        resp = self.client.post('/login', data={'username': 'admin', 'password': 'admin123'}, follow_redirects=True)
        self.assertEqual(resp.status_code, 200)

        # 2. Dashboard
        resp = self.client.get('/admin/dashboard')
        self.assertEqual(resp.status_code, 200)

        # 3. Live Attendance
        resp = self.client.get('/admin/live-attendance')
        self.assertEqual(resp.status_code, 200)

        # 4. Employees
        resp = self.client.get('/admin/employees')
        self.assertEqual(resp.status_code, 200)

        # 5. HR Management
        resp = self.client.get('/admin/hr-management')
        self.assertEqual(resp.status_code, 200)

        # 6. Attendance
        resp = self.client.get('/admin/attendance')
        self.assertEqual(resp.status_code, 200)

        # 7. Leaves & Permissions
        resp = self.client.get('/admin/leaves-permissions')
        self.assertEqual(resp.status_code, 200)

        # 8. Corrections
        resp = self.client.get('/admin/corrections')
        self.assertEqual(resp.status_code, 200)

        # 9. Salary Config
        resp = self.client.get('/admin/salary-config')
        self.assertEqual(resp.status_code, 200)

        # 10. Payroll
        resp = self.client.get('/admin/payroll')
        self.assertEqual(resp.status_code, 200)

        # 11. Payments
        resp = self.client.get('/admin/payments')
        self.assertEqual(resp.status_code, 200)

        # 12. Payslips
        resp = self.client.get('/admin/payslips')
        self.assertEqual(resp.status_code, 200)

        # 13. Reports
        resp = self.client.get('/admin/reports')
        self.assertEqual(resp.status_code, 200)

        # 14. Devices
        resp = self.client.get('/admin/devices')
        self.assertEqual(resp.status_code, 200)

        # 15. Company Settings
        resp = self.client.get('/admin/company-settings')
        self.assertEqual(resp.status_code, 200)

        # 16. Audit Logs
        resp = self.client.get('/admin/audit-logs')
        self.assertEqual(resp.status_code, 200)

        # 17. CSV Export
        resp = self.client.get('/admin/export/csv')
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.mimetype, 'text/csv')

        # 18. ZIP Download
        resp = self.client.get('/download-zip')
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.mimetype, 'application/zip')

        # Logout
        self.client.get('/logout')

    def test_02_employee_full_modules(self):
        """Test authentication and all 10 Employee modules."""
        # 1. Login Employee
        resp = self.client.post('/login', data={'username': 'john.doe', 'password': 'emp123'}, follow_redirects=True)
        self.assertEqual(resp.status_code, 200)

        # 2. Dashboard
        resp = self.client.get('/employee/dashboard')
        self.assertEqual(resp.status_code, 200)

        # 3. My Attendance
        resp = self.client.get('/employee/my-attendance')
        self.assertEqual(resp.status_code, 200)

        # 4. Attendance Calendar
        resp = self.client.get('/employee/attendance-calendar')
        self.assertEqual(resp.status_code, 200)

        # 5. Leave
        resp = self.client.get('/employee/leave')
        self.assertEqual(resp.status_code, 200)

        # 6. Permission
        resp = self.client.get('/employee/permission')
        self.assertEqual(resp.status_code, 200)

        # 7. Corrections
        resp = self.client.get('/employee/corrections')
        self.assertEqual(resp.status_code, 200)

        # 8. My Salary
        resp = self.client.get('/employee/my-salary')
        self.assertEqual(resp.status_code, 200)

        # 9. Payslips
        resp = self.client.get('/employee/payslips')
        self.assertEqual(resp.status_code, 200)

        # 10. Notifications
        resp = self.client.get('/employee/notifications')
        self.assertEqual(resp.status_code, 200)

        # 11. Profile
        resp = self.client.get('/employee/profile')
        self.assertEqual(resp.status_code, 200)

    def test_03_payroll_generation_and_payslip_view(self):
        """Test running automated payroll and viewing payslip."""
        # Logout any prior session
        self.client.get('/logout')
        
        # 1. Login as Admin
        self.client.post('/login', data={'username': 'admin', 'password': 'admin123'}, follow_redirects=True)
        month_str = date.today().strftime('%Y-%m')
        count = db.generate_monthly_payroll(month_str)
        self.assertGreater(count, 0)


        records = db.get_payroll_records(month_year=month_str)
        self.assertGreater(len(records), 0)
        p_id = records[0]['id']

        # View Payslip as Admin
        resp = self.client.get(f'/payslip/view/{p_id}')
        self.assertEqual(resp.status_code, 200)
        self.assertIn(b"Official Salary Slip", resp.data)



if __name__ == '__main__':
    unittest.main()
