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
        self.assertEqual(response.data.get('database'), 'connected')
        self.assertIn('CleanRoute AI backend is running', response.data.get('message', ''))
