from django.test import TestCase
from rest_framework.test import APIClient


class LoginAPITests(TestCase):
    def setUp(self):
        self.client = APIClient()

    def test_missing_credentials_returns_400(self):
        response = self.client.post('/api/auth/login/', {}, format='json')
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()['success'], False)
        self.assertEqual(response.json()['message'], 'Username and password are required')

    def test_invalid_credentials_returns_401(self):
        response = self.client.post(
            '/api/auth/login/',
            {'username': 'wrong', 'password': 'user123'},
            format='json',
        )
        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.json()['success'], False)
        self.assertEqual(response.json()['message'], 'Invalid username or password')

    def test_valid_credentials_returns_200(self):
        response = self.client.post(
            '/api/auth/login/',
            {'username': 'user', 'password': 'user123'},
            format='json',
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['success'], True)
        self.assertEqual(response.json()['message'], 'Login successful')
        self.assertEqual(response.json()['username'], 'user')
