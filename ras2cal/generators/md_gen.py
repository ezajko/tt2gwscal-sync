"""
md_gen.py - Markdown generator za raspored

Generise tekstualni izvjestaj u Markdown formatu.
Za svaki event ispisuje predmet, tip, nastavnika, grupe, prostoriju i termine.

Prima ScheduleModel (IR) objekat, konzistentno sa ostalim generatorima.
"""


class MarkdownReportGenerator:
    """Generator za Markdown izvjestaj rasporeda.

    Args:
        model: ScheduleModel IR objekat sa svim kompajliranim eventima.
    """

    def __init__(self, model):
        self.model = model

    def generate(self):
        """Generise kompletni Markdown izvjestaj."""
        report = "# Plan Nastave - Semestralni Izvještaj\n\n"

        for ev in self.model.events:
            nastavnici = ", ".join(t.name for t in ev.teachers)
            prostor = ", ".join(r.name for r in ev.rooms) if ev.rooms else "Nije definisano"

            # Labela tipa nastave (koristi puni naziv iz LectureType objekta)
            type_label = ev.type.name

            # Formatiranje grupa
            group_str = " + ".join(g.name for g in ev.groups)

            report += f"### {ev.subject.name}\n"
            report += f"- **Tip**: {type_label}\n"
            report += f"- **Nastavnik**: {nastavnici}\n"
            report += f"- **Grupe**: {group_str}\n"
            report += f"- **Prostorija**: {prostor}\n"
            report += f"- **Dan**: {ev.day_name}\n"
            report += f"- **Vrijeme**: `{ev.start_time_str} - {ev.end_time_str}`\n\n"

        return report
