import os
import re
import sys


def format_person_name(n):
    return re.sub(r'([a-z])([A-Z])', r'\1 \2', n.replace("_", "")).strip()

def format_subject_name(s):
    if s.startswith('t'): tipo = 'T'   # Tutorijal
    elif s.startswith('v'): tipo = 'V' # Vježbe
    elif s.startswith('l'): tipo = 'L' # Lab
    else: tipo = 'P'                   # Predavanje

    name = re.sub(r'^[ptlv]{1,2}(?=[A-Z])', '', s)
    name = re.sub(r'([a-z0-9])([A-Z])', r'\1 \2', name)
    name = re.sub(r'([A-Z])([A-Z][a-z])', r'\1 \2', name)
    name = re.sub(r'([a-zA-Z])(\d)', r'\1 \2', name)

    return name.strip(), tipo

def merge_events(events):
    merged_map = {}
    for e in events:
        key = (e['datum'], e['vrijeme_start'], e['vrijeme_kraj'], e['osoba'])
        if key in merged_map:
            existing = merged_map[key]
            if e['predmet'] not in existing['predmet']:
                existing['predmet'] += " / " + e['predmet']

            for sublist in e['grupe']:
                if sublist not in existing['grupe']:
                    existing['grupe'].append(sublist)

            if e['tip'] not in existing['tip']:
                 existing['tip'] += "/" + e['tip']
            existing_rooms = set(existing['prostorija'])
            new_rooms = set(e['prostorija'])
            existing['prostorija'] = sorted(list(existing_rooms.union(new_rooms)))
        else:
            merged_map[key] = e.copy()
            if not isinstance(merged_map[key]['prostorija'], list):
                 merged_map[key]['prostorija'] = [merged_map[key]['prostorija']]
    return list(merged_map.values())

def load_source_recursive(file_path, seen=None):
    if seen is None: seen = set()
    abs_path = os.path.abspath(file_path)
    if abs_path in seen:
        print(f"Upozorenje: Detektovan kružni import za '{file_path}'. Preskačem.")
        return ""
    seen.add(abs_path)
    if not os.path.exists(file_path):
        print(f"Greška: Fajl '{file_path}' nije pronađen.")
        sys.exit(1)
    combined_lines = []
    base_dir = os.path.dirname(file_path)
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            for line in f:
                match = re.match(r'^\s*UVEZI:\s*(.+)\s*$', line)
                if match:
                    import_path = match.group(1).strip().strip('"').strip("'")
                    full_import_path = os.path.join(base_dir, import_path)
                    imported_content = load_source_recursive(full_import_path, seen)
                    combined_lines.append(f"\n// --- Početak importa: {import_path} ---\n")
                    combined_lines.append(imported_content)
                    combined_lines.append(f"\n// --- Kraj importa: {import_path} ---\n")
                else:
                    combined_lines.append(line)
    except FileNotFoundError:
        print(f"Greška: Ulazni fajl '{file_path}' nije pronađen.")
        sys.exit(1)
    return "".join(combined_lines)

def filter_schedule(schedule, filters):
    from .models import Schedule

    new_schedule = Schedule()
    new_schedule.days = schedule.days
    new_schedule.slots = schedule.slots
    new_schedule.teachers = schedule.teachers
    new_schedule.subjects = schedule.subjects
    new_schedule.study_groups = schedule.study_groups
    new_schedule.subgroups = schedule.subgroups
    new_schedule.rooms = schedule.rooms

    for node in schedule.assignments:
        match = True

        if filters.get('teacher'):
            if not any(re.search(filters['teacher'], t, re.IGNORECASE) for t in node.teachers):
                match = False

        if match and filters.get('room'):
            if not any(re.search(filters['room'], r, re.IGNORECASE) for r in node.rooms):
                match = False

        if match and filters.get('group'):
            flat_groups = ", ".join([", ".join(sub) for sub in node.groups])
            if not re.search(filters['group'], flat_groups, re.IGNORECASE):
                match = False

        if match and filters.get('subject'):
            if not re.search(filters['subject'], node.subject, re.IGNORECASE):
                match = False

        if match:
            new_schedule.assignments.append(node)

    return new_schedule
