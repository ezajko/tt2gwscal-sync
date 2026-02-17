"""
html_gen.py - HTML generator za raspored (po entitetima)

Generise cetiri HTML fajla:
    {semestar}_predmeti.html    - grupisano po predmetima
    {semestar}_nastavnici.html  - grupisano po nastavnicima
    {semestar}_prostorije.html  - grupisano po prostorijama
    {semestar}_grupe.html       - grupisano po grupama (sa nasljedjivanjem)

Svaki fajl ima navigaciju izmedju pogleda i tabelarni prikaz.
"""
import os

from ..utils import merge_events, prepare_raw_data, condense_teachers


class HTMLScheduleGenerator:
    """Generator za HTML raspored sa grupiranjem po entitetima."""

    def __init__(self, model, output_dir, title=None):
        self.model = model
        self.output_dir = output_dir.rstrip('/')
        self.title = title or f"Raspored - {model.semester_name}"

        # Redoslijed dana iz modela (1-based -> 0-based)
        self.day_order = {}
        for day_name, day_number in model.days.items():
            try:
                self.day_order[day_name] = int(day_number) - 1
            except ValueError:
                self.day_order[day_name] = 99

        # Redoslijed tipova iz default_types (za sortiranje po tipu)
        self.type_order = {
            code: lt.priority for code, lt in model.default_types.items()
        }

    # ------------------------------------------------------------------
    # Priprema podataka
    # ------------------------------------------------------------------

    # _prepare_raw_data i _condense_teachers su sada u utils.py
    # kao zajednicke funkcije prepare_raw_data() i condense_teachers()

    # ------------------------------------------------------------------
    # Grupiranje podataka
    # ------------------------------------------------------------------

    def _group_by(self, data, key):
        """Grupise podatke po vrijednosti jednog kljuca (string)."""
        grouped = {}
        for item in data:
            val = item.get(key, "N/A")
            grouped.setdefault(val, []).append(item)
        return grouped

    def _group_by_list(self, data, list_key):
        """Grupise podatke po vrijednostima liste (jedan zapis moze
        pripadati vise grupa, npr. vise prostorija)."""
        grouped = {}
        for item in data:
            values = item.get(list_key, [])
            if not isinstance(values, list):
                values = [values]
            if not values:
                values = ["N/A"]
            for v in values:
                grouped.setdefault(v, []).append(item)
        return grouped

    def _generate_groups_view(self, raw_data):
        """Generise mapu evenata za svaku grupu sa nasljedjivanjem.
        Podgrupa nasljedjuje evente svog roditelja."""
        group_events = {}
        all_groups = sorted(self.model.groups.values(), key=lambda g: g.name)

        for group in all_groups:
            if group.name == "Svi":
                continue

            # Skupi nazive grupe i svih roditelja
            ancestors = group.get_all_ancestors()
            relevant_names = {group.name} | {a.name for a in ancestors}

            my_events = []
            for item in raw_data:
                is_relevant = False

                # Provjeri presjecanje grupa eventa sa relevantnim grupama
                for sublist in item['grupe']:
                    if not set(sublist).isdisjoint(relevant_names):
                        is_relevant = True
                        break

                # Eventi za grupu "Svi" se nasljedjuju svima
                if item['grupe'] == [["Svi"]]:
                    is_relevant = True

                if is_relevant:
                    my_events.append(item)

            if my_events:
                merged = merge_events(my_events)
                condensed = condense_teachers(merged)
                group_events[group.name] = condensed

        return group_events

    # ------------------------------------------------------------------
    # Generisanje HTML-a
    # ------------------------------------------------------------------

    def generate(self):
        """Generise sve HTML fajlove."""
        if not os.path.exists(self.output_dir):
            os.makedirs(self.output_dir)

        # Priprema podataka (zajednicke funkcije iz utils)
        raw_data = prepare_raw_data(self.model.events)
        merged_data = merge_events(raw_data)
        condensed_raw = condense_teachers(raw_data)
        condensed_merged = condense_teachers(merged_data)
        groups_data = self._generate_groups_view(raw_data)

        prefix = self.model.semester_name

        # Generisanje cetiri pogleda
        self._write_html(
            f"{prefix}_predmeti.html", f"{self.title} - Po Predmetima",
            self._group_by(condensed_raw, 'predmet'), prefix, sort_by_type=True,
        )
        self._write_html(
            f"{prefix}_nastavnici.html", f"{self.title} - Po Nastavnicima",
            self._group_by_list(condensed_merged, 'teachers'), prefix,
        )
        self._write_html(
            f"{prefix}_prostorije.html", f"{self.title} - Po Prostorijama",
            self._group_by_list(condensed_merged, 'prostorija'), prefix,
        )
        self._write_html(
            f"{prefix}_grupe.html", f"{self.title} - Po Grupama",
            groups_data, prefix,
        )

    def _resolve_tag_class(self, type_code):
        """Razrijesava CSS klasu za tip nastave.
        Provjerava da li tip postoji u default_types, inace koristi fallback."""
        if type_code in self.model.default_types:
            return self.model.default_types[type_code].css_class
        # Fallback: provjeri da li kod sadrzi poznati karakter
        for char in ('V', 'L', 'T'):
            if char in type_code:
                return f"tag-{char}"
        return "tag-P"

    def _write_html(self, filename, title, grouped_data, prefix, sort_by_type=False):
        """Generise i zapisuje jedan HTML fajl."""
        html = f"""
        <!DOCTYPE html>
        <html lang="bs">
        <head>
            <meta charset="UTF-8">
            <title>Raspored - {title}</title>
            <style>
                body {{ font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; margin: 20px; background-color: #f4f4f9; }}
                .nav {{ margin-bottom: 20px; padding: 10px; background: #fff; border-radius: 5px; box-shadow: 0 2px 5px rgba(0,0,0,0.1); }}
                .nav a {{ margin-right: 15px; text-decoration: none; font-weight: bold; color: #007bff; }}
                .nav a:hover {{ text-decoration: underline; }}
                h1 {{ color: #333; }}
                .section {{ margin-bottom: 30px; background: #fff; padding: 20px; border-radius: 8px; box-shadow: 0 2px 5px rgba(0,0,0,0.05); }}
                .section-title {{ font-size: 1.2em; font-weight: bold; margin-bottom: 10px; color: #555; border-bottom: 2px solid #eee; padding-bottom: 5px; }}
                table {{ width: 100%; border-collapse: collapse; margin-top: 10px; }}
                th, td {{ padding: 12px 15px; text-align: left; border-bottom: 1px solid #ddd; }}
                th {{ background-color: #f8f9fa; font-weight: 600; color: #444; }}
                tr:hover {{ background-color: #f1f1f1; }}
                .tag {{ display: inline-block; padding: 2px 6px; border-radius: 4px; font-size: 0.85em; margin-right: 5px; }}
                .tag-P {{ background-color: #e3f2fd; color: #0d47a1; }}
                .tag-V {{ background-color: #e8f5e9; color: #1b5e20; }}
                .tag-L {{ background-color: #fff3e0; color: #e65100; }}
                .tag-T {{ background-color: #f3e5f5; color: #4a148c; }}
            </style>
        </head>
        <body>
            <div class="nav">
                <a href="{prefix}_predmeti.html">Po Predmetima</a>
                <a href="{prefix}_nastavnici.html">Po Nastavnicima</a>
                <a href="{prefix}_grupe.html">Po Grupama</a>
                <a href="{prefix}_prostorije.html">Po Prostorijama</a>
            </div>
            <h1>{title}</h1>
        """

        for key in sorted(grouped_data.keys()):
            items = grouped_data[key]

            # Sortiranje: po tipu+dan+vrijeme ili dan+vrijeme
            if sort_by_type:
                items.sort(key=lambda x: (
                    self.type_order.get(x.get('tip', 'P'), 99),
                    self.day_order.get(x['datum'], 99),
                    x['vrijeme_start'],
                ))
            else:
                items.sort(key=lambda x: (
                    self.day_order.get(x['datum'], 99),
                    x['vrijeme_start'],
                ))

            html += f"<div class='section'><div class='section-title'>{key}</div><table>"
            html += ("<thead><tr><th>Predmet</th><th>Tip</th><th>Nastavnici</th>"
                     "<th>Grupe</th><th>Dan</th><th>Vrijeme</th><th>Prostorija</th>"
                     "</tr></thead><tbody>")

            for item in items:
                teachers_str = ", ".join(item['teachers'])
                rooms_to_show = item.get('prostorija', [])
                rooms_str = ", ".join(rooms_to_show) if rooms_to_show else "N/A"

                tag_class = self._resolve_tag_class(item.get('tip', 'P'))

                raw_groups = item.get('grupe', [])
                if isinstance(raw_groups, list):
                    group_str = " + ".join(", ".join(sub) for sub in raw_groups)
                else:
                    group_str = str(raw_groups)

                html += f"""
                <tr>
                    <td>{item.get('predmet', 'N/A')}</td>
                    <td><span class="tag {tag_class}">{item.get('tip', 'N/A')}</span></td>
                    <td>{teachers_str}</td>
                    <td>{group_str}</td>
                    <td>{item['datum']}</td>
                    <td>{item['time']}</td>
                    <td>{rooms_str}</td>
                </tr>
                """
            html += "</tbody></table></div>"

        html += "</body></html>"

        with open(f"{self.output_dir}/{filename}", "w", encoding="utf-8") as f:
            f.write(html)
