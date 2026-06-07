# Tamil Cinema Jeopardy — Product Spec

## 1. Overview

A party trivia game themed around Tamil cinema (Kollywood), styled after
the TV show *Jeopardy!*. The game is authored as a set of JSON content
files, compiled into a single self-contained HTML file, and played
entirely in a browser — no server, no install, no network connection
required at play time.

**Primary user:** a host who runs the game on a laptop/TV for a group of
2–4 players in the same room.

## 2. Goals

- Let a host stand up a full trivia night in under a minute (open file →
  enter names → play).
- Make content authoring trivial: drop a JSON file in `categories/`,
  rebuild, done — no HTML/JS knowledge required.
- Deliver the classic Jeopardy! experience: category board, point tiers,
  buzz-in race, host-judged answers, wagering Final round.
- Run anywhere a browser runs — offline, no installs, no accounts.

## 3. Non-goals

- Online/remote multiplayer (players are co-located; buzzing is via
  shared-keyboard number keys 1–4).
- User accounts, persistence across sessions, leaderboards across games.
- Automatic answer-checking / NLP grading — a human host always judges.
- Mobile-native app. (Responsive browser layout only.)

## 4. User roles

| Role | Description | Capabilities |
|---|---|---|
| Host | Runs the laptop/screen, reads questions aloud, judges answers | Sees hidden answers, controls game flow, judges correct/wrong, can skip questions |
| Player | Competes for points | Buzzes in via assigned number key (1–4), answers verbally (host judges), enters wagers/written answers in Final Jeopardy |

## 5. System architecture & execution model

This is the section a spec for a "code pulled and executed in browser"
game must pin down explicitly, since it determines the security and
distribution model:

- **Build-time compilation, not runtime fetch.** Content is organized
  into self-contained **packs** — `packs/<name>/{categories/*.json,
  final_jeopardy.json, config.json}`. `build.py --pack <name>` validates
  a pack's files and injects them as inline `GAME_CONFIG` /
  `QUESTION_BANK` / `FINAL_QUESTION` JS constants into `template.html`,
  producing one static file per pack: `output/<name>_jeopardy_game.html`.
  (If only one pack exists, `--pack` may be omitted — it auto-resolves;
  `--list` shows all available packs.) The engine itself
  (`template.html`) carries **no topic-specific content** — branding,
  taglines, and questions all come from the active pack, which is what
  makes "build it once, replay it for any group/topic" possible.
- **At play time, the browser loads exactly one local HTML file.** No
  `fetch`, no CDN, no remote script execution, no CSP concerns — the
  "pulled and executed" code is pulled by the *author* at build time, not
  by the *browser* at run time.
- **Requirement:** the shipped artifact MUST be a single, self-contained
  HTML file with inline `<style>` and `<script>` — openable via
  `file://` with zero network dependency. Do not introduce runtime
  `fetch()` of remote category data; that would convert a trusted static
  asset into a live code-injection surface (arbitrary JSON → arbitrary
  strings rendered via `innerHTML`, see §9.3).
- **Rebuild trigger:** any edit to a pack's files or to `template.html`
  requires re-running `python3 build.py --pack <name>` to regenerate
  that pack's output HTML. The spec should call out that the build step
  is manual (no watch mode / CI in scope).
- **Starting a new pack** (new group/topic — friends, coworkers, kids,
  etc.) is just: copy a pack folder, replace its category JSON /
  final-question / config, run the build with the new `--pack` name. No
  engine code changes required — this is the core requirement that makes
  the game "generic."
### 5.1 Pack location tiers — committed vs. personal vs. private

The host needs to mix three kinds of content in practice: packs they're
happy to version-control and reuse, personal packs they want to keep
local but not fuss over paths for, and packs sensitive enough that they
shouldn't touch this repo at all. The build supports all three with the
*same* commands and output convention:

| Tier | Where it lives | Tracked by git? | How to build |
|---|---|---|---|
| **Shared/reusable** | `packs/<name>/` | Yes (default) | `--pack <name>` |
| **Personal, default location** | `packs/<name>.local/` | No — `.gitignore` matches the `.local` suffix on both the pack folder *and* its build output (`output/*.local_jeopardy_game.html`) | `--pack <name>.local` (no extra flags — same `./packs` dir) |
| **Fully external/private** | anywhere on disk | No — never enters the repo's working tree | `--packs-dir /path/to/packs --pack <name>` |

