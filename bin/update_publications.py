#!/usr/bin/env python3
"""Regenerate _bibliography/papers.bib from NASA ADS.

Queries ADS for all publications matching the ORCID below, exports them as
BibTeX, expands AAS journal macros (\\mnras, \\apj, ...) so jekyll-scholar
renders proper journal names, and tags entries with ``lead = {true}`` when
Biprateep Dey is first or second author (matching the CV's
"Lead/Significant Contributing Author" convention).

Requires the environment variable ADS_API_TOKEN (get one for free at
https://ui.adsabs.harvard.edu/user/settings/token).

Usage:  python bin/update_publications.py
"""

import os
import re
import sys
import urllib.parse
import urllib.request
import json

ORCID = "0000-0002-5665-7912"
AUTHOR_REGEX = re.compile(r"^dey,\s*b", re.IGNORECASE)  # matches "Dey, B." / "Dey, Biprateep"
LEAD_MAX_POSITION = 2  # 1st or 2nd author => lead/significant contributing
OUTPUT = os.path.join(os.path.dirname(__file__), "..", "_bibliography", "papers.bib")

API = "https://api.adsabs.harvard.edu/v1"

# Bibcodes to always treat as lead/significant regardless of author position:
FORCE_LEAD: set[str] = set()
# Bibcodes to exclude entirely (e.g. duplicates, errata you don't want listed):
EXCLUDE: set[str] = set()

# AAS/ADS LaTeX journal macros -> full names
JOURNAL_MACROS = {
    "\\aj": "The Astronomical Journal",
    "\\apj": "The Astrophysical Journal",
    "\\apjl": "The Astrophysical Journal Letters",
    "\\apjs": "The Astrophysical Journal Supplement Series",
    "\\mnras": "Monthly Notices of the Royal Astronomical Society",
    "\\aap": "Astronomy & Astrophysics",
    "\\aaps": "Astronomy & Astrophysics Supplement",
    "\\jcap": "Journal of Cosmology and Astroparticle Physics",
    "\\prd": "Physical Review D",
    "\\prl": "Physical Review Letters",
    "\\pasp": "Publications of the Astronomical Society of the Pacific",
    "\\pasj": "Publications of the Astronomical Society of Japan",
    "\\nat": "Nature",
    "\\natas": "Nature Astronomy",
    "\\araa": "Annual Review of Astronomy and Astrophysics",
    "\\physrep": "Physics Reports",
    "\\rmxaa": "Revista Mexicana de Astronomia y Astrofisica",
    "\\aapr": "Astronomy & Astrophysics Review",
}


def api_request(url, data=None, token=None):
    req = urllib.request.Request(url)
    req.add_header("Authorization", f"Bearer {token}")
    if data is not None:
        req.add_header("Content-Type", "application/json")
        req.data = json.dumps(data).encode()
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read().decode())


def fetch_papers(token):
    """Return list of {bibcode, author[]} for all ORCID matches."""
    docs, start, rows = [], 0, 200
    while True:
        params = urllib.parse.urlencode(
            {
                "q": f"orcid:{ORCID}",
                "fl": "bibcode,author",
                "rows": rows,
                "start": start,
                "sort": "date desc, bibcode desc",
            }
        )
        result = api_request(f"{API}/search/query?{params}", token=token)
        response = result["response"]
        docs.extend(response["docs"])
        if len(docs) >= response["numFound"]:
            return docs
        start += rows


def export_bibtex(bibcodes, token):
    result = api_request(f"{API}/export/bibtex", data={"bibcode": bibcodes}, token=token)
    return result["export"]


def is_lead(doc):
    if doc["bibcode"] in FORCE_LEAD:
        return True
    for i, name in enumerate(doc.get("author", [])[:LEAD_MAX_POSITION]):
        if AUTHOR_REGEX.match(name):
            return True
    return False


def expand_macros(bibtex):
    for macro, name in sorted(JOURNAL_MACROS.items(), key=lambda kv: -len(kv[0])):
        bibtex = bibtex.replace("{" + macro + "}", "{" + name + "}")
    return bibtex


def tag_leads(bibtex, lead_bibcodes):
    """Insert `lead = {true}` into entries whose key is a lead bibcode."""
    out = []
    for chunk in re.split(r"(?=^@)", bibtex, flags=re.MULTILINE):
        m = re.match(r"@\w+\{([^,\s]+),", chunk)
        if m and m.group(1) in lead_bibcodes:
            chunk = re.sub(r"(@\w+\{[^,\s]+,\n)", r"\1         lead = {true},\n", chunk, count=1)
        out.append(chunk)
    return "".join(out)


def main():
    token = os.environ.get("ADS_API_TOKEN")
    if not token:
        sys.exit("Error: set the ADS_API_TOKEN environment variable.")

    docs = [d for d in fetch_papers(token) if d["bibcode"] not in EXCLUDE]
    if not docs:
        sys.exit("Error: ADS returned no publications; refusing to overwrite papers.bib.")

    lead_bibcodes = {d["bibcode"] for d in docs if is_lead(d)}
    print(f"Found {len(docs)} publications ({len(lead_bibcodes)} lead/significant).")

    bibtex = export_bibtex([d["bibcode"] for d in docs], token)
    bibtex = expand_macros(bibtex)
    bibtex = tag_leads(bibtex, lead_bibcodes)

    with open(OUTPUT, "w") as f:
        f.write(bibtex)
    print(f"Wrote {OUTPUT}")


if __name__ == "__main__":
    main()
