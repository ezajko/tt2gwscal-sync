"""
grid_gen.py - Grid (tabelarni) HTML generator za raspored

Generise tradicionalni grid prikaz rasporeda: redovi su termini,
kolone su dani, a celije sadrze evente.

Za svakog nastavnika generise zasebnu tabelu sa page-break-om za print.
Vremenske slots se generisu dinamicki na osnovu evenata u rasporedu.
"""
import os
from datetime import datetime, timedelta

from ..utils import merge_events, prepare_raw_data, condense_teachers


class GridGenerator:
    """Generator za tabelarni grid prikaz rasporeda.

    Pristup:
        1. Generise matricu (dani x slotovi) za svakog nastavnika
        2. Popunjava matricu eventima
        3. Renderuje HTML tabelu iz matrice
    """

    def __init__(self, model, output_dir, title=None):
        self.model = model
        self.output_dir = output_dir.rstrip('/')
        self.title = title or f"Raspored - {model.semester_name}"

        # Konfiguracija vremena iz modela
        self.base_time_str = model.base_time
        self.slot_duration = model.slot_duration
        self.slots_per_index = model.slots_per_index
        self.base_time = datetime.strptime(self.base_time_str, "%H:%M")

        # Redoslijed dana iz modela (1-based -> 0-based)
        self.day_order = {}
        for day_name, day_number in model.days.items():
            try:
                self.day_order[day_name] = int(day_number) - 1
            except ValueError:
                self.day_order[day_name] = 99

        # Generirani vremenski slotovi (dinamicki iz evenata)
        self.time_slots = self._generate_time_slots()

        # Sortirani dani
        self.days = sorted(
            self.model.days.keys(), key=lambda d: self.day_order.get(d, 99)
        )

    # ------------------------------------------------------------------
    # Vremenski slotovi
    # ------------------------------------------------------------------

    def _generate_time_slots(self):
        """Generise vremenske slotove na osnovu evenata u rasporedu.
        Dodaje 1h padding prije prvog i nakon zadnjeg eventa."""
        if not self.model.events:
            return self._generate_default_slots()

        # Nadje najraniji pocetak i najkasniji kraj
        min_time = None
        max_time = None
        for event in self.model.events:
            start = datetime.strptime(event.start_time_str, "%H:%M")
            end = datetime.strptime(event.end_time_str, "%H:%M")
            if min_time is None or start < min_time:
                min_time = start
            if max_time is None or end > max_time:
                max_time = end

        # Padding
        if min_time:
            min_time -= timedelta(hours=1)
        if max_time:
            max_time += timedelta(hours=1)

        return self._build_slots(
            min_time or self.base_time,
            max_time or (self.base_time + timedelta(hours=12)),
        )

    def _generate_default_slots(self):
        """Generise podrazumijevane slotove (08:00 - 20:00)."""
        return self._build_slots(
            self.base_time, self.base_time + timedelta(hours=12)
        )

    def _build_slots(self, start, end):
        """Gradi listu slot rjecnika od start do end vremena."""
        slots = []
        current = start
        slot_number = 1
        while current < end:
            slots.append({
                'number': slot_number,
                'time': current.strftime("%H:%M"),
                'datetime': current,
            })
            current += timedelta(minutes=self.slot_duration)
            slot_number += 1
        return slots

    def _get_time_slot_index(self, time_str):
        """Vraca indeks slota za dato vrijeme. Vraca -1 ako nije nadjen."""
        time_obj = datetime.strptime(time_str, "%H:%M")
        for i, slot in enumerate(self.time_slots):
            if abs((time_obj - slot['datetime']).total_seconds()) < self.slot_duration * 60:
                return i
        return -1

    # ------------------------------------------------------------------
    # Priprema podataka
    # ------------------------------------------------------------------

    # _prepare_raw_data i _condense_teachers su sada u utils.py
    # kao zajednicke funkcije prepare_raw_data() i condense_teachers()

    # ------------------------------------------------------------------
    # Matrica rasporeda
    # ------------------------------------------------------------------

    def _build_schedule_matrix(self, events):
        """Gradi matricu (dani x slotovi) popunjenu eventima.
        Vraca dict: {(dan_idx, slot_idx): [eventi]}"""
        matrix = {}

        # Inicijalizacija prazne matrice
        for day_idx in range(len(self.days)):
            for slot_idx in range(len(self.time_slots)):
                matrix[(day_idx, slot_idx)] = []

        # Popunjavanje eventima
        for event in events:
            day = event['datum']
            if day not in self.days:
                continue

            day_idx = self.days.index(day)
            start_idx = self._get_time_slot_index(event['vrijeme_start'])
            end_idx = self._get_time_slot_index(event['vrijeme_kraj'])

            if start_idx == -1:
                continue

            # Popuni sve slotove koje event zauzima
            end_bound = end_idx + 1 if end_idx != -1 else start_idx + 1
            for idx in range(start_idx, min(end_bound, len(self.time_slots))):
                matrix.setdefault((day_idx, idx), []).append(event)

        return matrix

    # ------------------------------------------------------------------
    # Generisanje HTML-a
    # ------------------------------------------------------------------

    def generate(self):
        """Generise grid HTML fajl sa tabelama za svakog nastavnika."""
        if not os.path.exists(self.output_dir):
            os.makedirs(self.output_dir)

        # Priprema podataka (zajednicke funkcije iz utils)
        raw_data = prepare_raw_data(self.model.events)
        merged_data = merge_events(raw_data)
        condensed_data = condense_teachers(merged_data)

        self._generate_grid_html(condensed_data)

    def _generate_grid_html(self, events):
        """Generise grid HTML sa sekcijama za svakog nastavnika."""
        # Grupisanje po nastavniku
        teachers_events = {}
        for event in events:
            teacher = event['osoba']
            teachers_events.setdefault(teacher, []).append(event)

        sorted_teachers = sorted(teachers_events.keys())

        # HTML izlaz
        html = self._generate_html_header()

        for i, teacher in enumerate(sorted_teachers):
            matrix = self._build_schedule_matrix(teachers_events[teacher])
            html += self._generate_teacher_section(
                teacher, matrix, i, len(sorted_teachers)
            )

        html += self._generate_html_footer()

        # Zapis u fajl
        filename = os.path.join(
            self.output_dir,
            f"grid_{self.model.semester_name.replace(' ', '_')}.html",
        )
        with open(filename, "w", encoding="utf-8") as f:
            f.write(html)

    def _generate_teacher_section(self, teacher, matrix, index, total):
        """Generise HTML sekciju za jednog nastavnika."""
        html = f'<div class="teacher-section">'
        html += f'<h2 class="teacher-header">Raspored za nastavnika: {teacher}</h2>'
        html += '<table>\n<thead>\n'

        # Zaglavlje sa danima
        html += '<tr><th class="time-cell">Vrijeme</th>'
        for day in self.days:
            html += f'<th>{day}</th>'
        html += '</tr>\n</thead>\n<tbody>\n'

        # Redovi za svaki vremenski slot
        for slot_idx, slot_info in enumerate(self.time_slots):
            html += '<tr>'
            html += (
                f'<td class="time-cell">'
                f'<strong>{slot_info["number"]}</strong><br>'
                f'<small>{slot_info["time"]}</small></td>'
            )

            # Kolone za svaki dan
            for day_idx in range(len(self.days)):
                cell_content = ""
                events_in_cell = matrix.get((day_idx, slot_idx), [])

                for event in events_in_cell:
                    subject = event['predmet']
                    groups = ', '.join(', '.join(sub) for sub in event['grupe'])
                    rooms = ', '.join(event['prostorija'])

                    cell_content += f'''<div class="event-details">
                        <span class="event-type tag-{event['tip']}">{event['tip']}</span>
                        <span class="event-subject">{subject}</span>
                        <span class="event-groups">{groups}</span>
                        <span class="event-room">{rooms}</span>
                    </div>'''

                html += f'<td class="event-cell">{cell_content}</td>'

            html += '</tr>\n'

        html += '</tbody></table></div>'

        # Page break za print (osim za zadnjeg nastavnika)
        if index < total - 1:
            html += '<p style="page-break-after: always;">&nbsp;</p>\n'

        return html

    # ------------------------------------------------------------------
    # HTML template (header/footer)
    # ------------------------------------------------------------------

    def _generate_html_header(self):
        """Generise HTML zaglavlje sa stilovima i JavaScript-om."""
        return f"""<!DOCTYPE html>
<html>
<head>
    <meta http-equiv="content-type" content="text/html; charset=UTF-8">
    <meta charset="UTF-8">
    <title>{self.title} - Raspored</title>
    <style>
        @page {{
            size: A4 landscape;
            margin: 15mm;
        }}

        * {{ box-sizing: border-box; }}

        body {{
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            margin: 0; padding: 15px;
            background-color: #f5f7fa; color: #333;
        }}

        .container {{
            max-width: 100%; margin: 0 auto;
            background: white; border-radius: 8px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1); overflow: hidden;
        }}

        header {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white; padding: 20px; text-align: center;
        }}

        h1 {{ margin: 0; font-size: 1.8em; font-weight: 600; }}

        .teacher-section {{ margin: 20px 0; padding: 0 15px; }}

        .teacher-header {{
            background: #4a90e2; color: white;
            padding: 12px 15px; margin: 0; font-size: 1.2em;
            border-radius: 4px 4px 0 0;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}

        table {{
            width: 100%; border-collapse: collapse;
            margin: 10px 0 20px 0; background: white;
            border-radius: 4px; overflow: hidden;
            box-shadow: 0 1px 3px rgba(0,0,0,0.1);
        }}

        th {{
            background: #2c3e50; color: white;
            padding: 12px 8px; text-align: center;
            font-weight: 600; font-size: 0.9em;
            border: 1px solid #34495e;
        }}

        td {{
            padding: 8px; text-align: center;
            border: 1px solid #e0e0e0; vertical-align: middle;
            font-size: 0.85em; min-height: 40px;
        }}

        tr:nth-child(even) {{ background-color: #f8f9fa; }}
        tr:nth-child(odd) {{ background-color: white; }}

        .time-cell {{
            background: #ecf0f1; font-weight: 600;
            text-align: center; min-width: 80px; width: 80px !important;
        }}

        .event-cell {{ text-align: left; padding: 5px 8px; }}

        .event-type {{
            display: inline-block; padding: 2px 6px;
            border-radius: 3px; font-weight: bold;
            font-size: 0.8em; margin-bottom: 2px;
        }}

        /* CSS klase za tipove nastave */
        .tag-P {{ background-color: #e3f2fd; color: #1976d2; }}
        .tag-V {{ background-color: #e8f5e8; color: #388e3c; }}
        .tag-L {{ background-color: #fff3e0; color: #f57c00; }}
        .tag-T {{ background-color: #f3e5f5; color: #7b1fa2; }}
        .tag-N {{ background-color: #ffebee; color: #d32f2f; }}

        .event-details {{ line-height: 1.3; }}
        .event-subject {{ font-weight: 600; color: #2c3e50; display: block; }}
        .event-groups {{ color: #7f8c8d; font-size: 0.8em; display: block; }}
        .event-room {{ color: #95a5a6; font-size: 0.8em; display: block; }}

        @media print {{
            body {{ background: white; padding: 0; }}
            .container {{ box-shadow: none; border-radius: 0; }}
            @page {{ size: A4 landscape; margin: 10mm; }}
        }}
    </style>
    <script>
        document.addEventListener('DOMContentLoaded', function() {{
            const tables = document.querySelectorAll('table');
            tables.forEach(table => {{
                const headerRow = table.querySelector('thead tr');
                if (headerRow) {{
                    const dayCells = Array.from(headerRow.cells).slice(1);
                    table.style.setProperty('--day-count', dayCells.length);
                }}
            }});
        }});
    </script>
</head>
<body>
<div class="container">
    <header>
        <h1>{self.title} - Raspored</h1>
    </header>
"""

    def _generate_html_footer(self):
        """Generise HTML footer."""
        return "</div></body></html>"
