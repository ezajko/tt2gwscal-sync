"""
compiler.py - Kompajler AST -> IR

Pretvara AST (sirove parsirane podatke) u IR (obogaceni model sa
razrijesenim referencama, vremenima i datumima).

Koraci kompajliranja:
    1. Izgradnja lookup tablela (nastavnici, prostorije, predmeti, grupe)
    2. Obrada assignmenta (razrjesavanje vremena, datuma, entiteta)
    3. Kreiranje Event objekata u ScheduleModel
"""
from datetime import datetime, timedelta
from typing import Dict, List

from .ir import (
    Event,
    Group,
    LectureType,
    Person,
    Room,
    ScheduleModel,
    Subject,
)
from .models import AssignmentNode, Schedule
from .utils import format_camel_case


class ScheduleCompiler:
    """Kompajlira Schedule AST u ScheduleModel IR."""

    def __init__(self, ast: Schedule):
        self.ast = ast

        # Precalculated vrijednosti za razrjesavanje vremena
        self.base_time = datetime.strptime(ast.base_time, "%H:%M")
        self.slot_duration = ast.slot_duration
        self.slots_per_index = ast.slots_per_index

        # Pocetak semestra (za racunanje datuma prvog pojavljivanja)
        if ast.start_date:
            self.semester_start = datetime.strptime(ast.start_date, "%Y-%m-%d")
        else:
            current_year = datetime.now().year
            self.semester_start = datetime(current_year, 10, 1)

        self.semester_end = ast.end_date

        # Rjecnik dana (naziv -> broj) iz AST-a
        days_dict = {}
        for day_name, day_node in ast.days.items():
            days_dict[day_name] = str(day_node.number)

        # Inicijalizacija IR modela
        self.model = ScheduleModel(
            semester_name=ast.semester_info.get('name', 'Schedule'),
            start_date=ast.start_date,
            end_date=ast.end_date or '',
            holidays=ast.holidays or [],
            days=days_dict,
        )

    def compile(self) -> ScheduleModel:
        """Glavna metoda: kompajlira AST u IR model."""
        self._build_lookups()
        self._process_assignments()
        # Propagiraj tipove nastave u IR (koriste ih html_gen i grid_gen)
        self.model.default_types = self.ast.default_types
        return self.model

    # ------------------------------------------------------------------
    # Pomocne metode
    # ------------------------------------------------------------------

    def _resolve_type(self, type_code: str) -> LectureType:
        """Razrijesava kod tipa u LectureType objekat.
        Ako kod nije poznat, vraca genericki tip sa prioritetom 99."""
        return self.ast.default_types.get(
            type_code, LectureType(type_code, type_code, 99)
        )

    def _build_lookups(self):
        """Gradi lookup rjecnike iz AST definicija."""

        # 1. Nastavnici
        for node in self.ast.teachers.values():
            p = Person(id=node.name, name=format_camel_case(node.name))
            self.model.people[node.name] = p

        # 2. Prostorije
        for node in self.ast.rooms.values():
            r = Room(id=node.name, name=node.name)
            self.model.rooms[node.name] = r

        # 3. Predmeti
        for node in self.ast.subjects.values():
            types = set()
            for t_code in node.types:
                types.add(self._resolve_type(t_code))
            s = Subject(id=node.name, name=format_camel_case(node.name), types=types)
            self.model.subjects[node.name] = s

        # 4. Grupe (sa hijerarhijom roditelj-dijete)
        # Prvi prolaz: kreiraj objekte
        all_group_names = set(self.ast.study_groups.keys()) | set(self.ast.subgroups.keys())
        for name in all_group_names:
            g = Group(id=name, name=name)
            self.model.groups[name] = g

        # Drugi prolaz: povezi roditelje i djecu
        for node in self.ast.subgroups.values():
            child = self.model.groups[node.name]
            if node.parent and node.parent in self.model.groups:
                parent = self.model.groups[node.parent]
                child.parent = parent
                parent.subgroups.append(child)

    def _resolve_time(self, slot_id: str) -> tuple:
        """Razrijesava ID termina u (start_datetime, duration_minutes).
        Koristi AST slot definicije za racunanje vremena."""
        slot_def = self.ast.slots.get(slot_id)
        if not slot_def:
            raise ValueError(f"Termin '{slot_id}' nije definisan u AST-u")

        # Svaki slot_number predstavlja jedan slot_duration interval od base_time
        minutes_offset = (slot_def.number - 1) * self.slot_duration
        start_dt = self.base_time + timedelta(minutes=minutes_offset)

        return start_dt, self.slot_duration

    def _process_assignments(self):
        """Obradjuje sve AssignmentNode-ove i kreira Event objekte."""
        uid_counter = 1

        for node in self.ast.assignments:
            if not node.slots:
                continue

            # Razrijesi entitete (sa fallback za nedefinirane)
            teachers = [
                self.model.people.get(t, Person(t, format_camel_case(t)))
                for t in node.teachers
            ]
            rooms = [
                self.model.rooms.get(r, Room(r, r))
                for r in node.rooms
            ]

            # Razrijesi grupe (preskoci "Svi")
            event_groups = []
            for sublist in node.groups:
                for g_name in sublist:
                    if g_name == "Svi":
                        continue
                    g = self.model.groups.get(g_name, Group(g_name, g_name))
                    event_groups.append(g)

            # Razrijesi predmet (kreiraj implicitni ako ne postoji)
            subj = self.model.subjects.get(node.subject)
            if not subj:
                l_type = self._resolve_type(node.type)
                subj = Subject(
                    id=node.subject,
                    name=format_camel_case(node.subject),
                    types={l_type},
                )

            l_type = self._resolve_type(node.type)

            # Razrijesi vrijeme iz slotova (od najranijeg do najkasnijeg)
            slot_times = []
            for slot_id in node.slots:
                start_dt, duration = self._resolve_time(slot_id)
                end_dt = start_dt + timedelta(minutes=duration)
                slot_times.append((start_dt, end_dt))

            start_t = min(st[0] for st in slot_times)
            end_t = max(st[1] for st in slot_times)
            start_str = start_t.strftime("%H:%M")
            end_str = end_t.strftime("%H:%M")

            # Razrijesi dan iz prvog slota
            first_slot_def = self.ast.slots.get(node.slots[0])
            if not first_slot_def:
                raise ValueError(f"Termin '{node.slots[0]}' nije definisan u AST-u")
            day_name = first_slot_def.day_name

            day_def = self.ast.days.get(day_name)
            if not day_def:
                raise ValueError(f"Dan '{day_name}' nije definisan u AST-u")

            # Indeks dana (0-based, Mon=0)
            day_idx = day_def.number - 1

            # Datum prvog pojavljivanja u semestru
            sem_start_weekday = self.semester_start.weekday()
            days_diff = (day_idx - sem_start_weekday + 7) % 7
            first_date = self.semester_start + timedelta(days=days_diff)

            # Konstruisi kompletne datetime-ove
            start_dt = first_date.replace(hour=start_t.hour, minute=start_t.minute)
            end_dt = first_date.replace(hour=end_t.hour, minute=end_t.minute)

            # Kreiraj Event
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
                exdates=self.model.holidays,
            )
            self.model.events.append(ev)
            uid_counter += 1
