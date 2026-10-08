"""SMTP delivery for account recovery codes."""
import os
import smtplib
import ssl
from email.message import EmailMessage


class EmailDeliveryError(RuntimeError):
    pass


class RecoveryEmailer:
    def __init__(self, host=None, port=587, username=None, password=None,
                 sender=None, use_ssl=False):
        self.host = host
        self.port = port
        self.username = username
        self.password = password
        self.sender = sender
        self.use_ssl = use_ssl

    @classmethod
    def from_environment(cls):
        return cls(
            host=os.environ.get("TRADEAPP_SMTP_HOST"),
            port=int(os.environ.get("TRADEAPP_SMTP_PORT", "587")),
            username=os.environ.get("TRADEAPP_SMTP_USERNAME"),
            password=os.environ.get("TRADEAPP_SMTP_PASSWORD"),
            sender=os.environ.get("TRADEAPP_SMTP_FROM"),
            use_ssl=os.environ.get("TRADEAPP_SMTP_SSL", "").lower() in ("1", "true", "yes"),
        )

    def send_recovery_code(self, recipient, recovery_code):
        if not self.host or not self.sender:
            return False
        if bool(self.username) != bool(self.password):
            raise EmailDeliveryError("SMTP username and password must both be configured")

        message = EmailMessage()
        message["Subject"] = "Your TradeApp recovery code"
        message["From"] = self.sender
        message["To"] = recipient
        message.set_content(
            "Use this recovery code to reset your TradeApp password. It can also "
            "restore access to your Solana wallet. Keep it private and do not "
            "forward this email. The code is replaced after a successful "
            "password reset.\n\n"
            f"{recovery_code}\n\n"
            "If you did not request this code, you can ignore this message."
        )

        try:
            context = ssl.create_default_context()
            if self.use_ssl:
                with smtplib.SMTP_SSL(
                    self.host, self.port, timeout=15, context=context
                ) as smtp:
                    self._send(smtp, message)
            else:
                with smtplib.SMTP(self.host, self.port, timeout=15) as smtp:
                    smtp.ehlo()
                    smtp.starttls(context=context)
                    smtp.ehlo()
                    self._send(smtp, message)
        except (OSError, smtplib.SMTPException) as error:
            raise EmailDeliveryError("SMTP delivery failed") from error
        return True

    def _send(self, smtp, message):
        if self.username:
            smtp.login(self.username, self.password)
        smtp.send_message(message)