Concretely: keep `tamil_cinema` committed and shareable, drop a family
roast round at `packs/family_roast.local/` for quick reuse without
thinking about paths, and point a sensitive coworker pack at an
external private folder (`--packs-dir ~/Private/jeopardy-packs`) — all
playable via the identical `python3 build.py --pack <name>` /
`--list` workflow. The `--packs-dir` override and the `.local` naming
convention are both load-bearing requirements: removing either would
force sensitive content back into the default tracked path.

Build artifacts are content-bearing (the full question bank is inlined
as plain JS in the output HTML), which is *why* the `.local` ignore
rule has to cover `output/` too — ignoring the source pack alone would
still leak its content into git via the built file.

## 6. Content data spec

Each pack lives at `packs/<pack_name>/` and contains:

| File | Required? | Purpose |
|---|---|---|
| `categories/*.json` | Yes | Board content — one or more category files |
| `final_jeopardy.json` | No (placeholder used if absent) | Final round question |
| `config.json` | No (generic defaults used if absent) | Branding: title, subtitle, win taglines |

### 6.1 Category file format (`packs/<name>/categories/*.json`)

A file holds either a single category object or a list of category
objects:

```json
{
  "id": "unique_snake_case_id",
  "name": "🕶️ Display Name",
  "questions": [
    {"value": 200,  "q": "Question text?", "a": "Answer"},
    {"value": 400,  "q": "Question text?", "a": "Answer"},
    {"value": 600,  "q": "Question text?", "a": "Answer"},
    {"value": 800,  "q": "Question text?", "a": "Answer"},
    {"value": 1000, "q": "Question text?", "a": "Answer"}
  ]
}
```

**Validation rules (enforced by `build.py:validate_category`, build fails
loudly on violation):**

- `id` and `name` are required on every category.
- `questions` must be a non-empty list.
- Every question requires `value`, `q`, and `a`.
- `id` must be unique within a pack — `build.py` now rejects duplicate
  ids at build time with a clear error (collisions would otherwise
  collide in the `answered` tile-tracking map at runtime).

**Conventions (not currently enforced by code, but expected by the
board UI — should be promoted to validation):**

- Standard point tiers are `200 / 400 / 600 / 800 / 1000`. The board
  renders one tile per tier per category; a missing tier renders as a
  blank/disabled tile (`renderBoard`). Authors should supply all five.
- `name` may include an emoji prefix for visual flavor (the shipped
  `tamil_cinema` pack follows this convention; it's a style choice per
  pack, not an engine requirement).

### 6.2 Final Jeopardy file format (`packs/<name>/final_jeopardy.json`)

```json
{
  "category": "The Grand Stage",
  "q": "Question text…",
  "a": "Answer"
}
```

If absent, the build substitutes a placeholder question and prints a
warning — a pack can ship without one, but shouldn't ship to players
without one.

### 6.3 Branding/config file format (`packs/<name>/config.json`) — NEW

This is what makes the engine topic-agnostic: anything that used to be
hardcoded Tamil-cinema flavor text in `template.html` (the win-screen
taglines, specifically) now lives here, per pack.

```json
{
  "title":    "JEOPARDY!",
  "subtitle": "Office Trivia Night",
  "taglines": ["Nice one!", "Crushing it!", "..."]
}
```

- All fields optional — any field omitted (or the whole file, or the
  whole pack lacking a `config.json`) falls back to a neutral generic
  default baked into `build.py` (`DEFAULT_CONFIG`). A brand-new pack
  with zero config still produces a fully-playable, non-Tamil-themed
  game out of the box.
- `title`/`subtitle` drive the splash-screen logo and browser tab title;
  `taglines` is the pool the winner-screen randomly draws from
  (`pickTagline()` now reads `GAME_CONFIG.taglines` — no hardcoded
  strings remain in the engine).

### 6.4 Category pool vs. board size

The board always shows **6 categories**, randomly drawn from whatever
the active pack provides (`selectRandomCategories()` shuffles the pack's
full set and takes the first 6). **Requirement:** a pack must contain
≥ 6 valid categories or the board renders short/empty — this should be
a build-time check, not a runtime surprise (currently not enforced;
flag as a gap when authoring small/test packs).

## 7. Functional requirements — game flow

### 7.1 Setup screen

- Host selects player count: **2, 3, or 4** (no more, no fewer — UI only
  exposes these three buttons).
- Host enters a display name per player (max 20 chars, optional — blanks
  default to "Player N").
- Each player is bound to keyboard key `1`/`2`/`3`/`4` in input order and
  assigned a fixed color (gold / cyan / orange / purple) for the whole
  game.
- "Start Game" begins Round 1 with all scores at $0.

### 7.2 Board

- 6 categories × 5 point tiers ($200/$400/$600/$800/$1000) = 30 tiles.
- Clicking an unanswered tile opens that question; answered tiles show
  blank and are unclickable.
