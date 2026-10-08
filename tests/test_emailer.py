import unittest
from email.message import EmailMessage
from unittest.mock import MagicMock, patch

from tradeapp.emailer import EmailDeliveryError, RecoveryEmailer


class RecoveryEmailerTest(unittest.TestCase):
    def test_unconfigured_emailer_reports_not_sent(self):
        emailer = RecoveryEmailer()
        self.assertFalse(emailer.send_recovery_code("person@example.com", "secret"))

    @patch("tradeapp.emailer.smtplib.SMTP")
    def test_sends_code_over_starttls(self, smtp_class):
        smtp = MagicMock()
        smtp_class.return_value.__enter__.return_value = smtp
        emailer = RecoveryEmailer(
            host="smtp.example.com", username="mailer", password="secret",
            sender="accounts@example.com",
        )

        self.assertTrue(emailer.send_recovery_code("person@example.com", "recovery-secret"))

        smtp_class.assert_called_once_with("smtp.example.com", 587, timeout=15)
        smtp.starttls.assert_called_once()
        smtp.login.assert_called_once_with("mailer", "secret")
        message = smtp.send_message.call_args.args[0]
        self.assertIsInstance(message, EmailMessage)
        self.assertEqual(message["To"], "person@example.com")
        self.assertIn("recovery-secret", message.get_content())

    @patch("tradeapp.emailer.smtplib.SMTP")
    def test_smtp_failure_is_reported(self, smtp_class):
        smtp_class.return_value.__enter__.side_effect = OSError("offline")
        emailer = RecoveryEmailer(host="smtp.example.com", sender="accounts@example.com")

        with self.assertRaises(EmailDeliveryError):
            emailer.send_recovery_code("person@example.com", "recovery-secret")


if __name__ == "__main__":
    unittest.main()