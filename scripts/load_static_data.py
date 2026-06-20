#!/usr/bin/env python
"""
scripts/load_static_data.py

Load and parse the static FanGraphs reference files from data/mlb/.
These files are manually downloaded (not fetched daily) and change weekly or less.

Files handled:
  data/mlb/splits_vs_LHP.txt          -- batter stats vs left-handed pitchers
  data/mlb/splits_vs_RHP.txt          -- batter stats vs right-handed pitchers
  data/mlb/splits_home.txt            -- batter stats in home games
  data/mlb/splits_away.txt            -- batter stats in away games
  data/mlb/pitchers_xfip_siera.txt    -- starter season xFIP, SIERA, K-BB% (2-yr blend)
  data/mlb/pitchers_last14.txt        -- starter stats last 14 days
  data/mlb/Bullpen.txt                -- all relievers with role, usage last 6 days
  data/mlb/park_factors_all.txt       -- park factors all conditions (3yr rolling)
  data/mlb/park_factors_roof_closed.txt -- park factors roof-closed only
  data/mlb/team_barrels.txt           -- team offensive Barrel% and HardHit% (FanGraphs export)
  data/mlb/lineup_tracker.txt        -- projected batting orders by date (FanGraphs roster resource)

Usage (standalone test):
    python scripts/load_static_data.py

Import usage:
    from scripts.load_static_data import load_splits_vs_lhp, fuzzy_match_player
"""

import csv
import difflib
import logging
from pathlib import Path

# ─────────────────────────────────────────────────────────────────────────────
# CONSTANTS
# ─────────────────────────────────────────────────────────────────────────────

# Root of the project (one level up from scripts/)
PROJECT_ROOT = Path(__file__).resolve().parent.parent

# All static MLB files live here
DATA_DIR = PROJECT_ROOT / "data" / "mlb"


# Fuzzy match cutoff — matches below this score are logged as warnings
FUZZY_CUTOFF = 0.85

# ─────────────────────────────────────────────────────────────────────────────
# TEAM CODE MAPPINGS
# FanGraphs uses different abbreviations from games.json (TheOddsAPI) for 6 teams.
# All other teams are identical in both systems.
# ─────────────────────────────────────────────────────────────────────────────

# FanGraphs team code → games.json abbreviation (for the 6 that differ)
_FG_TO_GAMES: dict[str, str] = {
    "ARI": "AZ",
    "KCR": "KC",
    "SDP": "SD",
    "SFG": "SF",
    "TBR": "TB",
    "WSN": "WAS",
}

# Reverse map: games.json abbreviation → FanGraphs code
_GAMES_TO_FG: dict[str, str] = {v: k for k, v in _FG_TO_GAMES.items()}

# FanGraphs park-factor file uses full team nicknames (e.g. "Rockies") —
# map these to games.json abbreviations so callers can look up by team abbr.
_PF_NAME_TO_GAMES_ABBR: dict[str, str] = {
    "Angels":    "LAA",
    "Astros":    "HOU",
    "Athletics": "ATH",
    "Blue Jays": "TOR",
    "Braves":    "ATL",
    "Brewers":   "MIL",
    "Cardinals": "STL",
    "Cubs":      "CHC",
    "D-backs":   "AZ",      # games.json uses AZ (not ARI)
    "Dodgers":   "LAD",
    "Giants":    "SF",      # games.json uses SF (not SFG)
    "Guardians": "CLE",
    "Mariners":  "SEA",
    "Marlins":   "MIA",
    "Mets":      "NYM",
    "Nationals": "WAS",     # games.json uses WAS (not WSN)
    "Orioles":   "BAL",
    "Padres":    "SD",      # games.json uses SD (not SDP)
    "Phillies":  "PHI",
    "Pirates":   "PIT",
    "Rangers":   "TEX",
    "Rays":      "TB",      # games.json uses TB (not TBR)
    "Red Sox":   "BOS",
    "Reds":      "CIN",
    "Rockies":   "COL",
    "Royals":    "KC",      # games.json uses KC (not KCR)
    "Tigers":    "DET",
    "Twins":     "MIN",
    "White Sox": "CHW",
    "Yankees":   "NYY",
}


def fg_to_games_abbr(fg_code: str) -> str:
    """Translate a FanGraphs team code to the games.json abbreviation."""
    return _FG_TO_GAMES.get(fg_code, fg_code)


