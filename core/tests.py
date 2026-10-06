from django import forms
from django.http import HttpResponse
from django.test import RequestFactory, SimpleTestCase, TestCase
from django.urls import reverse

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
            "/static/css/app.css",
        ):
            with self.subTest(path=path):
                response = self.client.get(path)
                self.assertEqual(response.status_code, 200)
                response.close()
