#!/usr/bin/env python3
#
# Author: Ernedin Zajko <ezajko@root.ba>
# License: GNU General Public License v2.0 or later (GPL-2.0+)
#

import argparse
import csv
import json
import logging
import os
import sys
from datetime import datetime

from google.oauth2 import service_account
from googleapiclient.discovery import build

# --- KONFIGURACIJA PUTANJA ---
CSV_DIR  = 'csv'
LOG_DIR  = 'logs'
AUTH_DIR = 'auth'
JSON_DIR = 'data'

SERVICE_ACCOUNT_FILE = os.path.join(AUTH_DIR, 'service_account.json')
SCOPES = ['https://www.googleapis.com/auth/calendar']

FILE_PERSONS   = os.path.join(CSV_DIR, 'person.csv')
FILE_CALENDARS = os.path.join(CSV_DIR, 'person_calendars.csv')
FILE_ROOMS     = os.path.join(CSV_DIR, 'rooms.csv')
FILE_TYPES     = os.path.join(CSV_DIR, 'lecture_type.csv')

def setup_logging(calendar_name):
    if not os.path.exists(LOG_DIR): os.makedirs(LOG_DIR)
    timestamp = datetime.now().strftime('%Y-%m-%d-%H-%M')
    log_path = os.path.join(LOG_DIR, f"sync.{calendar_name}.{timestamp}.log")

    logger = logging.getLogger()
    logger.setLevel(logging.INFO)
    if logger.hasHandlers(): logger.handlers.clear()

    fh = logging.FileHandler(log_path, encoding='utf-8')
    fh.setFormatter(logging.Formatter('%(asctime)s [%(levelname)s] %(message)s'))
    logger.addHandler(fh)

    ch = logging.StreamHandler()
    ch.setFormatter(logging.Formatter('%(message)s'))
    logger.addHandler(ch)
    return logger

def batch_callback(request_id, response, exception):
    """Callback funkcija koja hvata greške unutar batch-a."""
    if exception is not None:
        logging.error(f"   [BATCH ERROR] Zahtjev {request_id} neuspješan: {exception}")

def load_csv_to_dict(filename, key_col):
    if not os.path.exists(filename):
        logging.error(f"Nedostaje fajl: {filename}")
        sys.exit(1)
    with open(filename, mode='r', encoding='utf-8') as f:
        return {row[key_col]: row for row in csv.DictReader(f, quotechar='"')}

def transform_event(termin, tipovi, prostorije, osobe_map):
    tip = tipovi.get(termin['tip'], {"title": "Nastava", "color": "8", "label": "INFO"})
    attendees = []

    # Sale
    lista_sala = termin.get('prostorije', [])
    if isinstance(lista_sala, str): lista_sala = [lista_sala]
    for sala_naziv in lista_sala:
        sala_id = prostorije.get(sala_naziv)
        if sala_id: attendees.append({'email': sala_id, 'resource': True})

    # Dodatne osobe lookup
    if termin.get('dodatne_osobe'):
        for osoba_input in termin['dodatne_osobe']:
            osoba_input = osoba_input.strip()
            if osoba_input in osobe_map:
                attendees.append({'email': osobe_map[osoba_input]['google_id']})
            elif "@" in osoba_input:
                attendees.append({'email': osoba_input})

    # Izgradnja opisa (sve dostupne informacije)
    desc_lines = [
        f"Predmet: {termin['predmet']}",
        f"Tip: {tip['title']}",
        f"Grupa: {termin.get('grupa', 'Svi')}"
    ]
    if termin.get('napomena'):
        desc_lines.append(f"Napomena: {termin['napomena']}")

    if termin.get('dodatne_osobe'):
        desc_lines.append(f"Dodatne osobe: {', '.join(termin['dodatne_osobe'])}")

    ev = {
        'summary': f"{tip['label']}: {termin['predmet']} ({termin.get('grupa', 'Svi')})",
        # 'location' je uklonjen jer su sale već u attendees kao resursi
        'description': "\n".join(desc_lines),
        'colorId': tip['color'],
        'start': {'dateTime': f"{termin['datum']}T{termin['vrijeme_start']}:00", 'timeZone': 'Europe/Sarajevo'},
        'end': {'dateTime': f"{termin['datum']}T{termin['vrijeme_kraj']}:00", 'timeZone': 'Europe/Sarajevo'},
        'attendees': attendees,
        'reminders': {
            'useDefault': False,
            'overrides': [
                {'method': 'email', 'minutes': 24 * 60}, # Email dan prije
                {'method': 'popup', 'minutes': 24 * 60}, # Popup dan prije
                {'method': 'email', 'minutes': 60},      # Email sat prije
                {'method': 'popup', 'minutes': 60},      # Popup sat prije
                {'method': 'popup', 'minutes': 15},      # Popup 15 min prije
            ],
        },
    }
    if termin.get('ponavljanje'):
        until = termin['ponavljanje']['datum_kraj'].replace('-', '') + "T235959Z"
        ev['recurrence'] = [f"RRULE:FREQ={termin['ponavljanje']['frekvencija']};UNTIL={until}"]
    return ev

