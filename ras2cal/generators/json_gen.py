import re
from datetime import datetime, timedelta

from ..utils import merge_events


class JSONScheduleGenerator:
    def __init__(self, model):
        self.model = model

    def generate(self):
        events = []
        for ev in self.model.events:
            events.append(self._to_event(ev))

        return merge_events(events)

    def _to_event(self, ev):
        # Format groups as list of lists (compatibility)
        # IR groups is flat list.
        # But original AST groups was list of lists.
        # If we flattened it in Compiler, we lost that structure.
        # But for JSON sync, flat list [["G1", "G2"]] is fine if they are merged.
        # Or [["G1"], ["G2"]].
        # Compiler flattened it to [G1, G2].
        # Let's verify Compiler:
        # event_groups.append(g) for sublist for g_name
        # It flattened everything.
        # So we output [["G1", "G2"]] (one group list) or individual?
        # merge_events will merge identical events with different groups.
        # So providing individual groups is safer?
        # Actually, `sync.py` handles `grupe` as list of lists.
        # Let's provide `[[g.name] for g in ev.groups]`.

        groups_list = [[g.name] for g in ev.groups]

        return {
            "osoba": ev.teachers[0].name if ev.teachers else "Nepoznato",
            "predmet": ev.subject.name,
            "tip": ev.type.code,
            "grupe": groups_list,
            "datum": ev.start_dt.strftime("%Y-%m-%d"),
            "vrijeme_start": ev.start_time_str,
            "vrijeme_kraj": ev.end_time_str,
            "prostorija": [r.name for r in ev.rooms],
            "dodatne_osobe": [t.name for t in ev.teachers[1:]],
            "ponavljanje": {
                "frekvencija": ev.frequency,
                "datum_kraj": ev.until_date,
                "interval": ev.interval,
                "izuzeci": ev.exdates
            }
        }
