"""
Pack loader — reads Certification Pack YAML files and validates them into Pydantic models.

A "Pack" is the declarative artifact that makes the platform generic (spec v2 §2).
The loader is called once at session start; the resulting Pack object is injected
into every agent as their only source of certification-specific knowledge.
"""

from pathlib import Path

import yaml

from ai_tutor.config import settings
from ai_tutor.models import Concept, Domain, Pack


def load_pack(pack_id: str) -> Pack:
    """
    Load and validate a Certification Pack from disk.

    Raises FileNotFoundError if the pack directory or pack.yaml is missing.
    Raises ValidationError (Pydantic) if pack.yaml fails schema validation.
    """
    pack_dir = settings.packs_dir / pack_id

    if not pack_dir.exists():
        raise FileNotFoundError(f"Pack directory not found: {pack_dir}")

    # ── Load pack.yaml ────────────────────────────────────────────────────────
    pack_yaml_path = pack_dir / "pack.yaml"
    if not pack_yaml_path.exists():
        raise FileNotFoundError(f"pack.yaml missing in {pack_dir}")

    with pack_yaml_path.open() as f:
        raw = yaml.safe_load(f)

    # Convert scoring_scale list → tuple (YAML has no tuple type)
    if "scoring_scale" in raw and isinstance(raw["scoring_scale"], list):
        raw["scoring_scale"] = tuple(raw["scoring_scale"])

    # Build Domain objects from the YAML list
    raw["domains"] = [Domain(**d) for d in raw.get("domains", [])]

    # ── Load curriculum.yaml (optional — provides concept list) ───────────────
    curriculum_path = pack_dir / "curriculum.yaml"
    concepts: list[Concept] = []
    if curriculum_path.exists():
        with curriculum_path.open() as f:
            curriculum_raw = yaml.safe_load(f) or {}
        concepts = [Concept(**c) for c in curriculum_raw.get("concepts", [])]

    raw["concepts"] = concepts

    return Pack(**raw)


def load_corpus_urls(pack_id: str, domains: list[str] | None = None) -> list[dict]:
    """
    Load the corpus URL list for a pack, optionally filtered to specific domains.

    Returns a flat list of dicts with keys: url, title, domain, tier.
    This is the input to the ingestion pipeline.
    """
    pack_dir = settings.packs_dir / pack_id
    urls_path = pack_dir / "corpus_urls.yaml"

    if not urls_path.exists():
        raise FileNotFoundError(f"corpus_urls.yaml missing in {pack_dir}")

    with urls_path.open() as f:
        raw = yaml.safe_load(f)

    result = []
    for domain_id, domain_data in raw.get("domains", {}).items():
        # Skip domains not requested (when domains filter is provided)
        if domains and domain_id not in domains:
            continue

        domain_weight = domain_data.get("weight", 0.0)

        for tier, tier_key in [(1, "tier1"), (2, "tier2")]:
            for entry in domain_data.get(tier_key, []):
                if not entry:  # skip empty entries (placeholder domains)
                    continue
                result.append({
                    "url": entry["url"],
                    "title": entry.get("title", ""),
                    "domain": domain_id,
                    "domain_weight": domain_weight,
                    "tier": tier,
                })

    return result


def load_style_notes(pack_id: str) -> str:
    """Load free-form Examiner style guidance for a pack."""
    style_path = settings.packs_dir / pack_id / "style_notes.md"
    if not style_path.exists():
        return ""
    return style_path.read_text()