- Host may trigger Final Jeopardy at any time via the "⭐ Final Jeopardy"
  button — this is manual (the host decides when the board is "done"),
  not gated on all 30 tiles being cleared. **Open question (§12):** is
  early-trigger intentional, or should it require the board to be
  cleared first?

### 7.3 Question round — buzz-in & timing

1. Opening a tile shows: category, dollar value, question text, a 25-second
   countdown (bar + numeric), and the buzz-in prompt "Press your key
   (1/2/3/4) to buzz in!"
2. **Buzzing in:** any player not already locked out (see step 4) may
   press their assigned number key. First press wins; the timer freezes,
   that player's name + color are highlighted, and host judging controls
   appear.
3. **Host judges** the player's spoken answer:
   - **Correct →** value is **added** to that player's score; answer is
     revealed; tile marked answered; question closes on "Continue".
   - **Wrong →** value is **subtracted** from that player's score; that
     player is locked out for the remainder of *this* question
     (`wrongBuzzers`); if any players remain un-locked-out, buzzing
     re-opens with a fresh **15-second** timer and a prompt naming who
     can still ring in; if no players remain, the answer is revealed and
     the question closes unanswered-correctly.
4. **Timeout:** if nobody buzzes within the active window, the answer is
   revealed and the tile is marked answered — no score changes.
5. **Host controls available throughout:**
   - "👁 Host Answer" — toggles a host-only reveal of the correct answer
     (for the host's reference while judging; not shown to players'
     screen since there is only one shared screen — host must manage
     visibility/angle).
   - "Skip ✕" — abandons the question with no scoring, marks it answered,
     closes it.
6. Tiles cannot be revisited once marked answered (correct, wrong-with-no-
   remaining-buzzers, timeout, or skipped all mark it answered).

### 7.4 Scoring rules

- Starting score: $0 for every player.
- Correct buzz-in: **+ tile value**.
- Incorrect buzz-in: **− tile value** (scores can go negative; UI renders
  negative scores in red).
- No penalty for not buzzing.
- Scores persist across the whole board (no separate "Double Jeopardy"
  round with doubled values in the current build — single round only,
  despite the "Round 1" badge implying more could exist. **Open
  question:** is a Round 2 / Double Jeopardy in scope?).

### 7.5 Final Jeopardy

1. Host triggers it manually; current board question (if open) is closed
   first.
2. **Wager phase:** every player sees their current score and enters a
   wager between **$0 and their current score** (negative scores clamp
   wager range to $0–$0, i.e. they must wager $0). Wager input is clamped
   both by `min`/`max` HTML attributes and again in JS
   (`Math.min(Math.max(0, raw), Math.max(0, score))`) before being
   accepted.
3. **Question phase:** the single Final Jeopardy category + question is
   revealed; each player privately writes their answer in a text field
   (shared screen — same "host manages visibility" caveat as §7.3).
4. **Judging phase:** host reveals the correct answer and marks each
   player's written answer ✓ or ✗ individually:
   - ✓ → **+ wager**
   - ✗ → **− wager**
   - Each row locks after judging (buttons disable, row tinted).
5. Host clicks "Declare Winner" to proceed.

### 7.6 Winner screen

- Players are ranked by final score (descending); top 4 shown with medal
  icons (🥇🥈🥉4️⃣).
- Winner is announced by name with a randomly-chosen Tamil-cinema-themed
  tagline (8 options, e.g. "Thalaivar would be proud!").
- Confetti animation plays (120 pieces, randomized color/size/timing).
- Two replay options:
  - **"Play Again (New Categories)"** — same players, scores reset to
    $0, fresh random 6-category draw, round counter increments.
  - **"New Game (Change Players)"** — returns to setup screen to
    reconfigure player count/names entirely.

## 8. UI/UX requirements

- Visual theme: dark cinematic palette (gold/black), film-strip motifs,
  Tamil-cinema in-jokes in copy (taglines, category names).
- Layout responsive: board grid collapses from 6 to 3 columns at the
  defined mobile breakpoint (`template.html:307`); designed primarily for
  laptop/TV display, but should not break on tablet/phone if a host
  projects from one.
- All game-state transitions (setup → board → question → final → winner)
  are full-screen overlays/sections toggled via `display`, not page
  navigations — no reloads, no URL routing.
- Color-coding: each player has one fixed color used consistently across
  scoreboard, buzz-in highlight, wager rows, and final leaderboard.

## 9. Non-functional requirements

