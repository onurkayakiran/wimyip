from fastapi import APIRouter, HTTPException
from fastapi.responses import HTMLResponse

from app.api.routes.asns import get_asn, get_asn_history, get_asn_peeringdb, get_asn_peers, get_asn_prefixes
from app.api.routes.domains import get_domain, get_domain_dns_history
from app.api.routes.lookup import lookup_ip
from app.api.routes.nameservers import get_domains_by_nameserver, get_nameserver_history
from app.api.routes.prefixes import get_prefix, get_prefix_history
from app.api.routes.stats import stats as get_stats_counts
from app.core.seo_render import SITE_ORIGIN, breadcrumb_jsonld, esc, render_page

# Bu router SADECE bot User-Agent'lari icin (bkz. frontend/nginx.conf'taki
# $is_bot map'i + `rewrite ... last` ile buradaki /api/seo/* yollarina ic
# yonlendirme) - normal tarayicilar hep normal SPA'yi goruyor. Yeni Mongo
# sorgusu YOK: her renderer, JSON API'nin ayni verisini urettigi mevcut
# route fonksiyonlarini dogrudan cagirir (asns.py/domains.py/prefixes.py/
# lookup.py/nameservers.py/stats.py) - frontend'in api.js uzerinden ayni
# endpoint'leri cagirdigi deseninin backend-ici esdegeri.

router = APIRouter()

_HOME_CRUMB = ("Home", f"{SITE_ORIGIN}/")


def _breadcrumb_html(*crumbs: tuple[str, str | None]) -> str:
    parts = [f'<a href="{esc(href)}">{esc(name)}</a>' if href else esc(name) for name, href in crumbs]
    return " / ".join(parts)


def _rows(items: list[dict], row_fn, colspan: int, empty_text: str = "No data.") -> str:
    if not items:
        return f'<tr><td colspan="{colspan}">{esc(empty_text)}</td></tr>'
    return "".join(row_fn(i) for i in items)


def _not_found_page(entity_label: str, canonical: str) -> HTMLResponse:
    html_doc = render_page(
        title=f"{entity_label} not found",
        description=f"{entity_label} was not found in the archive.",
        canonical=canonical,
        body_html=f"<h1>{esc(entity_label)} not found</h1><p>{_breadcrumb_html(_HOME_CRUMB, (entity_label, None))}</p>",
        noindex=True,
    )
    return HTMLResponse(html_doc, status_code=404)


@router.get("/seo/home")
async def seo_home():
    counts = await get_stats_counts()
    title = "IP / ASN / Domain / WHOIS History Archive"
    description = (
        "Free, searchable archive of IP addresses, ASNs, IP prefixes, domains and nameservers "
        "with WHOIS ownership history, BGP announcement history, PeeringDB profiles and DNS record history."
    )
    body = f"""
    <h1>wimyip.net — {esc(title)}</h1>
    <p>{esc(description)}</p>
    <ul>
      <li>{counts['prefixes']:,} IP prefixes</li>
      <li>{counts['asns']:,} ASNs</li>
      <li>{counts['domains']:,} domains</li>
    </ul>
    <p>Example pages:
      <a href="/ip/8.8.8.8">8.8.8.8</a> ·
      <a href="/asn/15169">AS15169</a> ·
      <a href="/domain/google.com">google.com</a>
    </p>
    """
    jsonld = {
        "@context": "https://schema.org",
        "@type": "WebSite",
        "name": "wimyip.net",
        "url": f"{SITE_ORIGIN}/",
        "potentialAction": {
            "@type": "SearchAction",
            "target": f"{SITE_ORIGIN}/search?q={{search_term_string}}",
            "query-input": "required name=search_term_string",
        },
    }
    return HTMLResponse(
        render_page(title=title, description=description, canonical=f"{SITE_ORIGIN}/", body_html=body, jsonld=jsonld)
    )


