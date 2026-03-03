# seed_ingredients.py
#!/usr/bin/env python3
"""
Seeds Firestore ingredients/{ingredientId} with canonical ingredient names (NO measurements).

- Ingredient IDs are slugified canonical names (e.g., "breadcrumbs", "chicken_breast").
- Quantities/units are NOT stored in ingredients. Those are handled in recipes later.

Setup:
  - Put serviceAccountKey.json next to this file OR
  - Set GOOGLE_APPLICATION_CREDENTIALS to the JSON key path

Run:
  python seed_ingredients.py
Optional:
  python seed_ingredients.py --project YOUR_PROJECT_ID
  python seed_ingredients.py --dry-run
"""

from __future__ import annotations

import argparse
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Set

import firebase_admin
from firebase_admin import credentials, firestore


# -----------------------------
# Firebase init
# -----------------------------

def init_firestore(project_id: Optional[str] = None) -> firestore.Client:
    if firebase_admin._apps:
        return firestore.client()

    key_path_env = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS", "").strip()
    script_dir = Path(__file__).resolve().parent
    local_key_path = script_dir / "serviceAccountKey.json"

    if key_path_env:
        p = Path(key_path_env)
        if not p.exists():
            raise FileNotFoundError(f"GOOGLE_APPLICATION_CREDENTIALS is set, but file not found: {p}")
        cred_obj = credentials.Certificate(str(p))
    elif local_key_path.exists():
        cred_obj = credentials.Certificate(str(local_key_path))
    else:
        raise FileNotFoundError(
            "No service account key found. Set GOOGLE_APPLICATION_CREDENTIALS or place "
            "serviceAccountKey.json next to this script."
        )

    options: Dict[str, Any] = {}
    if project_id:
        options["projectId"] = project_id

    firebase_admin.initialize_app(cred_obj, options=options or None)
    return firestore.client()


# -----------------------------
# Canonicalization (no measurements)
# -----------------------------

UNITS = r"(?:oz|ounce|ounces|lb|lbs|pound|pounds|g|gram|grams|kg|cup|cups|tbsp|tablespoon|tablespoons|tsp|teaspoon|teaspoons|clove|cloves|can|cans|fillet|fillets|each)"
FRACTION = r"(?:\d+\s*/\s*\d+)"                     # 1/2
NUMBER = r"(?:\d+(?:\.\d+)?)"                       # 2 or 2.5
MIXED = rf"(?:{NUMBER}\s+{FRACTION})"               # 1 1/2
RANGE = rf"(?:{NUMBER}\s*-\s*{NUMBER})"             # 2-3
QTY_TOKEN = rf"(?:{MIXED}|{FRACTION}|{RANGE}|{NUMBER})"

LEADING_QTY_UNIT_RE = re.compile(
    rf"^\s*(?P<qty>{QTY_TOKEN})\s*(?P<unit>{UNITS})?\b\s*(?P<rest>.*)$",
    re.IGNORECASE,
)

PAREN_RE = re.compile(r"\([^)]*\)")
EXTRA_SPACE_RE = re.compile(r"\s+")
FILLER_RE = re.compile(r"\b(to taste|for garnish)\b", re.IGNORECASE)


def canonicalize_ingredient_name(original_line: str) -> str:
    """
    Returns a canonical ingredient name with:
    - NO leading measurements (qty/unit)
    - NO parenthetical package notes
    - NO "to taste" / "for garnish"
    - NO comma-notes (diced/minced/etc.)
    """
    line = original_line.strip()

    # Drop notes after comma for canonical name
    base = line.split(",", 1)[0].strip()

    # Remove parentheticals like "(15 oz)"
    base = PAREN_RE.sub("", base).strip()

    # Remove filler phrases
    base = FILLER_RE.sub("", base).strip()

    # Remove leading qty/unit
    m = LEADING_QTY_UNIT_RE.match(base)
    if m:
        rest = (m.group("rest") or "").strip()
        base = rest if rest else base

    base = EXTRA_SPACE_RE.sub(" ", base).strip()
    return base or line


def slugify(name: str) -> str:
    s = name.lower().strip()
    s = re.sub(r"[^a-z0-9]+", "_", s)
    s = re.sub(r"_+", "_", s).strip("_")
    return s or "ingredient"


