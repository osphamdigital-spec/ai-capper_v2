"""
scripts/tz_util.py

Provides ET (US Eastern Time) in a way that works on both:
  - Linux / WSL  (has system timezone database — zoneinfo works natively)
  - Windows      (no system tz database — needs tzdata package OR falls back
                  to a fixed UTC offset)

Import: from tz_util import ET
"""

from datetime import timezone, timedelta

try:
    from zoneinfo import ZoneInfo
    ET = ZoneInfo("America/New_York")
except Exception:
    # Windows without tzdata installed.
    # UTC-5 is EST (winter). EDT (summer, Mar second Sun - Nov first Sun) is UTC-4.
    # For date-only use (today_et()) this is accurate enough — the scripts run
    # in Australian evening which is US morning, well away from midnight ET.
    # If you want full DST accuracy on Windows: pip install tzdata
    import datetime as _dt
    _now_utc = _dt.datetime.now(_dt.timezone.utc)
    _month   = _now_utc.month
    _is_edt  = 3 <= _month <= 11   # rough DST window
    ET = timezone(timedelta(hours=-4 if _is_edt else -5))
    print("  NOTE: tzdata not installed — using fixed UTC offset for ET.")
    print("  For full accuracy on Windows: pip install tzdata")
