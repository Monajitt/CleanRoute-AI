from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient


class HealthCheckAPITests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.health_url = reverse('health-check')

    def test_health_check_endpoint_returns_success(self):
        response = self.client.get(self.health_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data.get('success'))
        self.assertEqual(response.data.get('status'), 'ok')
        self.assertEqual(response.data.get('database'), 'connected')
        self.assertIn('CleanRoute AI backend is running', response.data.get('message', ''))

    def test_health_check_with_browser_accept_header(self):
        # Browsers send text/html; ensure JSON is returned cleanly with 200 OK
        response = self.client.get(self.health_url, HTTP_ACCEPT='text/html,application/xhtml+xml')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response['Content-Type'], 'application/json')
        self.assertTrue(response.data.get('success'))
