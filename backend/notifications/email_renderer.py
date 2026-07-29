"""
Email Rendering Utilities for TMS Notification System

This module provides utilities for rendering HTML email templates
with markdown conversion and design system styling.
"""

import os

from django.conf import settings
from django.template.loader import render_to_string


class EmailTemplateRenderer:
    """
    Renders HTML email templates with TMS branding and design system colors.

    Design System Colors (from STYLING_UNIFICATION_ROADMAP.md):
    - Primary: #0d9488
    - Primary Dark: #0f766e
    - Primary Light: #5eead4
    - Primary Lightest: #ccfbf1
    - Grays: #f9fafb (50), #e5e7eb (200), #6b7280 (500), #1f2937 (800)
    - Success: #10b981
    - Error: #ef4444
    - Warning: #f59e0b
    - Info: #3b82f6
    """

    # Design system color palette
    COLORS = {
        "primary": "#0d9488",
        "primary_dark": "#0f766e",
        "primary_light": "#5eead4",
        "primary_lightest": "#ccfbf1",
        "gray_50": "#f9fafb",
        "gray_100": "#f3f4f6",
        "gray_200": "#e5e7eb",
        "gray_300": "#d1d5db",
        "gray_400": "#9ca3af",
        "gray_500": "#6b7280",
        "gray_600": "#4b5563",
        "gray_700": "#374151",
        "gray_800": "#1f2937",
        "gray_900": "#111827",
        "success": "#10b981",
        "error": "#ef4444",
        "warning": "#f59e0b",
        "info": "#3b82f6",
        "white": "#ffffff",
        "black": "#000000",
    }

    @classmethod
    def _make_absolute_url(cls, url):
        """
        Convert relative URL to absolute URL using FRONTEND_URL from settings.

        Args:
            url (str): Relative or absolute URL

        Returns:
            str: Absolute URL
        """
        if not url:
            return url

        # If already absolute, return as-is
        if url.startswith("http://") or url.startswith("https://"):
            return url

        # If relative, prepend FRONTEND_URL
        if url.startswith("/"):
            frontend_url = getattr(settings, "FRONTEND_URL", "http://localhost:4200")
            return f"{frontend_url.rstrip('/')}{url}"

        return url

    @classmethod
    def render_email(
        cls, subject, content, user_name=None, action_url=None, action_text=None
    ):
        """
        Render an HTML email using the base template.

        Args:
            subject (str): Email subject line
            content (str): Email body content (can be HTML or markdown)
            user_name (str, optional): Recipient's name for greeting
            action_url (str, optional): URL for call-to-action button (will be converted to absolute URL)
            action_text (str, optional): Text for CTA button (default: "View Details")

        Returns:
            str: Rendered HTML email
        """

        # Convert action_url to absolute URL
        absolute_action_url = cls._make_absolute_url(action_url)

        context = {
            "subject": subject,
            "content": content,
            "user_name": user_name,
            "action_url": absolute_action_url,
            "action_text": action_text or "View Details",
            "colors": cls.COLORS,
        }

        try:
            # Try to use Django's template loader
            html = render_to_string("email/base.html", context)
            return html
        except Exception:
            # Fallback: Read template file directly
            template_path = os.path.join(
                settings.BASE_DIR, "notifications", "templates", "email", "base.html"
            )

            if os.path.exists(template_path):
                with open(template_path, "r", encoding="utf-8") as f:
                    template_content = f.read()

                # Simple variable substitution
                html = template_content
                html = html.replace("{{ subject }}", subject)
                html = html.replace("{{ content|safe }}", content)

                if user_name:
                    html = html.replace("{% if user_name %}", "")
                    html = html.replace("{% endif %}", "")
                    html = html.replace("{{ user_name }}", user_name)
                else:
                    # Remove greeting section
                    import re

                    html = re.sub(
                        r"{% if user_name %}.*?{% endif %}", "", html, flags=re.DOTALL
                    )

                if absolute_action_url:
                    html = html.replace("{% if action_url %}", "")
                    html = html.replace("{{ action_url }}", absolute_action_url)
                    html = html.replace(
                        '{{ action_text|default:"View Details" }}',
                        action_text or "View Details",
                    )
                else:
                    # Remove button section
                    import re

                    html = re.sub(
                        r"{% if action_url %}.*?{% endif %}", "", html, flags=re.DOTALL
                    )

                return html
            else:
                raise Exception(f"Email template not found at: {template_path}")
