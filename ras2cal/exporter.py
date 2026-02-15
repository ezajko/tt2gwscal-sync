import os
from datetime import datetime

from .validator import validate_schedule


class Exporter:
    def __init__(self, schedule, output_dir):
        self.schedule = schedule
        self.output_dir = output_dir.rstrip('/')
        self.defs_dir = f"{self.output_dir}/definicije"

    def export(self):
        if not os.path.exists(self.defs_dir):
            os.makedirs(self.defs_dir)

        # 1. Eksport Definicija
        self._write_file(f"{self.defs_dir}/semestar.ras", self._gen_semester_defs())
        self._write_file(f"{self.defs_dir}/vrijeme.ras", self._gen_time_defs())
        self._write_file(f"{self.defs_dir}/nastavnici.ras", self._gen_teacher_defs())
        self._write_file(f"{self.defs_dir}/predmeti.ras", self._gen_subject_defs())
        self._write_file(f"{self.defs_dir}/prostorije.ras", self._gen_room_defs())
        self._write_file(f"{self.defs_dir}/grupe.ras", self._gen_group_defs())

        # 2. Validacija i Eksport Rasporeda
        valid, invalid = validate_schedule(self.schedule)

        raspored_content = self._gen_assignments(valid, include_imports=True)

        if invalid:
            self._write_file(f"{self.output_dir}/nevalidno.ras", self._gen_invalid_assignments(invalid))
            raspored_content += "\nUVEZI: nevalidno.ras\n"
            print(f"⚠ UPOZORENJE: Pronađeno {len(invalid)} nevalidnih unosa! Pogledajte 'nevalidno.ras'.")

        self._write_file(f"{self.output_dir}/raspored.ras", raspored_content)
        print(f"✓ Eksportovano u: {self.output_dir}/")

    def _write_file(self, path, content):
        with open(path, 'w', encoding='utf-8') as f:
            f.write(content)

    # --- De-formatting Helpers ---
    def _to_pascal(self, name):
        """Vraća 'Ime Prezime' u 'ImePrezime'."""
        return name.replace(" ", "")

    def _to_source_subject(self, name, type_code):
        """Vraća 'Uvod', 'P' -> 'pUvod'."""
        prefix = type_code.lower() if type_code != 'T' else 't' # T je t, P je p
        return f"{prefix}{self._to_pascal(name)}"

    # --- Generators ---

    def _gen_semester_defs(self):
        info = self.schedule.semester_info
        lines = ["// Konfiguracija Semestra"]
        if info.get('name'):
            name = info['name']
            lines.append(f"{name} je semestar.")
            if info.get('start_date'):
                d = datetime.strptime(info['start_date'], "%Y-%m-%d").strftime("%d.%m.%Y")
                lines.append(f"{name} pocinje {d}.")
            if info.get('end_date'):
                d = datetime.strptime(info['end_date'], "%Y-%m-%d").strftime("%d.%m.%Y")
                lines.append(f"{name} zavrsava {d}.")
            if info.get('duration_weeks'):
                lines.append(f"{name} traje {info['duration_weeks']} sedmica.")
            if info.get('holidays'):
                h_dates = [datetime.strptime(h, "%Y%m%d").strftime("%d.%m.%Y") for h in info['holidays']]
                lines.append(f"{name} ima nenastavne dane {', '.join(h_dates)}.")
        return "\n".join(lines)

    def _gen_time_defs(self):
        lines = ["// Definicije Dana i Termina"]
        for node in self.schedule.days.values():
            lines.append(f"{node.name} je dan broj {node.number}.")

        for node in self.schedule.slots.values():
            lines.append(f"{node.slot_id} je termin broj 0 dana {node.day_name}.")
        return "\n".join(lines)

    def _gen_teacher_defs(self):
        lines = ["// Definicije Nastavnika"]
        for node in self.schedule.teachers.values():
            lines.append(f"{self._to_pascal(node.name)} je nastavnik.")
        return "\n".join(lines)

    def _gen_subject_defs(self):
        lines = ["// Definicije Predmeta"]
        for node in self.schedule.subjects.values():
            if not node.types:
                lines.append(f"{self._to_pascal(node.name)} je predmet.")

            for t in node.types:
                lines.append(f"{self._to_source_subject(node.name, t)} je predmet.")

        return "\n".join(lines)

    def _gen_room_defs(self):
        lines = ["// Definicije Prostorija"]
        for node in self.schedule.rooms.values():
            lines.append(f"{self._to_pascal(node.name)} je prostorija.")
        return "\n".join(lines)

    def _gen_group_defs(self):
        lines = ["// Definicije Grupa"]
        for node in self.schedule.study_groups.values():
            lines.append(f"{self._to_pascal(node.name)} je odjeljenje.")
        for node in self.schedule.subgroups.values():
            lines.append(f"{self._to_pascal(node.name)} je grupa odjeljenja {self._to_pascal(node.parent)}.")
        return "\n".join(lines)

    def _gen_assignments(self, assignments, include_imports=False):
        lines = []
        if include_imports:
            lines.append("UVEZI: definicije/semestar.ras")
            lines.append("UVEZI: definicije/vrijeme.ras")
            lines.append("UVEZI: definicije/nastavnici.ras")
            lines.append("UVEZI: definicije/predmeti.ras")
            lines.append("UVEZI: definicije/prostorije.ras")
            lines.append("UVEZI: definicije/grupe.ras")
            lines.append("")

        for node in assignments:
            teachers_str = " i ".join([self._to_pascal(t) for t in node.teachers])
            subject_str = self._to_source_subject(node.subject, node.type)

            groups_parts = []
            for sublist in node.groups:
                g_str = ", ".join([self._to_pascal(g) for g in sublist])
                groups_parts.append(f"odjeljenju {g_str}")
            groups_str = " ".join(groups_parts)

            rooms_part = ""
            if node.rooms:
                rooms_str = ", ".join([self._to_pascal(r) for r in node.rooms])
                rooms_part = f"u prostoriji {rooms_str}"

            slots_str = " ".join(node.slots)

            line = f"{teachers_str} predaje {subject_str} {groups_str} {rooms_part} "

            if node.frequency_hint:
                line += f"{node.frequency_hint} puta sedmicno "

            if node.recurrence_interval > 1:
                line += f"svake {node.recurrence_interval} sedmice "

            if node.unknown_tokens:
                line += " ".join(node.unknown_tokens) + " "

            line += f"tacno u terminu {slots_str}."
            lines.append(line)

        return "\n".join(lines)

    def _gen_invalid_assignments(self, invalid_list):
        lines = ["// NEVALIDNI UNOSI - Nedostaju definicije"]
        for node, reason in invalid_list:
            lines.append(f"// Greška: {reason}")
            line = self._gen_assignments([node], include_imports=False)
            lines.append(line)
            lines.append("")
        return "\n".join(lines)