def now_ts() -> datetime:
    return datetime.now(timezone.utc)


# -----------------------------
# Source ingredient lines
# -----------------------------
# You can expand/replace this list, or load from a file later.

DEFAULT_INGREDIENT_LINES: List[str] = [
    # From your generator examples
    "12 oz pasta (penne or linguine)",
    "1 lb chicken breast, diced",
    "2 cups cream or milk",
    "1 cup parmesan cheese, grated",
    "3 cloves garlic, minced",
    "2 tbsp olive oil",
    "1 cup spinach or vegetables",
    "Salt and pepper to taste",
    "Fresh herbs for garnish",

    "4 salmon fillets (6 oz each)",
    "2 cups broccoli florets",
    "2 bell peppers, sliced",
    "1 zucchini, sliced",
    "Lemon juice and zest",
    "Fresh herbs (dill or parsley)",

    "1 lb beef sirloin, thinly sliced",
    "3 cups cooked rice",
    "2 cups mixed vegetables",
    "3 tbsp soy sauce",
    "2 tbsp oyster or teriyaki sauce",
    "1 tbsp sesame oil",
    "1 tbsp ginger, grated",
    "2 tbsp vegetable oil",
    "Green onions and sesame seeds for garnish",

    "2 cups cooked rice or quinoa",
    "1 can (15 oz) black beans, drained",
    "1 cup corn kernels",
    "1 bell pepper, diced",
    "1 avocado, sliced",
    "1 cup cherry tomatoes, halved",
    "1/2 cup shredded cheese",
    "Fresh cilantro",
    "Sour cream or Greek yogurt",
    "Salt, pepper, and cumin to taste",

    "1 lb ground turkey or beef",
    "1/2 cup breadcrumbs",
    "1 egg",
    "1/4 cup parmesan cheese",
    "2 cups marinara or BBQ sauce",
    "1 tbsp Italian seasoning",
    "Fresh basil for garnish",
    "Cooked pasta or rice for serving",

    "1 lb shrimp, peeled and deveined",
    "8 small tortillas",
    "2 cups shredded cabbage",
    "1 cup cherry tomatoes, diced",
    "1/4 cup sour cream or mayo",
    "2 tsp chili powder",
    "Lime juice",

    "1 lb chicken, cubed",
    "1 can (14 oz) coconut milk",
    "2 tbsp curry paste or powder",
    "1 onion, diced",
    "2 cups vegetables (bell peppers, carrots)",
    "3 cups cooked basmati rice",
]


def build_ingredient_doc(name: str) -> Dict[str, Any]:
    return {
        "name": name,
        "aliases": [],
        "category": None,
        "avgPrice": None,
        "priceUnit": None,
        "createdAt": now_ts(),
        "updatedAt": now_ts(),
    }


def unique_canonical_ingredients(lines: Iterable[str]) -> List[str]:
    seen: Set[str] = set()
    out: List[str] = []
    for line in lines:
        canon = canonicalize_ingredient_name(line)
        if canon and canon not in seen:
            seen.add(canon)
            out.append(canon)
    return out


def seed(db: firestore.Client, lines: List[str], dry_run: bool) -> None:
    canon_list = unique_canonical_ingredients(lines)
    print(f"Canonical ingredients to write: {len(canon_list)}")

    for canon in canon_list:
        ing_id = slugify(canon)
        doc = build_ingredient_doc(canon)
        if dry_run:
            print(f"[DRY RUN] Would write ingredients/{ing_id}: {canon}")
        else:
            db.collection("ingredients").document(ing_id).set(doc, merge=True)
            print(f"Wrote ingredients/{ing_id}: {canon}")


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Seed Firestore ingredients collection (no measurements).")
    p.add_argument("--project", dest="project_id", default=None)
    p.add_argument("--dry-run", dest="dry_run", action="store_true")
    return p.parse_args()


def main() -> int:
    args = parse_args()
    try:
        db = init_firestore(project_id=args.project_id)
        seed(db, DEFAULT_INGREDIENT_LINES, dry_run=args.dry_run)
        print("Done.")
        return 0
    except Exception as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
