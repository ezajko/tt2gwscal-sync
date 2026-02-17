#!/usr/bin/env python3
"""
tt2cal.py - Kompajler za raspored nastave (RAS DSL -> JSON/Markdown/HTML)

Ovaj fajl je glavni ulazni punkt za rad sa rasporedima.
Sva podrazumijevana konfiguracija (tipovi nastave, vrijeme termina, itd.)
se definise ovdje. Modul ras2cal/ je apstraktan i ne sadrzi defaulte.

Hijerarhija konfiguracije:
    1. Definicije iz .ras fajla (najjaci prioritet)
    2. CLI argumenti
    3. LECTURE_TYPES i ostale konstante iz ovog fajla (fallback)

Autor: Ernedin Zajko <ezajko@root.ba>
"""

import argparse
import json
import re
import signal
import sys
from datetime import datetime, timedelta

from ras2cal.compiler import ScheduleCompiler
from ras2cal.exporter import Exporter
from ras2cal.generators import (
    GridGenerator,
    HTMLScheduleGenerator,
    JSONScheduleGenerator,
    MarkdownReportGenerator,
)
from ras2cal.lexer import Lexer
from ras2cal.models import LectureType
from ras2cal.parser import Parser
from ras2cal.utils import filter_schedule, load_source_recursive

# Omogucava cist izlaz pri pipe-anju (npr. | head, | grep)
signal.signal(signal.SIGPIPE, signal.SIG_DFL)


# ---------------------------------------------------------------------------
# Podrazumijevana konfiguracija
# ---------------------------------------------------------------------------
# Tipovi nastave koji se koriste ako nisu definirani u .ras fajlu.
# Prioritet odredjuje redoslijed prikaza u generatorima (manji = vazniji).
LECTURE_TYPES = {
    "P": LectureType("P", "Predavanje", 0),
    "V": LectureType("V", "Vježbe", 1),
    "L": LectureType("L", "Laboratorijske vježbe", 2),
    "T": LectureType("T", "Tutorijal", 3),
    "N": LectureType("N", "Nepoznato", 9),
}


