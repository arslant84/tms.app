"""
Custom SMTP Email Backend with improved SSL/TLS handling for Windows.
This backend adds better error handling and SSL context configuration.
"""
import ssl
from django.core.mail.backends.smtp import EmailBackend as DjangoEmailBackend
import logging

logger = logging.getLogger(__name__)


class CustomEmailBackend(DjangoEmailBackend):
    """
    Custom email backend that handles SSL/TLS issues on Windows.
    Provides better error reporting and fallback mechanisms.
    """

    def open(self):
        """
        Override open() to add custom SSL context handling.
        This helps resolve certificate verification issues on Windows.
        """
        if self.connection:
            return False

        try:
            # Create a custom SSL context with relaxed certificate verification
            # Note: Only use this in development. In production, proper certificates should be used.
            self.ssl_context = ssl.create_default_context()

            # For development only: Disable hostname checking if needed
            # Uncomment the following lines if you're having SSL certificate issues:
            # self.ssl_context.check_hostname = False
            # self.ssl_context.verify_mode = ssl.CERT_NONE

            connection_params = {
                'timeout': self.timeout,
                'local_hostname': self.ssl_certfile or None,
            }

            self.connection = self.connection_class(
                self.host,
                self.port,
                **connection_params
            )

            # Set debug level for troubleshooting
            self.connection.set_debuglevel(0)  # Set to 1 for verbose SMTP logs

            # Server greeting
            self.connection.ehlo()

            # TLS/SSL setup
            if self.use_tls:
                self.connection.starttls(context=self.ssl_context)
                self.connection.ehlo()

            if self.username and self.password:
                self.connection.login(self.username, self.password)

            return True

        except Exception as e:
            logger.error(f"Failed to connect to SMTP server: {e}", exc_info=True)
            if not self.fail_silently:
                raise
            return False
