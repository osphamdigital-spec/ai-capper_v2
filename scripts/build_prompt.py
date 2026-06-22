#!/usr/bin/env python
"""
scripts/build_prompt.py

Reads games.json for a given sport and date, and writes a complete
betting analysis prompt to daily/{sport}/{date}/prompt.md.

The prompt is designed to be pasted directly into any AI model
(ChatGPT, Claude, Gemini, Grok, DeepSeek, Kimi, Manus) with zero editing.

The AI's response format is standardised so that log_picks.py can parse
every pick automatically — game, side, price, units, edge, reason.

Usage:
    python scripts/build_prompt.py --sport mlb
    python scripts/build_prompt.py --sport mlb --date 2026-06-02

Reads:
    data/{sport}/{date}/games.json

Writes:
    daily/{sport}/{date}/prompt.md
"""

import argparse
import glob as _glob
import json
import re
import sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from tz_util import ET

# Load static FanGraphs data (splits, advanced pitcher stats, bullpen, park factors).
# These files live in data/mlb/ and are manually refreshed weekly.
# If the import fails (e.g., wrong working directory), all static blocks are silently skipped.
try:
    _SCRIPTS_DIR = Path(__file__).resolve().parent
    if str(_SCRIPTS_DIR) not in sys.path:
        sys.path.insert(0, str(_SCRIPTS_DIR))
    from load_static_data import (
        load_splits_vs_lhp,
        load_splits_vs_rhp,
        load_splits_home,
        load_splits_away,
        load_pitchers_season,
        load_pitchers_last14,
        load_stuff_plus,
        load_pitchers_season_batted_ball,
        load_bullpen,
        load_park_factors,
        load_park_factors_roof_closed,
        load_team_barrels,
        load_lineup_tracker,
        fuzzy_match_player,
        games_abbr_to_fg,
    )
    _STATIC_DATA_AVAILABLE = True
except ImportError as _e:
    _STATIC_DATA_AVAILABLE = False
    print(f"  NOTE: load_static_data import failed ({_e}) -- static blocks will be omitted")




# ─────────────────────────────────────────────────────────────────────────────
# CONSTANTS
# ─────────────────────────────────────────────────────────────────────────────

# Display label for each sport code — shown in the prompt header and instructions.
# Add new sports here as we expand beyond MLB.
SPORT_LABELS = {
    "mlb":   "MLB",
    "nba":   "NBA",
    "nhl":   "NHL",
    "nfl":   "NFL",
    "ncaaf": "NCAAF",
    "ncaab": "NCAAB",
}

# The "spread" market has different names in different sports.
# Baseball: Run Line (+/- 1.5 runs)
# Hockey:   Puck Line (+/- 1.5 goals)
# Basketball/Football: Spread (variable points)
# We use the sport-correct label in the prompt so the AI understands the market.
SPREAD_LABEL = {
    "mlb":   "Run Line",
    "nba":   "Spread",
    "nhl":   "Puck Line",
    "nfl":   "Spread",
    "ncaaf": "Spread",
    "ncaab": "Spread",
}

# Section divider written to the .md file with utf-8 encoding so it displays correctly.
# Never printed to the Windows console — that would trigger a cp1252 encoding error.
DIVIDER = "═" * 55  # ═══════════════════════════════════════════════════════


# ─────────────────────────────────────────────────────────────────────────────
# FORMATTING HELPERS
# ─────────────────────────────────────────────────────────────────────────────

def today_et() -> str:
    """Return today's date in US Eastern Time as YYYY-MM-DD."""
    return datetime.now(ET).strftime("%Y-%m-%d")


def fmt_american(price: int | None) -> str:
    """
    Format an American odds price with an explicit +/- sign.
    The AI needs to read the sign clearly — "-128" not "128", "+109" not "109".
    Returns "—" if the price is missing (data gap, not a bug).

    Examples: 109 -> "+109"   -128 -> "-128"   None -> "—"
    """
    if price is None:
        return "—"  # em dash
    return f"+{price}" if price > 0 else str(price)


def fmt_line(point: float | None) -> str:
    """
    Format a spread/run-line point value with an explicit +/- sign.
    Separate from fmt_american because point values are floats (1.5, -1.5)
    while odds prices are ints (-199, +170).

    Examples: 1.5 -> "+1.5"   -1.5 -> "-1.5"   None -> "?"
    """
    if point is None:
        return "?"
    # Show as integer if it's a whole number (e.g. 2.0 -> "+2"), else keep decimal
    formatted = int(point) if point == int(point) else point
    return f"+{formatted}" if point > 0 else str(formatted)


def fmt_time(commence_et: str) -> str:
    """
    Convert an ISO 8601 ET timestamp to a readable 12-hour time string.
    "2026-06-02T19:16:00-04:00" -> "7:16 PM"

    Uses manual arithmetic rather than strftime %-I / %#I because those
    format codes are platform-specific (Linux vs Windows) and cause crashes.
    """
    try:
        dt     = datetime.fromisoformat(commence_et)
        hour   = dt.hour
        minute = dt.minute
        period = "AM" if hour < 12 else "PM"
        hour12 = hour % 12 or 12   # 0 -> 12 (midnight), 13 -> 1, etc.
        return f"{hour12}:{minute:02d} {period}"
    except Exception:
        # Fallback: slice raw HH:MM from the ISO string
        return commence_et[11:16]


def fmt_pitcher(pitcher: dict | None, side: str) -> str:
    """
    Format one pitcher line for the prompt.

    When advanced Savant stats are present (fetch_pitcher_advanced.py has run),
    uses a pipe-separated format showing xERA, K/9, Hard Hit %, Barrel %:
      Away: Gausman (RHP) — 4-3 | ERA 3.36 xERA 3.33 | K/9 8.4 HH% 36.6 Brl% 7.4 | 75.0 IP

    Without advanced stats falls back to the legacy compact format:
      Away: Gausman (RHP) — 4-3, 3.36 ERA, 1.09 WHIP, 66 K, 75.0 IP

    Small-sample note appended when IP < 40.
    """
    if not pitcher or not pitcher.get("name"):
        return f"  {side}: TBD"

    name = pitcher["name"]
    hand = pitcher.get("hand") or "?"
    w    = pitcher.get("wins")
    l    = pitcher.get("losses")
    wl   = f"{w}-{l}" if (w is not None and l is not None) else "?-?"
    ip   = pitcher.get("innings_pitched")

    has_advanced = any(
        pitcher.get(k) is not None
        for k in ("xera", "hard_hit_pct", "barrel_pct", "k_per_9")
    )

    if has_advanced:
        # ── Advanced format (Savant stats available) ──────────────────────────
        def _f(v, spec=".2f"):
            return format(v, spec) if v is not None else "—"   # em dash for missing

        # FIP sits between ERA and xERA: ERA is raw, FIP is defence-independent,
        # xERA is Statcast contact-quality based. Omit FIP entirely if None —
        # never show a placeholder, a missing FIP is less confusing than "— FIP".
        fip      = pitcher.get("fip")
        fip_part = f" FIP {_f(fip)}" if fip is not None else ""
        era_block  = f"ERA {_f(pitcher.get('era'))}{fip_part} xERA {_f(pitcher.get('xera'))}"
        whiff = pitcher.get("whiff_rate")
        whiff_part = f" Whiff: {_f(whiff, '.1f')}%" if whiff is not None else ""
        rate_block = (
            f"K/9 {_f(pitcher.get('k_per_9'), '.1f')}{whiff_part} "
            f"HH% {_f(pitcher.get('hard_hit_pct'), '.1f')} "
            f"Brl% {_f(pitcher.get('barrel_pct'), '.1f')}"
        )
        ip_block = f"{ip} IP" if ip is not None else "— IP"

        line = (
            f"  {side}: {name} ({hand}HP) — {wl} | "
            f"{era_block} | {rate_block} | {ip_block}"
        )
        if pitcher.get("small_sample"):
            line += "  [small sample — treat ERA with caution]"
        return line

    else:
        # ── Legacy format (advanced stats not yet fetched) ────────────────────
        stats = []
        if pitcher.get("era")            is not None:
            stats.append(f"{pitcher['era']:.2f} ERA")
        if pitcher.get("whip")           is not None:
            stats.append(f"{pitcher['whip']:.2f} WHIP")
        if pitcher.get("strikeouts")     is not None:
            stats.append(f"{pitcher['strikeouts']} K")
        if ip is not None:
            stats.append(f"{ip} IP")
        stats_str = ", ".join(stats) if stats else "no stats yet"
        return f"  {side}: {name} ({hand}HP) — {wl}, {stats_str}"


def fmt_pitcher_flags(pitcher: dict | None) -> list:
    """
    Return a list of warning lines for any data-quality flags set on a pitcher
    by the most recent fetch_pitchers.py run. Called BEFORE fmt_pitcher() in the
    STARTING PITCHERS block so the warning appears directly above the stat line.

    Two flags are checked:
      starter_change_flag — set when a late fetch_pitchers.py run finds a different
          pitcher than the morning run stored. Critical signal: means the morning
          prompt may have analysed the wrong pitcher entirely.
      opener_flag — set when the game is within 3 hours of first pitch AND the
          listed pitcher has fewer than 5.0 IP on the season. Likely an opener or
          a stale probable that hasn't been updated yet.
    """
    if not pitcher:
        return []

    warnings = []

    change = pitcher.get("starter_change_flag")
    if change:
        old = change.get("old_name", "?")
        new = change.get("new_name", pitcher.get("name", "?"))
        warnings.append(
            f"  !! STARTER CHANGE: morning listed {old}, now {new} -- verify !!"
        )

    if pitcher.get("opener_flag"):
        name = pitcher.get("name", "?")
        ip   = pitcher.get("innings_pitched", "?")
        warnings.append(
            f"  !! STARTER UNCONFIRMED / POSSIBLE OPENER: {name} {ip} IP !!"
        )

    return warnings


def fmt_weather(weather: dict | None) -> str:
    """
    Format the weather section.
    Dome: single token 'weather:dome'.
    Outdoor/retractable: up to three lines —
      wx:{temp}F {cond} wind:{speed}mph {dir} {precip}%rain [notes]
      wind_geo: from {from}° / to {to}° | cf_bearing {cf}° | wind-cf angle {angle}°
      air: gust {gust}mph | humidity {hum}% | pressure {hpa}hPa

    wind_geo line is omitted for dome (no data) and when wind_from_deg is absent.
    air line is shown whenever any of gust/humidity/pressure is present.
    Estimated CF bearings are flagged with (est) inline — models see this tag.
    """
    if not weather:
        return "  wx:unavailable"

    roof = weather.get("roof", "outdoor")

    if roof == "dome":
        return "  weather:dome"

    temp   = weather.get("temp_f")
    wind   = weather.get("wind_mph")
    wdir   = weather.get("wind_dir")
    precip = weather.get("precipitation_pct")
    cond   = weather.get("conditions", "")

    # When temp is None the API call failed -- show unavailable rather than ?F
    if temp is None:
        return "  wx:unavailable"

    # ── Line 1: wx: (unchanged from previous format) ─────────────────────────
    t_part = f"{temp}F"
    c_part = f" {cond}" if cond else ""
    w_part = (f" wind:{wind}mph {wdir}" if (wind is not None and wdir)
              else (f" wind:{wind}mph" if wind is not None else ""))
    p_part = f" {precip}%rain" if precip is not None else ""
    line1  = f"  wx:{t_part}{c_part}{w_part}{p_part}"
    if roof == "retractable":
        line1 += " (retractable — check roof status for park factor)"
    if roof == "outdoor" and precip is not None and precip >= 50:
        line1 += " [PPD RISK]"

    lines = [line1]

    # ── Line 2: wind_geo (raw geometry; omit only when wind_from_deg absent) ─
    wind_from = weather.get("wind_from_deg")
    wind_to   = weather.get("wind_to_deg")
    cf_bear   = weather.get("cf_bearing_deg")
    cf_est    = weather.get("cf_bearing_est", False)
    cf_angle  = weather.get("wind_cf_angle_deg")

    if wind_from is not None:
        # Print raw values even at low wind speed — do not null based on threshold
        if cf_bear is not None:
            est_tag   = "(est)" if cf_est else ""
            cf_str    = f"{cf_bear}°{est_tag}"
            angle_str = f"{cf_angle}°{est_tag}" if cf_angle is not None else "n/a"
        else:
            cf_str    = "UNKNOWN"
            angle_str = None   # omit angle when bearing unknown

        geo_parts = [f"from {wind_from}° / to {wind_to}°", f"cf_bearing {cf_str}"]
        if angle_str is not None:
            geo_parts.append(f"wind-cf angle {angle_str}")
        lines.append("  wind_geo: " + " | ".join(geo_parts))

    # ── Line 3: air (shown whenever any field is present) ────────────────────
    gust     = weather.get("wind_gust_mph")
    humidity = weather.get("humidity_pct")
    pressure = weather.get("pressure_hpa")
    if any(x is not None for x in (gust, humidity, pressure)):
        gust_str = f"gust {gust}mph"           if gust     is not None else "gust n/a"
        hum_str  = f"humidity {humidity}%"     if humidity is not None else "humidity n/a"
        pres_str = f"pressure {pressure}hPa"   if pressure is not None else "pressure n/a"
        lines.append(f"  air: {gust_str} | {hum_str} | {pres_str}")

    return "\n".join(lines)


def fmt_umpire(umpire: dict | None) -> str:
    """
    Format the plate umpire entry.
    Confirmed (status="assigned") shows the name only.
    Inferred (status="inferred") shows name with (est.) tag so models know
    it is a crew-rotation estimate, not a confirmed assignment.
    """
    if not umpire or not umpire.get("name"):
        return "Not yet assigned"
    if umpire.get("status") == "inferred":
        return f"{umpire['name']} (est. — crew rotation, ~85% accurate)"
    return umpire["name"]


def fmt_bullpen(bullpen: dict | None, abbr: str) -> list:
    """
    Format one team's bullpen entry as a list of lines for the BULLPEN block.

    Line 1: "{ABBR}: ERA X.XX | Closer: Name (available)"
    Line 2: "       Taxed: Name1 (45p yesterday), Name2 (2 consec days)"
         or "       No heavy usage last 2 days"

    Returns an empty list when bullpen data has not been fetched yet,
    so the caller can skip the whole BULLPEN section cleanly.
    """
    if not bullpen:
        return []

    # ── Line 1: closer ───────────────────────────────────────────────────────
    closer = bullpen.get("closer", {})
    closer_name = closer.get("name")
    if closer_name:
        avail_str  = "available" if closer.get("available", True) else "TAXED"
        closer_part = f"Closer: {closer_name} ({avail_str})"
    else:
        closer_part = "Closer: unknown"

    first_line = f"  {abbr}: {closer_part}"

    # ── Line 2: Taxed relievers ───────────────────────────────────────────────
    taxed = bullpen.get("taxed_relievers", [])
    if taxed:
        parts = []
        for t in taxed:
            p_yday = t.get("pitches_yesterday")
            consec = t.get("appeared_consecutive_days", False)
            t3in4  = t.get("three_in_four", False)
            d4     = t.get("days_pitched_last4")
            flag   = t.get("flag", "")

            # Build a concise parenthetical reason for the AI
            if flag == "likely_unavailable":
                if p_yday is not None and p_yday >= 25:
                    detail = f"{p_yday}p yesterday"
                elif consec:
                    detail = "2 consec days"
                elif t3in4:
                    detail = f"3-in-4 ({d4}/4 days)"
                else:
                    detail = "taxed"
            else:
                # "reduced" flag — light usage yesterday
                detail = f"{p_yday}p yesterday" if p_yday is not None else "pitched recently"

            parts.append(f"{t['name']} ({detail})")

        second_line = f"       Taxed: {', '.join(parts)}"
    else:
        second_line = "       No heavy usage last 2 days"

    return [first_line, second_line]


def fmt_recent_starts(pitcher: dict | None) -> str | None:
    """
    Format the last-N-starts rolling form line for one pitcher.
    Returns None when no recent_starts data exists (caller skips the line).

    Format:
      "       Last 3 starts: Jun 1 vs HOU 6.0 IP 1 ER | May 27 vs CLE 5.2 IP 3 ER | ... | L3 ERA: 2.45"
    Indented 7 spaces so it sits visually under the pitcher name line above it.
    """
    if not pitcher:
        return None
    recent = pitcher.get("recent_starts")
    if not recent or not recent.get("starts"):
        return None

    starts      = recent["starts"]
    rolling_era = recent.get("rolling_era")
    n           = len(starts)

    # Compact: L3: IP/ER/K/BB when K and BB are present; IP/ER when they are not.
    # K and BB come from the MLB Stats API game log -- available for most starts
    # but absent for very recent games where boxscores may not be finalised.
    has_kb = any("k" in s and "bb" in s for s in starts)
    if has_kb:
        parts   = [f"{s['ip']}/{s['er']}/{s.get('k', '-')}/{s.get('bb', '-')}" for s in starts]
        fmt_lbl = "(IP/ER/K/BB)"
    else:
        parts   = [f"{s['ip']}ip/{s['er']}er" for s in starts]
        fmt_lbl = "(IP/ER)"
    return f"       L{n}: {' | '.join(parts)}  {fmt_lbl}"


