from unittest import mock

from django import forms
from django.contrib.auth import get_user_model
from django.db import DatabaseError
from django.http import HttpResponse
from django.test import RequestFactory, SimpleTestCase, TestCase
from django.urls import reverse

from .bootstrap import prepare_database
from .forms import BootstrapFormMixin
from .middleware import SecurityHeadersMiddleware


class SampleForm(BootstrapFormMixin, forms.Form):
    name = forms.CharField()
    kind = forms.ChoiceField(choices=[("a", "A")])
    agree = forms.BooleanField(required=False)


class BootstrapFormMixinTests(SimpleTestCase):
    def test_widgets_get_bootstrap_classes(self):
        form = SampleForm()
        self.assertEqual(form.fields["name"].widget.attrs["class"], "form-control")
        self.assertEqual(form.fields["kind"].widget.attrs["class"], "form-select")
        self.assertEqual(form.fields["agree"].widget.attrs["class"], "form-check-input")

    def test_text_inputs_get_a_placeholder_for_floating_labels(self):
        form = SampleForm()
        self.assertEqual(form.fields["name"].widget.attrs["placeholder"], "name")
        self.assertNotIn("placeholder", form.fields["kind"].widget.attrs)

    def test_invalid_fields_are_flagged(self):
        form = SampleForm(data={})
        self.assertFalse(form.is_valid())
        self.assertIn("is-invalid", form.fields["name"].widget.attrs["class"])
        self.assertEqual(form.fields["name"].widget.attrs["aria-invalid"], "true")
        self.assertNotIn("is-invalid", form.fields["agree"].widget.attrs["class"])


class SecurityHeadersTests(TestCase):
    def test_pages_send_security_headers(self):
        response = self.client.get(reverse("accounts:login"))
        csp = response["Content-Security-Policy"]
        self.assertIn("default-src 'self'", csp)
        self.assertIn("script-src 'self'", csp)
        self.assertIn("frame-ancestors 'none'", csp)
        self.assertIn("camera=()", response["Permissions-Policy"])
        self.assertEqual(response["X-Frame-Options"], "DENY")
        self.assertEqual(response["X-Content-Type-Options"], "nosniff")

    def test_header_set_by_a_view_is_kept(self):
        def view(request):
            response = HttpResponse()
            response["Content-Security-Policy"] = "default-src 'none'"
            return response

        response = SecurityHeadersMiddleware(view)(RequestFactory().get("/"))
        self.assertEqual(response["Content-Security-Policy"], "default-src 'none'")

    def test_vendored_assets_are_served_locally(self):
        for path in (
            "/static/vendor/bootstrap/css/bootstrap.min.css",
            "/static/vendor/bootstrap/js/bootstrap.bundle.min.js",
            "/static/vendor/bootstrap-icons/bootstrap-icons.min.css",
            "/static/vendor/ibm-plex-sans/IBMPlexSans-Regular.woff2",
            "/static/vendor/ibm-plex-sans/IBMPlexSans-SemiBold.woff2",
            "/static/css/app.css",
            "/static/js/theme.js",
            "/static/js/app.js",
            "/static/favicon.svg",
        ):
            with self.subTest(path=path):
                response = self.client.get(path)
                self.assertEqual(response.status_code, 200)
                response.close()


class HealthCheckTests(TestCase):
    def test_reports_ok_without_login(self):
        response = self.client.get(reverse("health"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"status": "ok"})
        self.assertIn("no-cache", response["Cache-Control"])

    def test_reports_unavailable_when_the_database_fails(self):
        with mock.patch("core.views.get_user_model", side_effect=DatabaseError):
            response = self.client.get(reverse("health"))
        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.json(), {"status": "unavailable"})

    def test_only_get_is_allowed(self):
        self.assertEqual(self.client.post(reverse("health")).status_code, 405)


class PrepareDatabaseTests(TestCase):
    def test_creates_the_demo_account_once(self):
        env = {"DEMO_USERNAME": "judge", "DEMO_PASSWORD": "Judge-pass-2026"}
        with mock.patch.dict("os.environ", env):
            prepare_database()
            prepare_database()
        user = get_user_model().objects.get(username="judge")
        self.assertTrue(user.check_password("Judge-pass-2026"))
        self.assertEqual(user.categories.count(), 6)

    def test_skips_the_demo_account_when_not_configured(self):
        with mock.patch.dict("os.environ", {"DEMO_USERNAME": "", "DEMO_PASSWORD": ""}):
            prepare_database()
        self.assertFalse(get_user_model().objects.exists())