def games_abbr_to_fg(games_abbr: str) -> str:
    """Translate a games.json team abbreviation to the FanGraphs team code."""
    return _GAMES_TO_FG.get(games_abbr, games_abbr)

# ─────────────────────────────────────────────────────────────────────────────
# LOGGING
# ─────────────────────────────────────────────────────────────────────────────

logging.basicConfig(
    level=logging.INFO,
    format="%(levelname)s  %(message)s",
)
logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────────────────────
# PRIVATE HELPERS
# ─────────────────────────────────────────────────────────────────────────────

def _parse_float(value: str) -> float | None:
    """Convert a string to float, return None if blank or non-numeric."""
    v = value.strip()
    if not v or v == "-":
        return None
    try:
        return float(v.replace(",", ""))
    except ValueError:
        return None


def _parse_pct(value: str) -> float | None:
    """Convert a percentage string like '24.8%' to 0.248. Returns None if blank."""
    v = value.strip().rstrip("%")
    if not v or v == "-":
        return None
    try:
        return round(float(v) / 100.0, 6)
    except ValueError:
        return None


def _load_tsv(filepath: Path) -> list[list[str]] | None:
    """
    Read a tab-separated file and return all lines as lists of strings.
    Returns None if the file is missing or unreadable (caller logs the warning).
    """
    if not filepath.exists():
        return None
    try:
        with open(filepath, encoding="utf-8") as fh:
            reader = csv.reader(fh, delimiter="\t")
            return [row for row in reader]
    except Exception as exc:
        logger.warning("Could not read %s: %s", filepath.name, exc)
        return None


def _batter_splits_file(filepath: Path) -> dict:
    """
    Parse any of the four batter-split files (vs LHP, vs RHP, home, away).
    All four share the same column layout:
      # | Name | Team | BB% | AVG | OBP | wRC+ | PA | K% | SLG | wOBA | OPS

    Returns dict keyed by player name (str):
      { pa, woba, wrc_plus, ops, k_pct, bb_pct, avg }
    """
    rows = _load_tsv(filepath)
    if rows is None:
        logger.warning("Missing file: %s — returning empty dict", filepath.name)
        return {}

    result = {}
    for row in rows[1:]:  # skip header row
        # Guard against short / blank rows
        if len(row) < 12:
            continue
        # Columns (0-indexed): 0=#, 1=Name, 2=Team, 3=BB%, 4=AVG, 5=OBP,
        #                       6=wRC+, 7=PA, 8=K%, 9=SLG, 10=wOBA, 11=OPS
        name = row[1].strip()
        if not name:
            continue
        result[name] = {
            "team":     row[2].strip(),   # FanGraphs team code — used for team-aggregate lookups
            "pa":       _parse_float(row[7]),
            "woba":     _parse_float(row[10]),
            "wrc_plus": _parse_float(row[6]),
            "ops":      _parse_float(row[11]),
            "k_pct":    _parse_pct(row[8]),
            "bb_pct":   _parse_pct(row[3]),
            "avg":      _parse_float(row[4]),
        }
    logger.info("Loaded %d batters from %s", len(result), filepath.name)
    return result


def _pitcher_file(filepath: Path) -> dict:
    """
    Parse either pitchers_xfip_siera.txt or pitchers_last14.txt.
    Both share the same column layout:
      # | Name | Team | K/9 | BB/9 | K-BB% | xFIP | SIERA | IP

    Returns dict keyed by player name (str):
      { k9, bb9, k_bb_pct, xfip, siera, ip }
    """
    rows = _load_tsv(filepath)
    if rows is None:
        logger.warning("Missing file: %s — returning empty dict", filepath.name)
        return {}

    result = {}
    for row in rows[1:]:  # skip header row
        if len(row) < 9:
            continue
        # Columns: 0=#, 1=Name, 2=Team, 3=K/9, 4=BB/9, 5=K-BB%, 6=xFIP, 7=SIERA, 8=IP
        name = row[1].strip()
        if not name:
            continue
        result[name] = {
            "k9":      _parse_float(row[3]),
            "bb9":     _parse_float(row[4]),
            "k_bb_pct": _parse_pct(row[5]),
            "xfip":    _parse_float(row[6]),
            "siera":   _parse_float(row[7]),
            "ip":      _parse_float(row[8]),
        }
    logger.info("Loaded %d pitchers from %s", len(result), filepath.name)
    return result


