import unittest
from app import app, db, User, Todo
from flask_login import current_user

class BasicTests(unittest.TestCase):

    def setUp(self):
        app.config['TESTING'] = True
        app.config['WTF_CSRF_ENABLED'] = False
        app.config['DEBUG'] = False
        app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///test.db'
        self.app = app.test_client()
        with app.app_context():
            db.create_all()

    def tearDown(self):
        with app.app_context():
            db.session.remove()
            db.drop_all()

    def register(self, username, password):
        return self.app.post('/register', data=dict(username=username, password=password), follow_redirects=True)

    def login(self, username, password):
        return self.app.post('/login', data=dict(username=username, password=password), follow_redirects=True)

    def logout(self):
        return self.app.get('/logout', follow_redirects=True)

    def add_todo(self, description):
        return self.app.post('/add', data=dict(description=description), follow_redirects=True)

    def test_register(self):
        response = self.register('testuser', 'password')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Logout', response.data)

    def test_login(self):
        self.register('testuser', 'password')
        response = self.login('testuser', 'password')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Logout', response.data)

    def test_add_todo(self):
        self.register('testuser', 'password')
        self.login('testuser', 'password')
        response = self.add_todo('Test Todo')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Test Todo', response.data)

    def test_logout(self):
        self.register('testuser', 'password')
        self.login('testuser', 'password')
        response = self.logout()
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Login', response.data)

if __name__ == "__main__":
    unittest.main()
