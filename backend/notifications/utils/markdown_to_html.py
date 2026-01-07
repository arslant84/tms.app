"""
Markdown to HTML Converter for Email Templates

Converts markdown-style text to HTML with inline CSS styling
matching the TMS design system.

Supported Markdown Syntax:
- **bold** → <strong>bold</strong>
- [link text](url) → <a href="url">link text</a>
- *   bullet item → <li>bullet item</li>
- Line breaks → <br> or <p> tags
"""

import re


class MarkdownToHTMLConverter:
    """
    Converts markdown-style text to HTML with TMS design system styling.

    Design System Colors:
    - Primary: #0d9488
    - Text Primary: #1f2937
    - Text Secondary: #374151
    - Text Muted: #6b7280
    """

    # Design system colors for inline styles
    COLORS = {
        'primary': '#0d9488',
        'primary_hover': '#0f766e',
        'text_primary': '#1f2937',
        'text_secondary': '#374151',
        'text_muted': '#6b7280',
        'gray_200': '#e5e7eb',
    }

    @classmethod
    def convert(cls, markdown_text):
        """
        Convert markdown text to HTML with inline styling.

        Args:
            markdown_text (str): Markdown-formatted text

        Returns:
            str: HTML with inline CSS
        """
        if not markdown_text:
            return ''

        html = markdown_text

        # 1. Convert **bold** text
        html = cls._convert_bold(html)

        # 2. Convert [link](url) patterns
        html = cls._convert_links(html)

        # 3. Convert bullet points (*   item)
        html = cls._convert_bullets(html)

        # 4. Convert line breaks and paragraphs
        html = cls._convert_paragraphs(html)

        return html

    @classmethod
    def _convert_bold(cls, text):
        """Convert **bold** to <strong> tags with styling."""
        pattern = r'\*\*(.*?)\*\*'
        replacement = r'<strong style="font-weight: 600; color: {color};">\1</strong>'.format(
            color=cls.COLORS['text_primary']
        )
        return re.sub(pattern, replacement, text)

    @classmethod
    def _convert_links(cls, text):
        """Convert [text](url) to <a> tags with styling."""
        pattern = r'\[([^\]]+)\]\(([^\)]+)\)'

        def replace_link(match):
            link_text = match.group(1)
            url = match.group(2)

            # Add base URL if it's a relative path
            if url.startswith('/'):
                # Get FRONTEND_URL from Django settings
                from django.conf import settings
                base_url = getattr(settings, 'FRONTEND_URL', 'http://localhost:4200')
                full_url = f"{base_url.rstrip('/')}{url}"
            else:
                full_url = url

            return (
                f'<a href="{full_url}" '
                f'style="color: {cls.COLORS["primary"]}; text-decoration: none; font-weight: 600;" '
                f'target="_blank">'
                f'{link_text}'
                f'</a>'
            )

        return re.sub(pattern, replace_link, text)

    @classmethod
    def _convert_bullets(cls, text):
        """Convert *   item to <li> tags within <ul>."""
        # Find all bullet point lines
        lines = text.split('\n')
        result_lines = []
        in_list = False

        for line in lines:
            stripped = line.strip()

            # Check if line starts with *   (bullet point)
            if stripped.startswith('*   ') or stripped.startswith('* '):
                # Extract the bullet content
                bullet_content = stripped.lstrip('*').strip()

                if not in_list:
                    # Start a new list
                    result_lines.append(
                        f'<ul style="margin: 12px 0; padding-left: 24px; color: {cls.COLORS["text_secondary"]};">'
                    )
                    in_list = True

                # Add list item
                result_lines.append(
                    f'<li style="margin-bottom: 8px; line-height: 1.5;">{bullet_content}</li>'
                )
            else:
                # Not a bullet point
                if in_list:
                    # Close the list
                    result_lines.append('</ul>')
                    in_list = False

                # Add the line as-is
                if stripped:  # Only add non-empty lines
                    result_lines.append(line)

        # Close list if still open
        if in_list:
            result_lines.append('</ul>')

        return '\n'.join(result_lines)

    @classmethod
    def _convert_paragraphs(cls, text):
        """Convert double line breaks to paragraphs."""
        # Split by double newlines (paragraph breaks)
        paragraphs = re.split(r'\n\s*\n', text)

        result = []
        for para in paragraphs:
            para = para.strip()
            if not para:
                continue

            # Check if paragraph is already wrapped in HTML tags
            if para.startswith('<') and para.endswith('>'):
                # Already HTML (like <ul> or <strong>)
                result.append(para)
            elif para.startswith('<ul'):
                # Bullet list - don't wrap
                result.append(para)
            else:
                # Wrap in paragraph tag
                result.append(
                    f'<p style="margin: 0 0 16px 0; color: {cls.COLORS["text_secondary"]}; font-size: 15px; line-height: 1.6;">'
                    f'{para}'
                    f'</p>'
                )

        return '\n\n'.join(result)

    @classmethod
    def convert_greeting(cls, text, user_name=None):
        """
        Handle greeting line specially (e.g., "Hi {{userName}},").

        Args:
            text (str): Text that may contain greeting
            user_name (str, optional): User's name to insert

        Returns:
            str: HTML with greeting styled
        """
        if user_name:
            # Replace greeting placeholder
            text = text.replace('{{userName}}', user_name)
            text = text.replace('{{requestorName}}', user_name)

        # Style greeting line (Hi Name,)
        greeting_pattern = r'^(Hi [^,]+,)\s*'
        if re.match(greeting_pattern, text):
            text = re.sub(
                greeting_pattern,
                r'<p style="margin: 0 0 20px 0; color: {color}; font-size: 15px; font-weight: 500;">\1</p>\n\n'.format(
                    color=cls.COLORS['text_primary']
                ),
                text
            )

        return text


# Convenience functions

def markdown_to_html(text):
    """
    Convert markdown text to HTML.

    Convenience function for quick conversion.

    Args:
        text (str): Markdown-formatted text

    Returns:
        str: HTML with inline CSS
    """
    return MarkdownToHTMLConverter.convert(text)


def convert_template_body(body_text, context=None):
    """
    Convert template body with variable substitution and markdown conversion.

    Args:
        body_text (str): Template body with markdown and {{variables}}
        context (dict, optional): Context dictionary for variable substitution

    Returns:
        str: HTML-formatted body
    """
    # First, substitute variables if context provided
    if context:
        for key, value in context.items():
            body_text = body_text.replace(f'{{{{{key}}}}}', str(value))

    # Then convert markdown to HTML
    html_body = markdown_to_html(body_text)

    return html_body


# Example usage:
if __name__ == '__main__':
    # Test markdown conversion
    test_markdown = """
Hi John Doe,

This email confirms that your **Visa Request** request (ID: **#VISA-2026-001**) has been successfully submitted and is now pending review.

**Next Steps:**
*   The request has been assigned to **Jane Smith** for approval.
*   You will receive further notifications as your request progresses through the workflow.

You can track the progress of your request by clicking the link below.

[Track Progress](/visa/123)

Thank you,
The TMS Team
"""

    print("=" * 80)
    print("MARKDOWN TO HTML CONVERSION TEST")
    print("=" * 80)
    print("\nOriginal Markdown:")
    print(test_markdown)
    print("\n" + "=" * 80)
    print("\nConverted HTML:")
    print(markdown_to_html(test_markdown))
    print("=" * 80)