# ─────────────────────────────────────────────────────────────────────────────
# PUBLIC LOAD FUNCTIONS — batter splits
# ─────────────────────────────────────────────────────────────────────────────

def load_splits_vs_lhp() -> dict:
    """Batter stats vs left-handed pitchers. Keyed by player name."""
    return _batter_splits_file(DATA_DIR / "splits_vs_LHP.txt")


def load_splits_vs_rhp() -> dict:
    """Batter stats vs right-handed pitchers. Keyed by player name."""
    return _batter_splits_file(DATA_DIR / "splits_vs_RHP.txt")


def load_splits_home() -> dict:
    """Batter stats in home games. Keyed by player name."""
    return _batter_splits_file(DATA_DIR / "splits_home.txt")


def load_splits_away() -> dict:
    """Batter stats in away games. Keyed by player name."""
    return _batter_splits_file(DATA_DIR / "splits_away.txt")


# ─────────────────────────────────────────────────────────────────────────────
# PUBLIC LOAD FUNCTIONS — pitcher stats
# ─────────────────────────────────────────────────────────────────────────────

def load_pitchers_season() -> dict:
    """Starter xFIP/SIERA/K-BB% (2-year blended sample). Keyed by player name."""
    return _pitcher_file(DATA_DIR / "pitchers_xfip_siera.txt")


def load_pitchers_last14() -> dict:
    """Starter stats over the last 14 days. Keyed by player name."""
    return _pitcher_file(DATA_DIR / "pitchers_last14.txt")


def _pitcher_extra_col(filepath: Path, col_idx: int) -> dict:
    """
    Extract a single numeric column from a pitcher TSV file.
    Returns dict keyed by player name (str) → float.
    Rows with a missing or non-numeric value are silently skipped.

    Column layout (both pitcher files share this):
      0=#  1=Name  2=Team  3=K/9  4=BB/9  5=K-BB%  6=xFIP  7=SIERA  8=IP
      9=gmLI  10=Stuff+
    """
    rows = _load_tsv(filepath)
    if rows is None:
        logger.warning("Missing file: %s — returning empty dict", filepath.name)
        return {}

    result = {}
    for row in rows[1:]:   # skip header row
        if len(row) <= col_idx:
            continue
        name = row[1].strip() if len(row) > 1 else ""
        if not name:
            continue
        val = _parse_float(row[col_idx])
        if val is not None:
            result[name] = val

    logger.info(
        "Loaded %d entries (col %d) from %s", len(result), col_idx, filepath.name
    )
    return result


def load_stuff_plus() -> dict:
    """
    Pitcher Stuff+ (season blended). Keyed by player name → float.
    Source: pitchers_xfip_siera.txt, column 10.
    Stuff+ measures raw stuff quality vs league average (100 = average).
    """
    return _pitcher_extra_col(DATA_DIR / "pitchers_xfip_siera.txt", 10)


def load_gm_li() -> dict:
    """
    Pitcher gmLI last-14-days (average leverage index at game entry).
    Keyed by player name → float.
    Source: pitchers_last14.txt, column 9.
    gmLI > 1.0 indicates high-leverage usage (closer/setup territory).
    """
    return _pitcher_extra_col(DATA_DIR / "pitchers_last14.txt", 9)


# ─────────────────────────────────────────────────────────────────────────────
# PUBLIC LOAD FUNCTIONS — bullpen
# ─────────────────────────────────────────────────────────────────────────────