def main():
    # -------------------------------------------------------------------
    # Definicija CLI argumenata
    # -------------------------------------------------------------------
    parser = argparse.ArgumentParser(
        description="Kompajler za raspored nastave (RAS DSL) u JSON/Markdown/HTML."
    )

    # Ulazni fajl
    parser.add_argument("-i", "--input", required=True,
                        help="Putanja do ulaznog .ras fajla")

    # Izlazni formati
    parser.add_argument("-j", "--json", help="Putanja za JSON izlaz")
    parser.add_argument("-m", "--md", help="Putanja za Markdown izvjestaj")
    parser.add_argument("-w", "--html",
                        help="Direktorij za HTML izvjestaj (po nastavnicima/prostorima)")
    parser.add_argument("-g", "--grid",
                        help="Direktorij za tradicionalni grid HTML izvjestaj")
    parser.add_argument("-e", "--export",
                        help="Direktorij za eksport refaktorisanog RAS koda")

    # Debug i inspekcija
    parser.add_argument("-s", "--stdout", action="store_true",
                        help="Ispisi JSON na standardni izlaz (stdout)")
    parser.add_argument("-a", "--ast", action="store_true",
                        help="Ispisi AST strukturu na stdout (za debug/inspekciju)")

    # Filteri za suzavanje izlaza
    parser.add_argument("--teacher", help="Filtriraj po nastavniku (regex)")
    parser.add_argument("--room", help="Filtriraj po prostoriji (regex)")
    parser.add_argument("--group", help="Filtriraj po grupi/odjeljenju (regex)")
    parser.add_argument("--subject", help="Filtriraj po predmetu (regex)")

    # Konfiguracija semestra
    parser.add_argument("--semestar-start",
                        help="Pocetak semestra (YYYY-MM-DD ili DD.MM.YYYY)")
    parser.add_argument("--semestar-end",
                        help="Kraj semestra (YYYY-MM-DD ili DD.MM.YYYY)")
    parser.add_argument("--semestar-duration", default=15, type=int,
                        help="Trajanje u sedmicama (default: 15)")
    parser.add_argument("--semestar-title",
                        help="Naziv semestra (koristi se kao naziv kalendara)")

    # Konfiguracija vremena termina
    parser.add_argument("--base-time", default="08:00",
                        help="Vrijeme pocetka prvog termina, HH:MM (default: 08:00)")
    parser.add_argument("--duration", default=30, type=int,
                        help="Trajanje jednog slota u minutama (default: 30)")
    parser.add_argument("--slots-per-index", default=2, type=int,
                        help="Broj slotova po jednom indeksu (default: 2)")

    args = parser.parse_args()

    # Provjera da je specificiran barem jedan izlazni format
    has_output = any([args.json, args.md, args.html, args.grid,
                      args.stdout, args.ast, args.export])
    if not has_output:
        parser.print_help(sys.stderr)
        print("\nGreska: nije specificiran izlazni format."
              " Koristite -j, -m, -w, -g, -s, -a ili -e.", file=sys.stderr)
        sys.exit(1)

    # -------------------------------------------------------------------
    # 1. Ucitavanje izvornog koda
    # -------------------------------------------------------------------
    # load_source_recursive obraduje UVEZI direktive rekurzivno
    full_text = load_source_recursive(args.input)

    # -------------------------------------------------------------------
    # 2. Leksicka i sintaksna analiza (Lexer -> Parser -> AST)
    # -------------------------------------------------------------------
    lexer = Lexer(full_text)
    ast_parser = Parser(lexer.tokens)
    ast = ast_parser.parse()

    # -------------------------------------------------------------------
    # 3. Razrjesavanje semesterskih parametara
    # -------------------------------------------------------------------
    # Hijerarhija: CLI argument > .ras definicija > izracunati default

    # Pocetak semestra
    semester_start = _resolve_date(args.semestar_start)
    if not semester_start and ast.start_date:
        semester_start = ast.start_date
    if not semester_start:
        semester_start = f"{datetime.now().year}-10-01"

    # Trajanje u sedmicama
    duration_weeks = args.semestar_duration
    if ast.semester_info.get('duration_weeks'):
        duration_weeks = ast.semester_info['duration_weeks']

    # Kraj semestra
    semester_end = _resolve_date(args.semestar_end)
    if not semester_end and ast.end_date:
        semester_end = ast.end_date
    if not semester_end:
        start_dt = datetime.strptime(semester_start, "%Y-%m-%d")
        semester_end = (start_dt + timedelta(weeks=duration_weeks)).strftime("%Y-%m-%d")

    # Naziv semestra
    semester_title = args.semestar_title
    if not semester_title and ast.semester_info.get('name'):
        # Konvertuj CamelCase u razmak-odvojeni naziv
        semester_title = re.sub(r'([a-z])([A-Z])', r'\1 \2',
                                ast.semester_info['name'])
    if not semester_title:
        semester_title = f"Semestar {datetime.now().year}"

    # Postavi razrijesene vrijednosti nazad na AST (koriste ih generatori i exporter)
    if not ast.semester_info.get('name'):
        ast.semester_info['name'] = semester_title.replace(" ", "")
    ast.semester_info['start_date'] = semester_start
    ast.semester_info['end_date'] = semester_end
    ast.semester_info['duration_weeks'] = duration_weeks

    print(f"Semestar: {semester_title} ({semester_start} - {semester_end})",
          file=sys.stderr)

    # -------------------------------------------------------------------
    # 4. Filtriranje rasporeda (opcionalno)
    # -------------------------------------------------------------------
    filters = {
        'teacher': args.teacher,
        'room': args.room,
        'group': args.group,
        'subject': args.subject,
    }
    active_filters = {k: v for k, v in filters.items() if v}
    if active_filters:
        ast = filter_schedule(ast, filters)
        print(f"Primijenjeni filteri: {active_filters}", file=sys.stderr)

    # -------------------------------------------------------------------
    # 5. Postavljanje konfiguracije na AST
    # -------------------------------------------------------------------
    ast.base_time = args.base_time
    ast.slot_duration = args.duration
    ast.slots_per_index = args.slots_per_index

    # Spajanje tipova nastave:
    #   LECTURE_TYPES (defaults) <- .ras definicije (override) <- fallback za nepoznate
    merged_types = dict(LECTURE_TYPES)

    # Tipovi eksplicitno definirani u .ras fajlu imaju prednost
    for code, node in ast.lecture_types.items():
        merged_types[code] = LectureType(code, node.name, node.priority)

    # Tipovi koji se pojavljuju u predmetima/nastavi ali nigdje nisu definirani
    # dobijaju genericki naziv i najnizi prioritet
    for subj in ast.subjects.values():
        for t_code in subj.types:
            if t_code not in merged_types:
                merged_types[t_code] = LectureType(t_code, t_code, 99)
    for assignment in ast.assignments:
        if assignment.type and assignment.type not in merged_types:
            merged_types[assignment.type] = LectureType(assignment.type,
                                                        assignment.type, 99)

    ast.default_types = merged_types

    # -------------------------------------------------------------------
    # 6. AST ispis (debug/inspekcija)
    # -------------------------------------------------------------------
    # Pozicionirano nakon koraka 5 da prikaze kompletno stanje
    # ukljucujuci merged tipove nastave i postavljenu konfiguraciju.
    # Izlaz ide na stdout da se moze pipe-ati (| head, | grep, itd.)
    if args.ast:
        _print_ast(ast)

    # -------------------------------------------------------------------
    # 7. Kompajliranje AST-a u IR (Intermediate Representation)
    # -------------------------------------------------------------------
    compiler = ScheduleCompiler(ast)
    ir_model = compiler.compile()

    # Prenesi konfiguraciju na IR model (generatori citaju iz njega)
    ir_model.base_time = ast.base_time
    ir_model.slot_duration = ast.slot_duration
    ir_model.slots_per_index = ast.slots_per_index
    ir_model.default_types = ast.default_types

    # -------------------------------------------------------------------
    # 8. Generisanje izlaza
    # -------------------------------------------------------------------

    # JSON
    if args.json or args.stdout:
        json_gen = JSONScheduleGenerator(ir_model)
        events = json_gen.generate()

        output_data = {
            "meta": {
                "calendar_name": semester_title,
                "start": semester_start,
                "end": semester_end,
                "holidays": ast.holidays,
            },
            "events": events,
        }

        if args.json:
            with open(args.json, 'w', encoding='utf-8') as f:
                json.dump(output_data, f, indent=4, ensure_ascii=False)
            if not args.stdout:
                print(f"Generisan JSON: {args.json}", file=sys.stderr)

        if args.stdout:
            print(json.dumps(output_data, indent=4, ensure_ascii=False))

    # Markdown
    if args.md:
        md_gen = MarkdownReportGenerator(ir_model)
        with open(args.md, 'w', encoding='utf-8') as f:
            f.write(md_gen.generate())
        print(f"Generisan Markdown: {args.md}", file=sys.stderr)

    # HTML (po nastavnicima i prostorima)
    if args.html:
        html_gen = HTMLScheduleGenerator(ir_model, args.html,
                                         title=semester_title)
        html_gen.generate()
        print(f"Generisani HTML fajlovi: {args.html}/", file=sys.stderr)

    # Grid HTML (tradicionalni tabelarni prikaz)
    if args.grid:
        grid_gen = GridGenerator(ir_model, args.grid, title=semester_title)
        grid_gen.generate()
        print(f"Generisan grid HTML: {args.grid}/", file=sys.stderr)

    # Eksport refaktorisanog RAS koda
    if args.export:
        exporter = Exporter(ast, args.export)
        exporter.export()


