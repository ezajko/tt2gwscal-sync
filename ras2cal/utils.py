"""
utils.py - Pomocne funkcije za ras2cal modul

Sadrzi:
    - format_camel_case: CamelCase -> razmak-odvojeno ime
    - format_subject_name: tip-prefixed naziv -> (ime, kod_tipa)
    - merge_events: spajanje dupliciranih evenata u JSON izlazu
    - load_source_recursive: ucitavanje .ras fajlova sa UVEZI direktivama
    - filter_schedule: filtriranje rasporeda po nastavniku/grupi/prostoriji/predmetu
"""
import os
import re
import sys


# ---------------------------------------------------------------------------
# Formatiranje imena
# ---------------------------------------------------------------------------

def format_camel_case(n):
    """Pretvara CamelCase u razmak-odvojeno ime.
    Primjer: 'ImePrezime' -> 'Ime Prezime'
             'LaboratorijskeVjezbe' -> 'Laboratorijske Vjezbe'"""
    return re.sub(r'([a-z])([A-Z])', r'\1 \2', n.replace("_", "")).strip()


# Alias za kompatibilnost (koristi se u tt2cal.py i drugdje)
format_person_name = format_camel_case


def format_subject_name(s, valid_types=None):
    """Razdvaja naziv predmeta na (ime, tip_kod).

    Predmeti u RAS formatu koriste prefix za tip nastave:
        'pUvodUProgramiranje' -> ('Uvod U Programiranje', 'P')
        'vLinearnaAlgebra'    -> ('Linearna Algebra', 'V')

    Args:
        s: CamelCase string predmeta sa prefiksom tipa.
        valid_types: Opciona lista/set validnih kodova tipova (npr. ['P', 'V', 'L']).
                     Ako nije proslijedjen, koristi se prvi karakter bez validacije.

    Returns:
        (naziv_predmeta, kod_tipa) tuple.
    """
    if not s:
        return "", 'N'

    first_char = s[0].upper()

    # Provjeri da li je prvi karakter validni kod tipa nastave
    if valid_types is not None:
        tipo = first_char if first_char in valid_types else 'N'
    else:
        # Bez eksplicitne liste: koristi prvi karakter (originalno ponasanje)
        tipo = first_char

    # Ukloni prefix tipa i razdvoji CamelCase u rijeci
    name = s[1:]
    name = re.sub(r'([a-z0-9])([A-Z])', r'\1 \2', name)
    name = re.sub(r'([A-Z])([A-Z][a-z])', r'\1 \2', name)
    name = re.sub(r'([a-zA-Z])(\d)', r'\1 \2', name)

    return name.strip(), tipo


# ---------------------------------------------------------------------------
# Spajanje dupliciranih evenata
# ---------------------------------------------------------------------------

def merge_events(events):
    """Spaja evente koji imaju isti datum, vrijeme i osobu.
    Koristi se u JSON i HTML generatorima za konsolidaciju izlaza."""
    merged_map = {}

    for e in events:
        key = (e['datum'], e['vrijeme_start'], e['vrijeme_kraj'], e['osoba'])

        if key in merged_map:
            existing = merged_map[key]

            # Spoji predmete ako su razliciti
            if e['predmet'] not in existing['predmet']:
                existing['predmet'] += " / " + e['predmet']

            # Spoji grupe
            for sublist in e['grupe']:
                if sublist not in existing['grupe']:
                    existing['grupe'].append(sublist)

            # Spoji tipove
            if e['tip'] not in existing['tip']:
                existing['tip'] += "/" + e['tip']

            # Spoji prostorije (unikatne, sortirane)
            existing_rooms = set(existing['prostorija'])
            new_rooms = set(e['prostorija'])
            existing['prostorija'] = sorted(existing_rooms | new_rooms)
        else:
            merged_map[key] = e.copy()
            # Osiguraj da prostorija bude lista
            if not isinstance(merged_map[key]['prostorija'], list):
                merged_map[key]['prostorija'] = [merged_map[key]['prostorija']]

    return list(merged_map.values())


# ---------------------------------------------------------------------------
# Priprema IR podataka za generatore (zajednicka logika)
# ---------------------------------------------------------------------------

def prepare_raw_data(events):
    """Pretvara listu IR Event objekata u listu dict-ova.

    Za svakog nastavnika kreira zaseban zapis (za grupiranje po osobi).
    Koriste je html_gen.py i grid_gen.py.

    Args:
        events: lista Event objekata iz IR modela

    Returns:
        lista dict-ova sa kljucevima: predmet, tip, grupe, prostorija,
        datum, vrijeme_start, vrijeme_kraj, osoba, teachers, time, itd.
    """
    from .ir import Person

    raw_data = []
    for ev in events:
        teachers_list = [t.name for t in ev.teachers]
        # Ako nema nastavnika, koristi placeholder
        loop_teachers = ev.teachers or [Person("Nepoznato", "Nepoznato")]

        for teacher in loop_teachers:
            entry = {
                'predmet': ev.subject.name,
                'tip': ev.type.code,
                'grupe': [[g.name] for g in ev.groups],
                'prostorija': [r.name for r in ev.rooms],
                'datum': ev.day_name,
                'vrijeme_start': ev.start_time_str,
                'vrijeme_kraj': ev.end_time_str,
                'osoba': teacher.name,
                'teachers': teachers_list,
                'start_time': ev.start_time_str,
                'end_time': ev.end_time_str,
                'time': f"{ev.start_time_str} - {ev.end_time_str}",
            }
            raw_data.append(entry)
    return raw_data


