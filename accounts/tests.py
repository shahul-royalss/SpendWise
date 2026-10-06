from django.contrib.auth import SESSION_KEY, get_user_model
from django.test import TestCase
from django.urls import reverse

PASSWORD = "Sp3nd-Wise-2026!"


class RegistrationTests(TestCase):
    url = reverse("accounts:register")

    def post(self, **overrides):
        data = {"username": "newuser", "email": "", "password1": PASSWORD, "password2": PASSWORD}
        data.update(overrides)
        return self.client.post(self.url, data)

    def test_page_renders(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Create your account")

    def test_register_creates_user_logs_in_and_opens_dashboard(self):
        response = self.post()
        self.assertRedirects(response, reverse("tracker:dashboard"))
        user = get_user_model().objects.get(username="newuser")
        self.assertEqual(int(self.client.session[SESSION_KEY]), user.pk)
        self.assertTrue(user.check_password(PASSWORD))

    def test_mismatched_passwords_return_200(self):
        response = self.post(password2="something-else-2026")
        self.assertEqual(response.status_code, 200)
        self.assertIn("password2", response.context["form"].errors)
        self.assertFalse(get_user_model().objects.exists())

    def test_weak_password_is_rejected(self):
        response = self.post(password1="password", password2="password")
        self.assertEqual(response.status_code, 200)
        self.assertFalse(get_user_model().objects.exists())

    def test_username_must_be_unique_ignoring_case(self):
        get_user_model().objects.create_user("NewUser")
        response = self.post()
        self.assertEqual(response.status_code, 200)
        self.assertIn("username", response.context["form"].errors)

    def test_logged_in_users_are_sent_to_the_dashboard(self):
        self.client.force_login(get_user_model().objects.create_user("alice"))
        self.assertRedirects(
            self.client.get(self.url), reverse("tracker:dashboard"), fetch_redirect_response=False
        )


class LoginLogoutTests(TestCase):
    login_url = reverse("accounts:login")

    @classmethod
    def setUpTestData(cls):
        cls.user = get_user_model().objects.create_user("alice", password=PASSWORD)

    def test_login_page_renders(self):
        self.assertContains(self.client.get(self.login_url), "Log in to SpendWise")

    def test_login_redirects_to_the_dashboard(self):
        response = self.client.post(self.login_url, {"username": "alice", "password": PASSWORD})
        self.assertRedirects(response, reverse("tracker:dashboard"))
        self.assertEqual(int(self.client.session[SESSION_KEY]), self.user.pk)

    def test_login_follows_a_safe_next_url(self):
        response = self.client.post(
            self.login_url, {"username": "alice", "password": PASSWORD, "next": "/expenses/"}
        )
        self.assertRedirects(response, "/expenses/")

    def test_login_ignores_an_external_next_url(self):
        response = self.client.post(
            self.login_url,
            {"username": "alice", "password": PASSWORD, "next": "https://evil.example.com/"},
        )
        self.assertRedirects(response, reverse("tracker:dashboard"))

    def test_wrong_password_shows_an_error(self):
        response = self.client.post(self.login_url, {"username": "alice", "password": "nope"})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Please enter a correct username and password")
        self.assertNotIn(SESSION_KEY, self.client.session)

    def test_logged_in_users_skip_the_login_page(self):
        self.client.force_login(self.user)
        self.assertRedirects(
            self.client.get(self.login_url),
            reverse("tracker:dashboard"),
            fetch_redirect_response=False,
        )

    def test_logout_get_only_asks_for_confirmation(self):
        self.client.force_login(self.user)
        response = self.client.get(reverse("accounts:logout"))
        self.assertContains(response, "Log out of SpendWise?")
        self.assertEqual(int(self.client.session[SESSION_KEY]), self.user.pk)

    def test_logout_page_sends_anonymous_users_to_login(self):
        response = self.client.get(reverse("accounts:logout"))
        self.assertRedirects(response, self.login_url, fetch_redirect_response=False)

    def test_logout_ends_the_session(self):
        self.client.force_login(self.user)
        response = self.client.post(reverse("accounts:logout"))
        self.assertRedirects(response, self.login_url)
        self.assertNotIn(SESSION_KEY, self.client.session)
        dashboard = self.client.get(reverse("tracker:dashboard"))
        self.assertEqual(dashboard.status_code, 302)
