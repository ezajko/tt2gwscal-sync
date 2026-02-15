import re
from datetime import datetime, timedelta

from ..models import AssignmentNode
from ..utils import format_person_name, merge_events


class JSONCalendarGenerator:
    def __init__(self, schedule, start_date, end_date, base_time="08:00", slot_duration=30, slots_per_index=2):
        self.schedule = schedule
        self.start_date = start_date
        self.end_date = end_date
        self.base_time = base_time
        self.slot_duration = int(slot_duration)
        self.slots_per_index = int(slots_per_index)
        self.slots_map = {sid: node.day_name for sid, node in schedule.slots.items()}
        self.days_offset = {"Ponedjeljak": 0, "Utorak": 1, "Srijeda": 2, "Četvrtak": 3, "Petak": 4, "Subota": 5, "Nedjelja": 6}

    def generate(self):
        events = []
        for node in self.schedule.assignments:
            if isinstance(node, AssignmentNode) and node.slots:
                events.append(self._to_event(node))

        return merge_events(events)

    def _to_event(self, node):
        day_name = self.slots_map.get(node.slots[0], "Ponedjeljak")
        start_dt = datetime.strptime(self.start_date, "%Y-%m-%d") + timedelta(days=self.days_offset.get(day_name, 0))

        return {
            "osoba": node.teachers[0],
            "predmet": node.subject,
            "tip": node.type,
            "grupe": node.groups,
            "datum": start_dt.strftime("%Y-%m-%d"),
            "vrijeme_start": self._slot_to_t(node.slots[0]),
            "vrijeme_kraj": self._slot_to_t(node.slots[-1], end=True),
            "prostorija": node.rooms,
            "dodatne_osobe": [t for t in node.teachers[1:]],
            "ponavljanje": {
                "frekvencija": "WEEKLY",
                "datum_kraj": self.end_date,
                "interval": node.recurrence_interval,
                "izuzeci": self.schedule.holidays
            }
        }

    def _slot_to_t(self, slot, end=False):
        num_match = re.search(r'\d+', slot)
        num = int(num_match.group()) if num_match else 1
        minutes_offset = (num - 1) * (self.slots_per_index * self.slot_duration)
        if 'A' in slot: minutes_offset += self.slot_duration
        if end: minutes_offset += self.slot_duration
        start_time_dt = datetime.strptime(self.base_time, "%H:%M")
        return (start_time_dt + timedelta(minutes=minutes_offset)).strftime("%H:%M")