@router.get("/seo/asn/{asn}")
async def seo_asn(asn: int):
    canonical = f"{SITE_ORIGIN}/asn/{asn}"
    try:
        info = await get_asn(asn)
    except HTTPException:
        return _not_found_page(f"AS{asn}", canonical)

    history_data = await get_asn_history(asn)
    history = history_data["history"]
    prefixes_data = await get_asn_prefixes(asn, limit=100, offset=0)
    peers_data = await get_asn_peers(asn, limit=100, offset=0)
    try:
        peeringdb = await get_asn_peeringdb(asn)
    except HTTPException:
        peeringdb = None

    org_name = (peeringdb or {}).get("org_name") or (history[0].get("org_name") if history else None)
    title = f"AS{asn}" + (f" — {org_name}" if org_name else "")
    description = (
        f"WHOIS ownership history, BGP-announced prefixes and peering data for Autonomous System AS{asn}"
        + (f" ({org_name})" if org_name else "")
        + "."
    )

    hist_rows = _rows(
        history,
        lambda h: f"<tr><td>{esc(h.get('org_name'))}</td><td>{esc(h.get('handle'))}</td>"
        f"<td>{esc(h.get('first_seen'))}</td><td>{esc(h.get('last_seen'))}</td></tr>",
        colspan=4,
    )
    prefix_rows = _rows(
        prefixes_data["items"],
        lambda p: f'<tr><td><a href="/prefix/{esc(p["prefix"])}">{esc(p["prefix"])}</a></td>'
        f"<td>{esc(p.get('first_seen'))}</td><td>{esc(p.get('last_seen'))}</td></tr>",
        colspan=3,
    )
    peer_rows = _rows(
        peers_data["items"],
        lambda pe: f'<tr><td><a href="/asn/{esc(pe["neighbour_asn"])}">AS{esc(pe["neighbour_asn"])}</a></td>'
        f"<td>{esc(pe.get('direction'))}</td><td>{esc(pe.get('power'))}</td></tr>",
        colspan=3,
    )

    body = f"""
    <p>{_breadcrumb_html(_HOME_CRUMB, (f"AS{asn}", None))}</p>
    <h1>{esc(title)}</h1>
    <table><tbody>
      <tr><th>RIR</th><td>{esc(info.get('rir'))}</td></tr>
      <tr><th>Country</th><td>{esc(info.get('country'))}</td></tr>
      <tr><th>Allocation date</th><td>{esc(info.get('alloc_date'))}</td></tr>
    </tbody></table>
    <h2>Ownership history</h2>
    <table><thead><tr><th>Org</th><th>Handle</th><th>First seen</th><th>Last seen</th></tr></thead>
    <tbody>{hist_rows}</tbody></table>
    <h2>Announced prefixes</h2>
    <table><thead><tr><th>Prefix</th><th>First seen</th><th>Last seen</th></tr></thead>
    <tbody>{prefix_rows}</tbody></table>
    <h2>BGP peers</h2>
    <table><thead><tr><th>Neighbour ASN</th><th>Direction</th><th>Power</th></tr></thead>
    <tbody>{peer_rows}</tbody></table>
    """

    jsonld = [
        breadcrumb_jsonld([_HOME_CRUMB, (f"AS{asn}", canonical)]),
        {"@context": "https://schema.org", "@type": "Dataset", "name": title, "description": description, "url": canonical},
    ]
    return HTMLResponse(render_page(title=title, description=description, canonical=canonical, body_html=body, jsonld=jsonld))