def fmt_team_form(team: dict | None, side: str) -> str:
    """
    Format one team's form line for the TEAM FORM block.

    side is "away" or "home" — determines which split record to show.
    Away teams are shown their road record; home teams their home record.
    This is more contextually useful than showing the same split for both.

    Format: "  NYY: 36-23 (.610), last10 6-4, run diff +98, home 17-9, 5.2 RS/G / 3.5 RA/G"
    """
    if not team:
        return f"  {side.capitalize()}: no team stats — run fetch_teamstats.py"

    abbr = team.get("abbr", "???")

    # Overall record
    w   = team.get("wins")
    l   = team.get("losses")
    pct = team.get("pct", "")
    record = f"{w}-{l} ({pct})" if (w is not None and l is not None) else "?-?"

    # Last 10 — best short-term form signal
    l10w = team.get("last10_wins")
    l10l = team.get("last10_losses")
    last10 = f"{l10w}-{l10l}" if (l10w is not None and l10l is not None) else "?-?"

    # Run differential — season-wide measure of how dominant the team is
    rd = team.get("run_differential")
    rd_str = (f"+{rd}" if rd >= 0 else str(rd)) if rd is not None else "?"

    # Contextual split: away team shows away record, home team shows home record
    if side == "home":
        sw = team.get("home_wins")
        sl = team.get("home_losses")
        split_str = f"home {sw}-{sl}" if (sw is not None and sl is not None) else "home ?-?"
    else:
        sw = team.get("away_wins")
        sl = team.get("away_losses")
        split_str = f"away {sw}-{sl}" if (sw is not None and sl is not None) else "away ?-?"

    # Runs per game — quick read on offensive and pitching/defence quality
    rs_g = team.get("rs_per_game")
    ra_g = team.get("ra_per_game")
    rsg_str = str(rs_g) if rs_g is not None else "?"
    rag_str = str(ra_g) if ra_g is not None else "?"

    # L10 RS/G — last-10-games offensive form (more current than season RS/G)
    l10_rsg = team.get("l10_rs_per_game")
    l10_rsg_str = f", L10 RS/G {l10_rsg}" if l10_rsg is not None else ""

    # Offensive barrel% — from Baseball Savant via fetch_pitcher_advanced.py
    brl = team.get("barrel_pct")
    brl_str = f", off. Brl%: {brl}%" if brl is not None else ""

    # Compact: ABBR W-L L10:x-x RS/RA:x/x [L10RS:x] [Brl:x%]
    l10_part  = f" L10RS:{l10_rsg}" if l10_rsg is not None else ""
    brl_part  = f" Brl:{brl}%" if brl is not None else ""
    return (
        f"  {abbr} {w}-{l} L10:{last10} rdiff:{rd_str} {split_str} "
        f"RS/RA:{rsg_str}/{rag_str}{l10_part}{brl_part}"
    )


def _abbreviate_name(full_name: str) -> str:
    """Convert 'Christian Yelich' to 'C.Yelich' for compact batting order display."""
    parts = full_name.split()
    if len(parts) >= 2:
        return f"{parts[0][0]}.{parts[-1]}"
    return full_name


def fmt_lineups(lineups: dict | None, away_abbr: str, home_abbr: str) -> list:
    """
    Format the LINEUPS section as a list of lines for build_game_block().

    Three cases:
      - lineups is None (fetch_lineups.py never ran) → return [] to omit section
      - status "not_yet_confirmed" for both → single "not yet confirmed" line
      - at least one side confirmed → show compact batting order + IL absences

    Batting order is truncated to 5 batters with "..." to keep the block compact.
    The key signal is who is ABSENT (IL), not the full order.
    """
    if lineups is None:
        return []   # fetch_lineups.py never ran — omit entirely

    away = lineups.get("away", {})
    home = lineups.get("home", {})

    away_status = away.get("status", "not_yet_confirmed")
    home_status = home.get("status", "not_yet_confirmed")

    if away_status == "not_yet_confirmed" and home_status == "not_yet_confirmed":
        return [
            "LINEUPS: not yet confirmed",
            "",
        ]

    result = ["LINEUPS (confirmed)"]

    for abbr, side_data in [(away_abbr, away), (home_abbr, home)]:
        status = side_data.get("status", "not_yet_confirmed")

        if status == "not_yet_confirmed":
            result.append(f"  {abbr}: not yet confirmed")
        else:
            order = side_data.get("order", [])
            shown = order[:5]
            parts = []
            for p in shown:
                name = _abbreviate_name(p.get("name", "?"))
                pos  = p.get("pos", "")
                parts.append(f"{name} {pos}".strip())
            order_str = ", ".join(parts)
            if len(order) > 5:
                order_str += " ..."
            result.append(f"  {abbr}: {order_str}")

        # IL absences — always shown (even "none") when lineup status is known
        if status != "not_yet_confirmed":
            il = side_data.get("il_absences", [])
            if il:
                il_str = ", ".join(
                    f"{p.get('name', '?')} {p.get('pos', '')}".strip()
                    for p in il
                )
                result.append(f"  {abbr} IL: {il_str}")
            else:
                result.append(f"  {abbr} IL: none")

    result.append("")
    return result


def fmt_best(entry: dict | None) -> str:
    """
    Format one best_available entry: "+189 (BetOnline)" or "—" if missing.
    Used to append the "best:" suffix to each odds line.
    """
    if not entry or entry.get("price") is None:
        return "—"
    return f"{fmt_american(entry['price'])} ({entry.get('book', '?')})"


def _is_outlier_price(best_price: int | None, median_price: int | None) -> bool:
    """Return True if best_price deviates from median_price by more than 200 points."""
    if best_price is None or median_price is None:
        return False
    return abs(best_price - median_price) > 200


def _fmt_best_safe(entry: dict | None, median_price: int | None) -> str:
    """
    Format a best_available entry, flagging it if its price is an extreme outlier
    versus the consensus median. Prevents stale book data from appearing as edge.
    """
    if not entry or entry.get("price") is None:
        return "—"
    if _is_outlier_price(entry["price"], median_price):
        return "[price flagged as suspect — stale book data]"
    return fmt_best(entry)


def _big_move_note(
    opening: dict,
    current: dict,
    away_abbr: str,
    home_abbr: str,
    threshold: int = 30,
) -> str | None:
    """
    Return a flag note if the moneyline moved by more than threshold points
    (absolute value, American odds integers) from opening to current snapshot.

    Only fires when both snapshots exist and have different timestamps (i.e.
    fmt_line_move() already confirmed real movement happened).

    Direction logic:
      - A price that got shorter (more negative / less positive) = money moved
        TOWARD that team.
      - We report the team that received the money.

    Returns a single indented NOTE string, or None if no large move.
    """
    o_ml = opening.get("moneyline", {})
    c_ml = current.get("moneyline", {})
    if not o_ml or not c_ml:
        return None

    biggest_move   = 0
    toward_abbr    = ""

    for side, abbr, opp_abbr in [
        ("away", away_abbr, home_abbr),
        ("home", home_abbr, away_abbr),
    ]:
        o = o_ml.get(side)
        c = c_ml.get(side)
        if o is None or c is None:
            continue
        move = c - o
        if abs(move) > abs(biggest_move):
            biggest_move = move
            # Negative move = price shortened = money moved TOWARD this team
            toward_abbr = abbr if move < 0 else opp_abbr

    if abs(biggest_move) <= threshold:
        return None

    return (
        f"  [NOTE: ML moved toward {toward_abbr} by {abs(biggest_move)} pts — "
        f"possible roster/lineup change. Treat pitcher and lineup data as "
        f"potentially stale -- treat with caution.]"
    )


def fmt_line_move(opening: dict, current_snap: dict | None) -> str | None:
    """
    Generate the Line move row by comparing opening_snapshot to current_snapshot.

    Three outcomes:
      - current_snapshot missing (games.json pre-dates this feature) -> skip row entirely
      - same fetched_at (only one fetch today) -> "no movement yet"
      - different timestamps -> show what moved in ML and Total

    We show ML movement per side and the Total line point value only.
    RL price movement is skipped — the point (±1.5) never changes and price
    movement on the RL is less actionable as a signal than ML or Total.
    """
    if not opening or not current_snap:
        return None

    # Same timestamp = only one fetch today, nothing to compare yet — suppress line entirely
    if opening.get("fetched_at") == current_snap.get("fetched_at"):
        return None

    # Compare moneyline — report each side that changed
    o_ml = opening.get("moneyline", {})
    c_ml = current_snap.get("moneyline", {})
    ml_parts = []
    for side in ("away", "home"):
        o, c = o_ml.get(side), c_ml.get(side)
        if o is not None and c is not None and o != c:
            ml_parts.append(f"{fmt_american(o)}->{fmt_american(c)}")
    ml_str = " / ".join(ml_parts) if ml_parts else "unchanged"

    # Compare Total line point value — a shift from 7.5 to 8.0 is the key signal
    o_tot = opening.get("total", {})
    c_tot = current_snap.get("total", {})
    o_line = o_tot.get("line")
    c_line = c_tot.get("line")
    if o_line is not None and c_line is not None:
        tot_str = f"{o_line}->{c_line}" if o_line != c_line else "unchanged"
    else:
        tot_str = "—"

    return f"  Line move : ML {ml_str} | Total {tot_str}"


# ─────────────────────────────────────────────────────────────────────────────
# COVERS LINES FORMATTER
# ─────────────────────────────────────────────────────────────────────────────

def fmt_covers_lines(covers: dict | None, away_abbr: str, home_abbr: str) -> list:
    """
    Format the OPENING LINES (Covers/bet365) block for one game.
    Returns [] when covers_lines is None (fetch failed or game not matched).
    Movement entries are stored newest-first; reversed here for oldest→newest display.
    """
    if not covers:
        return []

    def _split_price(combined: str) -> str:
        # "+1.5 -160" -> "-160"   "-1.5 +135" -> "+135"
        parts = (combined or "").split()
        return parts[1] if len(parts) >= 2 else combined

    def _parse_p(s: str) -> int | None:
        try:
            return int(s)
        except (ValueError, TypeError):
            return None

    def _fmt_p(p: int | None) -> str:
        if p is None:
            return "—"
        return f"+{p}" if p > 0 else str(p)

    def _best_rl(current_rl: dict, field: str) -> tuple:
        # Highest integer = best for the bettor (less vig on + side, better payout on - side)
        best_price, best_book = None, "—"
        for book, data in current_rl.items():
            p = _parse_p(_split_price(data.get(field, "")))
            if p is not None and (best_price is None or p > best_price):
                best_price, best_book = p, book
        return best_price, best_book

    def _best_tot(current_total: dict, field: str) -> tuple:
        best_price, best_book = None, "—"
        for book, data in current_total.items():
            p = _parse_p(data.get(field))
            if p is not None and (best_price is None or p > best_price):
                best_price, best_book = p, book
        return best_price, best_book

    lines = ["OPENING LINES (Covers/bet365)"]

    op_rl  = covers.get("opening_rl")  or {}
    cur_rl = covers.get("current_rl")  or {}
    op_tot  = covers.get("opening_total") or {}
    cur_tot = covers.get("current_total") or {}
    bet365_rl  = cur_rl.get("bet365") or {}
    bet365_tot = cur_tot.get("bet365") or {}

    # ── RL: open → current (bet365) ──────────────────────────────────────────
    if op_rl:
        away_open = _split_price(op_rl.get("away", ""))
        home_open = _split_price(op_rl.get("home", ""))
        away_cur  = _split_price(bet365_rl.get("away", "")) if bet365_rl else "—"
        home_cur  = _split_price(bet365_rl.get("home", "")) if bet365_rl else "—"
        lines.append(
            f"  RL:    {away_abbr} +1.5 {away_open} / {home_abbr} -1.5 {home_open}"
            f"  →  current: +1.5 {away_cur} / -1.5 {home_cur}"
        )

    # ── Total: open → current (bet365) ───────────────────────────────────────
    if op_tot:
        lines.append(
            f"  Total: o/u {op_tot.get('line','?')} ({op_tot.get('over','?')}/{op_tot.get('under','?')})"
            f"  →  current: o/u {bet365_tot.get('line','?') if bet365_tot else '?'}"
            f" ({bet365_tot.get('over','?') if bet365_tot else '?'}"
            f"/{bet365_tot.get('under','?') if bet365_tot else '?'})"
        )

    # ── Best current RL across bet365 / Betway / William Hill ────────────────
    if cur_rl:
        bp_away, bk_away = _best_rl(cur_rl, "away")
        bp_home, bk_home = _best_rl(cur_rl, "home")
        lines.append(
            f"  Best current RL:    {away_abbr} +1.5 {_fmt_p(bp_away)} ({bk_away})"
            f" / {home_abbr} -1.5 {_fmt_p(bp_home)} ({bk_home})"
        )

    # ── Best current total across all books ──────────────────────────────────
    if cur_tot:
        bp_over,  bk_over  = _best_tot(cur_tot, "over")
        bp_under, bk_under = _best_tot(cur_tot, "under")
        lines.append(
            f"  Best current total: Over {_fmt_p(bp_over)} ({bk_over})"
            f" / Under {_fmt_p(bp_under)} ({bk_under})"
        )

    lines.append("")

    # ── RL movement: display oldest → newest ─────────────────────────────────
    rl_mv = covers.get("rl_movement") or []
    lines.append("RL MOVEMENT (bet365):")
    if rl_mv:
        # Storage is newest-first; reverse for left-to-right chronological display
        parts = [
            f"{e['time']}: +1.5 {_split_price(e['away'])}/-1.5 {_split_price(e['home'])}"
            for e in reversed(rl_mv)
        ]
        lines.append("  " + "  →  ".join(parts))
    else:
        lines.append("  [No movement recorded]")

    lines.append("")

    # ── Total movement: display oldest → newest ───────────────────────────────
    tot_mv = covers.get("total_movement") or []
    lines.append("TOTAL MOVEMENT (bet365):")
    if tot_mv:
        parts = [
            f"{e['time']}: {e['line']} {e['over']}/{e['under']}"
            for e in reversed(tot_mv)
        ]
        lines.append("  " + "  →  ".join(parts))
    else:
        lines.append("  [No movement recorded]")

    lines.append("")

    return lines


# ─────────────────────────────────────────────────────────────────────────────
# HEAVY-FAVOURITE NOTE
# ─────────────────────────────────────────────────────────────────────────────

def _heavy_fav_notes(snap: dict, away: dict, home: dict) -> list:
    """
    For any side whose ML is heavier than -180, return a NOTE line pointing
    to their -1.5 run line as a more efficient bet.

    Why -180 as the threshold: at that price the implied probability is ~64%.
    Beyond it, the juice eats most of the value — the -1.5 RL is almost always
    priced at or near even money, which is where the edge actually sits.

    Returns a list (usually empty; at most two items if both sides somehow
    qualify, though that is extremely rare in practice).
    """
    notes = []
    ml = snap.get("moneyline", {})
    rl = snap.get("runline", {})
    if not ml or not rl:
        return notes

    # Check both sides: (ml_price, rl_line, rl_price, full_team_name)
    sides = [
        (ml.get("away"), rl.get("away_line"), rl.get("away_price"), away["name"]),
        (ml.get("home"), rl.get("home_line"), rl.get("home_price"), home["name"]),
    ]

    for ml_price, rl_line, rl_price, team_name in sides:
        # Trigger only when ML is strictly heavier than -180 (more negative)
        if ml_price is None or ml_price > -180:
            continue
        # Only reference the -1.5 side (where the team is laying runs).
        # If their rl_line is positive they are the RL underdog — skip.
        if rl_line is None or rl_line > 0:
            continue
        if rl_price is None:
            continue

        ml_str = fmt_american(ml_price)
        rl_str = fmt_american(rl_price)

        # Phrase accurately: plus-money gets called out explicitly;
        # near-even-money is described as "more efficient" without overclaiming.
        if rl_price > 0:
            value_phrase = (
                f"at {rl_str} is plus-money and may be the better way to back them"
            )
        else:
            value_phrase = (
                f"at {rl_str} may be a more efficient way to back them"
            )

        notes.append(
            f"  NOTE: {team_name} ML is heavy at {ml_str}. "
            f"Their -1.5 run line {value_phrase} — consider it."
        )

    return notes


# ─────────────────────────────────────────────────────────────────────────────
# STATIC DATA HELPERS (platoon, advanced pitcher, bullpen, park factors)
# These are only called when static_data is available (MLB only).
# ─────────────────────────────────────────────────────────────────────────────

def _extract_pitch_count(usage_str: str) -> int:
    """
    Extract the leading pitch count from Bullpen.txt usage strings.
    '22 (H)' -> 22  |  '17 (W)' -> 17  |  '' / 'AAA' -> 0
    """
    s = usage_str.strip()
    if not s or s in ("AAA", "-", "--"):
        return 0
    m = re.match(r"(\d+)", s)
    return int(m.group(1)) if m else 0


def _team_wrc_aggregate(
    team_abbr: str, splits: dict, min_pa: int = 50
) -> tuple:
    """
    Compute team-level wRC+ stats from a splits dict when no confirmed lineup exists.
    Filters to players on this team with >= min_pa plate appearances.
    Returns (avg_wrc_plus: int | None, sorted_batters: list of (name, wrc, pa)).
    """
    fg_code = games_abbr_to_fg(team_abbr)
    batters = [
        (name, data["wrc_plus"], data.get("pa") or 0)
        for name, data in splits.items()
        if data.get("team") == fg_code
        and data.get("wrc_plus") is not None
        and (data.get("pa") or 0) >= min_pa
    ]
    if not batters:
        return None, []
    avg = round(sum(w for _, w, _ in batters) / len(batters))
    return avg, sorted(batters, key=lambda x: x[1], reverse=True)


def _lineup_wrc_stats(order: list, splits: dict, min_pa: int = 50) -> list:
    """
    Look up wRC+ for each batter in a confirmed lineup order.
    Uses fuzzy_match_player() to handle minor name differences.
    Returns list of (display_name, wrc_plus, pa) for players found in splits.
    """
    results = []
    for player in order:
        name = player.get("name", "")
        key = fuzzy_match_player(name, splits)
        if key:
            data = splits[key]
            wrc = data.get("wrc_plus")
            pa  = data.get("pa") or 0
            if wrc is not None:
                results.append((name, wrc, pa))
    return results


