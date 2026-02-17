"""
exporter.py - Eksport AST-a nazad u RAS format

Generise refaktorisane .ras fajlove iz AST-a:
    raspored.ras        - glavni fajl sa UVEZI direktivama i assignmentima
    definicije/          - direktorij sa definicijskim fajlovima
        semestar.ras     - pocetak, kraj, trajanje, nenastavni dani
        vrijeme.ras      - dani i termini
        tipovi.ras       - tipovi nastave (iz merged default_types)
        nastavnici.ras   - nastavnici
        predmeti.ras     - predmeti
        prostorije.ras   - prostorije
        grupe.ras        - odjeljenja i podgrupe
    nevalidno.ras       - assignmenti koji nisu prosli validaciju
"""
import os
from datetime import datetime

from .validator import validate_schedule


class Exporter:
    """Eksportuje Schedule AST u strukturirane .ras fajlove."""

    def __init__(self, schedule, output_dir):
        self.schedule = schedule
        self.output_dir = output_dir.rstrip('/')
        self.defs_dir = f"{self.output_dir}/definicije"

    def export(self):
        """Glavni metod: eksportuje sve fajlove."""
        if not os.path.exists(self.defs_dir):
            os.makedirs(self.defs_dir)

        # 1. Eksport definicija u zasebne fajlove
        self._write_file(f"{self.defs_dir}/semestar.ras", self._gen_semester_defs())
        self._write_file(f"{self.defs_dir}/vrijeme.ras", self._gen_time_defs())
        self._write_file(f"{self.defs_dir}/tipovi.ras", self._gen_lecture_type_defs())
        self._write_file(f"{self.defs_dir}/nastavnici.ras", self._gen_teacher_defs())
        self._write_file(f"{self.defs_dir}/predmeti.ras", self._gen_subject_defs())
        self._write_file(f"{self.defs_dir}/prostorije.ras", self._gen_room_defs())
        self._write_file(f"{self.defs_dir}/grupe.ras", self._gen_group_defs())

        # 2. Validacija i eksport assignmenta
        valid, invalid = validate_schedule(self.schedule)
        raspored_content = self._gen_assignments(valid, include_imports=True)

        if invalid:
            self._write_file(
                f"{self.output_dir}/nevalidno.ras",
                self._gen_invalid_assignments(invalid),
            )
            raspored_content += "\nUVEZI: nevalidno.ras\n"
            print(f"⚠ UPOZORENJE: Pronađeno {len(invalid)} nevalidnih unosa!"
                  " Pogledajte 'nevalidno.ras'.")

        self._write_file(f"{self.output_dir}/raspored.ras", raspored_content)
        print(f"✓ Eksportovano u: {self.output_dir}/")

    # ------------------------------------------------------------------
    # Pomocne metode za pisanje i formatiranje
    # ------------------------------------------------------------------

    def _write_file(self, path, content):
        """Zapisuje sadrzaj u fajl sa UTF-8 enkodingom."""
        with open(path, 'w', encoding='utf-8') as f:
            f.write(content)

    def _to_pascal(self, name):
        """Pretvara 'Ime Prezime' u 'ImePrezime' (svaka rijec kapitalizirana)."""
        return "".join(
            word[0].upper() + word[1:] if word else ""
            for word in name.split(" ")
        )

    def _to_source_subject(self, name, type_code):
        """Pretvara naziv predmeta i kod tipa nazad u source format.
        Primjer: ('Uvod U Programiranje', 'P') -> 'pUvodUProgramiranje'"""
        prefix = type_code.lower()
        return f"{prefix}{self._to_pascal(name)}"

    # ------------------------------------------------------------------
    # Generatori sadrzaja za pojedinacne definicijske fajlove
    # ------------------------------------------------------------------

    def _gen_semester_defs(self):
        """Generise definicije semestra."""
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
                h_dates = [
                    datetime.strptime(h, "%Y%m%d").strftime("%d.%m.%Y")
                    for h in info['holidays']
                ]
                lines.append(f"{name} ima nenastavne dane {', '.join(h_dates)}.")

        return "\n".join(lines)

    def _gen_time_defs(self):
        """Generise definicije dana i termina."""
        lines = ["// Definicije Dana i Termina"]

        for node in self.schedule.days.values():
            lines.append(f"{node.name} je dan broj {node.number}.")

        for node in self.schedule.slots.values():
            lines.append(
                f"{node.slot_id} je termin broj {node.number} dana {node.day_name}."
            )

        return "\n".join(lines)

    def _gen_lecture_type_defs(self):
        """Generise definicije tipova nastave iz merged default_types."""
        lines = ["// Definicije Tipova Nastave"]

        # Sortirano po prioritetu
        sorted_types = sorted(
            self.schedule.default_types.values(), key=lambda t: t.priority
        )
        for lt in sorted_types:
            lines.append(
                f"{lt.code} je tip nastave {self._to_pascal(lt.name)}"
                f" prioriteta {lt.priority}."
            )

        return "\n".join(lines)

    def _gen_teacher_defs(self):
        """Generise definicije nastavnika."""
        lines = ["// Definicije Nastavnika"]

        for node in self.schedule.teachers.values():
            lines.append(f"{self._to_pascal(node.name)} je nastavnik.")

        return "\n".join(lines)

    def _gen_subject_defs(self):
        """Generise definicije predmeta (sa prefiksom tipa)."""
        lines = ["// Definicije Predmeta"]

        for node in self.schedule.subjects.values():
            if not node.types:
                lines.append(f"{self._to_pascal(node.name)} je predmet.")
            for t in node.types:
                lines.append(f"{self._to_source_subject(node.name, t)} je predmet.")

        return "\n".join(lines)

    def _gen_room_defs(self):
        """Generise definicije prostorija."""
        lines = ["// Definicije Prostorija"]

        for node in self.schedule.rooms.values():
            lines.append(f"{node.name} je prostorija.")

        return "\n".join(lines)

    def _gen_group_defs(self):
        """Generise definicije odjeljenja i podgrupa."""
        lines = ["// Definicije Grupa"]

        for node in self.schedule.study_groups.values():
            lines.append(f"{self._to_pascal(node.name)} je odjeljenje.")

        for node in self.schedule.subgroups.values():
            lines.append(
                f"{self._to_pascal(node.name)} je grupa odjeljenja"
                f" {self._to_pascal(node.parent)}."
            )

        return "\n".join(lines)

    # ------------------------------------------------------------------
    # Generatori za assignment iskaze
    # ------------------------------------------------------------------

    def _gen_assignments(self, assignments, include_imports=False):
        """Generise iskaze nastave.
        Ako je include_imports True, dodaje UVEZI direktive na pocetak."""
        lines = []

        if include_imports:
            lines.extend([
                "UVEZI: definicije/semestar.ras",
                "UVEZI: definicije/vrijeme.ras",
                "UVEZI: definicije/tipovi.ras",
                "UVEZI: definicije/nastavnici.ras",
                "UVEZI: definicije/predmeti.ras",
                "UVEZI: definicije/prostorije.ras",
                "UVEZI: definicije/grupe.ras",
                "",
            ])

        for node in assignments:
            teachers_str = " i ".join(self._to_pascal(t) for t in node.teachers)
            subject_str = self._to_source_subject(node.subject, node.type)

            groups_parts = []
            for sublist in node.groups:
                g_str = ", ".join(self._to_pascal(g) for g in sublist)
                groups_parts.append(f"odjeljenju {g_str}")
            groups_str = " ".join(groups_parts)

            rooms_part = ""
            if node.rooms:
                rooms_str = ", ".join(self._to_pascal(r) for r in node.rooms)
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
        """Generise nevalidne assignmente sa komentarima o greskama."""
        lines = ["// NEVALIDNI UNOSI - Nedostaju definicije"]

        for node, reason in invalid_list:
            lines.append(f"// Greška: {reason}")
            line = self._gen_assignments([node], include_imports=False)
            lines.append(line)
            lines.append("")

        return "\n".join(lines)
