from ..models import AssignmentNode
from ..utils import format_person_name


class MarkdownReportGenerator:
    def __init__(self, schedule):
        self.schedule = schedule

    def generate(self):
        report = "# Plan Nastave - Semestralni Izvještaj\n\n"
        for node in self.schedule.assignments:
            if isinstance(node, AssignmentNode):
                prostor = ", ".join(node.rooms) if node.rooms else "Nije definisano"
                nastavnici = ", ".join([format_person_name(n) for n in node.teachers])
                subj_name = node.subject
                subj_type = node.type

                type_label = "Predavanje"
                if subj_type == 'V': type_label = "Vježbe"
                elif subj_type == 'L': type_label = "Laboratorijske vježbe"
                elif subj_type == 'T': type_label = "Tutorijal"

                # Formatiranje grupa (list of lists)
                raw_groups = node.groups
                if isinstance(raw_groups, list):
                     group_str = " + ".join([", ".join(sub) for sub in raw_groups])
                else:
                     group_str = str(raw_groups)

                report += f"### {subj_name}\n"
                report += f"- **Tip**: {type_label}\n"
                report += f"- **Nastavnik**: {nastavnici}\n"
                report += f"- **Grupe**: {group_str}\n"
                report += f"- **Prostorija**: {prostor}\n"
                report += f"- **Termini**: `{' '.join(node.slots)}`\n\n"
        return report
