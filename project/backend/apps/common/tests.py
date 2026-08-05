"""Smoke tests for the health endpoint.

This endpoint is what CI, uptime monitors and the deployment script use to
answer "is the app actually up?", so its contract is worth pinning down.
"""
from django.test import TestCase


class HealthEndpointTests(TestCase):
    URL = "/api/health/"

    def test_returns_200(self):
        self.assertEqual(self.client.get(self.URL).status_code, 200)

    def test_reports_status_ok(self):
        self.assertEqual(self.client.get(self.URL).json()["status"], "ok")

    def test_exposes_debug_flag(self):
        # Deploys are verified by checking this is False in production --
        # it proves the production settings file was actually loaded.
        self.assertIn("debug", self.client.get(self.URL).json())

    def test_allows_anonymous_access(self):
        # Every other endpoint requires a token. This one must not, or
        # monitoring can never reach it.
        self.assertEqual(self.client.get(self.URL).status_code, 200)

    def test_is_not_rate_limited(self):
        # Declared with @throttle_classes([]) so monitors can poll freely.
        for _ in range(10):
            self.assertEqual(self.client.get(self.URL).status_code, 200)
