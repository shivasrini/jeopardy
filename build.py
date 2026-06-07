#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════════════════╗
║              JEOPARDY GAME BUILDER                       ║
║                                                           ║
║  Each topic/group lives in its own self-contained pack:  ║
║    packs/<name>/categories/*.json   (required)           ║
║    packs/<name>/final_jeopardy.json (optional)           ║
║    packs/<name>/config.json         (optional)           ║
║                                                           ║
║  Build :  python3 build.py --pack <name>                 ║
║           python3 build.py          (auto if only 1 pack)║
║  List  :  python3 build.py --list                        ║
║  Output:  ./output/<name>_jeopardy_game.html             ║
╚══════════════════════════════════════════════════════════╝

Three ways to keep pack content where you want it:

  1. COMMITTED & SHARED — packs/<name>/  (default)
     Lives in this repo, tracked by git, travels with the project.
     Use for reusable packs you're fine version-controlling
     (e.g. tamil_cinema).

  2. LOCAL-ONLY, DEFAULT LOCATION — packs/<name>.local/
     Same ./packs folder, same commands (no extra flags) — but the
     ".local" suffix matches a .gitignore rule, so git never tracks
     it. Good for "mine, but I don't want to think about a separate
     path" personal packs (family roast, coworker quiz, etc.).
     e.g.:  packs/family_roast.local/categories/*.json
            python3 build.py --pack family_roast.local

  3. FULLY EXTERNAL — anywhere on disk, via --packs-dir
     Keeps content completely outside this repo's working tree and
     history (an iCloud folder, a private repo, wherever). Nothing
     under that path is read/written except via this explicit flag.
       python3 build.py --packs-dir /path/to/my-packs --pack <name>
       python3 build.py --packs-dir /path/to/my-packs --list

Mix and match per pack — e.g. keep the Tamil cinema pack committed
(#1), a family pack as packs/family.local/ (#2), and a sensitive
coworker pack on an external private path (#3), all built the same way.

categories/<file>.json — one category, or a LIST of categories:
{
  "id":   "unique_snake_case_id",
  "name": "🎵 Display Name",
  "questions": [
    {"value": 200,  "q": "Question text?", "a": "Answer"},
    {"value": 400,  "q": "Question text?", "a": "Answer"},
    {"value": 600,  "q": "Question text?", "a": "Answer"},
    {"value": 800,  "q": "Question text?", "a": "Answer"},
    {"value": 1000, "q": "Question text?", "a": "Answer"}
  ]
}

config.json — optional branding overrides (missing fields fall back
to generic defaults, so a pack can omit this file entirely):
{
  "title":    "JEOPARDY!",
  "subtitle": "Office Trivia Night",
  "taglines": ["Nice one!", "Crushing it!", "..."]
}

To start a new pack for a different group/topic, copy an existing
pack folder, replace its categories/final_jeopardy/config, and build
with --pack <new_name>.
"""

import json
import os
import sys
import glob
from datetime import datetime

# ── Paths ────────────────────────────────────────────────
SCRIPT_DIR    = os.path.dirname(os.path.abspath(__file__))
PACKS_DIR     = os.path.join(SCRIPT_DIR, 'packs')
TEMPLATE_FILE = os.path.join(SCRIPT_DIR, 'template.html')
OUTPUT_DIR    = os.path.join(SCRIPT_DIR, 'output')

# ── Generic defaults (used when a pack has no config.json, or omits a field) ──
DEFAULT_CONFIG = {
    "title": "JEOPARDY!",
    "subtitle": "Trivia Night",
    "taglines": [
        "Genius at work!",
        "Trivia champion!",
        "Walking encyclopedia!",
        "Nailed it!",
        "Top of the leaderboard!",
        "Brainpower unmatched!",
        "Quiz master in the house!",
        "Knowledge is power — and you've got plenty!"
    ]
}

# ── Helpers ──────────────────────────────────────────────
def discover_packs(packs_dir):
    if not os.path.isdir(packs_dir):
        return []
    return sorted(
        d for d in os.listdir(packs_dir)
        if os.path.isdir(os.path.join(packs_dir, d)) and not d.startswith('.')
    )


def resolve_pack(packs_dir, requested):
    packs = discover_packs(packs_dir)
    if not packs:
        print(f"✗  No packs found under {packs_dir}")
        print(f"   Create one: {packs_dir}/<name>/categories/*.json")
        sys.exit(1)
    if requested:
        if requested not in packs:
            print(f"✗  Pack '{requested}' not found in {packs_dir}. Available: {', '.join(packs)}")
            sys.exit(1)
        return requested
    if len(packs) == 1:
        return packs[0]
    print(f"✗  Multiple packs found in {packs_dir} — choose one with --pack <name>")
    print(f"   Available: {', '.join(packs)}")
    sys.exit(1)


def load_categories(pack_dir):
    cat_dir = os.path.join(pack_dir, 'categories')
    categories = []
    files = sorted(glob.glob(os.path.join(cat_dir, '*.json')))
    if not files:
        print(f"⚠  No JSON files found in {cat_dir}")
        sys.exit(1)

    for filepath in files:
        fname = os.path.basename(filepath)
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
            if isinstance(data, list):
                for item in data:
                    validate_category(item, fname)
                categories.extend(data)
            else:
                validate_category(data, fname)
                categories.append(data)
        except json.JSONDecodeError as e:
            print(f"✗  JSON parse error in {fname}: {e}")
            sys.exit(1)
        except ValueError as e:
            print(f"✗  Validation error in {fname}: {e}")
            sys.exit(1)

    ids = [c['id'] for c in categories]
    dupes = sorted({i for i in ids if ids.count(i) > 1})
    if dupes:
        print(f"✗  Duplicate category id(s) in {cat_dir}: {', '.join(dupes)}")
        sys.exit(1)

    return categories


def validate_category(cat, source):
    required = ['id', 'name', 'questions']
    for key in required:
        if key not in cat:
            raise ValueError(f"Missing '{key}' in category from {source}")
    if not isinstance(cat['questions'], list) or len(cat['questions']) == 0:
        raise ValueError(f"Category '{cat['id']}' must have at least 1 question")
    for q in cat['questions']:
        for k in ['value', 'q', 'a']:
            if k not in q:
                raise ValueError(f"Question in '{cat['id']}' missing field '{k}'")


def load_final_question(pack_dir):
    path = os.path.join(pack_dir, 'final_jeopardy.json')
    if not os.path.exists(path):
        print("⚠  final_jeopardy.json not found — using placeholder question.")
        return {
            "category": "Final Round",
            "q": "This is a placeholder Final Jeopardy question. Add final_jeopardy.json to this pack to change it!",
            "a": "Edit final_jeopardy.json"
        }
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)


def load_config(pack_dir):
    config = dict(DEFAULT_CONFIG)
    path = os.path.join(pack_dir, 'config.json')
    if os.path.exists(path):
        with open(path, 'r', encoding='utf-8') as f:
            overrides = json.load(f)
        for key, value in overrides.items():
            if value:
                config[key] = value
    return config


def load_template():
    if not os.path.exists(TEMPLATE_FILE):
        print(f"✗  template.html not found at: {TEMPLATE_FILE}")
        sys.exit(1)
    with open(TEMPLATE_FILE, 'r', encoding='utf-8') as f:
        return f.read()


def list_packs(packs_dir):
    packs = discover_packs(packs_dir)
    if not packs:
        print(f"⚠  No packs found in {packs_dir}")
        return
    print(f"\n📦 Found {len(packs)} pack(s) in {packs_dir}:\n")
    for name in packs:
        pack_dir = os.path.join(packs_dir, name)
        cat_dir  = os.path.join(pack_dir, 'categories')
        files    = glob.glob(os.path.join(cat_dir, '*.json'))
        flag     = '' if packs_dir == PACKS_DIR else f' --packs-dir {packs_dir}'
        print(f"  • {name}  ({len(files)} category file(s))  →  python3 build.py{flag} --pack {name}")
    print()


# ── Main build ───────────────────────────────────────────
def build(packs_dir, requested_pack):
    pack     = resolve_pack(packs_dir, requested_pack)
    pack_dir = os.path.join(packs_dir, pack)
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    categories = load_categories(pack_dir)
    final_q    = load_final_question(pack_dir)
    config     = load_config(pack_dir)
    template   = load_template()

    html = template
    html = html.replace(
        '// {{GAME_CONFIG}}',
        f'const GAME_CONFIG = {json.dumps(config, ensure_ascii=False, indent=2)};'
    )
    html = html.replace(
        '// {{QUESTION_BANK}}',
        f'const QUESTION_BANK = {json.dumps(categories, ensure_ascii=False, indent=2)};'
    )
    html = html.replace(
        '// {{FINAL_QUESTION}}',
        f'const FINAL_QUESTION = {json.dumps(final_q, ensure_ascii=False)};'
    )

    stamp = datetime.now().strftime('%Y-%m-%d %H:%M')
    html = html.replace(
        '<!-- BUILD_STAMP -->',
        f'<!-- Built: {stamp} | pack: {pack} | {len(categories)} categories -->'
    )

    output_file = os.path.join(OUTPUT_DIR, f'{pack}_jeopardy_game.html')
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(html)

    print(f"\n🎬 Build complete!")
    print(f"   Pack       : {pack}")
    print(f"   Categories : {len(categories)}")
    print(f"   Output     : {output_file}")
    print(f"\n   Categories loaded:")
    for cat in categories:
        q_count = len(cat.get('questions', []))
        print(f"     • {cat['name']} ({q_count} questions)")
    print(f"\n   ✓ Open {os.path.relpath(output_file, SCRIPT_DIR)} in your browser to play!\n")


# ── Entry point ──────────────────────────────────────────
def parse_value_arg(argv, flag, example):
    if flag not in argv:
        return None
    i = argv.index(flag)
    if i + 1 >= len(argv) or argv[i + 1].startswith('--'):
        print(f"✗  {flag} requires a value, e.g. {flag} {example}")
        sys.exit(1)
    return argv[i + 1]


if __name__ == '__main__':
    argv = sys.argv[1:]

    packs_dir_arg = parse_value_arg(argv, '--packs-dir', '/path/to/my-packs')
    packs_dir = os.path.abspath(os.path.expanduser(packs_dir_arg)) if packs_dir_arg else PACKS_DIR
    if packs_dir_arg and not os.path.isdir(packs_dir):
        print(f"✗  --packs-dir path not found: {packs_dir}")
        sys.exit(1)

    pack_name = parse_value_arg(argv, '--pack', 'tamil_cinema')

    if '--list' in argv:
        list_packs(packs_dir)
    else:
        build(packs_dir, pack_name)
