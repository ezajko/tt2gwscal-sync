"""
json_gen.py - JSON generator za raspored

Generise listu evenata u JSON formatu kompatibilnom sa sync.py skriptom
za sinhronizaciju sa Google Workspace kalendarom.

Svaki event ima: osobu, predmet, tip, grupe, datum, vrijeme, prostoriju,
dodatne osobe i podatke o ponavljanju.
"""
from ..utils import merge_events


class JSONScheduleGenerator:
    """Generise JSON evente iz IR modela."""

    def __init__(self, model):
        self.model = model

    def generate(self):
        """Generise listu evenata i spaja duplikate."""
        events = [self._to_event(ev) for ev in self.model.events]
        return merge_events(events)

    def _to_event(self, ev):
        """Pretvara IR Event u dict format za JSON izlaz.

        Grupe se izlazu kao lista lista radi kompatibilnosti sa sync.py
        koji ocekuje format [[G1], [G2]] za individualne grupe."""
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
                "izuzeci": ev.exdates,
            },
        }