def load_bullpen() -> dict:
    """
    Parse Bullpen.txt into a dict keyed by 3-letter team code (str).
    Each value is a list of reliever dicts:
      { name, throws, role, usage_last6, pitches_last, ip_last, era,
        k_pct, bb9, sv, hld }

    usage_last6 is a list of 6 strings (Fri→Sun dates) showing pitch counts or
    blank/result codes for each day the pitcher appeared. Example: ['', '16 (H)', '', '', '', '']

    Bullpen.txt structure (FanGraphs export):
      [global header row]                   ← skip
      [team-name separator row]             ← skip  (e.g. "Athletics   Pitcher Usage ...")
      [header row repeated]                 ← skip
      [player rows with real TEAM codes]    ← keep
      [blank line between teams]            ← skip
    """
    filepath = DATA_DIR / "Bullpen.txt"
    rows = _load_tsv(filepath)
    if rows is None:
        logger.warning("Missing file: Bullpen.txt — returning empty dict")
        return {}

    # Column indices in the player data rows:
    # 0=TEAM, 1=PLAYER, 2=THR, 3=PROJECTED ROLE,
    # 4=Fri, 5=Thu, 6=Wed, 7=Tue, 8=Mon, 9=Sun   (last 6 day usage columns)
    # 10=P (pitches last appearance), 11=IP (innings last appearance),
    # 12=G (season games), 13=IP (season), 14=ERA,
    # 15=Sv, 16=HLD, 17=SD, 18=MD,
    # 19=SwStr%, 20=K%, 21=K/9, 22=BB%, 23=BB/9

    # Extract day labels from the first header row (columns 4-9):
    # e.g. "Fri 6/5", "Thu 6/4", "Wed 6/3" ... → ["Fri", "Thu", "Wed", "Tue", "Mon", "Sun"]
    day_labels = ["Fri", "Thu", "Wed", "Tue", "Mon", "Sun"]  # fallback
    if rows and len(rows[0]) >= 10:
        day_labels = []
        for i in range(4, 10):
            raw = rows[0][i].strip()
            day_labels.append(raw.split()[0] if raw else f"D{i - 3}")

    result = {}

    # A "real" player row has a 3-letter (or ~3-char) uppercase team code in col 0
    # and a non-empty player name in col 1.
    # We detect non-player rows by:
    #   - col 0 == "TEAM"   → repeated header, skip
    #   - col 1 blank       → team separator row, skip
    #   - row shorter than 20 columns → incomplete / separator, skip

    for row in rows:
        if len(row) < 20:
            continue
        team_code = row[0].strip()
        player_name = row[1].strip()

        # Skip header rows and separator rows
        if team_code == "TEAM" or not player_name or not team_code:
            continue

        # Normalise team code — sometimes FanGraphs uses full names in separator rows
        # but player rows always have short codes (ATH, BAL, etc.)
        if len(team_code) > 5:
            # Looks like a full team name that slipped through — skip it
            continue

        reliever = {
            "name":        player_name,
            "throws":      row[2].strip(),
            "role":        row[3].strip(),
            # Last-6-day usage: list of 6 values (blank string = didn't pitch)
            "usage_last6": [row[i].strip() for i in range(4, 10)],
            # Last appearance: pitch count and innings
            "pitches_last": _parse_float(row[10]),
            "ip_last":      _parse_float(row[11]),
            # Season totals
            "era":  _parse_float(row[14]),
            "sv":   _parse_float(row[15]),
            "hld":  _parse_float(row[16]),
            # Shutdowns / Meltdowns — raw high-leverage outcome counts
            # (SD = appearance with WPA >= 0.06; MD = appearance with WPA <= -0.06).
            # A strong raw proxy for how often a reliever is used in, and wins/loses,
            # leverage spots. Ship raw — each model draws its own conclusion.
            "sd":   _parse_float(row[17]),
            "md":   _parse_float(row[18]),
            # Rate stats
            "swstr": _parse_pct(row[19]),
            "k_pct": _parse_pct(row[20]),
            "bb9":   _parse_float(row[23]),
        }

        # Group by team code
        result.setdefault(team_code, []).append(reliever)

    # Remap FanGraphs team codes to games.json abbreviations (6 teams differ).
    # This lets build_prompt.py look up by the same abbr used in games.json.
    remapped: dict = {}
    for fg_code, relievers in result.items():
        games_abbr = fg_to_games_abbr(fg_code)
        remapped[games_abbr] = relievers

    # Store day labels as metadata so callers can label the usage columns correctly.
    remapped["_meta"] = {"day_labels": day_labels}

    logger.info(
        "Loaded bullpen data for %d teams (%d total relievers) from Bullpen.txt",
        len(remapped) - 1,          # subtract the _meta entry
        sum(len(v) for k, v in remapped.items() if k != "_meta"),
    )
    return remapped


