import re
from datetime import datetime, timedelta
from typing import Dict, List

from .ir import (
    DEFAULT_TYPES,
    Event,
    Group,
    LectureType,
    Person,
    Room,
    ScheduleModel,
    Subject,
)
from .models import AssignmentNode, Schedule
from .utils import format_person_name


class ScheduleCompiler:
    def __init__(self, ast: Schedule, config: Dict):
        self.ast = ast
        self.config = config

        # Config shortcuts
        self.base_time = datetime.strptime(config.get('base_time', '08:00'), "%H:%M")
        self.slot_duration = int(config.get('slot_duration', 30))
        self.slots_per_index = int(config.get('slots_per_index', 2))

        # Start date is mandatory in config at this point (tt2cal ensures defaults)
        self.semester_start = datetime.strptime(config['start_date'], "%Y-%m-%d")
        self.semester_end = config.get('end_date')

        # Mappings
        self.day_map = {
            "Ponedjeljak": 0, "Ponedeljak": 0, "Mon": 0,
            "Utorak": 1, "Tue": 1,
            "Srijeda": 2, "Sreda": 2, "Wed": 2,
            "Četvrtak": 3, "Cetvrtak": 3, "Thu": 3,
            "Petak": 4, "Fri": 4,
            "Subota": 5, "Sat": 5,
            "Nedjelja": 6, "Nedelja": 6, "Sun": 6
        }

        # State
        self.model = ScheduleModel(
            semester_name=config.get('name', 'Schedule'),
            start_date=config['start_date'],
            end_date=config.get('end_date', ''),
            holidays=config.get('holidays', [])
        )

    def compile(self) -> ScheduleModel:
        self._build_lookups()
        self._process_assignments()
        return self.model

    def _build_lookups(self):
        # 1. People
        for node in self.ast.teachers.values():
            p = Person(id=node.name, name=format_person_name(node.name))
            self.model.people[node.name] = p

        # 2. Rooms
        for node in self.ast.rooms.values():
            r = Room(id=node.name, name=node.name)
            self.model.rooms[node.name] = r

        # 3. Subjects
        for node in self.ast.subjects.values():
            # Resolve types
            types = set()
            for t_code in node.types:
                types.add(DEFAULT_TYPES.get(t_code, LectureType(t_code, "Ostalo", 99)))

            s = Subject(id=node.name, name=format_person_name(node.name), types=types)
            self.model.subjects[node.name] = s

        # 4. Groups (Hierarchy)
        # First pass: create objects
        all_group_names = set(self.ast.study_groups.keys()) | set(self.ast.subgroups.keys())
        for name in all_group_names:
            g = Group(id=name, name=name)
            self.model.groups[name] = g

        # Second pass: link parents
        for node in self.ast.subgroups.values():
            child = self.model.groups[node.name]
            if node.parent and node.parent in self.model.groups:
                parent = self.model.groups[node.parent]
                child.parent = parent
                parent.subgroups.append(child)

    def _resolve_time(self, slot_id: str) -> (datetime, int):
        """Returns (start_time_dt, duration_minutes)."""
        # Try finding in AST slots
        slot_def = self.ast.slots.get(slot_id)

        if slot_def:
            # Use defined number
            num = slot_def.number
        else:
            # Fallback regex
            match = re.search(r'\d+', slot_id)
            num = int(match.group()) if match else 1

        minutes_offset = (num - 1) * (self.slots_per_index * self.slot_duration)
        if 'A' in slot_id: minutes_offset += self.slot_duration

        start_dt = self.base_time + timedelta(minutes=minutes_offset)
        return start_dt, self.slot_duration

    def _process_assignments(self):
        uid_counter = 1

        for node in self.ast.assignments:
            if not node.slots: continue

            # Resolve Entities
            teachers = [self.model.people.get(t, Person(t, format_person_name(t))) for t in node.teachers]
            rooms = [self.model.rooms.get(r, Room(r, r)) for r in node.rooms]

            # Resolve Groups
            event_groups = []
            for sublist in node.groups:
                for g_name in sublist:
                    if g_name == "Svi": continue
                    g = self.model.groups.get(g_name, Group(g_name, g_name))
                    event_groups.append(g)

            # Resolve Subject
            subj = self.model.subjects.get(node.subject)
            if not subj:
                # Implicit subject
                l_type = DEFAULT_TYPES.get(node.type, LectureType(node.type, "Ostalo", 99))
                subj = Subject(id=node.subject, name=format_person_name(node.subject), types={l_type})

            l_type = DEFAULT_TYPES.get(node.type, LectureType(node.type, "Ostalo", 99))

            # Resolve Time (Start/End)
            # Assuming contiguous slots
            first_slot = node.slots[0]
            last_slot = node.slots[-1]

            start_t, _ = self._resolve_time(first_slot)
            end_t_start, dur = self._resolve_time(last_slot)
            end_t = end_t_start + timedelta(minutes=dur)

            start_str = start_t.strftime("%H:%M")
            end_str = end_t.strftime("%H:%M")

            # Resolve Date
            # Get Day Name from first slot definition
            day_name = "Ponedjeljak" # Default
            slot_def = self.ast.slots.get(first_slot)
            if slot_def:
                day_name = slot_def.day_name
            elif len(node.slots) > 0 and node.slots[0] in self.ast.slots:
                 # Should have been caught by slot_def check above if key matches
                 pass

            # If not found in slots, try to infer from AST context?
            # Or assume Monday?
            # Existing generator assumed "Ponedjeljak" if not found.

            day_idx = self.day_map.get(day_name, 0)

            # Calculate first occurrence date
            sem_start_weekday = self.semester_start.weekday() # Mon=0

            # Days until first occurrence
            days_diff = (day_idx - sem_start_weekday + 7) % 7
            first_date = self.semester_start + timedelta(days=days_diff)

            # Construct full datetimes
            start_dt = first_date.replace(hour=start_t.hour, minute=start_t.minute)
            end_dt = first_date.replace(hour=end_t.hour, minute=end_t.minute)

            # Create Event
            ev = Event(
                uid=f"EV-{uid_counter}",
                subject=subj,
                type=l_type,
                teachers=teachers,
                groups=event_groups,
                rooms=rooms,
                day_name=day_name,
                start_time_str=start_str,
                end_time_str=end_str,
                start_dt=start_dt,
                end_dt=end_dt,
                frequency="WEEKLY",
                interval=node.recurrence_interval,
                until_date=self.semester_end,
                exdates=self.model.holidays
            )
            self.model.events.append(ev)
            uid_counter += 1
