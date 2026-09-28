import pytest

from soukk_backend.core.email import format_duration, mail_config

LINK = "http://localhost:3000/page?token=abc.def&x=1"

# template -> the name of its link placeholder
TEMPLATES = {"verify_email.html": "verify_url", "reset_password.html": "reset_url"}


def render(template_name: str, **overrides) -> str:
    values = {
        "first_name": "Test",
        "email": "user@example.com",
        TEMPLATES[template_name]: LINK,
        "expires_in": "30 minutes",
        "logo_url": "https://example.com/logo.png",
        **overrides,
    }
    return mail_config.template_engine().get_template(template_name).render(**values)


@pytest.mark.parametrize("template_name", TEMPLATES)
def test_template_fills_every_placeholder(template_name):
    html = render(template_name)

    assert "Hi Test," in html
    assert 'href="http://localhost:3000/page?token=abc.def&amp;x=1"' in html
    assert "30 minutes" in html
    assert "user@example.com" in html
    assert 'src="https://example.com/logo.png"' in html
    assert "{{" not in html


@pytest.mark.parametrize("template_name", TEMPLATES)
def test_template_escapes_user_input(template_name):
    html = render(template_name, first_name="<script>alert(1)</script>")

    assert "<script>" not in html
    assert "&lt;script&gt;" in html


@pytest.mark.parametrize(
    ("minutes", "text"),
    [(1440, "24 hours"), (60, "1 hour"), (30, "30 minutes"), (90, "90 minutes"), (1, "1 minute")],
)
def test_format_duration(minutes, text):
    assert format_duration(minutes) == text