# ─────────────────────────────────────────────────────────────────────────────
# PUBLIC LOAD FUNCTIONS — park factors
# ─────────────────────────────────────────────────────────────────────────────

def _park_factors_file(filepath: Path) -> dict:
    """
    Parse either park_factors_all.txt or park_factors_roof_closed.txt.
    Column layout:
      Rk. | Team | Venue | Year | Park Factor | wOBAcon | xwOBAcon | BACON |
      xBACON | HardHit | R | OBP | H | 1B | 2B | 3B | HR | BB | SO | PA

    Returns dict keyed by team name (str, e.g. 'Rockies', 'D-backs'):
      { park_factor, hr_factor, r_factor, woba_factor }

    Note: FanGraphs park factor files use full team name, not 3-letter code.
    The caller resolves team-name → code via the games.json team data.
    """
    rows = _load_tsv(filepath)
    if rows is None:
        logger.warning("Missing file: %s — returning empty dict", filepath.name)
        return {}

    result = {}
    for row in rows[1:]:  # skip header
        if len(row) < 17:
            continue
        team_name = row[1].strip()
        if not team_name or team_name == "Team":
            continue
        # Translate FanGraphs nickname ("Rockies") to games.json abbreviation ("COL")
        games_abbr = _PF_NAME_TO_GAMES_ABBR.get(team_name)
        if not games_abbr:
            logger.debug("Park factors: unknown team name '%s' — skipping", team_name)
            continue
        # Columns: 4=Park Factor (overall), 10=R, 16=HR, 5=wOBAcon
        result[games_abbr] = {
            "team_name":    team_name,                # keep for display
            "park_factor":  _parse_float(row[4]),     # overall run environment index (100 = neutral)
            "hr_factor":    _parse_float(row[16]),     # HR index
            "r_factor":     _parse_float(row[10]),     # runs index
            "woba_factor":  _parse_float(row[5]),      # wOBAcon index
        }
    logger.info("Loaded park factors for %d teams from %s", len(result), filepath.name)
    return result


def load_park_factors() -> dict:
    """Park factors all conditions (3yr rolling). Keyed by team name."""
    return _park_factors_file(DATA_DIR / "park_factors_all.txt")


def load_park_factors_roof_closed() -> dict:
    """Park factors roof-closed only. Keyed by team name (8 retractable-roof teams)."""
    return _park_factors_file(DATA_DIR / "park_factors_roof_closed.txt")


# ─────────────────────────────────────────────────────────────────────────────
# PUBLIC LOAD FUNCTIONS -- team barrel%
# ─────────────────────────────────────────────────────────────────────────────

def load_team_barrels() -> dict:
    """
    Load team offensive Barrel% and HardHit% from static FanGraphs export.

    Source file: data/mlb/team_barrels.txt
    Format: TSV with columns  #  Team  Barrel%  HardHit%
    Values are percentage strings (e.g. "9.0%") -- stripped to floats.
    FanGraphs abbreviations are remapped via _FG_TO_GAMES (e.g. WSN->WAS).

    Returns dict keyed by games.json team abbreviation:
        { "NYY": {"barrel_pct": 10.6, "hardhit_pct": 43.2}, ... }
    Returns empty dict if file not found or parse fails.
    """
    filepath = DATA_DIR / "team_barrels.txt"
    if not filepath.exists():
        print("WARNING: data/mlb/team_barrels.txt not found -- team barrel% unavailable")
        return {}

    result = {}
    try:
        rows = _load_tsv(filepath)
    except Exception as exc:
        print(f"WARNING: could not read team_barrels.txt: {exc}")
        return {}

    if not rows:
        print("WARNING: team_barrels.txt is empty")
        return {}

    for row in rows[1:]:  # skip header row
        # Expected columns: 0=rank#, 1=Team, 2=Barrel%, 3=HardHit%
        # Guard against short or blank rows
        if len(row) < 4:
            continue
        team_fg = row[1].strip()
        if not team_fg or team_fg == "Team":
            continue

        brl_raw  = row[2].strip().rstrip("%")
        hh_raw   = row[3].strip().rstrip("%")

        try:
            brl_f = round(float(brl_raw), 1)
        except (ValueError, TypeError):
            print(f"WARNING: team_barrels.txt -- could not parse Barrel% for {team_fg!r}: {row[2]!r}")
            continue

        try:
            hh_f = round(float(hh_raw), 1)
        except (ValueError, TypeError):
            print(f"WARNING: team_barrels.txt -- could not parse HardHit% for {team_fg!r}: {row[3]!r}")
            hh_f = None

        # Remap FanGraphs abbreviation to games.json abbreviation
        games_abbr = _FG_TO_GAMES.get(team_fg, team_fg)

        entry: dict = {"barrel_pct": brl_f}
        if hh_f is not None:
            entry["hardhit_pct"] = hh_f
        result[games_abbr] = entry

    logger.info("Loaded team barrel%% for %d teams from team_barrels.txt", len(result))
    return result