def sync_category(args):
    logger = setup_logging(args.calendar)

    # Učitavanje CSV podataka
    persons = load_csv_to_dict(FILE_PERSONS, 'firstName_lastName')

    # Za delete mode nam ne trebaju rooms/types ni events.json nužno, ali učitavamo persons i calendars
    with open(FILE_CALENDARS, mode='r', encoding='utf-8') as f:
        reader = csv.DictReader(f, quotechar='"')
        cal_rows = list(reader)
        fieldnames = reader.fieldnames

    if args.delete_calendar:
        if args.calendar not in fieldnames:
            logger.info(f"Kolona '{args.calendar}' ne postoji u CSV-u. Nema šta za brisanje.")
            return

        logger.info(f"--- POČETAK BRISANJA KALENDARA: {args.calendar} ---")

        updated_count = 0
        for row in cal_rows:
            cal_id = row.get(args.calendar, '').strip()
            if not cal_id: continue

            user_google_id = row['google_id']
            logger.info(f"Brisanje kalendara za: {user_google_id} (ID: {cal_id})")

            if args.dry_run:
                continue

            try:
                creds = service_account.Credentials.from_service_account_file(
                    SERVICE_ACCOUNT_FILE, scopes=SCOPES, subject=user_google_id)
                service = build('calendar', 'v3', credentials=creds)

                service.calendars().delete(calendarId=cal_id).execute()
                # row[args.calendar] = '' -> Ne samo prazniti, nego ćemo ukloniti kolonu skroz kasnije
                updated_count += 1
                logger.info("   Uspješno obrisan.")
            except Exception as e:
                logger.error(f"   Greška prilikom brisanja: {e}")

        if not args.dry_run:
            # Uklanjanje kolone iz zaglavlja i redova
            if args.calendar in fieldnames:
                fieldnames.remove(args.calendar)

            for row in cal_rows:
                if args.calendar in row:
                    del row[args.calendar]

            with open(FILE_CALENDARS, mode='w', encoding='utf-8', newline='') as f:
                writer = csv.DictWriter(f, fieldnames=fieldnames, quotechar='"', quoting=csv.QUOTE_MINIMAL)
                writer.writeheader()
                writer.writerows(cal_rows)
            logger.info(f"Ažuriran {FILE_CALENDARS}. Kolona '{args.calendar}' potpuno uklonjena.")

        return # Kraj za delete mode
    # --- Nastavak standardne sync logike ---
    rooms = {row['room']: row['google_id'] for row in csv.DictReader(open(FILE_ROOMS, encoding='utf-8'), quotechar='"') if row.get('room') and not row['room'].startswith('//')}
    types = {row['mark']: row for row in csv.DictReader(open(FILE_TYPES, encoding='utf-8'), quotechar='"')}

    with open(FILE_CALENDARS, mode='r', encoding='utf-8') as f:
        reader = csv.DictReader(f, quotechar='"')
        cal_rows = list(reader)
        fieldnames = reader.fieldnames

    if args.calendar not in fieldnames:
        fieldnames.append(args.calendar)

    json_path = os.path.join(JSON_DIR, args.events)
    with open(json_path, 'r', encoding='utf-8') as f:
        events_data = json.load(f)

    # Mapa email -> Ime za lookup po Google ID-u
    email_to_name = {v['google_id']: k for k, v in persons.items()}

    grouped = {}
    for t in events_data:
        raw_osoba = t['osoba'].strip()
        # Pokušaj naći po imenu
        if raw_osoba in persons:
            key = raw_osoba
        # Pokušaj naći po emailu
        elif raw_osoba in email_to_name:
            key = email_to_name[raw_osoba]
        else:
            logger.warning(f"Preskačem događaj: Nepoznata osoba '{raw_osoba}' (nije nađena u person.csv ni po imenu ni po ID-u)")
            continue

        grouped.setdefault(key, []).append(t)

    # Indeksiramo postojeće unose u person_calendars.csv radi bržeg pristupa
    cal_map = {row['google_id']: row for row in cal_rows}

    for ime_prezime, lista_termina in grouped.items():
        # ime_prezime je sigurno u persons jer smo gore filtrirali
        user_google_id = persons[ime_prezime]['google_id']

        # Ako osoba ne postoji u person_calendars.csv, dodajemo je
        if user_google_id not in cal_map:
            new_row = {'google_id': user_google_id}
            cal_rows.append(new_row)
            cal_map[user_google_id] = new_row

        row = cal_map[user_google_id]

        logger.info(f"Sync: {ime_prezime}")
        if args.dry_run:
            logger.info(f"   [DRY-RUN] Pronađeno {len(lista_termina)} događaja za obradu:")
            for t in lista_termina:
                # Simuliramo transformaciju da provjerimo logiku
                try:
                    ev = transform_event(t, types, rooms, persons)
                    logger.info(f"      - {ev['summary']} | {ev['start']['dateTime']} -> {ev['end']['dateTime']} | Sale: {ev['location']} | Polaznika: {len(ev.get('attendees', []))}")
                except Exception as e:
                    logger.error(f"      [GREŠKA U PARSIRANJU] {t.get('predmet', 'Nepoznat predmet')}: {e}")
            continue

        try:
            creds = service_account.Credentials.from_service_account_file(
                SERVICE_ACCOUNT_FILE, scopes=SCOPES, subject=user_google_id)
            service = build('calendar', 'v3', credentials=creds)

            target_id = row.get(args.calendar, '').strip()
            if not target_id:
                cal_name = args.calendar
                new_cal = service.calendars().insert(body={'summary': cal_name, 'timeZone': 'Europe/Sarajevo'}).execute()
                target_id = new_cal['id']
                row[args.calendar] = target_id

            # 1. Brisanje postojećih događaja
            # clear() radi samo za primarne kalendare, pa ručno brišemo sve evente
            all_events_to_delete = []
            page_token = None
            while True:
                events_res = service.events().list(calendarId=target_id, pageToken=page_token).execute()
                all_events_to_delete.extend(events_res.get('items', []))
                page_token = events_res.get('nextPageToken')
                if not page_token: break

            if all_events_to_delete:
                logger.info(f"   Brisanje {len(all_events_to_delete)} starih događaja...")
                for i in range(0, len(all_events_to_delete), 50):
                    chunk = all_events_to_delete[i:i+50]
                    batch_del = service.new_batch_http_request(callback=batch_callback)
                    for ev in chunk:
                        batch_del.add(service.events().delete(calendarId=target_id, eventId=ev['id']))
                    batch_del.execute()
            else:
                logger.info("   Nema starih događaja za brisanje.")

            # 2. Batch Insert (u paketima po 50)
            # lista_termina je već dostupna iz outer loop-a
            for i in range(0, len(lista_termina), 50):
                chunk = lista_termina[i:i+50]
                batch = service.new_batch_http_request(callback=batch_callback)

                for t in chunk:
                    body = transform_event(t, types, rooms, persons)
                    batch.add(service.events().insert(calendarId=target_id, body=body))

                batch.execute()

            logger.info(f"   Sinhronizovano: {len(lista_termina)} dogadjaja preko Batch API-ja.")

        except Exception as e:
            logger.error(f"   Greska za {user_google_id}: {e}")

    if not args.dry_run:
        with open(FILE_CALENDARS, mode='w', encoding='utf-8', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames, quotechar='"', quoting=csv.QUOTE_MINIMAL)
            writer.writeheader()
            writer.writerows(cal_rows)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('--calendar', required=False, help="Naziv kalendara (kolona u CSV-u).")
    parser.add_argument('--events', required=False, help="JSON fajl sa događajima.")
    parser.add_argument('--dry-run', action='store_true')
    parser.add_argument('--delete-calendar', action='store_true', help="Trajno briše navedeni kalendar za sve korisnike.")
    parser.add_argument('--list-calendars', action='store_true', help="Izlistava sve aktivne kalendare u CSV fajlu.")
    parser.add_argument('--verbose', action='store_true', help="Prikazuje detaljne informacije (npr. listu korisnika uz --list-calendars).")
    parser.add_argument('--init', action='store_true', help="Inicijalizuje strukturu direktorija i prazne CSV fajlove.")
    args = parser.parse_args()

    # INIT COMMAND
    if args.init:
        print("--- Inicijalizacija GWS Sync Projekta ---")

        # 1. Kreiranje direktorija
        dirs_to_create = [CSV_DIR, LOG_DIR, AUTH_DIR, JSON_DIR]
        for d in dirs_to_create:
            if not os.path.exists(d):
                os.makedirs(d)
                print(f" [OK] Kreiran direktorij: {d}/")
            else:
                print(f" [SKIP] Direktorij već postoji: {d}/")

        # 2. Kreiranje CSV fajlova
        files_def = {
            FILE_PERSONS: ['firstName_lastName', 'google_id'],
            FILE_ROOMS: ['room', 'google_id'],
            FILE_TYPES: ['mark', 'title', 'color', 'label'],
            FILE_CALENDARS: ['google_id']
        }

        for fpath, headers in files_def.items():
            if not os.path.exists(fpath):
                try:
                    with open(fpath, mode='w', encoding='utf-8', newline='') as f:
                        writer = csv.writer(f, quotechar='"', quoting=csv.QUOTE_MINIMAL)
                        writer.writerow(headers)
                    print(f" [OK] Kreiran fajl: {fpath}")
                except Exception as e:
                    print(f" [ERROR] Greška pri kreiranju {fpath}: {e}")
            else:
                print(f" [SKIP] Fajl već postoji: {fpath}")

        print("\nZavršeno. Molimo kopirajte vaš 'service_account.json' u 'auth/' direktorij.")
        sys.exit(0)

    # LIST COMMAND
    if args.list_calendars:
        if not os.path.exists(FILE_CALENDARS):
            print(f"Fajl {FILE_CALENDARS} ne postoji.")
            sys.exit(0)

        with open(FILE_CALENDARS, mode='r', encoding='utf-8') as f:
            reader = csv.DictReader(f, quotechar='"')
            fieldnames = reader.fieldnames
            rows = list(reader)

        # Ako je naveden specifičan kalendar, filtriraj samo njega
        if args.calendar:
            if args.calendar not in fieldnames:
                print(f"Kalendar '{args.calendar}' ne postoji u sistemu.")
                sys.exit(1)
            target_calendars = [args.calendar]
            show_details = True # Ako traži specifičan, uvijek prikaži detalje
        else:
            target_calendars = [f for f in fieldnames if f != 'google_id']
            show_details = args.verbose

        if not target_calendars:
            print("Nema definisanih kalendara.")
        else:
            print(f"Pronađeno {len(target_calendars)} kalendara:")

            # Učitavamo i imena ljudi radi ljepšeg ispisa
            persons = {}
            if show_details:
                try:
                    persons = load_csv_to_dict(FILE_PERSONS, 'google_id') # Učitaj mapu po Google ID-u
                    # persons je sad: {'email': {firstName_lastName: '...', ...}}
                except:
                    pass # Ako faila person.csv, prikazaćemo samo emailove

            for cal in target_calendars:
                active_users = [r for r in rows if r.get(cal, '').strip()]
                print(f"\nKalendar: '{cal}' (aktivno kod {len(active_users)} korisnika)")

                if show_details:
                    for i, u in enumerate(active_users, 1):
                        gid = u['google_id']
                        # Pokušaj naći ime
                        ime = "Nepoznato ime"
                        if gid in persons:
                            ime = persons[gid].get('firstName_lastName', ime)
                        elif persons: # Ako imamo persons dict ali nismo našli po ID, probaj naći po value['google_id'] (sporije)
                             found = next((v['firstName_lastName'] for k, v in persons.items() if v['google_id'] == gid), None)
                             if found: ime = found

                        print(f"   {i}. {ime} ({gid})")

        sys.exit(0)

    # VALIDACIJE ZA OSTALE MODE-ove
    if not args.calendar:
        parser.error("Argument --calendar je obavezan (osim za --list-calendars bez filtera).")

    if ',' in args.calendar:
        logging.error("GRESKA: Naziv kalendara ne smije sadržavati zarez (',') jer to narušava CSV format.")
        sys.exit(1)

    # Ako nije delete mode, events je obavezan
    if not args.delete_calendar and not args.events:
        parser.error("Argument --events je obavezan osim ako se koristi --delete-calendar")

    sync_category(args)
