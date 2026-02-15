from .models import AssignmentNode


def validate_schedule(schedule):
    """
    Validira raspored. Vraća (valid_assignments, invalid_assignments_with_reasons).
    """
    valid = []
    invalid = []

    valid_teachers = set(schedule.teachers.keys())
    valid_subjects = set(schedule.subjects.keys())
    valid_rooms = set(schedule.rooms.keys())
    valid_groups = set(schedule.subgroups.keys()) | set(schedule.study_groups.keys())

    for node in schedule.assignments:
        reasons = []

        # 1. Provjera Nastavnika
        for t in node.teachers:
            if t not in valid_teachers:
                if valid_teachers:
                    reasons.append(f"Nedefinisan nastavnik: '{t}'")

        # 2. Provjera Predmeta
        if node.subject not in valid_subjects:
            if valid_subjects:
                reasons.append(f"Nedefinisan predmet: '{node.subject}'")

        # 3. Provjera Prostorija
        for r in node.rooms:
            if r not in valid_rooms:
                if valid_rooms:
                    reasons.append(f"Nedefinisana prostorija: '{r}'")

        # 4. Provjera Grupa
        if valid_groups:
            for sublist in node.groups:
                for g in sublist:
                    if g not in valid_groups and g != "Svi":
                        reasons.append(f"Nedefinisana grupa: '{g}'")

        # 5. Provjera Frekvencije (Hint)
        if node.frequency_hint:
            if len(node.slots) < node.frequency_hint:
                reasons.append(f"Nedovoljno termina: Trazeno {node.frequency_hint}, pronadjeno {len(node.slots)} ({' '.join(node.slots)})")

        # 6. Provjera Nepoznatih Tokena
        if node.unknown_tokens:
            reasons.append(f"Nepoznati tokeni: {', '.join(map(str, node.unknown_tokens))}")

        if reasons:
            invalid.append((node, "; ".join(reasons)))
        else:
            valid.append(node)

    return valid, invalid