# ─────────────────────────────────────────────────────────────────────────────
# PUBLIC LOAD FUNCTIONS — lineup tracker (projected batting orders)
# ─────────────────────────────────────────────────────────────────────────────

def load_lineup_tracker(target_date: str | None = None) -> dict:
    """
    Parse lineup_tracker.txt — FanGraphs roster-resource export.

    The file has one block per team, separated by repeated 'Name\\tRole\\t...'
    header rows. Each data row is a player with columns:
      Name | Role (1-9=batting slot, Bench/IL/AAA/DFA) | Ovr | Last 7 Days |
      {dated columns: 'POS ( slot )' or blank/IL/AAA/INJ...}

    The file does NOT embed team codes, so we resolve them by cross-referencing
    the first few starters in each block against splits_vs_LHP.txt (which has a
    FanGraphs TEAM column per player).

    Args:
        target_date: The date column to extract, formatted as 'Wed 6/18' (matching
                     the column headers). If None, uses the first (most recent) column.

    Returns dict keyed by games.json team abbreviation (str):
      {
        "LAA": {
          "opponent_hand": "L",          # "L" or "R" (from column header)
          "starters": [                  # ordered 1–9
            {"slot": 1, "name": "Zach Neto", "pos": "SS"},
            ...
          ],
          "bench": [{"name": "...", "status": "Bench"}],
          "il":    [{"name": "...", "status": "IL"}],
        },
        ...
        "_meta": {"target_date": "Wed 6/18", "source": "lineup_tracker.txt"}
      }

    If lineup_tracker.txt is missing, returns {}.
    If a block's team cannot be resolved, it is logged and skipped.
    """
    filepath = DATA_DIR / "lineup_tracker.txt"
    rows = _load_tsv(filepath)
    if rows is None:
        logger.warning("Missing file: lineup_tracker.txt — returning empty dict")
        return {}

    # ── Step 1: split into per-team blocks ──────────────────────────────────
    # A block boundary is any row where col[0].strip() == "Name".
    # FanGraphs repeats the header row twice at each block start — we skip dupes.
    blocks: list[list[list[str]]] = []  # list of blocks; each block = list of rows
    current_block: list[list[str]] = []
    last_was_header = False

    for row in rows:
        is_header = (len(row) >= 1 and row[0].strip() == "Name")
        if is_header:
            if not last_was_header:
                # First header of a new block — save the old block if non-empty
                if current_block:
                    blocks.append(current_block)
                current_block = [row]  # store header so we can read date columns
            else:
                # Second (duplicate) header — skip it, keep current_block header
                pass
            last_was_header = True
        else:
            last_was_header = False
            current_block.append(row)

    if current_block:
        blocks.append(current_block)

    # ── Step 2: load a player→FG-team mapping from splits for team resolution ──
    # splits_vs_LHP is reliable: includes all active MLB batters with their team code.
    _splits = _batter_splits_file(DATA_DIR / "splits_vs_LHP.txt")
    # build {player_name_lower: fg_team_code}
    _player_team: dict[str, str] = {
        k.lower(): v["team"] for k, v in _splits.items() if v.get("team")
    }

    # ── Step 3: parse each block ─────────────────────────────────────────────
    result: dict = {}

    for block in blocks:
        if not block:
            continue

        # The first row of the block is the header — extract date column indices.
        header = block[0]
        # Columns: 0=Name 1=Role 2=Ovr 3=Last7Days 4=col4 5=col5 ...
        # Dated columns start at index 4.
        date_cols = header[4:] if len(header) > 4 else []

        # Find the target column index within the date_cols list.
        target_col_idx: int | None = None
        target_col_label: str = ""
        opp_hand: str = ""

        if date_cols:
            if target_date:
                # Find by partial match (e.g. "Wed 6/18" matches "Wed 6/18 vs. R")
                for i, col in enumerate(date_cols):
                    if target_date in col:
                        target_col_idx = i
                        target_col_label = col.strip()
                        break
            if target_col_idx is None:
                # Fall back to first dated column (most recent)
                target_col_idx = 0
                target_col_label = date_cols[0].strip()

            # Extract opponent handedness from column header: "Wed 6/18 vs. L" → "L"
            if "vs. L" in target_col_label:
                opp_hand = "L"
            elif "vs. R" in target_col_label:
                opp_hand = "R"

        data_rows = block[1:]

        # ── Resolve team for this block ──────────────────────────────────────
        fg_team: str | None = None
        for row in data_rows:
            if len(row) < 2:
                continue
            role = row[1].strip()
            # Only use active starters (slot 1-9) for team resolution
            if role.isdigit() and 1 <= int(role) <= 9:
                name = row[0].strip().lower()
                found = _player_team.get(name)
                if found:
                    fg_team = found
                    break

        if not fg_team:
            logger.warning(
                "lineup_tracker: could not resolve team for a block (first player: %r) — skipping",
                data_rows[0][0] if data_rows else "?"
            )
            continue

        # Remap FG code → games.json abbreviation
        games_abbr = fg_to_games_abbr(fg_team)

        # ── Parse players ────────────────────────────────────────────────────
        starters: list[dict] = []
        bench:    list[dict] = []
        il:       list[dict] = []

        for row in data_rows:
            if len(row) < 2:
                continue
            name = row[0].strip()
            role = row[1].strip()
            if not name:
                continue

            # Get the value from the target date column (absolute index = 4 + target_col_idx)
            cell = ""
            if target_col_idx is not None:
                abs_idx = 4 + target_col_idx
                cell = row[abs_idx].strip() if len(row) > abs_idx else ""

            # Parse cell: "SS ( 1 )" → pos="SS", slot=1 | "IL"/"AAA"/"INJ" → status
            pos = ""
            slot: int | None = None
            cell_upper = cell.upper()

            if "(" in cell and ")" in cell:
                # Format: "POS ( N )"
                try:
                    pos_part = cell[:cell.index("(")].strip()
                    slot_part = cell[cell.index("(") + 1: cell.index(")")].strip()
                    pos = pos_part
                    slot = int(slot_part)
                except (ValueError, IndexError):
                    pass

            if role.isdigit() and 1 <= int(role) <= 9:
                # Starters: use the role column as the expected slot (more stable
                # than the per-date cell which can occasionally be blank on off-days).
                starters.append({
                    "slot": int(role),
                    "name": name,
                    "pos":  pos or "?",          # position from today's cell
                    "today_cell": cell or "—",   # raw cell value for transparency
                })
            elif role == "Bench":
                bench.append({"name": name, "today_cell": cell or "—"})
            elif role in ("IL", "AAA", "DFA", "INJ", "SUSP"):
                il.append({"name": name, "status": role, "today_cell": cell or "—"})
            # Players with a team-code role (traded away / org assignment) are skipped

        # Sort starters by slot number
        starters.sort(key=lambda p: p["slot"])

        result[games_abbr] = {
            "opponent_hand": opp_hand,
            "target_date":   target_col_label,
            "starters":      starters,
            "bench":         bench,
            "il":            il,
        }

    result["_meta"] = {
        "target_date": target_date or "(most recent column)",
        "source":      "lineup_tracker.txt",
    }

    logger.info(
        "Loaded projected lineups for %d teams from lineup_tracker.txt",
        len(result) - 1,
    )
    return result


