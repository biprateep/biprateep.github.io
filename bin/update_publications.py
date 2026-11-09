# ---
# jupyter:
#   jupytext:
#     formats: ipynb,py:percent
#     text_representation:
#       extension: .py
#       format_name: percent
#       format_version: '1.3'
#       jupytext_version: 1.16.0
#   kernelspec:
#     display_name: Python 3 (ipykernel)
#     language: python
#     name: python3
# ---

# %% [markdown]
# # Regenerate `_bibliography/papers.bib` with Hybrid Preservation
#
# Queries NASA ADS for all publications matching Biprateep Dey's ORCID (or
# processes the existing `_bibliography/papers.bib` when `--offline` is
# passed), expands AAS journal macros, tags lead/significant author entries,
# sanitizes mangled LaTeX titles, overlays interactive `al-folio` metadata,
# and merges manual preprints from `_bibliography/papers_custom.bib`.

# %% Imports
from collections.abc import Mapping, Sequence
import json
import os
import pathlib
import re
import sys
from typing import Any
import urllib.parse
import urllib.request

# %% [markdown]
# ## Configuration
#
# Define ORCID, file paths, journal macro expansions, venue badge mappings,
# declarative metadata overlays, and title sanitization patterns.

# %% Configuration
ORCID = "0000-0002-5665-7912"
AUTHOR_PATTERN = re.compile(r"^dey,\s*b", re.IGNORECASE)
LEAD_MAX_POSITION = 2

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
BIB_DIR = REPO_ROOT / "_bibliography"
OUTPUT_PATH = BIB_DIR / "papers.bib"
CUSTOM_BIB_PATH = BIB_DIR / "papers_custom.bib"

ADS_API_URL = "https://api.adsabs.harvard.edu/v1"

FORCE_LEAD: frozenset[str] = frozenset({"dey2026tabular"})
EXCLUDE_BIBCODES: frozenset[str] = frozenset()