# ---------------------------------------------------------------------------
# Pomocne funkcije
# ---------------------------------------------------------------------------

def _resolve_date(date_str):
    """Parsira datum iz stringa. Podrzava formate YYYY-MM-DD i DD.MM.YYYY.
    Vraca None ako string nije dat ili je prazan."""
    if not date_str:
        return None
    try:
        return datetime.strptime(date_str, "%Y-%m-%d").strftime("%Y-%m-%d")
    except ValueError:
        return datetime.strptime(date_str, "%d.%m.%Y").strftime("%Y-%m-%d")


def _print_ast(ast):
    """Ispisuje kompletnu AST strukturu na stdout.
    Koristi se sa -a/--ast flagom za debug i inspekciju."""
    print("=== AST STRUKTURA ===")
    print(f"Summary: {ast}")

    print("\n--- SEMESTER INFO ---")
    print(ast.semester_info)

    print("\n--- DAYS ---")
    for node in ast.days.values():
        print(node)

    print("\n--- SLOTS ---")
    for node in ast.slots.values():
        print(node)

    print("\n--- TEACHERS ---")
    for node in ast.teachers.values():
        print(node)

    print("\n--- SUBJECTS ---")
    for node in ast.subjects.values():
        print(node)

    print("\n--- STUDY GROUPS ---")
    for node in ast.study_groups.values():
        print(node)

    print("\n--- SUBGROUPS ---")
    for node in ast.subgroups.values():
        print(node)

    print("\n--- ROOMS ---")
    for node in ast.rooms.values():
        print(node)

    print("\n--- LECTURE TYPES (merged) ---")
    for lt in sorted(ast.default_types.values(), key=lambda t: t.priority):
        print(lt)

    print("\n--- ASSIGNMENTS ---")
    for node in ast.assignments:
        print(node)

    print("=====================")


if __name__ == "__main__":
    main()