# ─────────────────────────────────────────────────────────────────────────────
# FUZZY NAME MATCHING
# ─────────────────────────────────────────────────────────────────────────────

def fuzzy_match_player(name: str, name_dict: dict, cutoff: float = FUZZY_CUTOFF) -> str | None:
    """
    Look up a player name in name_dict. Tries exact match first, then fuzzy.

    Returns the best matching key from name_dict, or None if no match above cutoff.
    Logs a WARNING for any match that required fuzzy logic (score < 0.85 by default),
    so the caller can audit it.

    Args:
        name:      The name to look up (e.g. from games.json).
        name_dict: A dict whose keys are player names (e.g. from load_splits_vs_lhp()).
        cutoff:    Minimum similarity score (0–1). Matches below this return None.

    Usage:
        splits = load_splits_vs_lhp()
        key = fuzzy_match_player("Shohei Ohtani", splits)
        if key:
            print(splits[key])
    """
    if not name:
        return None

    # 1. Exact match — fast path, no logging needed
    if name in name_dict:
        return name

    # 2. Case-insensitive exact match
    name_lower = name.lower()
    for key in name_dict:
        if key.lower() == name_lower:
            return key

    # 3. Fuzzy match via difflib
    candidates = list(name_dict.keys())
    matches = difflib.get_close_matches(name, candidates, n=1, cutoff=cutoff)
    if matches:
        best = matches[0]
        # Calculate actual score to decide whether to log a warning
        score = difflib.SequenceMatcher(None, name, best).ratio()
        if score < 0.85:
            logger.warning(
                "Fuzzy name match: '%s' → '%s' (score=%.2f) — verify this is correct",
                name, best, score,
            )
        else:
            logger.debug("Fuzzy name match: '%s' → '%s' (score=%.2f)", name, best, score)
        return best

    # No match found above cutoff
    logger.debug("No fuzzy match found for '%s' (cutoff=%.2f)", name, cutoff)
    return None