def _fmt_platoon_matchup(
    ctx: dict,
    away_abbr: str,
    home_abbr: str,
    splits_lhp: dict,
    splits_rhp: dict,
    projected_lineups: dict | None = None,
) -> list:
    """
    PLATOON MATCHUP block.
    Away batters face the HOME starter → use splits vs home starter's hand.
    Home batters face the AWAY starter → use splits vs away starter's hand.
    Returns [] when pitcher hand data is missing for both starters.
    """
    pitcher_away = ctx.get("pitcher_away") or {}
    pitcher_home = ctx.get("pitcher_home") or {}
    lineups      = ctx.get("lineups")

    # hand of the AWAY pitcher (what HOME batters face)
    away_hand = pitcher_away.get("hand")
    # hand of the HOME pitcher (what AWAY batters face)
    home_hand = pitcher_home.get("hand")

    # Returns [] only when splits data itself is missing (never happens in practice)
    # -- previously returned [] when both pitcher hands unknown, but Fix 5 shows
    # both LHP/RHP splits in that case so the model can reason under uncertainty.

    MIN_PA = 50       # guard for the team-wide SEASON AGGREGATE pool
    MIN_PA_BAT = 25   # per-bat guard: bats below this are shown but excluded from the average

    def _one_side(team_abbr, lineup_side, splits, hand_label):
        """
        Build wRC+ lines for one team batting against a given hand.
        Three-tier precedence:
          1. CONFIRMED — MLB Stats API confirmed lineup (fetch_lineups.py)
          2. REGULARS  — lineup_tracker.txt recent-actuals batting order
          3. AGGREGATE — full-team season average from splits
        """
        # Tier 1: confirmed lineup from fetch_lineups.py
        confirmed = (
            lineup_side is not None
            and lineup_side.get("status") == "confirmed"
        )
        order = lineup_side.get("order", []) if confirmed and lineup_side else []

        if confirmed and order:
            batter_stats = _lineup_wrc_stats(order, splits, min_pa=MIN_PA)
            status_tag   = "CONFIRMED"
        else:
            # Tier 2: recent-actuals pattern from lineup_tracker.txt (not a projection)
            proj = (projected_lineups or {}).get(team_abbr, {})
            proj_starters = proj.get("starters", [])
            if proj_starters:
                # Build an order list compatible with _lineup_wrc_stats
                proj_order = [{"name": p["name"]} for p in proj_starters]
                batter_stats = _lineup_wrc_stats(proj_order, splits, min_pa=MIN_PA)
                status_tag   = "REGULARS"
            else:
                # Tier 3: full-team season aggregate
                _, batter_stats = _team_wrc_aggregate(team_abbr, splits, min_pa=MIN_PA)
                status_tag      = "SEASON AGGREGATE"

        # Per-batter line: vs_{hand}: wRC+:{avg}({status},n) Last{wrc}({pa}) ... | low-PA(excl): ...
        # Every batter is shown with wRC+ AND plate appearances so the model can
        # judge sample size itself. Bats below MIN_PA_BAT are EXCLUDED from the
        # average (so a tiny-sample outlier like Callihan 370 wRC+ in 8 PA cannot
        # inflate the lineup figure) but are still printed under "low-PA(excl)".
        block = []

        if batter_stats:
            status_short = {"CONFIRMED": "CFM", "REGULARS": "REG",
                            "SEASON AGGREGATE": "AGG"}.get(status_tag, "AGG")
            sorted_s  = sorted(batter_stats, key=lambda x: x[1], reverse=True)
            qualified = [p for p in sorted_s if p[2] >= MIN_PA_BAT]
            lowpa     = [p for p in sorted_s if p[2] <  MIN_PA_BAT]
            pool      = qualified or sorted_s  # fall back to all if none clear the guard
            avg_wrc   = round(sum(w for _, w, _ in pool) / len(pool))

            def _bat(p):
                return f"{p[0].split()[-1]}{int(round(p[1]))}({int(p[2])})"

            line = (
                f"  vs_{hand_label}: wRC+:{avg_wrc}({status_short},n={len(pool)}) "
                + " ".join(_bat(p) for p in qualified)
            )
            if lowpa:
                line += f" | low-PA<{MIN_PA_BAT}(excl): " + " ".join(_bat(p) for p in lowpa)
            block.append(line)
        else:
            block.append(f"  vs_{hand_label}: wRC+:no-data")

        return block

    lines = ["PLATOON MATCHUP"]

    # Away batters face HOME pitcher
    if home_hand:
        splits = splits_lhp if home_hand == "L" else splits_rhp
        away_lineup = (lineups or {}).get("away") if lineups else None
        lines.extend(_one_side(away_abbr, away_lineup, splits, f"{home_hand}HP"))
    else:
        # Home pitcher hand unknown -- show both splits so model can reason under uncertainty
        away_lineup = (lineups or {}).get("away") if lineups else None
        lines.append("  (home starter hand unknown -- showing both splits)")
        lines.extend(_one_side(away_abbr, away_lineup, splits_lhp, "LHP"))
        lines.extend(_one_side(away_abbr, away_lineup, splits_rhp, "RHP"))

    # Home batters face AWAY pitcher
    if away_hand:
        splits = splits_lhp if away_hand == "L" else splits_rhp
        home_lineup = (lineups or {}).get("home") if lineups else None
        lines.extend(_one_side(home_abbr, home_lineup, splits, f"{away_hand}HP"))
    else:
        # Away pitcher hand unknown -- show both splits
        home_lineup = (lineups or {}).get("home") if lineups else None
        lines.append("  (away starter hand unknown -- showing both splits)")
        lines.extend(_one_side(home_abbr, home_lineup, splits_lhp, "LHP"))
        lines.extend(_one_side(home_abbr, home_lineup, splits_rhp, "RHP"))

    lines.append("")
    return lines


def _fmt_pitcher_oneline(  # noqa: PLR0913
    pitcher: dict | None,
    side: str,
    season_pitchers: dict,
    last14_pitchers: dict,
    stuff_plus: dict | None = None,
    pitchers_bb: dict | None = None,
) -> str:
    """
    Collapse the pitcher block into pipe-delimited segments.
    Segments: ERA/FIP/xERA/K9/Whiff/HH%/Brl%/IP | AGG xFIP/SIERA/K-BB%/Stf+/IP
              | AGG LD%/GB%/FB% (pitcher-season batted-ball) | L14 | L3 starts.

    pitchers_bb: from load_pitchers_season_batted_ball() (pitchers_season_ld_gb_fb.txt).
    Rendered as a distinct segment labelled "BB-profile" to avoid confusion with the
    team_barrels GB%/FB% which are BATTER-side batted-ball rates.
    """
    if not pitcher or not pitcher.get("name"):
        return f"  {side}: TBD"

    def _f(v, spec=".2f"):
        return format(v, spec) if v is not None else "--"

    name = pitcher["name"]
    hand = pitcher.get("hand") or "?"
    w    = pitcher.get("wins")
    l    = pitcher.get("losses")
    wl   = f"{w}-{l}" if (w is not None and l is not None) else "?-?"
    ip   = pitcher.get("innings_pitched")

    # ── Segment 1: season Savant stats ────────────────────────────────────────
    era  = _f(pitcher.get("era"))
    fip  = pitcher.get("fip")
    xera = _f(pitcher.get("xera"))
    k9   = _f(pitcher.get("k_per_9"), ".1f")
    hh   = _f(pitcher.get("hard_hit_pct"), ".1f")
    brl  = _f(pitcher.get("barrel_pct"), ".1f")
    whiff = pitcher.get("whiff_rate")
    whiff_part = f" Whiff:{_f(whiff, '.1f')}%" if whiff is not None else ""
    fip_part   = f" FIP {_f(fip)}" if fip is not None else ""
    ip_part    = f"{ip}IP" if ip is not None else "--IP"
    seg1 = f"ERA {era}{fip_part} xERA {xera} K/9 {k9}{whiff_part} HH% {hh} Brl% {brl} {ip_part}"
    if pitcher.get("small_sample"):
        seg1 += " [sm]"

    segments = [f"  {side}: {name} {hand}HP {wl}", seg1]

    # ── Segment 2: FanGraphs AGG (season xFIP/SIERA) ─────────────────────────
    season_key = fuzzy_match_player(name, season_pitchers)
    if season_key:
        s     = season_pitchers[season_key]
        xfip  = _f(s.get("xfip"))
        siera = _f(s.get("siera"))
        kbb   = f"{s['k_bb_pct'] * 100:.1f}%" if s.get("k_bb_pct") is not None else "--"
        s_ip  = s.get("ip", "--")
        stf_key  = fuzzy_match_player(name, stuff_plus or {})
        stf_val  = (stuff_plus or {}).get(stf_key) if stf_key else None
        stf_part = f" Stf+:{int(stf_val)}" if stf_val is not None else ""
        segments.append(f"AGG xFIP {xfip} SIERA {siera} K-BB%:{kbb}{stf_part} {s_ip}IP")
    else:
        season_key = None  # explicit for L14 fallback check

    # ── Segment 2b: pitcher-season batted-ball profile (LD%/GB%/FB%) ──────────
    # Source: pitchers_season_ld_gb_fb.txt — PITCHER-side rates (what batters do
    # against this starter). Labelled "BB-profile" to distinguish from the
    # BATTER-side team_barrels GB%/FB% shown in the TEAM FORM block above.
    if pitchers_bb:
        bb_key = fuzzy_match_player(name, pitchers_bb)
        if bb_key:
            bb = pitchers_bb[bb_key]
            ld  = f"{bb['ld_pct']*100:.1f}%" if bb.get("ld_pct") is not None else "--"
            gb  = f"{bb['gb_pct']*100:.1f}%" if bb.get("gb_pct") is not None else "--"
            fb  = f"{bb['fb_pct']*100:.1f}%" if bb.get("fb_pct") is not None else "--"
            segments.append(f"BB-profile LD%:{ld} GB%:{gb} FB%:{fb}")

    # ── Segment 3: FanGraphs L14 ──────────────────────────────────────────────
    last14_key = fuzzy_match_player(name, last14_pitchers)
    if last14_key:
        s14 = last14_pitchers[last14_key]
        l14_ip = s14.get("ip") or 0
        if l14_ip >= 3:
            sm_flag = " [sm]" if l14_ip < 12 else ""
            # K-BB% is stored as a fraction (0.087 == 8.7%), same as the AGG segment.
            kbb14 = f"{s14['k_bb_pct'] * 100:.1f}%" if s14.get("k_bb_pct") is not None else "--"
            segments.append(
                f"L14 xFIP {_f(s14.get('xfip'))} SIERA {_f(s14.get('siera'))}"
                f" K-BB%:{kbb14}"
                f" K/9:{_f(s14.get('k9'), '.1f')} BB/9:{_f(s14.get('bb9'), '.1f')}"
                f" {l14_ip}IP{sm_flag}"
            )
    elif season_key:
        segments.append("L14 no data")

    # ── Segment 4: last-3 starts ──────────────────────────────────────────────
    recent = pitcher.get("recent_starts")
    if recent and recent.get("starts"):
        starts    = recent["starts"]
        has_kb    = any("k" in s and "bb" in s for s in starts)
        if has_kb:
            parts = [f"{s['ip']}/{s['er']}/{s.get('k','-')}/{s.get('bb','-')}" for s in starts]
        else:
            parts = [f"{s['ip']}/{s['er']}" for s in starts]
        segments.append(f"L3 {';'.join(parts)}")

    return " | ".join(segments)


def _fmt_starter_advanced_lines(
    pitcher: dict | None,
    season_pitchers: dict,
    last14_pitchers: dict,
    stuff_plus: dict | None = None,
) -> list:
    """
    Return 0-2 indented lines of FanGraphs advanced stats for one starter.
    Placed directly below the fmt_pitcher() line in the STARTING PITCHERS block.

    Season line: always shown when data found.
      Includes Stuff+ when available (keyed by pitcher name from pitchers_xfip_siera.txt).
    Last-14 line: shown if found AND >= 3 IP in the window.
                  Shows 'no data' when season data exists but last-14 doesn't.
    """
    if not pitcher or not pitcher.get("name"):
        return []

    name   = pitcher["name"]
    result = []

    season_key = fuzzy_match_player(name, season_pitchers)
    last14_key = fuzzy_match_player(name, last14_pitchers)

    def _f(v, spec=".2f"):
        return format(v, spec) if v is not None else "--"

    if season_key:
        s     = season_pitchers[season_key]
        xfip  = _f(s.get("xfip"))
        siera = _f(s.get("siera"))
        kbb   = f"{s['k_bb_pct'] * 100:.1f}%" if s.get("k_bb_pct") is not None else "--"
        ip    = s.get("ip", "--")

        # Stuff+ from load_stuff_plus() — omit entirely when unavailable
        stf_key = fuzzy_match_player(name, stuff_plus or {})
        stf_val = (stuff_plus or {}).get(stf_key) if stf_key else None
        stf_part = f" | Stf+: {int(stf_val)}" if stf_val is not None else ""

        result.append(
            f"       AGG: xFIP {xfip} SIERA {siera} K-BB%:{kbb}{stf_part} {ip}IP"
        )

    if last14_key:
        s  = last14_pitchers[last14_key]
        ip = s.get("ip") or 0
        if ip >= 3:
            sample_flag = f"  [small sample — {ip}IP]" if ip < 12 else ""
            result.append(
                f"       L14: xFIP {_f(s.get('xfip'))} SIERA {_f(s.get('siera'))}"
                f" K/9:{_f(s.get('k9'), '.1f')} BB/9:{_f(s.get('bb9'), '.1f')} {ip}IP{sample_flag}"
            )
    elif season_key:
        result.append("       L14: no data")

    return result


def _fmt_bullpen_static(team_abbr: str, bullpen_data: dict) -> list:
    """
    Format one team's bullpen block from static Bullpen.txt data.
    Returns [] when no data exists for this team (caller falls back to fetch_bullpen.py output).
    Does NOT include the 'BULLPEN -- TEAM' header line — caller adds that.

    Each reliever line carries raw stats only (ERA, K%, SwStr%, SV, HLD, SD/MD).
    SD/MD (shutdowns/meltdowns) are a raw high-leverage-usage proxy; no derived
    verdict is computed — each model interprets the leverage signal itself.
    """
    relievers = bullpen_data.get(team_abbr)
    if not relievers:
        return []

    day_labels = bullpen_data.get("_meta", {}).get(
        "day_labels", ["Fri", "Thu", "Wed", "Tue", "Mon", "Sun"]
    )

    def _usage_str(usage_list):
        parts = []
        for day, val in zip(day_labels, usage_list):
            pc = _extract_pitch_count(val)
            if pc:
                m    = re.search(r"\(([^)]+)\)", val)
                code = f"({m.group(1)})" if m else ""
                parts.append(f"{day} {pc}p{code}")
            else:
                parts.append(f"{day} -")
        return " | ".join(parts)

    def _reliever_lines(r, role_label):
        hand = r.get("throws", "?")
        era  = f"{r['era']:.2f}" if r.get("era") is not None else "--"
        kpct = f"{r['k_pct'] * 100:.1f}%" if r.get("k_pct") is not None else "--"
        swstr = f"{r['swstr'] * 100:.1f}%" if r.get("swstr") is not None else None
        sv   = int(r["sv"])  if r.get("sv")  is not None else 0
        hld  = int(r["hld"]) if r.get("hld") is not None else 0
        sd   = int(r["sd"])  if r.get("sd")  is not None else None
        md   = int(r["md"])  if r.get("md")  is not None else None
        extras = []
        if sv:  extras.append(f"{sv} SV")
        if hld: extras.append(f"{hld} HLD")
        # SD/MD — raw shutdown/meltdown counts (high-leverage usage proxy)
        if sd is not None or md is not None:
            extras.append(f"{sd or 0} SD/{md or 0} MD")
        stat_str = f"{era} ERA, {kpct} K%"
        if swstr is not None:
            stat_str += f", {swstr} SwStr%"
        if extras:
            stat_str += ", " + ", ".join(extras)
        return [
            f"  {role_label}: {r['name']} ({hand}) -- {stat_str}",
            f"    Usage last 6: {_usage_str(r.get('usage_last6', []))}",
        ]

    # Role priority order for selection. Any role containing "IL" is excluded.
    ROLE_ORDER = [
        "Closer",
        "Closer Committee",
        "Setup Man",
        "Middle Reliever",
        "Long Reliever",
    ]
    MAX_ARMS = 6

    def _role_rank(role: str) -> int:
        for i, r in enumerate(ROLE_ORDER):
            if r in role:
                return i
        return len(ROLE_ORDER)  # unknown roles sort last

    # Exclude IL arms, then sort by priority, then cap at MAX_ARMS
    available = [r for r in relievers if "IL" not in r.get("role", "")]
    selected  = sorted(available, key=lambda r: _role_rank(r.get("role", "")))[:MAX_ARMS]

    # ── Leverage-tier availability index ────────────────────────────────────
    # Summarises how many arms in each tier are fresh vs. taxed today.
    # "Taxed" = pitched ≥16 pitches in any of the 3 most recent days.
    # Displayed as a single compact line before the per-arm detail.
    _TAXED_THRESHOLD = 15   # pitches in last 3 days → "taxed"

    def _recent_pitches(r: dict) -> int:
        """Sum pitch counts across the 3 most-recent usage columns."""
        return sum(
            _extract_pitch_count(v) or 0
            for v in r.get("usage_last6", [])[:3]
        )

    def _tier_label(role: str) -> str:
        if "Closer" in role:
            return "T1"
        if "Setup" in role:
            return "T2"
        if "Middle" in role or "Long" in role:
            return "T3"
        return "T?"

    tier_summary: dict[str, list[str]] = {"T1": [], "T2": [], "T3": []}
    for r in available:
        tl = _tier_label(r.get("role", ""))
        if tl not in tier_summary:
            continue
        recent = _recent_pitches(r)
        status = "taxed" if recent > _TAXED_THRESHOLD else "avail"
        tier_summary[tl].append(status)

    tier_parts = []
    for tl in ("T1", "T2", "T3"):
        arms = tier_summary[tl]
        if not arms:
            continue
        n_avail = sum(1 for s in arms if s == "avail")
        tier_parts.append(f"{tl}: {n_avail}/{len(arms)} avail")

    lines = []
    if tier_parts:
        lines.append(f"  [Bullpen: {' | '.join(tier_parts)}]")

    for r in selected:
        lines.extend(_reliever_lines(r, r.get("role", "Reliever")))

    return lines


