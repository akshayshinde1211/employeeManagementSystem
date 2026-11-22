"""
Tests for Employee Management System Flask Application
Developer: Akshay Shinde
"""
import os
import sys
import unittest
import tempfile
import sqlite3
import json

# Ensure project root is in sys.path
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

import app as app_module
from app import app, init_db


class EmployeeManagementSystemTestCase(unittest.TestCase):

    def setUp(self):
        """Set up a temporary database and test client for each test."""
        self.db_fd, self.temp_db_path = tempfile.mkstemp(suffix='.db')
        app_module.DATABASE = self.temp_db_path
        app.config['TESTING'] = True
        self.client = app.test_client()

        # Initialize schema and seed data in the temporary database
        init_db()

    def tearDown(self):
        """Clean up temporary database after each test."""
        os.close(self.db_fd)
        if os.path.exists(self.temp_db_path):
            try:
                os.remove(self.temp_db_path)
            except PermissionError:
                pass

    # ── Page & Static File Tests ───────────────────────────────────────────────

    def test_index_page(self):
        """Test that the main page loads successfully with proper branding."""
        response = self.client.get('/')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'AkshayCorp', response.data)
        self.assertIn(b'Employee Management System', response.data)

    def test_static_assets(self):
        """Test that static CSS and JavaScript files are served properly."""
        with self.client.get('/static/css/style.css') as css_resp:
            self.assertEqual(css_resp.status_code, 200)

        with self.client.get('/static/js/app.js') as js_resp:
            self.assertEqual(js_resp.status_code, 200)

    # ── Departments API Tests ──────────────────────────────────────────────────

    def test_get_departments(self):
        """Test fetching all departments (verifies seed data)."""
        response = self.client.get('/api/departments')
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertIsInstance(data, list)
        self.assertGreaterEqual(len(data), 6)
        dept_names = [d['name'] for d in data]
        self.assertIn('Information Technology', dept_names)
        self.assertIn('Engineering', dept_names)

    def test_create_department_success(self):
        """Test creating a new department with valid payload."""
        payload = {'name': 'Quality Assurance', 'budget': 450000}
        response = self.client.post('/api/departments', json=payload)
        self.assertEqual(response.status_code, 201)
        data = response.get_json()
        self.assertIn('id', data)

        # Verify it appears in get
        depts = self.client.get('/api/departments').get_json()
        self.assertTrue(any(d['id'] == data['id'] and d['name'] == 'Quality Assurance' for d in depts))

    def test_create_department_missing_name(self):
        """Test creating a department without a name returns 400 error."""
        response = self.client.post('/api/departments', json={'budget': 100000})
        self.assertEqual(response.status_code, 400)
        data = response.get_json()
        self.assertIn('error', data)

    def test_update_department(self):
        """Test updating an existing department."""
        # Create department
        res = self.client.post('/api/departments', json={'name': 'Old Name', 'budget': 100000})
        dept_id = res.get_json()['id']

        # Update department
        upd_res = self.client.put(f'/api/departments/{dept_id}', json={'name': 'New Name', 'budget': 200000})
        self.assertEqual(upd_res.status_code, 200)
        self.assertTrue(upd_res.get_json().get('ok'))

        # Verify changes
        depts = self.client.get('/api/departments').get_json()
        updated = next(d for d in depts if d['id'] == dept_id)
        self.assertEqual(updated['name'], 'New Name')
        self.assertEqual(updated['budget'], 200000)

    def test_delete_department(self):
        """Test deleting a department."""
        res = self.client.post('/api/departments', json={'name': 'To Delete', 'budget': 10000})
        dept_id = res.get_json()['id']

        del_res = self.client.delete(f'/api/departments/{dept_id}')
        self.assertEqual(del_res.status_code, 200)

        depts = self.client.get('/api/departments').get_json()
        self.assertFalse(any(d['id'] == dept_id for d in depts))

    # ── Employees API Tests ────────────────────────────────────────────────────

    def test_get_employees(self):
        """Test fetching all employees with joined department details."""
        response = self.client.get('/api/employees')
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertIsInstance(data, list)
        self.assertGreaterEqual(len(data), 9)
        first_emp = data[0]
        self.assertIn('first_name', first_emp)
        self.assertIn('last_name', first_emp)
        self.assertIn('email', first_emp)
        self.assertIn('department', first_emp)

    def test_create_employee_success(self):
        """Test creating a new employee with valid data."""
        depts = self.client.get('/api/departments').get_json()
        dept_id = depts[0]['id']

        payload = {
            'first_name': 'Akshay',
            'last_name': 'Shinde',
            'email': 'akshay.shinde@company.com',
            'phone': '9876543210',
            'salary': 120000,
            'department_id': dept_id
        }
        response = self.client.post('/api/employees', json=payload)
        self.assertEqual(response.status_code, 201)
        data = response.get_json()
        self.assertIn('id', data)

        # Verify added employee
        emps = self.client.get('/api/employees').get_json()
        created = next(e for e in emps if e['id'] == data['id'])
        self.assertEqual(created['first_name'], 'Akshay')
        self.assertEqual(created['last_name'], 'Shinde')
        self.assertEqual(created['department']['id'], dept_id)

    def test_create_employee_validation(self):
        """Test employee creation fails when required fields are missing."""
        # Missing email
        response = self.client.post('/api/employees', json={'first_name': 'John', 'last_name': 'Doe'})
        self.assertEqual(response.status_code, 400)

        # Missing first_name
        response = self.client.post('/api/employees', json={'last_name': 'Doe', 'email': 'john@doe.com'})
        self.assertEqual(response.status_code, 400)

    def test_update_employee(self):
        """Test updating an employee's record."""
        emps = self.client.get('/api/employees').get_json()
        emp_id = emps[0]['id']

        payload = {
            'first_name': 'UpdatedFirst',
            'last_name': 'UpdatedLast',
            'email': 'updated@example.com',
            'phone': '9999999999',
            'salary': 95000,
            'department_id': emps[0]['department_id']
        }
        res = self.client.put(f'/api/employees/{emp_id}', json=payload)
        self.assertEqual(res.status_code, 200)

        emps_after = self.client.get('/api/employees').get_json()
        updated = next(e for e in emps_after if e['id'] == emp_id)
        self.assertEqual(updated['first_name'], 'UpdatedFirst')
        self.assertEqual(updated['email'], 'updated@example.com')

    def test_delete_employee(self):
        """Test deleting an employee."""
        res = self.client.post('/api/employees', json={
            'first_name': 'Temp',
            'last_name': 'User',
            'email': 'temp.user@example.com',
            'salary': 50000
        })
        emp_id = res.get_json()['id']

        del_res = self.client.delete(f'/api/employees/{emp_id}')
        self.assertEqual(del_res.status_code, 200)

        emps = self.client.get('/api/employees').get_json()
        self.assertFalse(any(e['id'] == emp_id for e in emps))

    # ── Projects API Tests ─────────────────────────────────────────────────────

    def test_get_projects(self):
        """Test fetching all projects."""
        response = self.client.get('/api/projects')
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertIsInstance(data, list)
        self.assertGreaterEqual(len(data), 9)

    def test_create_project_success(self):
        """Test creating a project with valid data."""
        payload = {
            'name': 'Cloud Migration Initiative',
            'budget': 500000,
            'status': 'active',
            'start_date': '2026-06-01'
        }
        response = self.client.post('/api/projects', json=payload)
        self.assertEqual(response.status_code, 201)
        data = response.get_json()
        self.assertIn('id', data)

    def test_create_project_missing_name(self):
        """Test project creation requires name."""
        response = self.client.post('/api/projects', json={'budget': 200000})
        self.assertEqual(response.status_code, 400)

    def test_update_project(self):
        """Test updating project details."""
        projs = self.client.get('/api/projects').get_json()
        proj_id = projs[0]['id']

        payload = {
            'name': 'Updated Project Name',
            'budget': 750000,
            'status': 'completed',
            'department_id': projs[0].get('department_id'),
            'start_date': projs[0].get('start_date'),
            'end_date': '2026-11-20'
        }
        res = self.client.put(f'/api/projects/{proj_id}', json=payload)
        self.assertEqual(res.status_code, 200)

        projs_after = self.client.get('/api/projects').get_json()
        updated = next(p for p in projs_after if p['id'] == proj_id)
        self.assertEqual(updated['name'], 'Updated Project Name')
        self.assertEqual(updated['status'], 'completed')

    def test_delete_project(self):
        """Test deleting a project."""
        res = self.client.post('/api/projects', json={'name': 'Temp Project', 'budget': 10000})
        proj_id = res.get_json()['id']

        del_res = self.client.delete(f'/api/projects/{proj_id}')
        self.assertEqual(del_res.status_code, 200)

        projs = self.client.get('/api/projects').get_json()
        self.assertFalse(any(p['id'] == proj_id for p in projs))

    # ── Dependents API Tests ───────────────────────────────────────────────────

    def test_get_dependents(self):
        """Test fetching all dependents."""
        response = self.client.get('/api/dependents')
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertIsInstance(data, list)
        self.assertGreaterEqual(len(data), 8)

    def test_create_dependent_success(self):
        """Test creating a dependent record linked to an employee."""
        emps = self.client.get('/api/employees').get_json()
        emp_id = emps[0]['id']

        payload = {
            'employee_id': emp_id,
            'name': 'Rohan Shinde',
            'relationship': 'Child',
            'date_of_birth': '2016-04-10'
        }
        response = self.client.post('/api/dependents', json=payload)
        self.assertEqual(response.status_code, 201)
        data = response.get_json()
        self.assertIn('id', data)

    def test_create_dependent_missing_fields(self):
        """Test dependent creation fails when required fields are missing."""
        response = self.client.post('/api/dependents', json={'name': 'Incomplete'})
        self.assertEqual(response.status_code, 400)

    def test_update_dependent(self):
        """Test updating a dependent record."""
        deps = self.client.get('/api/dependents').get_json()
        dep_id = deps[0]['id']

        payload = {
            'employee_id': deps[0]['employee_id'],
            'name': 'Updated Dependent Name',
            'relationship': 'Spouse',
            'date_of_birth': '1992-05-15'
        }
        res = self.client.put(f'/api/dependents/{dep_id}', json=payload)
        self.assertEqual(res.status_code, 200)

        deps_after = self.client.get('/api/dependents').get_json()
        updated = next(d for d in deps_after if d['id'] == dep_id)
        self.assertEqual(updated['name'], 'Updated Dependent Name')
        self.assertEqual(updated['relationship'], 'Spouse')

    def test_delete_dependent(self):
        """Test deleting a dependent record."""
        deps = self.client.get('/api/dependents').get_json()
        dep_id = deps[0]['id']

        del_res = self.client.delete(f'/api/dependents/{dep_id}')
        self.assertEqual(del_res.status_code, 200)

        deps_after = self.client.get('/api/dependents').get_json()
        self.assertFalse(any(d['id'] == dep_id for d in deps_after))

    # ── Cascade & Integrity Tests ──────────────────────────────────────────────

    def test_dependent_cascade_on_employee_delete(self):
        """Test that deleting an employee cascades to delete their dependents."""
        # Create an employee
        emp_res = self.client.post('/api/employees', json={
            'first_name': 'Parent',
            'last_name': 'Employee',
            'email': 'parent.emp@example.com',
            'salary': 60000
        })
        emp_id = emp_res.get_json()['id']

        # Create dependent for this employee
        dep_res = self.client.post('/api/dependents', json={
            'employee_id': emp_id,
            'name': 'Child Dependent',
            'relationship': 'Child',
            'date_of_birth': '2018-01-01'
        })
        dep_id = dep_res.get_json()['id']

        # Verify dependent exists
        deps = self.client.get('/api/dependents').get_json()
        self.assertTrue(any(d['id'] == dep_id for d in deps))

        # Delete the employee
        self.client.delete(f'/api/employees/{emp_id}')

        # Verify dependent was automatically deleted by ON DELETE CASCADE
        deps_after = self.client.get('/api/dependents').get_json()
        self.assertFalse(any(d['id'] == dep_id for d in deps_after))


if __name__ == '__main__':
    unittest.main()