### 9.1 Portability
Must run from a local file (`file://…/jeopardy_game.html`) in any modern
evergreen browser (Chrome/Firefox/Safari/Edge) with zero network access
and zero install steps.

### 9.2 Performance
Single static HTML file; all 12 categories' worth of question data is
inlined at build time — page weight should stay small enough (low
hundreds of KB) to load instantly even on old hardware.

### 9.3 Security / trust model
Because category content is rendered via `innerHTML` (category names,
question text, answers, player names all interpolate directly into the
DOM), the **trust boundary is the JSON authoring step, not the browser
runtime**. Anyone who can place a file under `packs/<name>/` can inject
arbitrary HTML/script into that pack's built game. This is acceptable
for a single-author/trusted-author local game — and the pack model
*assumes* the person assembling a pack for "Friday's coworker quiz" is
the same person who'll run it. It would NOT be acceptable if this spec
were extended to let one party share/import another party's pack
unvetted — that would require sanitizing interpolated content (escape
before `innerHTML`, or switch to `textContent`) before going out of
scope of "trusted local build."

Note this is a distinct concern from §5.1's pack-location tiers:
§5.1 is about *confidentiality* (keeping sensitive question content out
of git history); this section is about *integrity* (whether rendered
content can carry executable payloads). Both matter, but the location
tiers do nothing to mitigate an injection risk, and sanitization does
nothing to keep content out of git — they're orthogonal and both apply.

### 9.4 Accessibility
Not currently addressed (no ARIA roles, no keyboard nav beyond the 1–4
buzzer binding, color is a primary differentiator for players with no
text fallback beyond the name label). Flag as a gap if accessibility is
a stated goal.

## 10. Acceptance criteria (sample — expand per feature during QA)

- [ ] Starting a 2/3/4-player game shows exactly that many scoreboard
      cards, each bound to keys 1…N respectively.
- [ ] Selecting a tile opens its question, starts a 25s countdown, and
      the bar shifts to the "warning" red gradient at ≤8s remaining.
- [ ] First valid keypress among 1–4 (matching an active player) locks in
      that buzzer; subsequent presses by others are ignored until
      judged.
- [ ] Marking an answer correct adds the tile value to the buzzed
      player's score and immediately reveals the answer.
- [ ] Marking an answer wrong subtracts the tile value, locks that player
      out, and — if others remain — restarts a 15s window naming the
      remaining eligible players.
- [ ] A fully-timed-out question reveals the answer with no score change
      and marks the tile answered.
- [ ] Skipping a question marks it answered with no score change.
- [ ] Final Jeopardy wager input cannot exceed the player's current score
      nor go below $0, including via direct input manipulation.
- [ ] Final Jeopardy judging correctly applies +/- wager per player and
      disables the row after judging.
- [ ] Winner screen ranks by final score correctly, including negative
      scores, and displays the top 4 with correct medals.
- [ ] "Play Again" resets scores/board but keeps players; "New Game"
      returns to setup with no residual player state.
- [ ] `python3 build.py --pack <name>` fails loudly (non-zero exit,
      clear message) on malformed category JSON (missing
      `id`/`name`/`questions`/per-question fields, empty `questions`,
      duplicate `id` within the pack).
- [ ] A pack with no `config.json` still builds and plays with neutral
      generic branding/taglines (no Tamil-cinema strings leak from the
      engine into an unrelated pack).
- [ ] `python3 build.py --list` enumerates every pack under `packs/`
      with its category count; `python3 build.py` auto-builds the only
      pack when exactly one exists, and errors with a pack list when
      more than one exists and `--pack` is omitted.

## 11. Open questions

1. Should reaching Final Jeopardy require the board to be cleared, or is
   host-discretion-to-trigger-anytime intentional (current behavior)?
2. Is a Double Jeopardy round (doubled values, second 6-category board)
   in scope for a future version, given the "Round N" badge already
   exists in the UI?
3. Should there be any sound design (buzzer SFX, correct/wrong stings,
   countdown tick) — currently silent?
4. Is there a need to persist game state (e.g. `localStorage`) so a game
   can survive an accidental reload?
5. Should category authoring get a lighter-weight tool/validator than
   hand-editing JSON + rerunning the Python build (`build.py --pack
   <name>`)?
6. Is sharing/importing packs between people ever in scope (vs. each
   host authoring their own)? If yes, §9.3's trust model needs to
   change — untrusted pack content would need sanitizing before render.

## 12. Out of scope (explicitly)

- Networked/remote play.
- Automatic answer grading.
- Persistent player profiles or cross-session stats.
- Sound/voice integration.
- Localization beyond the current English-with-Tamil-cinema-flavor copy.