@router.get("/seo/prefix/{cidr:path}")
async def seo_prefix(cidr: str):
    canonical = f"{SITE_ORIGIN}/prefix/{cidr}"
    try:
        info = await get_prefix(cidr)
    except HTTPException:
        return _not_found_page(cidr, canonical)

    history_data = await get_prefix_history(cidr)
    history = history_data["history"]

    title = info.get("cidr", cidr)
    description = f"RIR allocation and WHOIS ownership history for the IP prefix {title}."

    hist_rows = _rows(
        history,
        lambda h: f"<tr><td>{esc(h.get('org_name'))}</td><td>{esc(h.get('handle'))}</td>"
        f"<td>{esc(h.get('first_seen'))}</td><td>{esc(h.get('last_seen'))}</td></tr>",
        colspan=4,
    )

    body = f"""
    <p>{_breadcrumb_html(_HOME_CRUMB, (title, None))}</p>
    <h1>{esc(title)}</h1>
    <table><tbody>
      <tr><th>RIR</th><td>{esc(info.get('rir'))}</td></tr>
      <tr><th>Country</th><td>{esc(info.get('country'))}</td></tr>
      <tr><th>Status</th><td>{esc(info.get('status'))}</td></tr>
      <tr><th>Allocation date</th><td>{esc(info.get('alloc_date'))}</td></tr>
    </tbody></table>
    <h2>Ownership history</h2>
    <table><thead><tr><th>Org</th><th>Handle</th><th>First seen</th><th>Last seen</th></tr></thead>
    <tbody>{hist_rows}</tbody></table>
    """

    jsonld = [
        breadcrumb_jsonld([_HOME_CRUMB, (title, canonical)]),
        {"@context": "https://schema.org", "@type": "Dataset", "name": title, "description": description, "url": canonical},
    ]
    return HTMLResponse(render_page(title=title, description=description, canonical=canonical, body_html=body, jsonld=jsonld))


@router.get("/seo/domain/{domain}")
async def seo_domain(domain: str):
    canonical = f"{SITE_ORIGIN}/domain/{domain}"
    try:
        info = await get_domain(domain)
    except HTTPException:
        return _not_found_page(domain, canonical)

    history = await get_domain_dns_history(domain)

    title = domain
    description = f"DNS record history (A/AAAA, NS, MX, TXT) and archive metadata for the domain {domain}."

    ip_rows = _rows(
        history["ip_history"],
        lambda r: f'<tr><td><a href="/ip/{esc(r["ip"])}">{esc(r["ip"])}</a></td>'
        f"<td>{esc(r.get('first_seen'))}</td><td>{esc(r.get('last_seen'))}</td></tr>",
        colspan=3,
    )
    ns_rows = _rows(
        history["ns_history"],
        lambda r: f'<tr><td><a href="/nameserver/{esc(r["nameserver"])}">{esc(r["nameserver"])}</a></td>'
        f"<td>{esc(r.get('first_seen'))}</td><td>{esc(r.get('last_seen'))}</td></tr>",
        colspan=3,
    )

    body = f"""
    <p>{_breadcrumb_html(_HOME_CRUMB, (domain, None))}</p>
    <h1>{esc(domain)}</h1>
    <table><tbody>
      <tr><th>Sources</th><td>{esc(', '.join(info.get('sources') or []))}</td></tr>
      <tr><th>First seen</th><td>{esc(info.get('first_seen'))}</td></tr>
      <tr><th>Last seen</th><td>{esc(info.get('last_seen'))}</td></tr>
    </tbody></table>
    <h2>IP history (A/AAAA)</h2>
    <table><thead><tr><th>IP</th><th>First seen</th><th>Last seen</th></tr></thead>
    <tbody>{ip_rows}</tbody></table>
    <h2>Nameserver history (NS)</h2>
    <table><thead><tr><th>Nameserver</th><th>First seen</th><th>Last seen</th></tr></thead>
    <tbody>{ns_rows}</tbody></table>
    """

    jsonld = [
        breadcrumb_jsonld([_HOME_CRUMB, (domain, canonical)]),
        {"@context": "https://schema.org", "@type": "Dataset", "name": title, "description": description, "url": canonical},
    ]
    return HTMLResponse(render_page(title=title, description=description, canonical=canonical, body_html=body, jsonld=jsonld))


