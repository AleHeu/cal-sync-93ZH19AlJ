import os
import requests
from datetime import datetime, timezone
from zoneinfo import ZoneInfo
from icalendar import Calendar

ICS_URL = os.environ["OUTLOOK_ICS_URL"]
OUTPUT_FILE = "fixed.ics"

# Zeitzone, in der dein Arbeitskalender geführt wird.
# Wird nur für Termine OHNE jede Zeitzoneninfo ("floating time") verwendet.
LOCAL_TZ = ZoneInfo("Europe/Berlin")


def main():
    resp = requests.get(ICS_URL, timeout=30)
    resp.raise_for_status()
    cal = Calendar.from_ical(resp.content)

    report = []

    for component in cal.walk("VEVENT"):
        summary = str(component.get("SUMMARY", "(ohne Titel)"))
        for field in ("DTSTART", "DTEND"):
            if field not in component:
                continue
            dt = component[field].dt

            # Ganztägige Termine (nur Datum, keine Uhrzeit) unangetastet lassen
            if not isinstance(dt, datetime):
                continue

            original = dt.isoformat()

            if dt.tzinfo is not None:
                # Hat schon eine Zeitzone (egal ob TZID oder bereits UTC) -> sauber nach UTC
                dt_utc = dt.astimezone(timezone.utc)
                status = "tz vorhanden -> normalisiert"
            else:
                # Floating time: keine Zeitzone angegeben -> als Europe/Berlin annehmen
                dt_local = dt.replace(tzinfo=LOCAL_TZ)
                dt_utc = dt_local.astimezone(timezone.utc)
                status = "FLOATING (ohne TZ) -> als Europe/Berlin angenommen"

            del component[field]
            component.add(field, dt_utc)

            report.append(f"[{status}] {summary} | {field}: {original} -> {dt_utc.isoformat()}")

    # Nicht mehr benötigte VTIMEZONE-Blöcke entfernen
    cal.subcomponents = [c for c in cal.subcomponents if c.name != "VTIMEZONE"]

    with open(OUTPUT_FILE, "wb") as f:
        f.write(cal.to_ical())

    print("=== Prüfbericht ===")
    for line in report:
        print(line)
    print(f"\n{len(report)} Zeitangaben geprüft/angepasst.")


if __name__ == "__main__":
    main()
