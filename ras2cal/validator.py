"""
validator.py - Validacija rasporeda

Provjerava da li svi assignmenti referenciraju definirane entitete
(nastavnike, predmete, prostorije, grupe).
Takodje provjerava konzistentnost frekvencije i nepoznate tokene.

Koristi se u exporteru za razdvajanje validnih od nevalidnih unosa.
"""
from .models import AssignmentNode


def validate_schedule(schedule):
    """Validira raspored provjerom referenci u assignmentima.

    Vraca:
        (valid, invalid) - valid je lista AssignmentNode-ova,
        invalid je lista (AssignmentNode, razlog_string) parova.
    """
    valid = []
    invalid = []

    # Skupovi definiranih entiteta za brzu provjeru
    valid_teachers = set(schedule.teachers.keys())
    valid_subjects = set(schedule.subjects.keys())
    valid_rooms = set(schedule.rooms.keys())
    valid_groups = set(schedule.subgroups.keys()) | set(schedule.study_groups.keys())

    for node in schedule.assignments:
        reasons = []

        # 1. Provjera nastavnika
        for t in node.teachers:
            if t not in valid_teachers:
                reasons.append(f"Nedefinisan nastavnik: '{t}'")

        # 2. Provjera predmeta
        if node.subject not in valid_subjects:
            reasons.append(f"Nedefinisan predmet: '{node.subject}'")

        # 3. Provjera prostorija
        for r in node.rooms:
            if r not in valid_rooms:
                reasons.append(f"Nedefinisana prostorija: '{r}'")

        # 4. Provjera grupa
        for sublist in node.groups:
            for g in sublist:
                if g not in valid_groups and g != "Svi":
                    reasons.append(f"Nedefinisana grupa: '{g}'")

        # 5. Provjera frekvencije (hint vs stvarni broj slotova)
        if node.frequency_hint:
            if len(node.slots) < node.frequency_hint:
                reasons.append(
                    f"Nedovoljno termina: trazeno {node.frequency_hint},"
                    f" pronadjeno {len(node.slots)} ({' '.join(node.slots)})"
                )

        # 6. Provjera nepoznatih tokena
        if node.unknown_tokens:
            reasons.append(f"Nepoznati tokeni: {', '.join(map(str, node.unknown_tokens))}")

        if reasons:
            invalid.append((node, "; ".join(reasons)))
        else:
            valid.append(node)

    return valid, invalid