JOURNAL_MACROS: Mapping[str, str] = {
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

JOURNAL_ABBRS: Mapping[str, str] = {
    "The Astronomical Journal": "AJ",
    "The Astrophysical Journal": "ApJ",
    "The Astrophysical Journal Letters": "ApJL",
    "The Astrophysical Journal Supplement Series": "ApJS",
    "Monthly Notices of the Royal Astronomical Society": "MNRAS",
    "Astronomy & Astrophysics": "A&A",
    "Journal of Cosmology and Astroparticle Physics": "JCAP",
    "Physical Review D": "PRD",
    "Physical Review Letters": "PRL",
    "Publications of the Astronomical Society of the Pacific": "PASP",
    "The Open Journal of Astrophysics": "OJAp",
    "Machine Learning: Science and Technology": "MLST",
    "arXiv e-prints": "arXiv",
}

METADATA_OVERLAYS: Mapping[str, Mapping[str, str]] = {
    "dey2026tabular": {
        "abbr": "ML4PS",
        "selected": "true",
        "lead": "true",
        "month": "oct",
        "code": "https://github.com/biprateep/lazy-tfm",
        "website": "https://lazy-tfm.readthedocs.io",
        "note": (
            "NeurIPS 2026 Workshop on Machine Learning and the Physical "
            "Sciences (ML4PS)"
        ),
    },
    "2026AJ....172...65D": {
        "abbr": "AJ",
        "selected": "true",
        "lead": "true",
        "website": "https://biprateep.github.io/desi-deep-pilot",
        "code": "https://github.com/biprateep/desi-deep-pilot",
    },
    "2026arXiv260610197P": {
        "abbr": "arXiv",
        "selected": "true",
        "lead": "true",
        "code": "https://github.com/harrypenguin/MultiModal",
    },
    "2026arXiv260609576P": {
        "abbr": "arXiv",
        "selected": "true",
        "lead": "true",
        "code": "https://github.com/pratsosa/SCREAM",
    },
    "2025MLS&T...6d5058D": {
        "abbr": "MLST",
        "selected": "true",
        "lead": "true",
        "code": "https://github.com/lee-group-cmu/Cal-PIT",
        "website": "https://cal-pit.readthedocs.io",
    },
    "2022MNRAS.515.5285D": {
        "abbr": "MNRAS",
        "selected": "true",
        "lead": "true",
        "website": "https://biprateep.github.io/encapZulate-1",
        "code": "https://github.com/biprateep/encapZulate-1",
    },
    "2021arXiv211015209D": {
        "abbr": "ML4PS",
        "selected": "true",
        "lead": "true",
        "code": "https://github.com/biprateep/recalibrate-pdfs",
    },
    "Sanders:2026kgp": {
        "abbr": "DESI DR2",
        "collaboration": "DESI",
        "month": "aug",
        "doi": "10.5281/zenodo.22135162",
    },
    "Shao:2026syl": {
        "abbr": "DESI DR1",
        "collaboration": "DESI",
        "month": "sep",
        "doi": "10.5281/zenodo.22234808",
    },
    "Moore_2026": {
        "abbr": "PRD",
        "month": "sep",
        "note": "Accepted in Physical Review D",
    },
    "Leonard:2026pkh": {
        "abbr": "DESI Y1",
        "collaboration": "DESI",
        "month": "sep",
        "doi": "10.5281/zenodo.22149470",
    },
    "Gong:2026tpn": {
        "abbr": "DESI DR2",
        "collaboration": "DESI",
        "month": "sep",
        "doi": "10.5281/zenodo.20790055",
    },
    "medina2026": {
        "abbr": "DESI DR2",
        "collaboration": "DESI",
        "month": "nov",
    },
}

TITLE_SANITIZATIONS: tuple[tuple[re.Pattern[str], str], ...] = (
    (re.compile(r"z\s{2,3}1"), r"z \\sim 1"),
)

PRESERVE_KEYWORDS: frozenset[str] = frozenset(
    {
        "abbr",
        "abstract",
        "altmetric",
        "annotation",
        "arxiv",
        "bibtex_show",
        "blog",
        "code",
        "collaboration",
        "dimensions",
        "google_scholar_id",
        "html",
        "lead",
        "note",
        "pdf",
        "poster",
        "preview",
        "selected",
        "slides",
        "supp",
        "video",
        "website",
    }
)

# %% [markdown]
# ## NASA ADS API Client Helpers
#
# Functions to query the NASA ADS search and BibTeX export endpoints using only
# the Python standard library.


# %% ADS API Helpers
def api_request(
    url: str,
    token: str,
    payload: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Executes an authenticated HTTP request against the NASA ADS API.

    Args:
      url: Full request URL.
      token: NASA ADS API bearer token.
      payload: Optional JSON body mapping for POST requests.

    Returns:
      Parsed JSON response dictionary.
    """
    req = urllib.request.Request(url)
    req.add_header("Authorization", f"Bearer {token}")
    if payload is not None:
        req.add_header("Content-Type", "application/json")
        req.data = json.dumps(payload).encode("utf-8")
    with urllib.request.urlopen(req) as resp:
        result: dict[str, Any] = json.loads(resp.read().decode("utf-8"))
        return result


def fetch_papers(
    api_url: str,
    orcid: str,
    token: str,
) -> list[dict[str, Any]]:
    """Fetches all publication records matching an ORCID from NASA ADS.

    Args:
      api_url: Base URL of the NASA ADS API.
      orcid: Author ORCID identifier string.
      token: NASA ADS API bearer token.

    Returns:
      List of ADS document dictionaries containing bibcode and author lists.
    """
    docs: list[dict[str, Any]] = []
    start = 0
    rows = 200
    while True:
        params = urllib.parse.urlencode(
            {
                "q": f"orcid:{orcid}",
                "fl": "bibcode,author,eid,identifier",
                "rows": rows,
                "start": start,
                "sort": "date desc, bibcode desc",
            }
        )
        result = api_request(f"{api_url}/search/query?{params}", token=token)
        response = result["response"]
        docs.extend(response["docs"])
        if len(docs) >= response["numFound"]:
            return docs
        start += rows


def export_bibtex(
    api_url: str,
    bibcodes: Sequence[str],
    token: str,
) -> str:
    """Exports BibTeX text for a sequence of ADS bibcodes.

    Args:
      api_url: Base URL of the NASA ADS API.
      bibcodes: Sequence of ADS bibcode strings.
      token: NASA ADS API bearer token.

    Returns:
      Raw BibTeX export string from NASA ADS.
    """
    result = api_request(
        f"{api_url}/export/bibtex",
        token=token,
        payload={"bibcode": list(bibcodes)},
    )
    export_text: str = result["export"]
    return export_text


# %% [markdown]
# ## BibTeX Parsing and Enrichment Helpers
#
# Functions to split BibTeX entries, extract keys and arXiv eprints, expand
# AAS macros, repair mangled titles, and inject `al-folio` metadata fields.


# %% BibTeX Helpers
def is_lead_author(
    doc: Mapping[str, Any],
    force_lead: frozenset[str],
    author_pattern: re.Pattern[str],
    max_position: int,
) -> bool:
    """Determines whether the author is in a lead or significant position.

    Args:
      doc: ADS document record with 'bibcode' and 'author' keys.
      force_lead: Set of bibcodes or keys always treated as lead.
      author_pattern: Compiled regex matching the author's surname/initial.
      max_position: Maximum 1-indexed author position considered lead.

    Returns:
      True if the record qualifies as a lead-author publication.
    """
    if doc["bibcode"] in force_lead:
        return True
    authors: Sequence[str] = doc.get("author", [])
    return any(
        author_pattern.match(name) for name in authors[:max_position]
    )


def expand_macros(bibtex: str, journal_macros: Mapping[str, str]) -> str:
    """Replaces AAS LaTeX journal macros with full journal names.

    Args:
      bibtex: Raw BibTeX string.
      journal_macros: Mapping from LaTeX macro to full journal name.

    Returns:
      BibTeX string with macros expanded.
    """
    ordered = sorted(journal_macros.items(), key=lambda kv: -len(kv[0]))
    for macro, name in ordered:
        bibtex = bibtex.replace("{" + macro + "}", "{" + name + "}")
    return bibtex


def parse_bib_chunks(bibtex: str) -> list[str]:
    """Splits BibTeX content into individual entry chunks, skipping comments.

    Args:
      bibtex: Full BibTeX file content.

    Returns:
      List of trimmed BibTeX entry strings.
    """
    cleaned_lines = [
        line
        for line in bibtex.splitlines()
        if not line.strip().startswith("@comment{")
    ]
    cleaned_text = "\n".join(cleaned_lines)
    chunks: list[str] = []
    for chunk in re.split(r"(?=^@)", cleaned_text, flags=re.MULTILINE):
        stripped = chunk.strip()
        if stripped:
            chunks.append(stripped)
    return chunks


def extract_entry_key(chunk: str) -> str | None:
    """Extracts the citation key from a BibTeX entry chunk.

    Args:
      chunk: Single BibTeX entry block.

    Returns:
      Citation key string, or None if not found.
    """
    match = re.match(r"@\w+\{([^,\s]+),", chunk)
    return match.group(1).strip() if match else None


def extract_entry_eprint(chunk: str) -> str | None:
    """Extracts the arXiv eprint identifier from a BibTeX entry chunk.

    Args:
      chunk: Single BibTeX entry block.

    Returns:
      Normalized arXiv identifier string, or None if absent.
    """
    match = re.search(r"eprint\s*=\s*\{?([^,\s\}]+)\}?", chunk, re.IGNORECASE)
    return match.group(1).strip() if match else None


def extract_entry_journal(chunk: str) -> str | None:
    """Extracts the journal name from a BibTeX entry chunk.

    Args:
      chunk: Single BibTeX entry block.

    Returns:
      Journal name string without outer braces, or None if absent.
    """
    match = re.search(
        r"^\s*journal\s*=\s*[\{\"]([^\}\"\n]+)[\}\"]",
        chunk,
        re.MULTILINE | re.IGNORECASE,
    )
    return match.group(1).strip() if match else None


# %% [markdown]
# ## Metadata Harvesting and Sanitization
#
# Harvests existing custom fields from `papers.bib`, repairs known ADS title
# export glitches, and injects metadata overlays into each BibTeX chunk.


# %% Metadata Preservation Helpers
def harvest_existing_metadata(
    file_path: pathlib.Path,
    preserve_keywords: frozenset[str],
) -> dict[str, dict[str, str]]:
    """Reads an existing `.bib` file and harvests custom `al-folio` fields.

    Args:
      file_path: Path to the existing `.bib` file.
      preserve_keywords: Set of lowercase field names to preserve.

    Returns:
      Mapping from entry citation key to a dictionary of preserved fields.
    """
    if not file_path.exists():
        return {}
    content = file_path.read_text(encoding="utf-8")
    harvested: dict[str, dict[str, str]] = {}
    field_pattern = re.compile(
        r"^\s*([a-zA-Z_][a-zA-Z0-9_\-]*)\s*=\s*\{?(.*?)\}?,?\s*$"
    )
    for chunk in parse_bib_chunks(content):
        key = extract_entry_key(chunk)
        if not key:
            continue
        fields: dict[str, str] = {}
        for line in chunk.splitlines():
            match = field_pattern.match(line)
            if match:
                field_name = match.group(1).lower()
                field_value = match.group(2).strip()
                if field_name in preserve_keywords:
                    fields[field_name] = field_value
        if fields:
            harvested[key] = fields
    return harvested


def sanitize_chunk_title(
    chunk: str,
    sanitizations: Sequence[tuple[re.Pattern[str], str]],
) -> str:
    """Applies regex repairs to mangled LaTeX titles in a BibTeX chunk.

    Args:
      chunk: Single BibTeX entry block.
      sanitizations: Sequence of (pattern, replacement) pairs.

    Returns:
      BibTeX entry block with sanitized title field.
    """
    title_match = re.search(
        r'(title\s*=\s*[\{"][^"\n\}]+[\}"])', chunk, re.IGNORECASE
    )
    if not title_match:
        return chunk
    original = title_match.group(1)
    sanitized = original
    for pattern, replacement in sanitizations:
        sanitized = pattern.sub(replacement, sanitized)
    if sanitized != original:
        return chunk.replace(original, sanitized)
    return chunk


def inject_fields_into_chunk(
    chunk: str,
    fields: Mapping[str, str],
) -> str:
    """Injects missing BibTeX fields at the top of an entry block.

    Args:
      chunk: Single BibTeX entry block.
      fields: Mapping of field names to values to ensure on the entry.

    Returns:
      Updated BibTeX entry block.
    """
    if not fields:
        return chunk
    lines_to_inject: list[str] = []
    for field_name, field_value in fields.items():
        pattern = rf"^\s*{re.escape(field_name)}\s*="
        if not re.search(pattern, chunk, re.MULTILINE | re.IGNORECASE):
            lines_to_inject.append(
                f"         {field_name} = {{{field_value}}},\n"
            )
    if lines_to_inject:
        header_injection = r"\1" + "".join(lines_to_inject)
        chunk = re.sub(
            r"(@\w+\{[^,\s]+,\n)", header_injection, chunk, count=1
        )
    return chunk


# %% [markdown]
# ## Entry Processing and Custom Preprint Merging
#
# Processes ADS entries and merges non-ADS preprints from `papers_custom.bib`,
# normalizing `@MISC` arXiv exports for `jekyll-scholar` compatibility.


# %% Entry Processing
def enrich_single_chunk(
    chunk: str,
    lead_keys: frozenset[str],
    harvested: Mapping[str, Mapping[str, str]],
    overlays: Mapping[str, Mapping[str, str]],
    journal_abbrs: Mapping[str, str],
    sanitizations: Sequence[tuple[re.Pattern[str], str]],
) -> str:
    """Applies title sanitization, lead tags, and overlays to one BibTeX chunk.

    Args:
      chunk: Single BibTeX entry block.
      lead_keys: Set of citation keys that are lead-author works.
      harvested: Previously harvested custom metadata per citation key.
      overlays: Declarative metadata overlays per key or eprint.
      journal_abbrs: Mapping from full journal name to short badge string.
      sanitizations: Sequence of title regex repairs.

    Returns:
      Enriched BibTeX entry block.
    """
    key = extract_entry_key(chunk)
    eprint = extract_entry_eprint(chunk)
    chunk = sanitize_chunk_title(chunk, sanitizations)

    combined: dict[str, str] = {}
    journal_name = extract_entry_journal(chunk)
    if journal_name and journal_name in journal_abbrs:
        combined["abbr"] = journal_abbrs[journal_name]
    if key and key in harvested:
        combined.update(harvested[key])
    if key and key in lead_keys:
        combined["lead"] = "true"
    if key and key in overlays:
        combined.update(overlays[key])
    if eprint and eprint in overlays:
        combined.update(overlays[eprint])

    return inject_fields_into_chunk(chunk, combined)


def process_ads_bibtex(
    bibtex: str,
    lead_keys: frozenset[str],
    harvested: Mapping[str, Mapping[str, str]],
    overlays: Mapping[str, Mapping[str, str]],
    journal_macros: Mapping[str, str],
    journal_abbrs: Mapping[str, str],
    sanitizations: Sequence[tuple[re.Pattern[str], str]],
) -> tuple[list[str], set[str], set[str]]:
    """Processes raw ADS BibTeX into enriched entry chunks.

    Args:
      bibtex: Raw BibTeX string from NASA ADS or existing `papers.bib`.
      lead_keys: Set of citation keys to mark with `lead = {true}`.
      harvested: Harvested custom fields from existing `papers.bib`.
      overlays: Declarative metadata overlays.
      journal_macros: Mapping of LaTeX journal macros to full names.
      journal_abbrs: Mapping of journal names to badge abbreviations.
      sanitizations: Title regex repair rules.

    Returns:
      Tuple of (processed_chunks, ads_eprints, ads_keys) as a tuple
      (chunks, eprints, keys).
    """
    expanded = expand_macros(bibtex, journal_macros)
    processed: list[str] = []
    ads_eprints: set[str] = set()
    ads_keys: set[str] = set()

    for chunk in parse_bib_chunks(expanded):
        key = extract_entry_key(chunk)
        eprint = extract_entry_eprint(chunk)
        if key:
            ads_keys.add(key)
        if eprint:
            ads_eprints.add(eprint)
        enriched = enrich_single_chunk(
            chunk=chunk,
            lead_keys=lead_keys,
            harvested=harvested,
            overlays=overlays,
            journal_abbrs=journal_abbrs,
            sanitizations=sanitizations,
        )
        processed.append(enriched)

    return processed, ads_eprints, ads_keys


def normalize_custom_preprint(chunk: str) -> str:
    """Normalizes an official `@MISC` arXiv entry for `jekyll-scholar`.

    Args:
      chunk: Raw BibTeX entry chunk from `papers_custom.bib`.

    Returns:
      Normalized `@ARTICLE` BibTeX chunk with `journal = {arXiv e-prints}`
      and `{Dey}, Biprateep` formatting for self-bolding.
    """
    eprint = extract_entry_eprint(chunk)
    if chunk.startswith("@MISC{") and eprint:
        chunk = "@ARTICLE{" + chunk[len("@MISC{") :]
    chunk = re.sub(
        r"\bBiprateep Dey\b",
        "{Dey}, Biprateep",
        chunk,
    )
    extra_fields: dict[str, str] = {}
    if eprint and not extract_entry_journal(chunk):
        extra_fields["journal"] = "arXiv e-prints"
        extra_fields["eid"] = f"arXiv:{eprint}"
        extra_fields["pages"] = f"arXiv:{eprint}"
    return inject_fields_into_chunk(chunk, extra_fields)


def load_custom_papers(
    custom_bib_path: pathlib.Path,
    ads_eprints: frozenset[str],
    ads_keys: frozenset[str],
    lead_keys: frozenset[str],
    harvested: Mapping[str, Mapping[str, str]],
    overlays: Mapping[str, Mapping[str, str]],
    journal_abbrs: Mapping[str, str],
    sanitizations: Sequence[tuple[re.Pattern[str], str]],
) -> list[str]:
    """Loads manual preprints from `papers_custom.bib` and deduplicates.

    Args:
      custom_bib_path: Path to `papers_custom.bib`.
      ads_eprints: Set of arXiv eprint IDs already present in ADS chunks.
      ads_keys: Set of citation keys already present in ADS chunks.
      lead_keys: Set of citation keys to mark as lead author.
      harvested: Harvested metadata from existing `papers.bib`.
      overlays: Declarative metadata overlays.
      journal_abbrs: Mapping of journal names to badge abbreviations.
      sanitizations: Title regex repair rules.

    Returns:
      List of deduplicated and enriched custom BibTeX chunks.
    """
    if not custom_bib_path.exists():
        return []
    content = custom_bib_path.read_text(encoding="utf-8")
    deduped: list[str] = []
    for raw_chunk in parse_bib_chunks(content):
        key = extract_entry_key(raw_chunk)
        eprint = extract_entry_eprint(raw_chunk)
        if (key and key in ads_keys) or (eprint and eprint in ads_eprints):
            continue
        normalized = normalize_custom_preprint(raw_chunk)
        enriched = enrich_single_chunk(
            chunk=normalized,
            lead_keys=lead_keys,
            harvested=harvested,
            overlays=overlays,
            journal_abbrs=journal_abbrs,
            sanitizations=sanitizations,
        )
        deduped.append(enriched)
    return deduped


# %% [markdown]
# ## Pipeline Execution
#
# Runs the full publication sync (or offline enrichment when `--offline` is
# passed on the command line) and writes `_bibliography/papers.bib`.


# %% Pipeline Execution
def run_pipeline(
    argv: Sequence[str],
    output_path: pathlib.Path,
    custom_bib_path: pathlib.Path,
    api_url: str,
    orcid: str,
    force_lead: frozenset[str],
    exclude_bibcodes: frozenset[str],
    author_pattern: re.Pattern[str],
    lead_max_position: int,
    preserve_keywords: frozenset[str],
    overlays: Mapping[str, Mapping[str, str]],
    journal_macros: Mapping[str, str],
    journal_abbrs: Mapping[str, str],
    sanitizations: Sequence[tuple[re.Pattern[str], str]],
) -> None:
    """Executes the publication update and preservation pipeline.

    Args:
      argv: Command-line arguments after the script name.
      output_path: Destination path for `papers.bib`.
      custom_bib_path: Source path for `papers_custom.bib`.
      api_url: Base NASA ADS API URL.
      orcid: Author ORCID string.
      force_lead: Set of keys always marked as lead author.
      exclude_bibcodes: Set of bibcodes to omit.
      author_pattern: Compiled regex matching the author's name.
      lead_max_position: Maximum author index for lead classification.
      preserve_keywords: Set of `al-folio` keywords to preserve.
      overlays: Declarative metadata overlays.
      journal_macros: AAS journal macro mapping.
      journal_abbrs: Venue badge abbreviation mapping.
      sanitizations: Title regex repair rules.
    """
    offline_mode = "--offline" in argv
    harvested = harvest_existing_metadata(output_path, preserve_keywords)

    custom_keys: set[str] = set()
    if custom_bib_path.exists():
        for chunk in parse_bib_chunks(
            custom_bib_path.read_text(encoding="utf-8")
        ):
            custom_key = extract_entry_key(chunk)
            if custom_key:
                custom_keys.add(custom_key)

    if offline_mode:
        if not output_path.exists():
            sys.exit(f"Error: {output_path} not found for --offline mode.")
        raw_full = output_path.read_text(encoding="utf-8")
        existing_ads_chunks = [
            chunk
            for chunk in parse_bib_chunks(raw_full)
            if extract_entry_key(chunk) not in custom_keys
        ]
        raw_bibtex = "\n\n".join(existing_ads_chunks)
        lead_keys = frozenset(
            key
            for key, meta in harvested.items()
            if meta.get("lead") == "true"
        ) | force_lead
    else:
        token = os.environ.get("ADS_API_TOKEN")
        if not token:
            sys.exit("Error: set the ADS_API_TOKEN environment variable.")
        docs = [
            doc
            for doc in fetch_papers(api_url, orcid, token)
            if doc["bibcode"] not in exclude_bibcodes
        ]
        if not docs:
            sys.exit(
                "Error: ADS returned no publications; refusing to overwrite."
            )
        lead_keys = (
            frozenset(
                doc["bibcode"]
                for doc in docs
                if is_lead_author(
                    doc, force_lead, author_pattern, lead_max_position
                )
            )
            | force_lead
        )
        raw_bibtex = export_bibtex(
            api_url, [doc["bibcode"] for doc in docs], token
        )

    ads_chunks, ads_eprints, ads_keys = process_ads_bibtex(
        bibtex=raw_bibtex,
        lead_keys=lead_keys,
        harvested=harvested,
        overlays=overlays,
        journal_macros=journal_macros,
        journal_abbrs=journal_abbrs,
        sanitizations=sanitizations,
    )
    custom_chunks = load_custom_papers(
        custom_bib_path=custom_bib_path,
        ads_eprints=frozenset(ads_eprints),
        ads_keys=frozenset(ads_keys),
        lead_keys=lead_keys,
        harvested=harvested,
        overlays=overlays,
        journal_abbrs=journal_abbrs,
        sanitizations=sanitizations,
    )

    all_chunks = custom_chunks + ads_chunks
    output_path.write_text("\n\n".join(all_chunks) + "\n", encoding="utf-8")
    print(
        f"Wrote {len(all_chunks)} entries "
        f"({len(ads_chunks)} ADS + {len(custom_chunks)} custom) "
        f"to {output_path}"
    )


if __name__ == "__main__":
    run_pipeline(
        argv=sys.argv[1:],
        output_path=OUTPUT_PATH,
        custom_bib_path=CUSTOM_BIB_PATH,
        api_url=ADS_API_URL,
        orcid=ORCID,
        force_lead=FORCE_LEAD,
        exclude_bibcodes=EXCLUDE_BIBCODES,
        author_pattern=AUTHOR_PATTERN,
        lead_max_position=LEAD_MAX_POSITION,
        preserve_keywords=PRESERVE_KEYWORDS,
        overlays=METADATA_OVERLAYS,
        journal_macros=JOURNAL_MACROS,
        journal_abbrs=JOURNAL_ABBRS,
        sanitizations=TITLE_SANITIZATIONS,
    )