def _fmt_park_factors_block(
    home_abbr: str,
    venue: str,
    weather_roof: str | None,
    park_data: dict,
    roof_data: dict,
) -> list:
    """
    PARK FACTORS block for the home team's venue.
    Returns [] if the home team has no park factor entry.
    """
    pf = park_data.get(home_abbr)
    if not pf:
        return []

    factor = pf.get("park_factor")
    if factor is None:
        return []

    hr_fac = pf.get("hr_factor")
    r_fac  = pf.get("r_factor")

    # Narrative qualifier
    if factor >= 105:
        qualifier = " -- hitter-friendly"
    elif factor <= 95:
        qualifier = " -- pitcher-friendly"
    else:
        qualifier = ""

    hr_str = f" | HR: {int(hr_fac)}" if hr_fac is not None else ""
    r_str  = f" | Runs: {int(r_fac)}" if r_fac is not None else ""

    lines = [
        f"PARK: {venue or pf.get('team_name', home_abbr)}",
        f"  Park factor: {int(factor)} (3yr){hr_str}{r_str}{qualifier}",
    ]

    # Coors Field altitude note
    if home_abbr == "COL":
        lines.append("  Altitude park (5,280 ft) -- significant run inflation expected")

    # High-variance caution: when the runs factor is > 115, margin-of-victory
    # outcomes are particularly unpredictable — relevant context for run lines.
    if r_fac is not None and r_fac > 115:
        lines.append(
            "  (High-scoring environment -- margin-of-victory outcomes carry"
            " very high variance here.)"
        )

    # Retractable roof: show roof-closed factor so AI can use it when roof is confirmed shut
    if weather_roof == "retractable":
        roof_pf = roof_data.get(home_abbr)
        if roof_pf and roof_pf.get("park_factor") is not None:
            lines.append(
                f"  Roof-closed factor: {int(roof_pf['park_factor'])}"
                f" -- use this value if roof confirmed closed at game time"
            )

    lines.append("")
    return lines


# ─────────────────────────────────────────────────────────────────────────────
# GAME BLOCK BUILDER
# ─────────────────────────────────────────────────────────────────────────────

# ─────────────────────────────────────────────────────────────────────────────
# STATIC STADIUM DIMENSIONS  (LF line / CF / RF line, in feet)
# Keyed by home-team abbreviation as used in games.json. Park dimensions are
# fixed facts, so they live here as a static table — the daily prompt does NOT
# depend on CrookedFence (which updates unpredictably) for this. Correct any
# value in place if a park is reconfigured.
# ─────────────────────────────────────────────────────────────────────────────

STADIUM_DIMENSIONS: dict[str, tuple[int, int, int]] = {
    "ARI": (330, 407, 334),
    "ATL": (335, 400, 325),
    "BAL": (333, 410, 318),
    "BOS": (310, 390, 302),
    "CHC": (355, 400, 353),
    "CWS": (330, 400, 335),
    "CIN": (328, 404, 325),
    "CLE": (325, 405, 325),
    "COL": (347, 415, 350),
    "DET": (345, 420, 330),
    "HOU": (315, 409, 326),
    "KC":  (330, 410, 330),
    "LAA": (330, 396, 330),
    "LAD": (330, 395, 330),
    "MIA": (344, 400, 335),
    "MIL": (335, 400, 325),
    "MIN": (339, 404, 328),
    "NYM": (335, 408, 330),
    "NYY": (318, 408, 314),
    "ATH": (330, 403, 325),
    "PHI": (330, 401, 326),
    "PIT": (325, 399, 320),
    "SD":  (334, 396, 322),
    "SF":  (339, 399, 309),
    "SEA": (331, 401, 326),
    "STL": (336, 400, 335),
    "TB":  (315, 404, 322),
    "TEX": (330, 400, 326),
    "TOR": (328, 400, 328),
    "WSH": (336, 402, 335),
}


def build_game_block(game: dict, i: int, total: int, sport: str, static_data: dict | None = None,
                     hoist_lineups: bool = False, hoist_umpire: bool = False) -> str:
    """
    Build the complete data block for one game. Returns a multi-line string.

    Every field is handled defensively — missing data shows as a clear
    placeholder rather than crashing or printing Python's "None".

    Block structure:
      GAME N OF T: AWAY (ABBR) @ HOME (ABBR)
      Time | Venue
      ODDS (moneyline / run line / total)
      STARTING PITCHERS (away / home)
      WEATHER
      PLATE UMPIRE
    """
    away = game["away"]
    home = game["home"]
    ctx  = game.get("context") or {}   # context may be None if no scripts have run

    # ── Header ────────────────────────────────────────────────────────────────
    time_str = fmt_time(game["commence_et"])

    # Venue info lives in the weather context block (that's where stadium data is stored)
    weather = ctx.get("weather") or {}
    venue   = weather.get("venue", "Venue TBD")

    lines = [
        f"GAME {i}: {away['abbr']} @ {home['abbr']}  {time_str} ET  {venue}",
        "",
    ]

    # ── Odds — compact single-line format (2b) ────────────────────────────────
    snap = game.get("odds", {}).get("opening_snapshot", {})

    ba     = game.get("odds", {}).get("best_available", {})
    ba_ml  = ba.get("moneyline", {})
    ba_rl  = ba.get("runline", {})
    ba_tot = ba.get("total", {})

    ml  = snap.get("moneyline", {})
    rl  = snap.get("runline", {})
    tot = snap.get("total", {})

    # ML:{away}/{home}  RL:{away_rl_price}/{home_rl_price}  TT:{line}({over}/{under})
    ml_str  = f"ML:{fmt_american(ml.get('away'))}/{fmt_american(ml.get('home'))}" if ml else "ML:n/a"
    rl_str  = (f"RL:{fmt_american(rl.get('away_price'))}/{fmt_american(rl.get('home_price'))}"
               if rl else "RL:n/a")
    tot_str = (f"TT:{tot.get('line','?')}({fmt_american(tot.get('over_price'))}/{fmt_american(tot.get('under_price'))})"
               if tot else "TT:n/a")
    lines.append(f"  {ml_str}  {rl_str}  {tot_str}")

    # Best available on a second compact line when present
    best_parts = []
    if ba_ml:
        best_parts.append(f"best-ML:{_fmt_best_safe(ba_ml.get('away'), ml.get('away') if ml else None)}"
                          f"/{_fmt_best_safe(ba_ml.get('home'), ml.get('home') if ml else None)}")
    if ba_tot:
        best_parts.append(f"best-TT:O{_fmt_best_safe(ba_tot.get('over'), tot.get('over_price') if tot else None)}"
                          f"/U{_fmt_best_safe(ba_tot.get('under'), tot.get('under_price') if tot else None)}")
    if best_parts:
        lines.append(f"  {' '.join(best_parts)}")

    # Line movement — compare opening_snapshot to current_snapshot.
    # Shows "no movement yet" on first daily fetch; shows actual moves thereafter.
    opening_snap = game.get("odds", {}).get("opening_snapshot", {})
    current_snap = game.get("odds", {}).get("current_snapshot")
    lm = fmt_line_move(opening_snap, current_snap)
    if lm:
        lines.append(lm)

    # Flag large ML moves (> 30 pts) as a potential roster/news signal.
    # Only fires when both snapshots exist and timestamps differ (real movement).
    if (current_snap and
            opening_snap.get("fetched_at") != current_snap.get("fetched_at")):
        big_note = _big_move_note(opening_snap, current_snap, away["abbr"], home["abbr"])
        if big_note:
            lines.append(big_note)

    # Heavy-favourite note: if either team's ML is heavier than -180, point to
    # their -1.5 run line as a more price-efficient way to back them.
    for note in _heavy_fav_notes(snap, away, home):
        lines.append(note)

    lines.append("")

    # ── Covers opening lines + movement (if fetch_covers_lines.py has run) ───
    covers_block = fmt_covers_lines(
        game.get("covers_lines"), away["abbr"], home["abbr"]
    )
    lines.extend(covers_block)

    # ── Team form ─────────────────────────────────────────────────────────────
    # Placed BEFORE pitchers so the AI establishes team-level context first,
    # preventing it from anchoring to pitcher ERA before considering overall
    # team quality, run differential, and recent form.
    lines.append("TEAM FORM")
    team_barrels = (static_data or {}).get("team_barrels", {})
    for team_ctx, side_str, abbr in [
        (ctx.get("team_away"), "away", away["abbr"]),
        (ctx.get("team_home"), "home", home["abbr"]),
    ]:
        line = fmt_team_form(team_ctx, side_str)
        brl_entry = team_barrels.get(abbr)
        if brl_entry:
            brl_val = brl_entry.get("barrel_pct")
            hh_val  = brl_entry.get("hardhit_pct")
            gb_val  = brl_entry.get("gb_pct")
            fb_val  = brl_entry.get("fb_pct")
            pul_val = brl_entry.get("pull_pct")
            la_val  = brl_entry.get("launch_angle")
            if brl_val is not None: line += f" Brl%:{brl_val}"
            if hh_val  is not None: line += f" HH%:{hh_val}"
            if gb_val  is not None: line += f" GB%:{gb_val}"
            if fb_val  is not None: line += f" FB%:{fb_val}"
            if pul_val is not None: line += f" Pull%:{pul_val}"
            if la_val  is not None: line += f" LA:{la_val}°"
        lines.append(line)
    lines.append("")

    # ── Platoon matchup ───────────────────────────────────────────────────────
    # Shows how each team's offence performs vs the opposing starter's hand.
    # Uses confirmed lineup when available; falls back to full-team aggregate.
    if static_data:
        lines.extend(_fmt_platoon_matchup(
            ctx,
            away["abbr"], home["abbr"],
            static_data.get("splits_lhp", {}),
            static_data.get("splits_rhp", {}),
            projected_lineups=static_data.get("lineup_tracker", {}),
        ))

    # ── Starting pitchers ─────────────────────────────────────────────────────
    lines.append("STARTING PITCHERS")

    # Helper: True when pitcher dict is missing or has no name (TBD)
    def _is_tbd(p: dict | None) -> bool:
        return not p or not p.get("name")

    away_tbd = _is_tbd(ctx.get("pitcher_away"))
    home_tbd = _is_tbd(ctx.get("pitcher_home"))

    # Emit any data-quality flags BEFORE the stat line so they are impossible
    # to miss. Flags are set by fetch_pitchers.py on late re-runs.
    sd = static_data or {}
    lines.extend(fmt_pitcher_flags(ctx.get("pitcher_away")))
    lines.append(_fmt_pitcher_oneline(
        ctx.get("pitcher_away"), "Away",
        sd.get("pitchers_season", {}), sd.get("pitchers_l14", {}), sd.get("stuff_plus", {}),
        sd.get("pitchers_bb", {}),
    ))
    if away_tbd:
        lines.append("  NOTE: TBD starter -- pass on this game unless starter confirmed before your submission. Do not estimate edge without confirmed pitcher data.")
    lines.extend(fmt_pitcher_flags(ctx.get("pitcher_home")))
    lines.append(_fmt_pitcher_oneline(
        ctx.get("pitcher_home"), "Home",
        sd.get("pitchers_season", {}), sd.get("pitchers_l14", {}), sd.get("stuff_plus", {}),
        sd.get("pitchers_bb", {}),
    ))
    if home_tbd:
        lines.append("  NOTE: TBD starter -- pass on this game unless starter confirmed before your submission. Do not estimate edge without confirmed pitcher data.")
    lines.append("")

    # ── Lineups ───────────────────────────────────────────────────────────────
    # Only shown when fetch_lineups.py has run — omitted silently otherwise.
    # When all games are unconfirmed, hoist_lineups=True suppresses per-game block.
    if not hoist_lineups:
        lineup_lines = fmt_lineups(ctx.get("lineups"), away["abbr"], home["abbr"])
        if lineup_lines:
            lines.extend(lineup_lines)

    # ── Bullpen ───────────────────────────────────────────────────────────────
    # Priority: static Bullpen.txt data (richer) > fetch_bullpen.py output.
    # Each team gets its own "BULLPEN -- TEAM" header per spec.
    bullpen_static = (static_data or {}).get("bullpen", {})

    static_away_bpen = _fmt_bullpen_static(away["abbr"], bullpen_static)
    static_home_bpen = _fmt_bullpen_static(home["abbr"], bullpen_static)
    ctx_away_bpen    = fmt_bullpen(ctx.get("bullpen_away"), away["abbr"])
    ctx_home_bpen    = fmt_bullpen(ctx.get("bullpen_home"), home["abbr"])

    away_bpen = static_away_bpen or ctx_away_bpen
    home_bpen = static_home_bpen or ctx_home_bpen

    if away_bpen or home_bpen:
        if away_bpen:
            lines.append(f"BULLPEN -- {away['abbr']}")
            lines.extend(away_bpen)
            lines.append("")
        if home_bpen:
            lines.append(f"BULLPEN -- {home['abbr']}")
            lines.extend(home_bpen)
            lines.append("")

    # ── Weather ───────────────────────────────────────────────────────────────
    lines.append(f"WEATHER")
    lines.append(fmt_weather(ctx.get("weather")))
    lines.append("")

    # ── Stadium dimensions (raw input for totals) ─────────────────────────────
    # Sourced from the static STADIUM_DIMENSIONS table so the daily prompt has
    # ZERO dependency on CrookedFence (which updates unpredictably). Park
    # dimensions are fixed facts. Raw wind speed + compass direction is already
    # in the WEATHER line above (from Open-Meteo); each model reasons about wind
    # effect on its own. No pre-computed HR/runs edge is injected — models stay
    # independent.
    dims = STADIUM_DIMENSIONS.get(home["abbr"])
    if dims:
        lf, cf, rf = dims
        lines.append("STADIUM")
        lines.append(f"  {venue} — LF {lf}ft | CF {cf}ft | RF {rf}ft")
        lines.append("")

    # ── Park factors ──────────────────────────────────────────────────────────
    # Keyed by home team (park doesn't change). Uses static FanGraphs 3yr rolling data.
    # Roof-closed factor shown separately when venue has a retractable roof.
    if static_data:
        lines.extend(_fmt_park_factors_block(
            home["abbr"],
            venue,
            (ctx.get("weather") or {}).get("roof"),
            static_data.get("park_factors", {}),
            static_data.get("park_roof", {}),
        ))

    # ── Umpire ────────────────────────────────────────────────────────────────
    # When all games are unassigned, hoist_umpire=True suppresses per-game line.
    if not hoist_umpire:
        lines.append(f"PLATE UMPIRE: {fmt_umpire(ctx.get('umpire'))}")
        lines.append("")

    return "\n".join(lines)


# ─────────────────────────────────────────────────────────────────────────────
# MODEL INSTRUCTION LOADER
# ─────────────────────────────────────────────────────────────────────────────

def _load_highest_version(methods_dir: Path, pattern: str) -> str | None:
    """
    Glob method docs matching `pattern` (e.g. "method_kimi_v*.md") and return the
    text of the highest version number. Returns None if no file matches.
    """
    candidates = []
    for f in methods_dir.glob(pattern):
        stem = f.stem  # e.g. "method_deepseek_v2" or "method_deepseek_totals_v1"
        try:
            version = int(stem.rsplit("_v", 1)[1])
            candidates.append((version, f))
        except (IndexError, ValueError):
            pass  # skip files that don't match the version pattern
    if not candidates:
        return None
    _, best_path = max(candidates, key=lambda x: x[0])
    return best_path.read_text(encoding="utf-8").strip()


def load_model_instruction(model_name: str, project_root: Path) -> str | None:
    """
    Load the model's self-authored method(s), selecting the highest version of each.

    Two method docs are loaded and combined when present:
      method_{model}_v{N}.md         -- the ML / run-line method (the original)
      method_{model}_totals_v{N}.md  -- the self-authored Over/Under method (added
                                        in the June 2026 totals-authoring round)

    The totals method is appended after the ML/RL method under a clear header so
    each market's strategy stays distinct but both reach the model every slate.

    A missing method file is not an error — the prompt still builds. Returns None
    only if NEITHER file exists for this model.
    """
    methods_dir = project_root / "docs" / "methods"
    model_key   = model_name.lower()

    # ML/RL method: method_{model}_v{N}.md  — but NOT method_{model}_totals_v{N}.md.
    # The totals glob below is separate; exclude it here by checking the stem.
    ml_candidates = []
    for f in methods_dir.glob(f"method_{model_key}_v*.md"):
        stem = f.stem
        try:
            version = int(stem.rsplit("_v", 1)[1])
            ml_candidates.append((version, f))
        except (IndexError, ValueError):
            pass
    ml_method = None
    if ml_candidates:
        _, best_path = max(ml_candidates, key=lambda x: x[0])
        ml_method = best_path.read_text(encoding="utf-8").strip()

    # Totals method: method_{model}_totals_v{N}.md
    totals_method = _load_highest_version(methods_dir, f"method_{model_key}_totals_v*.md")

    if ml_method is None and totals_method is None:
        return None

    parts = []
    if ml_method:
        parts.append(ml_method)
    if totals_method:
        parts.append(
            "\n\n=== TOTALS (OVER/UNDER) METHOD — applies to the TOTAL bet slot ===\n\n"
            + totals_method
        )
    return "\n".join(parts)


