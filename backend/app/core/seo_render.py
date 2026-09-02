import html
import json
from typing import Any

# Bot'lara (Google/Yandex/GPTBot/ClaudeBot vb. - bkz. frontend/nginx.conf'taki
# $is_bot map'i) servis edilen, JS gerektirmeyen, tamamen sunucu tarafinda
# uretilen HTML sayfalari icin ortak yardimcilar. jinja2 KULLANILMIYOR
# (backend/requirements.txt'te yok, projedeki minimal-bagimlilik prensibiyle
# tutarli kaliniyor - bkz. passlib yerine dogrudan bcrypt) - sablonlar basit
# key/value tablolari oldugu icin duz f-string + html.escape yeterli.

SITE_NAME = "wimyip.net"
SITE_ORIGIN = "https://wimyip.net"


def esc(value: Any) -> str:
    """Her interpolasyon icin ZORUNLU: bot client'a karsi XSS riskini onler."""
    if value is None:
        return ""
    return html.escape(str(value))


def breadcrumb_jsonld(items: list[tuple[str, str]]) -> dict:
    return {
        "@context": "https://schema.org",
        "@type": "BreadcrumbList",
        "itemListElement": [
            {"@type": "ListItem", "position": i + 1, "name": name, "item": url}
            for i, (name, url) in enumerate(items)
        ],
    }


def render_page(
    *,
    title: str,
    description: str,
    canonical: str,
    body_html: str,
    og_type: str = "website",
    jsonld: list[dict] | dict | None = None,
    noindex: bool = False,
) -> str:
    full_title = f"{esc(title)} | {SITE_NAME}"
    robots_tag = '<meta name="robots" content="noindex">' if noindex else ""

    jsonld_html = ""
    if jsonld:
        payload = jsonld if isinstance(jsonld, list) else [jsonld]
        jsonld_html = "".join(
            f'<script type="application/ld+json">{json.dumps(item)}</script>' for item in payload
        )

    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{full_title}</title>
<meta name="description" content="{esc(description)}">
<link rel="canonical" href="{esc(canonical)}">
{robots_tag}
<meta property="og:title" content="{full_title}">
<meta property="og:description" content="{esc(description)}">
<meta property="og:type" content="{esc(og_type)}">
<meta property="og:url" content="{esc(canonical)}">
<meta property="og:site_name" content="{SITE_NAME}">
<meta property="og:image" content="{SITE_ORIGIN}/og-image.svg">
<meta name="twitter:card" content="summary_large_image">
{jsonld_html}
</head>
<body>
{body_html}
</body>
</html>"""
