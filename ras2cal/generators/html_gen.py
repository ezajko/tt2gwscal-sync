import os

from ..utils import merge_events


class HTMLScheduleGenerator:
    def __init__(self, model, output_dir, title=None):
        self.model = model
        self.output_dir = output_dir.rstrip('/')
        self.title = title if title else f"Raspored - {model.semester_name}"

        self.day_order = {
            "Ponedjeljak": 0, "Ponedeljak": 0, "Mon": 0,
            "Utorak": 1, "Tue": 1,
            "Srijeda": 2, "Sreda": 2, "Wed": 2,
            "Četvrtak": 3, "Cetvrtak": 3, "Thu": 3,
            "Petak": 4, "Fri": 4,
            "Subota": 5, "Sat": 5,
            "Nedjelja": 6, "Nedelja": 6, "Sun": 6,
            "Nepoznato": 7
        }
        self.type_order = {'P': 0, 'V': 1, 'L': 2, 'T': 3}

    def generate(self):
        if not os.path.exists(self.output_dir):
            os.makedirs(self.output_dir)

        raw_data = []
        for ev in self.model.events:
             entry = {
                'subject': ev.subject.name,
                'type': ev.type.code,
                'teachers': [t.name for t in ev.teachers],
                'grupe': [[g.name] for g in ev.groups],
                'rooms': [r.name for r in ev.rooms],
                'day': ev.day_name,
                'time': f"{ev.start_time_str} - {ev.end_time_str}",
                'start_time': ev.start_time_str,
                'end_time': ev.end_time_str,

                # Legacy fields for compatibility with existing templates/methods
                'predmet': ev.subject.name,
                'tip': ev.type.code,
                'prostorija': [r.name for r in ev.rooms]
            }
             raw_data.append(entry)

        merged_data = merge_events(raw_data)
        condensed_raw = self._condense_teachers(raw_data)
        condensed_merged = self._condense_teachers(merged_data)

        # Generisanje podataka za grupe (sa nasljeđivanjem)
        groups_data = self._generate_groups_view(raw_data)

        prefix = self.model.semester_name

        self._write_html(f"{prefix}_predmeti.html", f"{self.title} - Po Predmetima", self._group_by(condensed_raw, 'subject'), prefix, sort_by_type=True)
        self._write_html(f"{prefix}_nastavnici.html", f"{self.title} - Po Nastavnicima", self._group_by_list(condensed_merged, 'teachers'), prefix)
        self._write_html(f"{prefix}_prostorije.html", f"{self.title} - Po Prostorijama", self._group_by_list(condensed_merged, 'prostorija'), prefix)
        self._write_html(f"{prefix}_grupe.html", f"{self.title} - Po Grupama", groups_data, prefix)

    def _generate_groups_view(self, raw_data):
        """Generiše mapu evenata za svaku grupu, uključujući naslijeđene evente od roditelja."""

        group_events = {}
        # Sort groups by name for consistent output
        all_groups = sorted(self.model.groups.values(), key=lambda g: g.name)

        for group in all_groups:
            if group.name == "Svi": continue # Skip "Svi" as a specific group view

            # Ancestors (parents)
            ancestors = group.get_all_ancestors()
            relevant_names = {group.name} | {a.name for a in ancestors}

            my_events = []
            for item in raw_data:
                # Check intersection
                is_relevant = False
                for sublist in item['grupe']:
                    if not set(sublist).isdisjoint(relevant_names):
                        is_relevant = True
                        break

                # Check "Svi"
                if [["Svi"]] == item['grupe']:
                    is_relevant = True

                if is_relevant:
                    my_events.append(item)

            if my_events:
                merged = merge_events(my_events)
                condensed = self._condense_teachers(merged)
                group_events[group.name] = condensed

        return group_events

    def _condense_teachers(self, data):
        grouped = {}
        for item in data:
            rooms_list = item.get('prostorija', item.get('rooms', []))
            rooms_tuple = tuple(sorted(rooms_list))

            raw_groups = item.get('grupe', item.get('group', []))
            groups_tuple = tuple(tuple(sub) for sub in raw_groups)

            key = (
                item['day'],
                item['start_time'],
                item['end_time'],
                item.get('predmet', item.get('subject')),
                groups_tuple,
                rooms_tuple,
                item.get('tip', item.get('type'))
            )

            if key not in grouped:
                grouped[key] = item.copy()
                # Ensure list copy
                grouped[key]['teachers'] = list(item['teachers'])
            else:
                current = grouped[key]['teachers']
                for t in item['teachers']:
                    if t not in current:
                        current.append(t)
        return list(grouped.values())

    def _group_by(self, data, key):
        grouped = {}
        for item in data:
            val = item.get(key)
            if not val and key == 'subject': val = item.get('predmet')
            if not val: val = "N/A"

            if val not in grouped: grouped[val] = []
            grouped[val].append(item)
        return grouped

    def _group_by_list(self, data, list_key):
        grouped = {}
        for item in data:
            values = item.get(list_key, [])
            if not isinstance(values, list): values = [values]
            if not values: values = ["N/A"]
            for v in values:
                if v not in grouped: grouped[v] = []
                grouped[v].append(item)
        return grouped

    def _write_html(self, filename, title, grouped_data, prefix, sort_by_type=False):
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

        sorted_keys = sorted(grouped_data.keys())

        for key in sorted_keys:
            items = grouped_data[key]

            if sort_by_type:
                items.sort(key=lambda x: (
                    self.type_order.get(x.get('tip', 'P')[0], 99),
                    self.day_order.get(x['day'], 99),
                    x['start_time']
                ))
            else:
                items.sort(key=lambda x: (
                    self.day_order.get(x['day'], 99),
                    x['start_time']
                ))

            html += f"<div class='section'><div class='section-title'>{key}</div><table>"
            html += "<thead><tr><th>Predmet</th><th>Tip</th><th>Nastavnici</th><th>Grupe</th><th>Dan</th><th>Vrijeme</th><th>Prostorija</th></tr></thead><tbody>"

            for item in items:
                teachers_str = ", ".join(item['teachers'])

                rooms_to_show = item.get('prostorija', item.get('rooms', []))
                rooms_str = ", ".join(rooms_to_show) if rooms_to_show else "N/A"

                current_type = item.get('tip', item.get('type', 'P'))

                tag_class = "tag-P"
                if "V" in current_type: tag_class = "tag-V"
                elif "L" in current_type: tag_class = "tag-L"
                elif "T" in current_type: tag_class = "tag-T"

                raw_groups = item.get('grupe', item.get('group', []))
                if isinstance(raw_groups, list):
                     group_str = " + ".join([", ".join(sub) for sub in raw_groups])
                else:
                     group_str = str(raw_groups)

                html += f"""
                <tr>
                    <td>{item.get('predmet', item.get('subject'))}</td>
                    <td><span class="tag {tag_class}">{current_type}</span></td>
                    <td>{teachers_str}</td>
                    <td>{group_str}</td>
                    <td>{item['day']}</td>
                    <td>{item['time']}</td>
                    <td>{rooms_str}</td>
                </tr>
                """
            html += "</tbody></table></div>"

        html += "</body></html>"

        with open(f"{self.output_dir}/{filename}", "w", encoding="utf-8") as f:
            f.write(html)
