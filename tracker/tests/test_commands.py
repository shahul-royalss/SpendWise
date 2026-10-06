from io import StringIO

from django.contrib.auth import get_user_model
from django.core.management import CommandError, call_command
from django.test import TestCase

from tracker.dates import current_month
from tracker.services import AlertLevel, get_monthly_summary


class SeedDemoCommandTests(TestCase):
    def test_creates_data_covering_every_alert_state(self):
        out = StringIO()
        call_command("seed_demo", "--username", "demo", "--password", "Demo-pass-2026", stdout=out)

        user = get_user_model().objects.get(username="demo")
        self.assertTrue(user.check_password("Demo-pass-2026"))
        self.assertEqual(user.categories.count(), 6)

        summary = get_monthly_summary(user, current_month())
        levels = {row.category.name: row.alert_level for row in summary.rows}
        self.assertEqual(levels["Food"], AlertLevel.WARNING)
        self.assertEqual(levels["Transport"], AlertLevel.DANGER)
        self.assertEqual(levels["Entertainment"], AlertLevel.DANGER)
        self.assertEqual(levels["Utilities"], AlertLevel.NORMAL)
        self.assertEqual(levels["Shopping"], AlertLevel.NORMAL)
        self.assertEqual(levels["Health"], AlertLevel.NO_BUDGET)
        self.assertIn('Created demo user "demo"', out.getvalue())

    def test_generates_a_password_when_none_is_given(self):
        out = StringIO()
        call_command("seed_demo", stdout=out)
        self.assertIn("Password: ", out.getvalue())
        self.assertTrue(get_user_model().objects.get(username="demo").has_usable_password())

    def test_refuses_to_touch_an_existing_user(self):
        get_user_model().objects.create_user(username="demo")
        with self.assertRaises(CommandError):
            call_command("seed_demo", stdout=StringIO())