# ─────────────────────────────────────────────────────────────────────────────
# v3 BANKROLL ACCOUNT INJECTION
# ─────────────────────────────────────────────────────────────────────────────

def _fmt_bucket(b: dict) -> str:
    """Format one by-type bucket as 'bets / W-L / +$net'."""
    net = b.get("dollars_net", 0.0)
    sign = "+" if net >= 0 else "-"
    return f"{b.get('bets', 0)} / {b.get('w', 0)}-{b.get('l', 0)} / {sign}${abs(net):,.0f}"


def render_account_block(model: str, sport: str, date: str, project_root: Path) -> str:
    """
    Build the v3 bankroll account block injected into the per-model prompt.

    Returns "" (nothing) when:
      - no model specified, or
      - bankroll/{sport}/_config.json is missing, or
      - the slate date is BEFORE v3_start_date.
    So v2 prompts are completely untouched -- the block only appears from the
    first v3 slate onward.

    RAW OBSERVATIONS ONLY. No verdicts, no interpretation. The model draws its
    own conclusions (or none). The small-sample warning is the first thing read.
    """
    if not model:
        return ""
    bdir = project_root / "bankroll" / sport
    cfg_path = bdir / "_config.json"
    if not cfg_path.exists():
        return ""
    try:
        cfg = json.loads(cfg_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return ""
    v3_start = cfg.get("v3_start_date")
    if not v3_start or date < v3_start:
        return ""  # pre-v3 slate -> no block at all

    acct_path = bdir / f"{model}.json"
    start_bal = float(cfg.get("starting_balance", 10000.0))

    L = [DIVIDER,
         "YOUR ACCOUNT — v3 bankroll (your own history only)",
         DIVIDER]

    acct = None
    if acct_path.exists():
        try:
            acct = json.loads(acct_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            acct = None

    n_bets = acct["summary"]["bets"] if acct else 0

    # ── Empty case: no settled bets yet (expected for the first v3 slates) ──
    if not acct or n_bets == 0:
        L.append(
            f"Balance: ${start_bal:,.2f} (starting balance). No settled bets yet — v3 has "
            "just begun. There is nothing to analyze. Pick on your method alone this slate."
        )
        return "\n".join(L) + "\n"

    s = acct["summary"]
    bal = acct["current_balance"]
    net = bal - start_bal
    net_sign = "+" if net >= 0 else "-"
    risked = s.get("dollars_risked", 0.0)
    roi = s.get("roi_pct")
    roi_str = f"{roi:+.1f}%" if roi is not None else "n/a"
    avg_clv = s.get("avg_clv")
    clv_str = f"{avg_clv:+.1f}c average over {s.get('clv_count', 0)} bets" if avg_clv is not None \
        else f"n/a ({s.get('clv_count', 0)} bets with closing line)"
    bt = s["by_type"]

    L += [
        f"SMALL-SAMPLE WARNING: {n_bets} settled bets is far too few to draw reliable",
        "conclusions about your method. Variance dominates at this size. These are",
        "raw observations, not verdicts — do not overfit. Drawing no conclusion is",
        "a valid response.",
        "",
        f"Balance: ${bal:,.2f}   (start ${start_bal:,.2f} — net {net_sign}${abs(net):,.2f})",
        f"Record:  {s['wins']}-{s['losses']}-{s['pushes']} (W-L-P) over {n_bets} settled bets",
        f"ROI:     {roi_str} on ${risked:,.0f} risked",
        f"CLV:     {clv_str}",
        "",
        "By bet type — THREE OVERLAPPING VIEWS of the SAME bets. Each of the three",
        "groups (fav/dog, stake size, market) independently sums to your total bet",
        "count; categories are NOT additive across groups. Fav/dog is split purely by",
        "odds sign (−odds vs +odds), so a −110 coinflip and a −350 heavy favorite both",
        "count as \"favorite.\"",
        "  (bets / W-L / net $)",
        f"  Favorites (−odds):  {_fmt_bucket(bt['favorite'])}",
        f"  Underdogs (+odds):  {_fmt_bucket(bt['underdog'])}",
        "  ----",
        f"  1-unit bets:        {_fmt_bucket(bt['1u'])}",
        f"  3-unit bets:        {_fmt_bucket(bt['3u'])}",
        "  ----",
        f"  Moneyline:          {_fmt_bucket(bt['ml'])}",
        f"  Run line:           {_fmt_bucket(bt['rl'])}",
        f"  Totals (O/U):       {_fmt_bucket(bt['total'])}",
        "",
    ]

    # ── Leaderboard: own rank + gap-to-leader only (no other models' details) ──
    lb_path = bdir / "_leaderboard.json"
    if lb_path.exists():
        try:
            lb = json.loads(lb_path.read_text(encoding="utf-8"))
            ranks = lb.get("ranks", [])
            total_models = len(ranks)
            my_row = next((r for r in ranks if r["model"] == model), None)
            leader = ranks[0] if ranks else None
            if my_row and leader:
                gap = my_row["balance"] - leader["balance"]
                gap_sign = "+" if gap >= 0 else "-"
                L.append(f"Leaderboard: you are rank {my_row['rank']} of {total_models}. "
                         f"Leader has ${leader['balance']:,.2f}.")
                L.append(f"Gap to leader: {gap_sign}${abs(gap):,.2f}.")
                L.append("")
        except (json.JSONDecodeError, KeyError, IndexError):
            pass

    L += [
        "These are facts about YOUR OWN past bets only. You cannot see other",
        "competitors' picks or methods. Reason from your own method; use this",
        "history only insofar as the sample supports it.",
    ]
    return "\n".join(L) + "\n"


# ─────────────────────────────────────────────────────────────────────────────
# PROMPT ASSEMBLER
# ─────────────────────────────────────────────────────────────────────────────

def build_prompt(games: list, sport: str, date: str, model: str | None = None, static_data: dict | None = None) -> str:
    """
    Assemble the USER MESSAGE portion of the prompt: slate header + game blocks.
    Instructions, staking rules, output format, and model-specific content are
    in the SYSTEM prompt (build_system_prompt). This file is the daily data only.
    """
    sport_label = SPORT_LABELS.get(sport, sport.upper())

    # ── Date display ──────────────────────────────────────────────────────────
    dt      = datetime.strptime(date, "%Y-%m-%d")
    weekday = dt.strftime("%A")   # "Monday"
    month   = dt.strftime("%B")   # "June"
    day     = dt.day              # 2  (integer — no leading zero)
    year    = dt.year             # 2026

    # ── Prompt generation time ────────────────────────────────────────────────
    # Recorded so the AI knows how fresh the data is.
    # "Built at 3:42 AM ET" signals umpires aren't posted yet.
    # "Built at 4:30 PM ET" signals umpires and lineups are confirmed.
    now    = datetime.now(ET)
    hour12 = now.hour % 12 or 12
    period = "AM" if now.hour < 12 else "PM"
    gen_time = f"{hour12}:{now.minute:02d} {period} ET"

    # ── Max book count ────────────────────────────────────────────────────────
    # Tells the AI how many books the consensus median is derived from.
    # We show the max across all games (some games have fewer books covered).
    n_books = max(
        (len(g.get("odds", {}).get("current", {}).get("bookmakers", []))
         for g in games),
        default=0,
    )

    # ─────────────────────────────────────────────────────────────────────────
    # PART 1: HEADER
    # ─────────────────────────────────────────────────────────────────────────
    parts = [
        DIVIDER,
        f"{sport_label} SLATE — {weekday}, {month} {day} {year} (US Eastern Time)",
        f"{len(games)} games | Prompt built at {gen_time} | Source: TheOddsAPI median of {n_books} books",
        DIVIDER,
        "",
    ]

    # ── Detect global boilerplate to hoist ───────────────────────────────────
    # Lineups: if fetch_lineups.py ran for ANY game and ALL statuses are unconfirmed,
    # say it once in the header and suppress per-game LINEUPS blocks.
    def _lineup_status(g):
        lu = (g.get("context") or {}).get("lineups")
        if lu is None:
            return None  # never fetched
        away_s = lu.get("away", {}).get("status", "not_yet_confirmed")
        home_s = lu.get("home", {}).get("status", "not_yet_confirmed")
        if away_s == "not_yet_confirmed" and home_s == "not_yet_confirmed":
            return "unconfirmed"
        return "confirmed"

    statuses = [_lineup_status(g) for g in games]
    lineups_fetched = any(s is not None for s in statuses)
    all_lineups_unconfirmed = lineups_fetched and all(s in (None, "unconfirmed") for s in statuses)

    # Umpires: if ALL games have no umpire assigned, say it once in header.
    def _umpire_assigned(g):
        u = (g.get("context") or {}).get("umpire")
        return bool(u and u.get("name"))

    all_umpires_unassigned = not any(_umpire_assigned(g) for g in games)

    if all_lineups_unconfirmed:
        parts.append("[All lineups unconfirmed at build time — run fetch_lineups.py closer to game time]")
        parts.append("")
    if all_umpires_unassigned:
        parts.append("[Plate umpires not yet assigned for this slate]")
        parts.append("")

    # ── v3 bankroll account injection ─────────────────────────────────────────
    # Raw own-history observations, gated on V3_START_DATE. Returns "" for pre-v3
    # slates, so v2 prompts are unchanged. Sits before the game blocks so the
    # model reads its standing, then handicaps the slate.
    account_block = render_account_block(model, sport, date, Path(__file__).resolve().parent.parent)
    if account_block:
        parts.append(account_block)
        parts.append("")

    hoist_lu  = all_lineups_unconfirmed
    hoist_ump = all_umpires_unassigned

    # Instructions, staking rules, output format and model-specific text all
    # live in build_system_prompt() / system_{model}.md — NOT in this file.
    # ─────────────────────────────────────────────────────────────────────────
    # PART 2: GAME BLOCKS
    # ─────────────────────────────────────────────────────────────────────────
    # ── Game blocks ───────────────────────────────────────────────────────────
    for i, game in enumerate(games, start=1):
        parts.append(build_game_block(game, i, len(games), sport, static_data=static_data,
                                      hoist_lineups=hoist_lu, hoist_umpire=hoist_ump))

    parts.append("")
    parts.append("BEFORE SUBMITTING: apply the edge gate, slate ceiling, and 1u/3u rule")
    parts.append("from YOUR OWN method document. Respect the fixed data-integrity rules")
    parts.append("(TBD starter = PASS, stale price = absent, postponed = PASS).")
    parts.append("")

    return "\n".join(parts)


    # ── ORIGINAL INSTRUCTION TEXT BELOW -- moved to build_system_prompt() ──
    # Kept as dead code for reference. Do not delete; update system prompt instead.
    if False:  # noqa
        parts.append(
        f"YOU ARE A PROFESSIONAL BETTOR, NOT AN ANALYST.\n"
        f"\n"
        f"  An analyst's job is to produce insight on every game.\n"
        f"  Your job is to find the two or three times per week when\n"
        f"  the market has made a meaningful pricing mistake -- and\n"
        f"  bet those moments correctly.\n"
        f"\n"
        f"  The difference in practice:\n"
        f"\n"
        f"  An analyst looks at 15 games and finds 6 interesting angles.\n"
        f"  You look at 15 games and find 13 correctly priced games,\n"
        f"  1 marginal lean, and 1 genuine edge worth a 1-unit bet.\n"
        f"  That is a good day's work. The 13 passes are not failures --\n"
        f"  they are proof you are not fooling yourself.\n"
        f"\n"
        f"  Your only performance metric is unit-weighted ROI over\n"
        f"  hundreds of bets. Nothing else matters. A 40-35 record\n"
        f"  with +4% ROI beats a 180-170 record with +0.8% ROI.\n"
        f"  The first bettor knows when they have an edge.\n"
        f"  The second bettor is grinding noise.\n"
        f"\n"
        f"  Before you evaluate a single game, accept this:\n"
        f"  The most likely outcome of today's slate is that you\n"
        f"  find nothing worth betting. That is not a problem.\n"
        f"  That is the correct answer most days.\n"
        f"\n"
        f"HOW TO APPROACH THIS:\n"
        f"\n"
        f"  Use the data below as your foundation.\n"
        f"  If you have web access, you MAY look up additional information you think\n"
        f"  matters — bullpen usage, lineup news, recent form, splits, injuries, park\n"
        f"  factors. State clearly what you looked up and what you found. If you cannot\n"
        f"  browse, say so and work from the data given.\n"
        f"  Reason however you think is best. There is no required formula. Use your\n"
        f"  own judgment on how to weigh pitching, matchups, weather, and market price.\n"
        f"  Two good analysts will disagree — that is expected and fine.\n"
        f"\n"
        f"UNIT SCALE (how much you would actually bet):\n"
        f"\n"
        f"  3 units = STRONG PLAY. Clear, identified market mispricing.\n"
        f"            Minimum 7-point probability gap. Confirmed clean data.\n"
        f"            Rare -- a few times per week across all models combined.\n"
        f"            This is the ceiling. There is no higher rating.\n"
        f"  1 unit  = STANDARD PLAY. Real but ordinary edge. 4-7 point gap.\n"
        f"            The most common published rating.\n"
        f"  LEAN    = Slight lean exists. Gap under 4 points. Zero stake.\n"
        f"            Noted in the log. Never published as a bet.\n"
        f"  PASS    = No edge found. The correct answer on most games.\n"
        f"\n"
        f"PROFESSIONAL STANDARD:\n"
        f"\n"
        f"  This service tracks unit-weighted ROI over hundreds of bets.\n"
        f"  Pick volume is not a measure of quality. It is a warning sign.\n"
        f"\n"
        f"  A professional bettor passes on roughly 85-90% of available games.\n"
        f"  On a 15-game slate, finding 1 genuine bet is a strong day.\n"
        f"  Finding 3 is exceptional and should trigger a self-audit.\n"
        f"  Finding 5 or more means you are manufacturing edge.\n"
        f"\n"
        f"  The correct answer on most games is PASS. Pass confidently.\n"
        f"  A skip day -- where no game clears the betting threshold --\n"
        f"  is not a failure. It is discipline, and it will be published\n"
        f"  as such. That transparency is what makes this service credible\n"
        f"  to serious bettors.\n"
        f"\n"
        f"  If you are finding 3-unit plays on more than one game per slate,\n"
        f"  go back and recheck your gap calculations. Multiple 3-unit plays\n"
        f"  on the same slate is a red flag, not a strong slate.\n"
        f"\n"
        f"STAKING DISCIPLINE:\n"
        f"\n"
        f"  Before assigning any bet, state three things explicitly:\n"
        f"    (a) Your estimated win probability as a percentage\n"
        f"    (b) The implied probability of the offered price\n"
        f"        (implied prob = 100 / (100 + positive_odds) for underdogs,\n"
        f"         or |negative_odds| / (|negative_odds| + 100) for favourites)\n"
        f"    (c) The gap between (a) and (b) in percentage points\n"
        f"\n"
        f"  Then apply this hard mapping. No exceptions:\n"
        f"    Gap under 4 points       -> LEAN or PASS. Never a bet.\n"
        f"    Gap 4-7 points           -> 1 unit maximum\n"
        f"    Gap 7+ points, confirmed clean data -> 3 units maximum\n"
        f"\n"
        f"  3 units is the ceiling. There is no higher rating.\n"
        f"  Narrative richness does not increase units.\n"
        f"  A bet with six supporting factors but a 5-point gap is a 1-unit bet.\n"
        f"  A bet with one clean factor and a 9-point gap is a 3-unit bet.\n"
        f"  The gap wins. Always.\n"
        f"\n"
        f"MINIMUM EDGE GATE:\n"
        f"\n"
        f"  A bet requires a minimum gap of 4 percentage points between your\n"
        f"  estimated win probability and the market implied probability.\n"
        f"  Below 4 points the answer is LEAN or PASS. Always.\n"
        f"\n"
        f"  This threshold cannot be overridden by:\n"
        f"    - A rich narrative or multiple supporting factors\n"
        f"    - An attractive price or plus-money line\n"
        f"    - Line movement in your direction\n"
        f"    - Momentum, recent form, or gut feel\n"
        f"\n"
        f"  A 3.8-point gap with six supporting factors is a LEAN.\n"
        f"  A 4.2-point gap with one clean factor is a 1-unit bet.\n"
        f"  The gap is the only variable that determines whether a bet exists.\n"
        f"\n"
        f"RUN LINE NOTE:\n"
        f"\n"
        f"  A run line (-1.5) is a different bet from the moneyline — it requires\n"
        f"  the team to win by 2+ runs, not just win. A heavy ML favourite is often\n"
        f"  only ~50% to cover -1.5. Price the run line on its own merits.\n"
        f"\n"
        f"UNDERDOG NOTE:\n"
        f"\n"
        f"  Plus-money underdogs with genuine edge can be strong value. Compare\n"
        f"  your own win-probability estimate to the price implied by the odds\n"
        f"  before deciding.\n"
        f"\n"
        f"BULLPEN FATIGUE RULE:\n"
        f"\n"
        f"  Bullpen state affects win probability. Quantify it, do not just note it.\n"
        f"  Apply these adjustments to your estimated win probability before staking:\n"
        f"\n"
        f"  If the starting pitcher is likely to exit before the 6th inning\n"
        f"  (opener, bulk reliever, or last-3-starts average IP under 5.0):\n"
        f"    - Identify the team's top 3 relief arms by role (CL, SU, MR)\n"
        f"    - If 2 or more of those arms pitched in the last 2 days: -3 points\n"
        f"    - If the closer is unavailable or taxed: -2 points\n"
        f"\n"
        f"  If the starter is projected to go 6+ innings (last-3-starts avg IP >= 5.0):\n"
        f"    - Bullpen fatigue adjustment applies only if the game is projected\n"
        f"      to be close (implied total under 9.0 and ML within -140/+120)\n"
        f"    - Same adjustments as above if applicable\n"
        f"\n"
        f"  A fatigue flag in the data is not sufficient. You must state the\n"
        f"  specific adjustment you applied and recalculate your gap accordingly.\n"
        f"  If you note fatigue but do not adjust, you are not using the data.\n"
        f"\n"
        f"ODDS APPROACH:\n"
        f"  Line movement from open to now is shown where available — use it as a\n"
        f"  signal of where money is going if you find it useful.\n"
        f"  There is no hard odds ceiling or floor. Any market is eligible if you\n"
        f"  identify genuine edge.\n"
        f"  SINGLES — bet any side where your estimated win probability clearly exceeds\n"
        f"  the implied probability. The bigger the gap, the stronger the play. Do NOT\n"
        f"  avoid plus-money underdogs — a +200 dog that genuinely wins 40% of the time\n"
        f"  is strong value and pays better than a -110 favourite at 52%. Do NOT bet\n"
        f"  heavy favourites just because they will probably win — if -200 is fairly\n"
        f"  priced at ~67%, there is no edge there.\n"
        f"  HEAVY FAVOURITES — when a moneyline is heavier than -180, consider that\n"
        f"  team's -1.5 run line instead — it is usually plus-money and a more efficient\n"
        f"  way to back a strong favourite.\n"
        f"BEFORE PICKING ANY SIDE: estimate a fair moneyline for this game using team\n"
        f"  quality, pitching, and matchup factors — before reading the market price.\n"
        f"  Write it down mentally. Then compare your estimate to the actual line. If\n"
        f"  the market price is within 10 cents of your estimate, there is likely no\n"
        f"  edge. If it is 15+ cents away, investigate why the market disagrees with\n"
        f"  you. This prevents anchoring to the offered price.\n"
        f"\n"
        f"  2-LEG PARLAY — you MAY suggest ONE 2-leg moneyline parlay, but only if:\n"
        f"\n"
        f"    Both legs are independently identified as having edge in your game-by-game\n"
        f"    analysis (never parlay games you would otherwise pass)\n"
        f"    Neither leg is shorter than -180 individually\n"
        f"    The games have no obvious correlation (not same division, not both\n"
        f"    weather-affected, not the same travel pattern)\n"
        f"    A parlay is optional — only include it if it genuinely adds value\n"
    )

    parts.append(
        "RUN LINE (RL) APPROACH\n"
        "The Run Line and the Moneyline are SEPARATE markets. Evaluate both independently.\n"
        "\n"
        "  When to prefer RL over ML:\n"
        "    - You have a 7+ pt edge on a team BUT the ML price is -140 or worse.\n"
        "      Check if RL -1.5 at better odds still gives 4+ pts of edge. If yes,\n"
        "      RL -1.5 offers better EV than ML. Bet RL instead.\n"
        "    - You have a moderate edge (4-6 pts) on the underdog. RL +1.5 at better\n"
        "      price may convert a marginal ML play into a clear edge.\n"
        "    - Line movement shows RL price tightening (sharp action covering the 1.5).\n"
        "\n"
        "  When RL does NOT help:\n"
        "    - Your edge is marginal (4-5 pts) on the favourite — RL -1.5 shrinks the\n"
        "      win probability enough to erase the edge. Stick with ML or pass.\n"
        "    - A coinflip game — neither side RL makes sense.\n"
        "\n"
        "  Syntax: PICK: TOR RL or PICK: BOS RL (parser infers -1.5 for favourite,\n"
        "  +1.5 for underdog from the matchup odds). Price is the RL price.\n"
    )

    parts.append(
        "TOTALS APPROACH\n"
        "Totals and sides are INDEPENDENT MARKETS. A game can produce one side bet\n"
        "(ML or RL) AND one totals bet. Both count toward the slate ceiling.\n"
        "The TOTAL field in the output format is a full betting slot — not a note.\n"
        "\n"
        "Evaluate totals using this sequence for every game:\n"
        "\n"
        "  1. Estimate expected combined runs using L10 RS/G where available:\n"
        "       (Away L10 RS/G + Home L10 RA/G + Home L10 RS/G + Away L10 RA/G) / 2\n"
        "       Use season RS/G if L10 is absent.\n"
        "  2. Adjust for park factor — a factor of 105 adds roughly +0.3 to +0.5 runs;\n"
        "       a factor of 95 subtracts the same. Coors always inflates.\n"
        "       For retractable roofs: use roof-closed factors if rain/cold expected.\n"
        "  3. Adjust for starter quality — elite starter (xFIP < 3.50) suppresses\n"
        "       0.5-0.8 runs. Small-sample/opener starter adds 0.3-0.5 (bullpen game).\n"
        "  4. Adjust for bullpen — taxed bullpen on either side adds 0.3-0.5 runs late.\n"
        "  5. Adjust for wind — blowing out >12 mph adds +0.3 to +0.5; in subtracts.\n"
        "  6. State your estimated total as a number, then the gap vs the posted line.\n"
        "       A gap of 1.0+ runs IS a bettable edge if two or more factors align.\n"
        "       A gap of 0.5-0.9 runs = lean only. Under 0.5 = no bet.\n"
        "  7. Total line movement of 0.5+ points = sharp action — factor it in.\n"
        "\n"
        "  TOTALS CONFIRMATION RULE: At least TWO of the five factors (park, starter\n"
        "  quality, bullpen, wind, run-scoring environment) must point the same way\n"
        "  for a totals BET. One factor alone = lean only, not a bet.\n"
        "\n"
        "  Strong UNDER: elite starter matchup, pitcher-friendly park, cold/wind-in,\n"
        "    dome/roof closed.\n"
        "  Strong OVER: weak/small-sample starters, hitter-friendly park (esp. Coors),\n"
        "    wind out, both bullpens taxed, warm humid weather.\n"
        "\n"
        "  PARK CAUTION: In parks with runs factor above 115, Under bets carry extreme\n"
        "  variance regardless of starter quality. Hard caution — do not fade it.\n"
    )

    parts.append(
        "TEAM QUALITY CHECK:\n"
        "\n"
        "  Before finalising any moneyline or run line bet, confirm:\n"
        "    (a) Run differential gap between the two teams\n"
        "    (b) RS/G gap between the two teams\n"
        "    (c) L10 RS/G gap -- current offensive form\n"
        "\n"
        "  If the team you are backing trails in ALL THREE of (a), (b), and (c),\n"
        "  apply a one-tier downgrade:\n"
        "    - A 3-unit bet becomes 1 unit maximum\n"
        "    - A 1-unit bet becomes a LEAN\n"
        "    - A LEAN becomes a PASS\n"
        "\n"
        "  This downgrade can be overridden ONLY if you can document a specific\n"
        "  structural reason the run differential gap is misleading -- for example:\n"
        "    - Recent key injury to the opponent's rotation now resolved\n"
        "    - Extreme early-season schedule imbalance now corrected\n"
        "    - Opponent's run differential inflated by 2-3 blowout outlier games\n"
        "\n"
        "  Override logic must be stated explicitly. \"The pitching matchup\n"
        "  favours our side\" is not a valid override -- that is already\n"
        "  captured in your gap calculation. The override must explain why\n"
        "  the run differential data itself is unreliable.\n"
    )

    parts.append(
        "SMALL SAMPLE CHECK:\n"
        "\n"
        "  If either starter is marked [small sample] or [sm] in the pitcher block:\n"
        "    - No 3-unit play or Best Bet designation on that game.\n"
        "    - Cite at least one non-ERA indicator (K/9, K-BB%, Brl%, L3 ERA trend,\n"
        "      or last-3-starts data) if you bet at all. ERA is not predictive.\n"
        "\n"
        "  VOLUME FLOOR (applies even without a [small sample] flag):\n"
        "    - A starter with fewer than 60 IP in the AGG section is below the\n"
        "      3-unit volume floor. Assign 1 unit maximum on games where that\n"
        "      starter's AGG xFIP/SIERA is your primary edge signal.\n"
        "    - A starter with fewer than 8 starts in the AGG section carries\n"
        "      the same 1-unit ceiling regardless of ERA/xFIP quality.\n"
        "    - Exception: if the volume-floor starter is on the OPPOSING side\n"
        "      (i.e. you are fading them), the floor does not apply to your\n"
        "      stake — but you must state you are fading a small-volume arm.\n"
        "\n"
        "  SIERA SPIKE RULE:\n"
        "    - If a starter's AGG SIERA exceeds their AGG xFIP by more than\n"
        "      0.50 (e.g. SIERA 4.85, xFIP 4.20), that divergence is a red\n"
        "      flag for contact management issues not captured by strikeout\n"
        "      and walk rates alone. Do NOT base a 3-unit play solely on xFIP\n"
        "      when SIERA diverges this sharply — require a corroborating\n"
        "      indicator (L14 trends, Brl%, platoon advantage, park factor).\n"
        "\n"
        "OPENER/BULK FLAG:\n"
        "\n"
        "  If either starter has 5.0 or fewer innings pitched for the season\n"
        "  total (shown in the IP field), treat them as a probable opener or\n"
        "  bulk-use scenario rather than a traditional starter. Explicitly\n"
        "  reframe that team's pitching matchup as: \"[Team] is effectively\n"
        "  running a bullpen game today.\" Evaluate the matchup against their\n"
        "  full bullpen quality, not the listed starter's stats.\n"
        "\n"
        "TBD STARTER RULE:\n"
        "\n"
        "  Do not bet any game where either starter is listed TBD.\n"
        "  A TBD starter is an unresolved structural risk -- the entire\n"
        "  pitching matchup input is unreliable when one arm is unknown.\n"
        "  No edge calculation is valid when a key input is missing.\n"
        "  PASS the game regardless of all other factors including edge size,\n"
        "  team form, odds movement, or how attractive the price looks.\n"
        "\n"
        "SLATE DISCIPLINE CHECK -- complete this before your first pick:\n"
        "\n"
        "  Count the games on this slate. Apply these hard ceilings:\n"
        "    1-7 games:   1 bet maximum. 0 is fine.\n"
        "    8-14 games:  2 bets maximum. 1 is fine. 0 is fine.\n"
        "    15+ games:   3 bets maximum. 1-2 is normal. 0 is fine.\n"
        "\n"
        "  These are hard ceilings, not targets.\n"
        "  Of those bets, expect at most ONE to reach 3 units on any slate.\n"
        "  Multiple 3-unit plays on the same slate is a calibration error.\n"
        "\n"
        "  If you are at or above the ceiling, apply this filter in order:\n"
        "    1. Drop any pick where your gap is under 5 points\n"
        "    2. Drop any pick where a key input is unconfirmed or estimated\n"
        "    3. Drop any pick where you cannot state the specific market\n"
        "       inefficiency in one sentence without mentioning team quality\n"
        "       or win-loss record\n"
        "\n"
        "  What survives that filter is your actual pick list.\n"
        "\n"
        "  A 15-game slate that produces 0 bets is a good outcome.\n"
        "  It means the market priced those games correctly.\n"
        "  That is published as a skip day and builds credibility\n"
        "  with serious bettors faster than three marginal picks would.\n"
        "\n"
        "ESTIMATED DATA RULE:\n"
        "\n"
        "  Platoon wRC+ figures in the prompt are labeled one of:\n"
        "    CONFIRMED       — derived from the actual confirmed batting order.\n"
        "                      High trust.\n"
        "    SEASON AGGREGATE — full-season team average from FanGraphs static\n"
        "                      splits files. Valid but not lineup-specific.\n"
        "                      Use as supporting context only.\n"
        "\n"
        "  A metric labeled SEASON AGGREGATE is not fabricated, but it may not\n"
        "  reflect today's actual lineup. You may cite it as one supporting\n"
        "  signal, but it may not be the primary justification for a bet.\n"
        "  Corroborate with at least one independent signal (pitcher metrics,\n"
        "  bullpen state, park factor, or team form) before committing units.\n"
    )

    # ─────────────────────────────────────────────────────────────────────────
    # PART 3: GAME BLOCKS
    # One block per game, in chronological order (games.json is pre-sorted
    # by commence_utc from fetch_odds.py).
    # ─────────────────────────────────────────────────────────────────────────
    for i, game in enumerate(games, start=1):
        parts.append(build_game_block(game, i, len(games), sport, static_data=static_data))

    parts.append(DIVIDER)
    parts.append("")

    # ─────────────────────────────────────────────────────────────────────────
    # PART 4: OUTPUT FORMAT
    # The AI must follow this exactly. Every field matters for log_picks.py:
    #   ## GAME  -> join key back to games.json via abbr pair
    #   PICK     -> side (team name + market, or PASS/LEAN)
    #   PRICE    -> odds at pick time (needed for CLV calculation later)
    #   UNITS    -> stake tier (needed for unit-weighted ROI)
    #   EDGE     -> confidence level (for calibration tracking)
    #   REASON   -> kept for display and model comparison, not parsed numerically
    #   DATA GAP -> data not in the prompt that would have changed this pick (S3 request loop)
    # ─────────────────────────────────────────────────────────────────────────
    parts.append(
        "NOW MAKE YOUR PICKS.\n"
        "\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        "OUTPUT FORMAT — THIS IS MANDATORY. DO NOT DEVIATE.\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        "\n"
        "Your response will be parsed by an automated script. Any deviation from\n"
        "this format — including prose introductions, analysis summaries, markdown\n"
        "tables, or section headings not shown below — will cause your picks to be\n"
        "lost entirely and your record will show 0 bets for the day.\n"
        "\n"
        "REQUIRED: one block for EVERY game on the slate, including passes.\n"
        "A pass is data, not a non-answer.\n"
        "\n"
        "## GAME: {AWAY_ABBR} @ {HOME_ABBR}\n"
        "PICK: [team abbr + ML, or team abbr + RL, or PASS, or LEAN: side]\n"
        "PRICE: [exact American odds e.g. -128, or N/A for PASS]\n"
        "UNITS: [3 / 1 / LEAN / PASS]\n"
        "EDGE: [your gap in percentage points e.g. \"6.2 pts\" — or \"none\" for PASS]\n"
        "TOTAL: [Over {line} / Under {line} / Lean Over / Lean Under / No bet]\n"
        "TOTAL PRICE: [American odds for the total e.g. -110, or N/A]\n"
        "TOTAL UNITS: [1 / LEAN / No bet]\n"
        "TOTAL EDGE: [run gap vs posted line e.g. \"1.4 runs\" — or \"none\"]\n"
        "REASON: [2-4 sentences — cover both side pick and totals analysis]\n"
        "DATA GAP: [data NOT in this prompt that would have changed this pick — or \"none\"]\n"
        "\n"
        "POSTPONEMENT NOTE: If a game is postponed before first pitch, treat it as PASS.\n"
        "Log it as: PICK: PASS | PRICE: N/A | UNITS: PASS | REASON: Postponed — no result.\n"
        "\n"
        "Rules:\n"
        "  - AWAY_ABBR and HOME_ABBR must exactly match the abbreviations in the game data above.\n"
        "  - Separate each game block with ---\n"
        "  - Do NOT write any text before the first ## GAME: block. No pre-analysis,\n"
        "    no slate overview, no thinking-out-loud. The first character of your response\n"
        "    must be '#' (the start of ## GAME:).\n"
        "  - Do NOT write prose summaries, tables, or analysis between or inside game blocks.\n"
        "  - Do NOT include mid-response reasoning such as 'Wait --', 'Let me check',\n"
        "    'Revisiting', or any other thinking text. All reasoning belongs in the\n"
        "    REASON field of the relevant game block — nowhere else.\n"
        "\n"
        "If you have a qualifying 2-leg parlay, add ONE block after all the game blocks:\n"
        "\n"
        "## PARLAY\n"
        "LEG 1: {team abbr} ML {price}\n"
        "LEG 2: {team abbr} ML {price}\n"
        "COMBINED PRICE: {parlay payout e.g. +195}\n"
        "TRUE PROBABILITY ESTIMATE: {your estimate both legs win}\n"
        "UNITS: [1 or 2 — parlays capped at 2 units maximum]\n"
        "REASON: [why both legs have independent edge and are not correlated]\n"
        "\n"
        "Then end with this block — it is required even if you have no parlay:\n"
        "\n"
        "## SLATE SUMMARY\n"
        "BEST BET: [your 3-unit play -- game and units]\n"
        "         [if no 3-unit play exists: NO BEST BET -- no 3-unit play identified today]\n"
        "WHY THIS ONE: [1-2 sentences -- complete only if a 3-unit play exists, otherwise omit]\n"
        "\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        "START YOUR RESPONSE WITH ## GAME: — NOTHING BEFORE IT.\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    )

    # ─────────────────────────────────────────────────────────────────────────
    # PART 5: MODEL-SPECIFIC INSTRUCTION (optional)
    # Only included when --model is passed to build_prompt.py.
    # Derived from post-mortem analysis — each model's recurring reasoning
    # patterns are captured here as a targeted corrective instruction.
    # Omitted entirely when no model is specified so the base prompt.md
    # still works as a generic template for any model.
    # ─────────────────────────────────────────────────────────────────────────
    if model:
        project_root = Path(__file__).parent.parent
        instruction  = load_model_instruction(model, project_root)
        if instruction:
            parts.append("")
            parts.append(DIVIDER)
            parts.append("MODEL-SPECIFIC INSTRUCTION")
            parts.append(DIVIDER)
            parts.append("")
            parts.append(instruction)
            parts.append("")
        else:
            # Not an error — just means this model isn't in MODEL_INSTRUCTIONS.md yet
            print(f"  NOTE: No instruction found for model '{model}' in docs/MODEL_INSTRUCTIONS.md")

    return "\n".join(parts)


# Minimum graded bets before a model's calibration is shown in its prompt.
# Matches calc_calibration.py MIN_SAMPLE — below this the stats are too noisy
# (calc_calibration writes a "PROVISIONAL" warning) and would invite the model
# to over-react to small-sample variance. Gate keeps the feedback signal honest.
CALIBRATION_MIN_SAMPLE = 20


def load_calibration_block(model_name: str, project_root: Path) -> str | None:
    """
    Load the model's calibration summary for injection into its prompt.

    Reads picks/calibration/{model}_calibration.md (written nightly by
    calc_calibration.py) and returns the human-readable summary paragraph ONLY
    — never the raw-stats table.

    Gated: returns None when the file is missing, when graded-bet count is below
    CALIBRATION_MIN_SAMPLE, or when the file is marked PROVISIONAL. This is
    feedback data, not an instruction — the caller frames it as such.
    """
    cal_file = project_root / "picks" / "calibration" / f"{model_name.lower()}_calibration.md"
    if not cal_file.exists():
        return None

    text = cal_file.read_text(encoding="utf-8")

    # Gate 1: explicit provisional marker → too small to show.
    if "PROVISIONAL" in text:
        return None

    # Gate 2: parse the authoritative "| Graded bets | N |" row.
    m = re.search(r"\|\s*Graded bets\s*\|\s*(\d+)\s*\|", text)
    if not m or int(m.group(1)) < CALIBRATION_MIN_SAMPLE:
        return None

    # Extract the summary paragraph: everything from the "Across your last ..."
    # line up to (but not including) the "---" / "## Raw stats" delimiter.
    summary = text.split("\n---", 1)[0]
    start = summary.find("Across your last")
    if start == -1:
        return None
    return summary[start:].strip()


# ─────────────────────────────────────────────────────────────────────────────
# SYSTEM PROMPT BUILDER
# Permanent instructions sent as the system message — no date, no game data.
# ─────────────────────────────────────────────────────────────────────────────

def build_system_prompt(sport_label: str, model: str | None, project_root: Path) -> str:
    """
    Assemble the system prompt from permanent instruction sections.
    Contains: professional bettor identity, staking rules, analytical rules,
    output format, and model-specific instruction.
    This text does NOT change day-to-day and is cached by the API on
    providers that support prompt caching (e.g. Anthropic).
    """
    parts = [
        "# SYSTEM INSTRUCTIONS -- AI CAPPER MLB",
        f"# Model: {model or 'generic'}",
        "# These instructions are sent as the system prompt on every call.",
        "",
        "You are an independent professional sports bettor competing in a long-running",
        "MLB forecasting experiment. You design and apply your own handicapping method.",
        "There is no house methodology to follow. Do not try to reverse-engineer what",
        "the operator wants — there is no preferred way to handicap.",
        "",
        "Your objective is long-term unit-weighted ROI. You are not an analyst and not a",
        "content producer. Passing is the correct action on most games. A slate with no",
        "bet is a valid, often correct, outcome.",
        "",
        "HOW YOU ARE SCORED",
        "Performance is unit-weighted ROI measured against closing line value (CLV).",
        "CLV is the strongest available indicator of process quality: short-term results",
        "are noisy, and a losing wager with positive CLV can reflect better forecasting",
        "than a winning wager with negative CLV. Your estimated probability, the implied",
        "probability, and the gap are tracked across every bet to evaluate your",
        "calibration over time.",
        "",
        "WHAT IS FIXED (the competition rules — identical for every competitor):",
        "",
        "UNIT DENOMINATIONS (fixed — for leaderboard comparability, NOT methodology)",
        "  Every bet is staked at either 1 unit or 3 units. Those are the only two",
        "  stake sizes. LEAN = zero stake (noted, not bet). PASS = no action.",
        "  WHEN to use 1u vs 3u, your minimum edge to bet at all, and how many bets",
        "  you make per slate are YOUR decisions — defined in your method document.",
        "  The best bet is your single highest-conviction 3-unit play, or none.",
        "",
        "YOU AUTHOR YOUR OWN STAKING DISCIPLINE",
        "  There is no house edge gate, no house slate ceiling, and no house",
        "  1u-vs-3u threshold. Your method document states your own edge gate, your",
        "  own max bets per slate (or 'no ceiling'), and your own 1u/3u rule. Apply",
        "  the rules you wrote. State your win-probability estimate and the gap as",
        "  numbers on every bet so your calibration can still be measured.",
        "",
        "TOTALS (Over/Under is a real, stakeable bet — not a note)",
        "Totals are priced in RUNS, not win-probability points. Compare your own",
        "estimated combined runs to the posted total; the gap in runs is your edge.",
        "Your run-gap threshold to bet, and your 1u-vs-3u rule on totals, are YOUR",
        "decisions — defined in your totals method. State your estimated total as a",
        "number and the run gap so it can be measured.",
        "",
        "DATA INTEGRITY (non-negotiable)",
        "  Either starter TBD             -> PASS that game.",
        "  Starter flagged [small sample] -> no 3-unit play on that game.",
        "  Price flagged stale/suspect    -> treat that market as absent.",
        "  Postponed game                 -> PASS.",
        "",
        "HOW YOU REASON IS YOURS",
        "You decide how to weigh pitching, bullpen, offense, park, weather, line",
        "movement, stake size relative to price, and anything else in the data. You",
        "decide what matters and what to ignore. When you bet, state your win-probability",
        "estimate and the gap as numbers so your calibration can be measured. Beyond",
        "that, the method is yours to apply and defend using only the information",
        "available in this slate.",
        "",
        "OUTPUT FORMAT — MANDATORY, MACHINE-PARSED. NO DEVIATION.",
        "One block per game, including passes. No text before the first ## GAME: block.",
        "No prose between blocks. All reasoning lives in the REASON field.",
        "",
        "## GAME: {AWAY_ABBR} @ {HOME_ABBR}",
        "PICK: [team abbr + ML, or RL, or PASS, or LEAN: side]",
        "PRICE: [exact American odds e.g. -128, or N/A for PASS]",
        "UNITS: [3 / 1 / LEAN / PASS]",
        "EDGE: [gap in percentage points e.g. \"6.2 pts\", or \"none\" for PASS]",
        "TOTAL: [Over {line} / Under {line} / Lean Over / Lean Under / No bet]",
        "TOTAL PRICE: [American odds for the total e.g. -110, or N/A]",
        "TOTAL UNITS: [3 / 1 / LEAN / No bet]",
        "TOTAL EDGE: [your run gap vs the posted line e.g. \"1.4 runs\", or \"none\"]",
        "REASON: [2-4 sentences — cover both the side pick and the total]",
        "DATA GAP: [missing data that would have changed this pick, or \"none\"]",
        "",
        "Separate each block with ---",
        "",
        "If you have a qualifying 2-leg parlay, add ONE block after all games:",
        "## PARLAY",
        "LEG 1: {team abbr} ML {price}",
        "LEG 2: {team abbr} ML {price}",
        "COMBINED PRICE: {parlay payout e.g. +195}",
        "TRUE PROBABILITY ESTIMATE: {your estimate both legs win}",
        "UNITS: [1 or 2 — capped at 2 units]",
        "REASON: [why both legs have independent, uncorrelated edge]",
        "",
        "End with:",
        "## SLATE SUMMARY",
        "BEST BET: [your 3-unit play and game, or \"NO BEST BET -- no 3-unit play identified today\"]",
        "WHY THIS ONE: [1-2 sentences only if a 3-unit play exists]",
        "",
        "START YOUR RESPONSE WITH ## GAME: — NOTHING BEFORE IT.",
    ]

    # Model-specific instruction appended last
    if model:
        instruction = load_model_instruction(model, project_root)
        if instruction:
            parts.extend([
                "",
                "MODEL-SPECIFIC INSTRUCTION",
                "",
                instruction,
                "",
            ])

        # Calibration feedback — only once a model has enough graded bets
        # (>= CALIBRATION_MIN_SAMPLE). Framed as data, never as instruction:
        # how the model responds to its own track record is its decision.
        calibration = load_calibration_block(model, project_root)
        if calibration:
            parts.extend([
                "",
                "YOUR CALIBRATION TO DATE (feedback data — not an instruction)",
                "This is your own measured track record from prior slates. It is",
                "information only; how you weigh it is your decision, and it changes",
                "no competition rule.",
                "",
                calibration,
                "",
            ])

    return "\n".join(parts)


# ─────────────────────────────────────────────────────────────────────────────
# ANTHROPIC PROMPT CACHING HELPER
# Used by Anthropic models (opus, sonnet) -- see add_anthropic_model task
# ─────────────────────────────────────────────────────────────────────────────

def build_anthropic_messages_with_cache(system_text: str, prompt_text: str) -> dict:
    """
    Build the messages payload for Anthropic API calls with prompt caching.
    The system prompt (permanent instructions) is marked ephemeral so the
    API caches it across calls -- reducing cost and latency for repeat queries.
    Not called yet; will be wired in when Anthropic models are connected.
    """
    return {
        "system": [
            {
                "type": "text",
                "text": system_text,
                "cache_control": {"type": "ephemeral"},
            }
        ],
        "messages": [
            {"role": "user", "content": prompt_text}
        ],
    }


# ─────────────────────────────────────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────────────────────────────────────

def build_prompt_main(sport: str = "mlb", date: str = None, model: str = None):
    """
    Load games.json for the given sport and date, build the prompt, write it to disk.

    model: optional short model name (e.g. "claude", "kimi"). When provided:
      - A model-specific instruction is appended from docs/MODEL_INSTRUCTIONS.md
      - Output is written to prompt_{model}.md instead of prompt.md
    """
    target_date = date or today_et()

    print(f"\n{'='*55}")
    print(f"  BUILD PROMPT -- {sport.upper()}")
    print(f"  Date: {target_date}")
    if model:
        print(f"  Model: {model}")
    print(f"{'='*55}\n")

    if sport not in SPORT_LABELS:
        print(f"ERROR: Unknown sport '{sport}'.")
        print(f"  Valid: {list(SPORT_LABELS.keys())}")
        sys.exit(1)

    project_root = Path(__file__).parent.parent
    games_path   = project_root / "data" / sport / target_date / "games.json"

    if not games_path.exists():
        print(f"ERROR: games.json not found at {games_path}")
        print("  Run fetch_odds.py first.")
        sys.exit(1)

    with open(games_path, encoding="utf-8") as f:
        games = json.load(f)

    print(f"Loaded {len(games)} games")

    # Warn about missing context — but continue, partial data is usable
    ctx_list     = [g.get("context") or {} for g in games]
    no_pitchers  = sum(1 for c in ctx_list if not c.get("pitcher_away"))
    no_weather   = sum(1 for c in ctx_list if not c.get("weather"))
    no_umpire    = sum(1 for c in ctx_list if not (c.get("umpire") or {}).get("name"))
    no_teamstats = sum(1 for c in ctx_list if not c.get("team_away"))

    no_bullpen   = sum(1 for c in ctx_list if not c.get("bullpen_away"))

    if no_pitchers:  print(f"  NOTE: {no_pitchers} game(s) missing pitcher data (TBD shown)")
    if no_weather:   print(f"  NOTE: {no_weather} game(s) missing weather data")
    if no_umpire:    print(f"  NOTE: {no_umpire} game(s) have no plate umpire assigned yet")
    if no_teamstats: print(f"  NOTE: {no_teamstats} game(s) missing team stats -- run fetch_teamstats.py")
    if no_bullpen:   print(f"  NOTE: {no_bullpen} game(s) missing bullpen data -- run fetch_bullpen.py")

    # Build-time CF bearing estimate warning — lists every venue where the
    # bearing in CF_BEARINGS is flagged as an estimate, so the operator can
    # track which parks still need verification against a published source.
    est_venues = sorted({
        c.get("weather", {}).get("venue", "")
        for c in ctx_list
        if c.get("weather", {}).get("cf_bearing_est") is True
    } - {""})
    if est_venues:
        print(f"  CF BEARING ESTIMATES ({len(est_venues)} venue(s)) — verify against "
              f"Andrew Clem (andrewclem.com/Baseball) or Seamheads (seamheads.com/ballparks):")
        for v in est_venues:
            print(f"    {v}")

    # ── Load static FanGraphs reference data (MLB only) ───────────────────────
    # These files are manually refreshed weekly and don't change per-game.
    # Loaded once here so every call to build_game_block() reuses the same dicts.
    static_data = None
    if sport == "mlb" and _STATIC_DATA_AVAILABLE:
        print("Loading static FanGraphs data...")
        static_data = {
            "splits_lhp":      load_splits_vs_lhp(),
            "splits_rhp":      load_splits_vs_rhp(),
            "splits_home":     load_splits_home(),
            "splits_away":     load_splits_away(),
            "pitchers_season": load_pitchers_season(),
            "pitchers_l14":    load_pitchers_last14(),
            "stuff_plus":      load_stuff_plus(),    # col 10 of pitchers_xfip_siera.txt
            "pitchers_bb":     load_pitchers_season_batted_ball(),  # LD%/GB%/FB% from pitchers_season_ld_gb_fb.txt
            "bullpen":         load_bullpen(),
            "park_factors":    load_park_factors(),
            "park_roof":       load_park_factors_roof_closed(),
            "team_barrels":    load_team_barrels(),
            # Convert YYYY-MM-DD to the column-header format used in lineup_tracker.txt
            # e.g. "2026-06-18" → "Thu 6/18"  (abbreviated weekday, no leading zero on month/day)
            "lineup_tracker":  load_lineup_tracker(
                datetime.strptime(target_date, "%Y-%m-%d").strftime("%a %-m/%-d")
                if not sys.platform.startswith("win")
                else datetime.strptime(target_date, "%Y-%m-%d").strftime("%a %#m/%#d")
            ),
        }
        print("  Static data loaded.")

    print("\nBuilding prompt...")
    sport_label = SPORT_LABELS.get(sport, sport.upper())

    # Build the two-file output: system_{model}.md and prompt_{model}.md
    prompt_text = build_prompt(games, sport, target_date, model=model, static_data=static_data)
    system_text = build_system_prompt(sport_label, model, project_root)

    out_dir  = project_root / "daily" / sport / target_date
    out_dir.mkdir(parents=True, exist_ok=True)

    # User message file — slate data (daily, smaller)
    prompt_filename = f"prompt_{model}.md" if model else "prompt.md"
    prompt_path     = out_dir / prompt_filename

    # System prompt file — permanent instructions (stable day-to-day)
    system_filename = f"system_{model}.md" if model else "system.md"
    system_path     = out_dir / system_filename

    with open(prompt_path, "w", encoding="utf-8") as f:
        f.write(prompt_text)
    with open(system_path, "w", encoding="utf-8") as f:
        f.write(system_text)

    p_chars = len(prompt_text)
    s_chars = len(system_text)
    print(f"Saved user msg  -> {prompt_path.relative_to(project_root)}  ({p_chars:,} chars)")
    print(f"Saved system    -> {system_path.relative_to(project_root)}  ({s_chars:,} chars)")
    print(f"Combined total  : {p_chars + s_chars:,} chars")

    print(f"\n{'='*55}")
    print(f"  DONE -- system_{model or ''}.md + prompt_{model or ''}.md written")
    print(f"  query_model.py will load both files automatically")
    print(f"{'='*55}\n")


# ─────────────────────────────────────────────────────────────────────────────
# CONFIRM-CHECK PROMPT BUILDER
# ─────────────────────────────────────────────────────────────────────────────

def _find_method_doc(model: str, root: Path) -> tuple:
    """
    Find the highest-version method_{model}_v{N}.md in docs/methods/.
    Returns (content, resolved_path_str). Exits if none found.

    Candidates are sorted lexicographically; this works correctly as long as
    version numbers stay below 10 (v1–v9). If a model ever reaches v10+,
    switch to a numeric sort on the version suffix.
    """
    methods_dir = root / "docs" / "methods"
    pattern     = str(methods_dir / f"method_{model}_v*.md")
    candidates  = sorted(_glob.glob(pattern))
    if not candidates:
        print(f"ERROR: no method doc found for model '{model}' at {pattern}")
        sys.exit(1)
    path    = Path(candidates[-1])
    content = path.read_text(encoding="utf-8")
    return content, str(path)


def _run1_wrc_for_team(
    team_abbr:         str,
    lineup_side:       dict | None,
    projected_lineups: dict | None,
    splits:            dict,
    min_pa_guard:      int = 25,
    min_pa_aggregate:  int = 50,
) -> tuple:
    """
    Reconstruct the Run-1 wRC+ estimate for one team using the same three-tier
    precedence as _fmt_platoon_matchup() — so the before/after comparison is
    apples-to-apples with what the model actually saw in the Run-1 prompt.

    Tier 1 CONFIRMED  — lineups were confirmed at Run-1 build time
    Tier 2 REGULARS   — lineup_tracker.txt recent-actuals order
    Tier 3 AGGREGATE  — full-team season average from splits

    Returns (batter_stats, status_tag) where:
      batter_stats : [(name, wrc_plus, pa), ...]   (empty list if no data)
      status_tag   : "CFM" | "REG" | "AGG"
    """
    # Tier 1: lineup was already confirmed when Run 1 built the prompt
    if (lineup_side is not None
            and lineup_side.get("status") == "confirmed"):
        order  = lineup_side.get("order", [])
        stats  = _lineup_wrc_confirm(order, splits, min_pa=min_pa_guard)
        return stats, "CFM"

    # Tier 2: lineup_tracker.txt recent-actuals order
    proj = (projected_lineups or {}).get(team_abbr, {})
    proj_starters = proj.get("starters", [])
    if proj_starters:
        proj_order = [{"name": p["name"]} for p in proj_starters]
        stats      = _lineup_wrc_confirm(proj_order, splits, min_pa=min_pa_guard)
        return stats, "REG"

    # Tier 3: full-team season aggregate
    fg_code = games_abbr_to_fg(team_abbr) if _STATIC_DATA_AVAILABLE else None
    if not fg_code:
        return [], "AGG"
    batters = [
        (name, data["wrc_plus"], data.get("pa") or 0)
        for name, data in splits.items()
        if data.get("team") == fg_code
        and data.get("wrc_plus") is not None
        and (data.get("pa") or 0) >= min_pa_aggregate
    ]
    return batters, "AGG"


def _lineup_wrc_confirm(order: list, splits: dict, min_pa: int = 25) -> list:
    """
    Look up wRC+ for each batter in a confirmed order list using fuzzy name match.
    Returns [(name, wrc_plus, pa), ...] for players found; others silently omitted.
    Mirrors _lineup_wrc_stats() from the Run-1 path.
    """
    results = []
    for player in order:
        name = player.get("name", "")
        key  = fuzzy_match_player(name, splits) if _STATIC_DATA_AVAILABLE else None
        if key:
            data = splits[key]
            wrc  = data.get("wrc_plus")
            pa   = data.get("pa") or 0
            if wrc is not None:
                results.append((name, wrc, pa))
    return results


def _fmt_wrc_summary(batter_stats: list, vs_hand: str, status_tag: str,
                     min_pa_excl: int = 25, lineup_size: int | None = None) -> str:
    """
    Format a single wRC+ summary line in the same style as the Run-1
    PLATOON MATCHUP block, so before/after numbers are directly comparable.

    Example:
      vs_RHP: wRC+:112(CFM,n=7) Soto134(210) Judge91(180) ...

    lineup_size: expected batter count (9). If provided and len(batter_stats) < 7,
    appends [LOW-MATCH: n/lineup_size] to flag a low-confidence aggregate.
    """
    if not batter_stats:
        return f"  vs_{vs_hand}: wRC+:no-data ({status_tag})"

    qualified = [p for p in batter_stats if p[2] >= min_pa_excl]
    lowpa     = [p for p in batter_stats if p[2] <  min_pa_excl]
    pool      = qualified or batter_stats
    avg_wrc   = round(sum(w for _, w, _ in pool) / len(pool))

    def _bat(p):
        return f"{p[0].split()[-1]}{int(round(p[1]))}({int(p[2])})"

    sorted_stats = sorted(batter_stats, key=lambda x: x[1], reverse=True)
    line = (
        f"  vs_{vs_hand}: wRC+:{avg_wrc}({status_tag},n={len(pool)}) "
        + " ".join(_bat(p) for p in sorted_stats[:8])
    )
    if lowpa:
        line += f" | low-PA<{min_pa_excl}(excl): " + " ".join(_bat(p) for p in lowpa[:4])
    if lineup_size is not None and len(batter_stats) < 7:
        line += f" [LOW-MATCH: {len(batter_stats)}/{lineup_size}]"
    return line


def build_confirm_check_prompt(model: str, sport: str, date: str) -> None:
    """
    Build the confirm-check two-file output for one model:

      daily/{sport}/{date}/confirm_system_{model}.md   — system prompt
          Contains: instructions + full method_{model}_v{N}.md
      daily/{sport}/{date}/confirm_prompt_{model}.md   — user message
          Contains: per-game data blocks (one per confirmed-lineup game
          where this model has a bet or lean)

    The sentinel "---GAME BLOCKS---" in confirm_system_{model}.md marks the
    split point — query_model.py --confirm-check reads the system file,
    strips everything from the sentinel onwards (which is empty in the system
    file), and sends the game-blocks file as the user message.  This exactly
    mirrors the system_{model}.md / prompt_{model}.md split used at Run 1.

    Only games where BOTH teams' lineups are confirmed at call time are
    included.  Games still pending are handled by the auto-HOLD fallback in
    run_lineup_watcher.py.

    Reads:
      picks/{sport}/{date}/{model}.json
      data/{sport}/{date}/games.json
      data/mlb/ static FanGraphs split files (wRC+ lookup)
      docs/methods/method_{model}_v{N}.md

    Writes:
      daily/{sport}/{date}/confirm_system_{model}.md
      daily/{sport}/{date}/confirm_prompt_{model}.md
    """
    root        = Path(__file__).parent.parent
    picks_path  = root / "picks"  / sport / date / f"{model}.json"
    games_path  = root / "data"   / sport / date / "games.json"
    out_dir     = root / "daily"  / sport / date

    if not picks_path.exists():
        print(f"ERROR: picks file not found: {picks_path}")
        sys.exit(1)
    if not games_path.exists():
        print(f"ERROR: games.json not found: {games_path}")
        sys.exit(1)

    picks_doc = json.loads(picks_path.read_text(encoding="utf-8"))
    games_raw = json.loads(games_path.read_text(encoding="utf-8"))

    method_text, method_path = _find_method_doc(model, root)
    print(f"  Method doc       : {method_path}")

    # ── Index games by game_id ────────────────────────────────────────────────
    game_by_id = {g["game_id"]: g for g in games_raw}

    # ── Load static splits for wRC+ (same files as Run 1) ─────────────────────
    if _STATIC_DATA_AVAILABLE:
        splits_lhp         = load_splits_vs_lhp()
        splits_rhp         = load_splits_vs_rhp()
        # lineup_tracker for Run-1 "before" Tier 2 reconstruction.
        # Use the same date-column format as the main build path.
        try:
            date_col = (
                datetime.strptime(date, "%Y-%m-%d").strftime("%a %-m/%-d")
                if not sys.platform.startswith("win")
                else datetime.strptime(date, "%Y-%m-%d").strftime("%a %#m/%#d")
            )
        except ValueError:
            date_col = None
        lineup_tracker = load_lineup_tracker(date_col) if date_col else {}
    else:
        splits_lhp = splits_rhp = lineup_tracker = {}

    # ── Collect this model's bet/lean picks on confirmed-lineup games ─────────
    picks = picks_doc.get("picks", [])
    engaged = []   # list of (pick, game)
    for pick in picks:
        if (pick.get("action") or "").lower() not in ("bet", "lean"):
            continue
        gid  = pick.get("game_id")
        game = game_by_id.get(gid)
        if not game:
            continue
        ctx     = game.get("context") or {}
        lineups = ctx.get("lineups") or {}
        away_lu = lineups.get("away", {})
        home_lu = lineups.get("home", {})
        if (away_lu.get("status") != "confirmed"
                or home_lu.get("status") != "confirmed"):
            continue   # watcher handles auto-HOLD for still-pending games
        engaged.append((pick, game))

    if not engaged:
        print(f"  No confirmed-lineup games for {model} — nothing written.")
        return

    n_games = len({p[0]["game_id"] for p in engaged})
    print(f"  Confirmed games  : {n_games}")
    print(f"  Picks to check   : {len(engaged)}")

    # ── Group picks by game_id so ML+Total on the same game share one block ───
    picks_by_game: dict = defaultdict(list)
    game_obj_by_gid: dict = {}
    for pick, game in engaged:
        gid = pick["game_id"]
        picks_by_game[gid].append(pick)
        game_obj_by_gid[gid] = game

    # ── Build system file (instructions + method doc) ─────────────────────────
    sys_lines = []
    sys_lines.append(f"# LINEUP CONFIRM-CHECK — SYSTEM INSTRUCTIONS")
    sys_lines.append(f"# {sport.upper()}  {date}  model: {model}")
    sys_lines.append("")
    sys_lines.append(
        "Lineups are now confirmed for the games below. During Run 1 you made "
        "picks before lineups were posted. Your task is NOT to re-handicap each "
        "game from scratch. Re-evaluate ONLY whether the specific pre-game edge "
        "you cited still holds given the confirmed batting orders, any key "
        "scratches, and any line movement since Run 1."
    )
    sys_lines.append("")
    sys_lines.append(
        "For each pick, output exactly the four fields shown. "
        "CITED_FACT must name a specific player, wRC+ number, or line move — "
        "not a general impression. NEW_UNITS must equal your original units on "
        "HOLD; 0 on CANCEL; an adjusted number on DOWNGRADE/UPGRADE. "
        "An UPGRADE must respect the gap→units map in your method below. "
        "Do not add new bets not in your Run-1 picks."
    )
    sys_lines.append("")
    sys_lines.append("## YOUR METHOD (gate and unit rules — apply exactly as written)")
    sys_lines.append("")
    sys_lines.append(method_text.strip())
    sys_lines.append("")

    system_text = "\n".join(sys_lines)

    # ── Build prompt file (per-game data blocks) ──────────────────────────────
    prompt_lines = []

    for gid, game_picks in sorted(
        picks_by_game.items(),
        key=lambda kv: game_obj_by_gid[kv[0]].get("commence_et", "")
    ):
        game     = game_obj_by_gid[gid]
        away     = game["away"]
        home     = game["home"]
        ctx      = game.get("context") or {}
        lineups  = ctx.get("lineups") or {}
        away_lu  = lineups.get("away", {})
        home_lu  = lineups.get("home", {})
        umpire   = ctx.get("umpire") or {}

        away_abbr    = away["abbr"]
        home_abbr    = home["abbr"]
        matchup      = f"{away_abbr} @ {home_abbr}"
        pitcher_away = ctx.get("pitcher_away") or {}
        pitcher_home = ctx.get("pitcher_home") or {}
        # AWAY SP hand → HOME batters face this hand
        away_hand = pitcher_away.get("hand")
        # HOME SP hand → AWAY batters face this hand
        home_hand = pitcher_home.get("hand")

        prompt_lines.append(f"## GAME: {matchup}  ({game.get('commence_et', '')})  [gid:{gid}]")
        prompt_lines.append("")

        # ── Run-1 pick(s) ─────────────────────────────────────────────────────
        prompt_lines.append("### YOUR RUN-1 PICK(S)")
        for pick in game_picks:
            action = pick.get("action", "").upper()
            raw    = pick.get("pick_raw", "")
            side   = pick.get("pick_side", "")
            market = (pick.get("pick_market") or "").upper()
            price  = pick.get("price")
            units  = pick.get("units")
            reason = pick.get("reason", "")

            price_str = fmt_american(price) if price is not None else "—"
            units_str = f"{units}u" if units else "LEAN"
            prompt_lines.append(
                f"  {action} {raw}  {price_str}  {units_str}"
                f"  [market:{market} side:{side}]"
            )
            prompt_lines.append(f"  Cited reason: {reason}")
        prompt_lines.append("")

        # ── Line movement since Run 1 ──────────────────────────────────────────
        opening_snap = game.get("odds", {}).get("opening_snapshot", {})
        current_snap = game.get("odds", {}).get("current_snapshot")
        lm = fmt_line_move(opening_snap, current_snap)
        if lm:
            prompt_lines.append("LINE MOVEMENT SINCE RUN 1:")
            prompt_lines.append(lm)
            prompt_lines.append("")

        # ── Confirmed lineups + before/after wRC+ ─────────────────────────────
        prompt_lines.append("CONFIRMED LINEUPS + PLATOON wRC+ (before → after):")
        prompt_lines.append("")

        # (team, lineup_side, opp_hand_label, side_label)
        for abbr, lu, opp_hand, side_label in [
            (away_abbr, away_lu, home_hand, "AWAY"),
            (home_abbr, home_lu, away_hand, "HOME"),
        ]:
            order = lu.get("order", [])
            il    = lu.get("il_absences", [])

            prompt_lines.append(f"  {abbr} ({side_label}) confirmed batting order:")
            for p in order:
                prompt_lines.append(
                    f"    {p.get('bat_order', '?')}. {p.get('name', '?')}"
                    f"  {p.get('pos', '')}"
                )

            if il:
                il_str = ", ".join(
                    f"{p['name']} ({p.get('pos', '')})" for p in il
                )
                prompt_lines.append(f"  {abbr} IL: {il_str}")
            else:
                prompt_lines.append(f"  {abbr} IL: none")

            # wRC+ before/after — only when opposing starter hand is known
            if opp_hand:
                splits   = splits_lhp if opp_hand == "L" else splits_rhp
                vs_label = f"{opp_hand}HP"

                # BEFORE: reconstruct what Run-1 would have used
                before_stats, before_tag = _run1_wrc_for_team(
                    abbr, lu, lineup_tracker, splits
                )
                # AFTER: confirmed lineup
                after_stats = _lineup_wrc_confirm(order, splits)
                after_tag   = "CFM"

                before_line = _fmt_wrc_summary(before_stats, vs_label, before_tag, lineup_size=9)
                after_line  = _fmt_wrc_summary(after_stats,  vs_label, after_tag,  lineup_size=9)
                prompt_lines.append(f"  Run-1  {before_line.strip()}")
                prompt_lines.append(f"  Now    {after_line.strip()}")

                # Named diff: only meaningful when Run-1 used projected order (REG tier)
                if before_tag != "CFM":
                    before_names = {s[0].split()[-1].lower() for s in before_stats}
                    after_names  = {s[0].split()[-1].lower() for s in after_stats}
                    scratched    = sorted(before_names - after_names)
                    added        = sorted(after_names  - before_names)
                    if scratched or added:
                        parts = []
                        if scratched:
                            parts.append("SCRATCHED: " + ", ".join(scratched))
                        if added:
                            parts.append("ADDED: " + ", ".join(added))
                        prompt_lines.append(f"  LINEUP CHANGE ({abbr}): " + " | ".join(parts))
            else:
                prompt_lines.append(
                    f"  (opposing starter hand unknown — wRC+ not computed)"
                )

            prompt_lines.append("")

        # ── Required structured response — one block per pick ─────────────────
        prompt_lines.append("### REQUIRED RESPONSE — complete one block per pick:")
        prompt_lines.append("")
        for pick in game_picks:
            market = (pick.get("pick_market") or "").upper()
            raw    = pick.get("pick_raw", "")
            prompt_lines.append(f"PICK: {raw}  [market:{market} gid:{gid}]")
            prompt_lines.append("OUTCOME: HOLD | CANCEL | DOWNGRADE | UPGRADE")
            prompt_lines.append("DRIVER: lineup | price | none")
            prompt_lines.append(
                "CITED_FACT: <specific confirmed-data point — "
                "name a player, a wRC+ number, a line move; not a vibe>"
            )
            prompt_lines.append(
                "NEW_UNITS: <same as original if HOLD; "
                "0 if CANCEL; adjusted number if DOWNGRADE/UPGRADE>"
            )
            prompt_lines.append("")

        prompt_lines.append(DIVIDER)
        prompt_lines.append("")

    # ── Write both files ──────────────────────────────────────────────────────
    out_dir.mkdir(parents=True, exist_ok=True)

    sys_path    = out_dir / f"confirm_system_{model}.md"
    prompt_path = out_dir / f"confirm_prompt_{model}.md"

    sys_path.write_text(system_text,              encoding="utf-8")
    prompt_path.write_text("\n".join(prompt_lines), encoding="utf-8")

    print(f"  System  -> {sys_path.relative_to(root)}  ({len(system_text):,} chars)")
    print(f"  Prompt  -> {prompt_path.relative_to(root)}"
          f"  ({len('\n'.join(prompt_lines)):,} chars)")


# ─────────────────────────────────────────────────────────────────────────────
# ENTRY POINT
# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Build a betting analysis prompt from games.json."
    )
    parser.add_argument(
        "--sport", default="mlb",
        help="Sport code: mlb, nba, nhl, nfl, ncaaf, ncaab  (default: mlb)"
    )
    parser.add_argument(
        "--date", default=None,
        help="Override target date (YYYY-MM-DD). Default: today in US Eastern Time."
    )
    parser.add_argument(
        "--model", default=None,
        help=(
            "Short model name (e.g. claude, chatgpt, gemini, grok, deepseek, "
            "kimi, qwen, sonnet). Appends a model-specific instruction from "
            "docs/MODEL_INSTRUCTIONS.md and writes to prompt_{model}.md."
        )
    )
    parser.add_argument(
        "--confirm-check", action="store_true",
        help=(
            "Build confirm-check prompts instead of the daily slate prompt. "
            "Requires --model. Reads {model}.json picks + confirmed lineups "
            "from games.json. Writes confirm_system_{model}.md and "
            "confirm_prompt_{model}.md to daily/{sport}/{date}/."
        )
    )
    args = parser.parse_args()

    if args.confirm_check:
        if not args.model:
            print("ERROR: --confirm-check requires --model")
            sys.exit(1)
        target_date = args.date or today_et()
        print(f"\n{'='*55}")
        print(f"  CONFIRM-CHECK PROMPT BUILD  {args.sport.upper()}  {target_date}")
        print(f"  Model: {args.model}")
        print(f"{'='*55}\n")
        build_confirm_check_prompt(
            model=args.model,
            sport=args.sport,
            date=target_date,
        )
        print(f"\n{'='*55}")
        print(f"  DONE")
        print(f"{'='*55}\n")
    else:
        build_prompt_main(sport=args.sport, date=args.date, model=args.model)
