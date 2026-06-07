#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════════════════╗
║              JEOPARDY GAME BUILDER                       ║
║  Drop JSON category files into ./categories/             ║
║  Run:  python3 build.py                                  ║
║  Output: ./output/jeopardy_game.html                     ║
╚══════════════════════════════════════════════════════════╝

JSON format for a category file (one category per file):
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

A single JSON file can also hold a LIST of categories:
[
  { "id": "cat1", "name": "...", "questions": [...] },
  { "id": "cat2", "name": "...", "questions": [...] }
]
"""

import json
import os
import sys
import glob
from datetime import datetime

# ── Paths ────────────────────────────────────────────────
SCRIPT_DIR    = os.path.dirname(os.path.abspath(__file__))
CATEGORIES_DIR = os.path.join(SCRIPT_DIR, 'categories')
FINAL_Q_FILE  = os.path.join(SCRIPT_DIR, 'final_jeopardy.json')
TEMPLATE_FILE = os.path.join(SCRIPT_DIR, 'template.html')
OUTPUT_DIR    = os.path.join(SCRIPT_DIR, 'output')
OUTPUT_FILE   = os.path.join(OUTPUT_DIR, 'jeopardy_game.html')

# ── Helpers ──────────────────────────────────────────────
def load_categories():
    categories = []
    files = sorted(glob.glob(os.path.join(CATEGORIES_DIR, '*.json')))
    if not files:
        print("⚠  No JSON files found in ./categories/")
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


def load_final_question():
    if not os.path.exists(FINAL_Q_FILE):
        print("⚠  final_jeopardy.json not found — using default question.")
        return {
            "category": "The Grand Stage",
            "q": "This is a placeholder Final Jeopardy question. Edit final_jeopardy.json to change it!",
            "a": "Edit final_jeopardy.json"
        }
    with open(FINAL_Q_FILE, 'r', encoding='utf-8') as f:
        return json.load(f)


def load_template():
    if not os.path.exists(TEMPLATE_FILE):
        print(f"✗  template.html not found at: {TEMPLATE_FILE}")
        sys.exit(1)
    with open(TEMPLATE_FILE, 'r', encoding='utf-8') as f:
        return f.read()


def list_categories():
    """Print all available categories without building."""
    categories = load_categories()
    print(f"\n📚 Found {len(categories)} categories:\n")
    for i, cat in enumerate(categories, 1):
        q_count = len(cat.get('questions', []))
        print(f"  {i:2}. {cat['name']:<35} ({q_count} questions)  [{cat['id']}]")
    print()


# ── Main build ───────────────────────────────────────────
def build():
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    categories  = load_categories()
    final_q     = load_final_question()
    template    = load_template()

    # Inject question bank + final question into the template
    html = template
    html = html.replace(
        '// {{QUESTION_BANK}}',
        f'const QUESTION_BANK = {json.dumps(categories, ensure_ascii=False, indent=2)};'
    )
    html = html.replace(
        '// {{FINAL_QUESTION}}',
        f'const FINAL_QUESTION = {json.dumps(final_q, ensure_ascii=False)};'
    )

    # Stamp build date into title comment
    stamp = datetime.now().strftime('%Y-%m-%d %H:%M')
    html = html.replace('<!-- BUILD_STAMP -->', f'<!-- Built: {stamp} | {len(categories)} categories -->')

    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        f.write(html)

    print(f"\n🎬 Build complete!")
    print(f"   Categories : {len(categories)}")
    print(f"   Output     : {OUTPUT_FILE}")
    print(f"\n   Categories loaded:")
    for cat in categories:
        q_count = len(cat.get('questions', []))
        print(f"     • {cat['name']} ({q_count} questions)")
    print(f"\n   ✓ Open output/jeopardy_game.html in your browser to play!\n")


# ── Entry point ──────────────────────────────────────────
if __name__ == '__main__':
    if '--list' in sys.argv:
        list_categories()
    else:
        build()
