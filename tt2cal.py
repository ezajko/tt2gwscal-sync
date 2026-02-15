import argparse
import json
import sys
from datetime import datetime, timedelta

from ras2cal.generators import (
    HTMLScheduleGenerator,
    JSONCalendarGenerator,
    MarkdownReportGenerator,
)
from ras2cal.lexer import Lexer
from ras2cal.parser import Parser
from ras2cal.utils import filter_schedule, load_source_recursive

# --- DEFAULT KONFIGURACIJA ---
DEFAULT_SEMESTAR_START = "2024-09-30"
DEFAULT_SEMESTAR_KRAJ = "2025-01-15"

def main():
    parser = argparse.ArgumentParser(description="Kompajler za školski raspored DSL u JSON/Markdown/HTML.")

    # Ulaz
    parser.add_argument("-i", "--input", required=True, help="Putanja do ulaznog .txt fajla")

    # Izlazi
    parser.add_argument("-j", "--json", help="Putanja za JSON izlaz")
    parser.add_argument("-m", "--md", help="Putanja za Markdown izvještaj")
    parser.add_argument("-w", "--html", help="Direktorij za generisanje HTML izvještaja")
    parser.add_argument("-e", "--export", help="Direktorij za eksport validiranog i refaktorisanog RAS koda")

    # Debug / Info
    parser.add_argument("-s", "--stdout", action="store_true", help="Ispiši generisani JSON na standardni izlaz (stdout)")
    parser.add_argument("-a", "--ast", action="store_true", help="Ispiši AST strukturu na stdout (debug)")

    # Filteri
    parser.add_argument("--teacher", help="Filtriraj po nastavniku (regex)")
    parser.add_argument("--room", help="Filtriraj po prostoriji (regex)")
    parser.add_argument("--group", help="Filtriraj po grupi (regex)")
    parser.add_argument("--subject", help="Filtriraj po predmetu (regex)")

    # Konfiguracija vremena
    parser.add_argument("--semestar-start", help="Početak semestra YYYY-MM-DD or DD.MM.YYYY")
    parser.add_argument("--semestar-end", help="Kraj semestra YYYY-MM-DD or DD.MM.YYYY")
    parser.add_argument("--semestar-duration", default=15, type=int, help="Trajanje u sedmicama (default 15)")
    parser.add_argument("--semestar-title", help="Naziv semestra (kalendara)")
    # Deprecated but kept for compat
    parser.add_argument("--start", help="Alias for --semestar-start")
    parser.add_argument("--end", help="Alias for --semestar-end")

    parser.add_argument("--base-time", default="08:00", help="Vrijeme početka prvog termina (HH:MM), default 08:00")
    parser.add_argument("--duration", default=30, type=int, help="Trajanje osnovnog slota u minutama (default 30)")
    parser.add_argument("--slots-per-index", default=2, type=int, help="Koliko slotova stane u jedan indeks broj (default 2)")

    args = parser.parse_args()

    # Provjera da li je zatražen ikakav izlaz
    if not any([args.json, args.md, args.html, args.stdout, args.ast, args.export]):
        parser.print_help(sys.stderr)
        print("\nUPOZORENJE: Niste specificirali izlazni format! Koristite -j, -m, -w, -s ili -e.", file=sys.stderr)
        sys.exit(1)

    # 1. Učitavanje
    full_text = load_source_recursive(args.input)

    # 2. Parsiranje
    lexer = Lexer(full_text)
    ast_parser = Parser(lexer.tokens)
    ast = ast_parser.parse() # Vraća Schedule objekat

    # Resolve Start
    arg_start = args.semestar_start or args.start
    if arg_start:
        try:
            semester_start = datetime.strptime(arg_start, "%Y-%m-%d").strftime("%Y-%m-%d")
        except ValueError:
            semester_start = datetime.strptime(arg_start, "%d.%m.%Y").strftime("%Y-%m-%d")
    elif ast.start_date:
        semester_start = ast.start_date
    else:
        # Default: 01.10.CurrentYear
        current_year = datetime.now().year
        semester_start = f"{current_year}-10-01"

    # Resolve Duration (weeks)
    duration_weeks = args.semestar_duration
    if ast.semester_info.get('duration_weeks'):
         duration_weeks = ast.semester_info['duration_weeks']

    # Resolve End
    arg_end = args.semestar_end or args.end
    if arg_end:
        try:
            semester_end = datetime.strptime(arg_end, "%Y-%m-%d").strftime("%Y-%m-%d")
        except ValueError:
            semester_end = datetime.strptime(arg_end, "%d.%m.%Y").strftime("%Y-%m-%d")
    elif ast.end_date:
        semester_end = ast.end_date
    else:
        # Calculate from start + duration
        start_dt = datetime.strptime(semester_start, "%Y-%m-%d")
        end_dt = start_dt + timedelta(weeks=duration_weeks)
        semester_end = end_dt.strftime("%Y-%m-%d")

    # Resolve Title
    semester_title = args.semestar_title
    if not semester_title and ast.semester_info.get('name'):
        # Format CamelCase to Space Separated
        import re
        raw_name = ast.semester_info['name']
        semester_title = re.sub(r'([a-z])([A-Z])', r'\1 \2', raw_name)
    if not semester_title:
        semester_title = f"Semestar {datetime.now().year}"

    print(f"Semestar: {semester_title} ({semester_start} - {semester_end})", file=sys.stderr)

    # 3. Filtriranje
    filters = {
        'teacher': args.teacher,
        'room': args.room,
        'group': args.group,
        'subject': args.subject
    }
    if any(filters.values()):
        ast = filter_schedule(ast, filters)
        print(f"✓ Primijenjeni filteri: { {k:v for k,v in filters.items() if v} }", file=sys.stderr)

    # 4. AST Ispis (opcionalno)
    if args.ast:
        print("=== AST STRUKTURA ===", file=sys.stderr)
        print(f"Summary: {ast}", file=sys.stderr)

        print("\n--- DAYS ---", file=sys.stderr)
        for node in ast.days.values(): print(node, file=sys.stderr)

        print("\n--- TEACHERS ---", file=sys.stderr)
        for node in ast.teachers.values(): print(node, file=sys.stderr)

        print("\n--- SUBJECTS ---", file=sys.stderr)
        for node in ast.subjects.values(): print(node, file=sys.stderr)

        print("\n--- STUDY GROUPS (DEPARTMENTS) ---", file=sys.stderr)
        for node in ast.study_groups.values(): print(node, file=sys.stderr)

        print("\n--- SUBGROUPS (GROUPS) ---", file=sys.stderr)
        for node in ast.subgroups.values(): print(node, file=sys.stderr)

        print("\n--- ROOMS ---", file=sys.stderr)
        for node in ast.rooms.values(): print(node, file=sys.stderr)

        print("\n--- ASSIGNMENTS ---", file=sys.stderr)
        for node in ast.assignments: print(node, file=sys.stderr)

        print("=====================", file=sys.stderr)

    # 5. Generisanje JSON-a (Samo ako je traženo)
    if args.json or args.stdout:
        json_gen = JSONCalendarGenerator(ast, semester_start, semester_end, args.base_time, args.duration, args.slots_per_index)
        events = json_gen.generate()

        output_data = {
            "meta": {
                "calendar_name": semester_title,
                "start": semester_start,
                "end": semester_end,
                "holidays": ast.holidays
            },
            "events": events
        }

        if args.json:
            with open(args.json, 'w', encoding='utf-8') as f:
                json.dump(output_data, f, indent=4, ensure_ascii=False)
            if not args.stdout:
                print(f"Generisan JSON: {args.json}", file=sys.stderr)

        if args.stdout:
            print(json.dumps(output_data, indent=4, ensure_ascii=False))

    # 6. Generisanje Markdown-a
    if args.md:
        md_gen = MarkdownReportGenerator(ast)
        with open(args.md, 'w', encoding='utf-8') as f:
            f.write(md_gen.generate())
        print(f"Generisan Markdown: {args.md}", file=sys.stderr)

    # 7. Generisanje HTML-a
    if args.html:
        html_gen = HTMLScheduleGenerator(ast, args.html, args.base_time, args.duration, args.slots_per_index)
        html_gen.generate()
        print(f"Generisani HTML fajlovi: {args.html}/", file=sys.stderr)

    # 8. Eksport (Refaktoring)
    if args.export:
        from ras2cal.exporter import Exporter
        exporter = Exporter(ast, args.export)
        exporter.export()

if __name__ == "__main__":
    main()