def condense_teachers(data):
    """Spaja evente koji se razlikuju samo po nastavniku u jedan zapis.

    Koriste je html_gen.py i grid_gen.py za eliminaciju duplikata
    kod grupiranja po entitetima.

    Args:
        data: lista dict-ova (izlaz iz prepare_raw_data ili merge_events)

    Returns:
        lista konsolidiranih dict-ova.
    """
    grouped = {}
    for item in data:
        rooms_tuple = tuple(sorted(item.get('prostorija', [])))
        groups_tuple = tuple(tuple(sub) for sub in item.get('grupe', []))

        key = (
            item['datum'], item['vrijeme_start'], item['vrijeme_kraj'],
            item['predmet'], groups_tuple, rooms_tuple, item['tip'],
        )

        if key not in grouped:
            grouped[key] = item.copy()
            grouped[key]['teachers'] = list(item['teachers'])
        else:
            # Dodaj nastavnike kojih nema u listi
            current = grouped[key]['teachers']
            for t in item['teachers']:
                if t not in current:
                    current.append(t)

    return list(grouped.values())


# ---------------------------------------------------------------------------
# Ucitavanje izvornog koda sa UVEZI direktivama
# ---------------------------------------------------------------------------

def load_source_recursive(file_path, seen=None):
    """Ucitava .ras fajl i rekurzivno razrijesava UVEZI direktive.
    Detektuje kruzne importe i zaustavlja se sa upozorenjem.

    Args:
        file_path: putanja do .ras fajla
        seen: skup vec ucitanih putanja (za detekciju kruznih importa)

    Returns:
        string sa spojenim sadrzajem svih fajlova
    """
    if seen is None:
        seen = set()

    abs_path = os.path.abspath(file_path)

    # Provjera kruznog importa
    if abs_path in seen:
        print(f"Upozorenje: Detektovan kružni import za '{file_path}'. Preskačem.")
        return ""
    seen.add(abs_path)

    combined_lines = []
    base_dir = os.path.dirname(file_path)

    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            for line in f:
                match = re.match(r'^\s*UVEZI:\s*(.+)\s*$', line)
                if match:
                    # Razrijesi UVEZI direktivu rekurzivno
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


# ---------------------------------------------------------------------------
# Filtriranje rasporeda
# ---------------------------------------------------------------------------

def filter_schedule(schedule, filters):
    """Filtrira assignments po nastavniku, prostoriji, grupi ili predmetu.
    Vraca novi Schedule sa svim definicijama ali samo filtriranim assignmentima.

    Kopira sve definicije (dani, termini, nastavnici, itd.) i konfiguraciju
    (semester_info, base_time, default_types) na novi Schedule objekat.

    Args:
        schedule: Schedule AST objekat
        filters: dict sa kljucevima 'teacher', 'room', 'group', 'subject'
                 (vrijednosti su regex obrasci ili None)
    """
    from .models import Schedule

    new_schedule = Schedule()

    # Kopiraj sve definicije (ove se ne filtriraju)
    new_schedule.days = schedule.days
    new_schedule.slots = schedule.slots
    new_schedule.teachers = schedule.teachers
    new_schedule.subjects = schedule.subjects
    new_schedule.study_groups = schedule.study_groups
    new_schedule.subgroups = schedule.subgroups
    new_schedule.rooms = schedule.rooms
    new_schedule.lecture_types = schedule.lecture_types

    # Kopiraj semester info i konfiguraciju
    new_schedule.semester_info = type(schedule.semester_info)(schedule.semester_info)
    new_schedule.base_time = schedule.base_time
    new_schedule.slot_duration = schedule.slot_duration
    new_schedule.slots_per_index = schedule.slots_per_index
    new_schedule.default_types = schedule.default_types

    # Filtriraj assignments
    for node in schedule.assignments:
        match = True

        if filters.get('teacher'):
            if not any(re.search(filters['teacher'], t, re.IGNORECASE)
                       for t in node.teachers):
                match = False

        if match and filters.get('room'):
            if not any(re.search(filters['room'], r, re.IGNORECASE)
                       for r in node.rooms):
                match = False

        if match and filters.get('group'):
            flat_groups = ", ".join(", ".join(sub) for sub in node.groups)
            if not re.search(filters['group'], flat_groups, re.IGNORECASE):
                match = False

        if match and filters.get('subject'):
            if not re.search(filters['subject'], node.subject, re.IGNORECASE):
                match = False

        if match:
            new_schedule.assignments.append(node)

    return new_schedule