# ─────────────────────────────────────────────────────────────────────────────
# STANDALONE TEST — run each loader and print 3 sample rows
# ─────────────────────────────────────────────────────────────────────────────

def _print_samples(label: str, data: dict, n: int = 3):
    """Print n sample entries from a dict in a readable format."""
    print(f"\n{'-' * 60}")
    print(f"  {label}  ({len(data)} entries)")
    print(f"{'-' * 60}")
    for i, (key, value) in enumerate(data.items()):
        if i >= n:
            break
        print(f"  {key!r:30s}  ->  {value}")


if __name__ == "__main__":
    print("\n=== load_static_data.py — self-test ===\n")

    # ── Batter splits ──────────────────────────────────────────────────────────
    _print_samples("splits_vs_LHP",  load_splits_vs_lhp())
    _print_samples("splits_vs_RHP",  load_splits_vs_rhp())
    _print_samples("splits_home",    load_splits_home())
    _print_samples("splits_away",    load_splits_away())

    # ── Pitcher stats ──────────────────────────────────────────────────────────
    _print_samples("pitchers_season (xFIP/SIERA)", load_pitchers_season())
    _print_samples("pitchers_last14",              load_pitchers_last14())
    _print_samples("stuff_plus",                   load_stuff_plus())
    _print_samples("gm_li (last 14 days)",         load_gm_li())

    # ── Bullpen ────────────────────────────────────────────────────────────────
    bullpen = load_bullpen()
    print(f"\n{'-' * 60}")
    print(f"  Bullpen  ({len(bullpen)} teams)")
    print(f"{'-' * 60}")
    for team_code, relievers in list(bullpen.items())[:3]:
        print(f"\n  Team: {team_code}  ({len(relievers)} relievers)")
        for r in relievers[:2]:
            print(f"    {r}")

    # ── Park factors ──────────────────────────────────────────────────────────
    _print_samples("park_factors_all",          load_park_factors())
    _print_samples("park_factors_roof_closed",  load_park_factors_roof_closed())

    # ── Team barrel% ──────────────────────────────────────────────────────────
    _print_samples("team_barrels",              load_team_barrels())

    # ── Fuzzy match demo ──────────────────────────────────────────────────────
    print(f"\n{'-' * 60}")
    print("  fuzzy_match_player -- demo")
    print(f"{'-' * 60}")
    season_pitchers = load_pitchers_season()
    test_names = [
        "Aaron Nola",          # exact match expected
        "Aron Nola",           # typo — should fuzzy-match
        "Zack Wheeler",        # exact or near-exact
        "Completely Unknown",  # should return None
    ]
    for test in test_names:
        result_key = fuzzy_match_player(test, season_pitchers)
        if result_key:
            print(f"  lookup({test!r:25s}) -> {result_key!r}")
        else:
            print(f"  lookup({test!r:25s}) -> NO MATCH")

    print("\n=== Done ===\n")