@router.get("/seo/ip/{ip}")
async def seo_ip(ip: str):
    canonical = f"{SITE_ORIGIN}/ip/{ip}"
    try:
        data = await lookup_ip(ip)
    except HTTPException:
        return _not_found_page(ip, canonical)

    title = ip
    description = f"IP address lookup for {ip}: announcing ASN, BGP history, PTR record and containing IP prefix."

    bgp_rows = _rows(
        data["bgp"],
        lambda r: f'<tr><td><a href="/asn/{esc(r["asn"])}">AS{esc(r["asn"])}</a></td>'
        f"<td>{esc(r.get('first_seen'))}</td><td>{esc(r.get('last_seen'))}</td></tr>",
        colspan=3,
    )
    ptr_rows = _rows(
        data["ptr"],
        lambda r: f'<tr><td><a href="/domain/{esc(r["ptr_hostname"])}">{esc(r["ptr_hostname"])}</a></td>'
        f"<td>{esc(r.get('first_seen'))}</td></tr>",
        colspan=2,
    )

    body = f"""
    <p>{_breadcrumb_html(_HOME_CRUMB, (ip, None))}</p>
    <h1>{esc(ip)}</h1>
    <table><tbody>
      <tr><th>Prefix</th><td><a href="/prefix/{esc(data['prefix']['cidr'])}">{esc(data['prefix']['cidr'])}</a></td></tr>
      <tr><th>RIR</th><td>{esc(data['prefix'].get('rir'))}</td></tr>
      <tr><th>Country</th><td>{esc(data['prefix'].get('country'))}</td></tr>
    </tbody></table>
    <h2>BGP announcement history</h2>
    <table><thead><tr><th>ASN</th><th>First seen</th><th>Last seen</th></tr></thead>
    <tbody>{bgp_rows}</tbody></table>
    <h2>PTR record</h2>
    <table><thead><tr><th>Hostname</th><th>First seen</th></tr></thead>
    <tbody>{ptr_rows}</tbody></table>
    """

    jsonld = [
        breadcrumb_jsonld([_HOME_CRUMB, (ip, canonical)]),
        {"@context": "https://schema.org", "@type": "Dataset", "name": title, "description": description, "url": canonical},
    ]
    return HTMLResponse(render_page(title=title, description=description, canonical=canonical, body_html=body, jsonld=jsonld))


@router.get("/seo/nameserver/{nameserver}")
async def seo_nameserver(nameserver: str):
    canonical = f"{SITE_ORIGIN}/nameserver/{nameserver}"
    history = await get_nameserver_history(nameserver)
    domains = await get_domains_by_nameserver(nameserver)

    if not history["ip_history"] and not domains["items"]:
        return _not_found_page(nameserver, canonical)

    title = nameserver
    description = f"Nameserver history for {nameserver}: IP address history and the domains it serves."

    ip_rows = _rows(
        history["ip_history"],
        lambda r: f'<tr><td><a href="/ip/{esc(r["ip"])}">{esc(r["ip"])}</a></td>'
        f"<td>{esc(r.get('first_seen'))}</td><td>{esc(r.get('last_seen'))}</td></tr>",
        colspan=3,
    )
    domain_rows = _rows(
        domains["items"],
        lambda r: f'<tr><td><a href="/domain/{esc(r["domain"])}">{esc(r["domain"])}</a></td>'
        f"<td>{esc(r.get('first_seen'))}</td><td>{esc(r.get('last_seen'))}</td></tr>",
        colspan=3,
    )

    body = f"""
    <p>{_breadcrumb_html(_HOME_CRUMB, (nameserver, None))}</p>
    <h1>{esc(nameserver)}</h1>
    <h2>IP history</h2>
    <table><thead><tr><th>IP</th><th>First seen</th><th>Last seen</th></tr></thead>
    <tbody>{ip_rows}</tbody></table>
    <h2>Domains it serves</h2>
    <table><thead><tr><th>Domain</th><th>First seen</th><th>Last seen</th></tr></thead>
    <tbody>{domain_rows}</tbody></table>
    """

    jsonld = [
        breadcrumb_jsonld([_HOME_CRUMB, (nameserver, canonical)]),
        {"@context": "https://schema.org", "@type": "Dataset", "name": title, "description": description, "url": canonical},
    ]
    return HTMLResponse(render_page(title=title, description=description, canonical=canonical, body_html=body, jsonld=jsonld))
