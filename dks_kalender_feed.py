#!/usr/bin/env python3
"""
Genererer dks_asker.ics — ein ICS-kalender over DKS-programmet i Asker.
Køyrast av GitHub Actions kvar natt og legg fila i docs/ for GitHub Pages.
"""

import json
import re
import sys
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

API_URL = "https://portal.denkulturelleskolesekken.no/api/wordpress/productions/get_calendar_events"
WORDPRESS_HOME = "https://www.denkulturelleskolesekken.no/asker"
OUTPUT = Path("docs/dks_asker.ics")

API_BODY_BASE = {
    "view": "calendar",
    "sort": "date",
    "academicYearId": "",
    "openAllEvents": False,
    "datePeriods": [],
    "includeEvents": True,
    "hideUnspecifiedLocationName": True,
    "includeSchoolDetails": True,
    "wordpressHomeUrl": WORDPRESS_HOME,
}


def fetch_events():
    events = []
    skip = 0
    limit = 100

    while True:
        body = json.dumps({**API_BODY_BASE, "skip": skip, "limit": limit}).encode()
        req = urllib.request.Request(
            API_URL,
            data=body,
            headers={
                "Content-Type": "application/json",
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.0 Safari/605.1.15",
                "Accept": "application/json, */*;q=0.8",
                "Origin": "https://www.denkulturelleskolesekken.no",
                "Referer": "https://www.denkulturelleskolesekken.no/asker",
            },
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=30) as r:
            data = json.loads(r.read())

        batch = data.get("events") or data.get("data") or []
        if not batch:
            break
        events.extend(batch)
        if len(batch) < limit:
            break
        skip += limit

    return events


def str_val(obj):
    if not obj:
        return ""
    if isinstance(obj, str):
        return obj
    if isinstance(obj, dict):
        return obj.get("name") or obj.get("title") or ""
    return str(obj)


def ics_escape(text):
    return (text or "").replace("\\", "\\\\").replace(";", "\\;").replace(",", "\\,").replace("\n", "\\n")


def fmt_ics_date(ts):
    dt = datetime.fromtimestamp(int(ts), tz=timezone.utc)
    return dt.strftime("%Y%m%dT%H%M%SZ")


def fold_line(line):
    """ICS-spesifikasjon: linjer maks 75 teikn, fortsett med CRLF + mellomrom."""
    result = []
    while len(line.encode("utf-8")) > 75:
        result.append(line[:75])
        line = " " + line[75:]
    result.append(line)
    return "\r\n".join(result)


def event_to_vevent(ev):
    title = str_val(ev.get("production")) or str_val(ev.get("tour")) or "DKS-arrangement"
    title = re.sub(r"[,;]", "", title)

    lok = re.sub(r"[,;]", "", str_val(ev.get("location")) or "")

    schools = ev.get("schools") or {}
    school_list = schools if isinstance(schools, list) else list(schools.values())
    skular = ", ".join(s.get("name", "") for s in school_list if s.get("name"))
    elevar = ev.get("numberOfStudents", 0)

    desc_parts = []
    if skular:
        desc_parts.append(f"Skule: {skular}")
    if elevar:
        desc_parts.append(f"Elevar: {elevar}")
    desc = "\n".join(desc_parts)

    start = fmt_ics_date(ev["dateStart"])
    end_ts = ev.get("dateEnd") or (int(ev["dateStart"]) + 3600)
    end = fmt_ics_date(end_ts)

    uid = f"dks-{ev['id']}@asker.dks"

    lines = [
        "BEGIN:VEVENT",
        f"UID:{uid}",
        f"DTSTART:{start}",
        f"DTEND:{end}",
        f"SUMMARY:{ics_escape(title)}",
        f"DESCRIPTION:{ics_escape(desc)}",
        f"LOCATION:{ics_escape(lok)}",
        "END:VEVENT",
    ]
    return "\r\n".join(fold_line(l) for l in lines)


def build_ics(events):
    now = datetime.now(tz=timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    vevents = "\r\n".join(event_to_vevent(ev) for ev in events if ev.get("dateStart"))
    return "\r\n".join([
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//DKS Asker//Kalender//NO",
        "CALSCALE:GREGORIAN",
        "METHOD:PUBLISH",
        f"X-WR-CALNAME:DKS Asker",
        f"X-WR-CALDESC:Den Kulturelle Skolesekken – program for Asker",
        f"LAST-MODIFIED:{now}",
        vevents,
        "END:VCALENDAR",
    ]) + "\r\n"


def main():
    print("Hentar arrangement...", file=sys.stderr)
    events = fetch_events()
    print(f"Henta {len(events)} arrangement.", file=sys.stderr)

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    ics = build_ics(events)
    OUTPUT.write_text(ics, encoding="utf-8")
    print(f"Skreiv {OUTPUT} ({len(events)} arrangement).", file=sys.stderr)


if __name__ == "__main__":
    main()
