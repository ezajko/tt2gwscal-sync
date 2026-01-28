# GWS Sync (Google Workspace Sync)

Ovaj alat služi za sinhronizaciju rasporeda nastave (ili drugih događaja) iz JSON formata u Google Kalendare korisnika, koristeći Google Workspace (Service Account) integraciju.

## 🚀 Instalacija i Priprema

1.  **Python Okruženje:**
    Potreban je Python 3. Preporučuje se korištenje virtualnog okruženja.
    ```bash
    # Kreiranje venv-a (ako već ne postoji)
    python3 -m venv venv
    
    # Aktivacija
    source venv/bin/activate
    
    # Instalacija zavisnosti
    pip install -r requirements.txt
    ```

2. **Autentifikacija (Service Account):**

   

   Ovaj alat zahtijeva Google Service Account sa "Domain-Wide Delegation" ovlaštenjima.



   **A. Google Cloud Console (Kreiranje naloga):**

   1.  Idite na [Google Cloud Console](https://console.cloud.google.com/).

   2.  Kreirajte novi projekat ili odaberite postojeći.

   3.  Idite na **APIs & Services > Library**, potražite "Google Calendar API" i omogućite ga (**Enable**).

   4.  Idite na **IAM & Admin > Service Accounts**.

   5.  Kliknite **Create Service Account**, dajte mu ime i kreirajte ga.

   6.  Kliknite na novokreirani email service account-a.

   7.  Idite na tab **Keys** > **Add Key** > **Create new key** > **JSON**.

   8.  Preuzeti fajl sačuvajte kao `auth/service_account.json` u projektu.

   9.  Idite na tab **Details**, kliknite na **Advanced settings** (ili "Show Domain-Wide Delegation") i kopirajte **Client ID** (dugi niz brojeva).



   **B. Google Workspace Admin Console (Delegacija):**

   1.  Idite na [admin.google.com](https://admin.google.com).

   2.  Idite na **Security > Access and data control > API controls**.

   3.  Na dnu sekcije kliknite na **Manage Domain Wide Delegation**.

   4.  Kliknite **Add new**.

   5.  U polje **Client ID** zalijepite ID koji ste kopirali u koraku A.9.

   6.  U polje **OAuth scopes** unesite (tačno ovako):

       `https://www.googleapis.com/auth/calendar`

   7.  Kliknite **Authorize**.



   *Napomena: Propagacija ovih prava može potrajati nekoliko minuta.*

## 📂 Struktura Podataka

Alat koristi CSV fajlove za mapiranje podataka i JSON fajl za definiciju događaja.

### CSV Direktorij (`csv/`)

*   **`person.csv`**: Mapiranje imena u email/Google ID.
    *   Zaglavlja: `firstName_lastName`, `google_id`
    *   Primjer: `"Ime Prezime","email@domena.com"`
*   **`rooms.csv`**: Mapiranje oznaka sala u Google Resource emailove.
    *   Zaglavlja: `room`, `google_id`
*   **`lecture_type.csv`**: Definicije tipova nastave (boje, oznake).
    *   Zaglavlja: `mark`, `title`, `color`, `label`
*   **`person_calendars.csv`**: (Automatski se popunjava/ažurira) Čuva ID-eve kreiranih kalendara za svaku osobu.
    *   Zaglavlja: `google_id`, `<naziv_kalendara_1>`, `<naziv_kalendara_2>`, ...

### JSON Podaci (`data/`)

Ulazni fajl sa događajima treba biti u `data/` direktoriju (npr. `data/raspored.json`).

#### Schema za `events.json`

Fajl je niz (array) objekata, gdje svaki objekat predstavlja jedan termin.

| Polje | Tip | Obavezno | Opis |
| :--- | :--- | :--- | :--- |
| `osoba` | string | DA | Identifikator osobe. Može biti **Ime Prezime** (iz `firstName_lastName`) ili **Email** (iz `google_id`). **Ova osoba je vlasnik kalendara i događaja** (njima se događaj direktno upisuje, ne šalje se pozivnica). |
| `predmet` | string | DA | Naziv predmeta. |
| `tip` | string | DA | Kratka oznaka tipa (mora postojati u `lecture_type.csv`, npr. "P", "V"). |
| `grupa` | string | NE | Oznaka grupe (default: "Svi"). |
| `datum` | string | DA | Datum u formatu `YYYY-MM-DD`. |
| `vrijeme_start` | string | DA | Vrijeme početka `HH:MM`. |
| `vrijeme_kraj` | string | DA | Vrijeme kraja `HH:MM`. |
| `prostorije` | array | NE | Lista oznaka sala (npr. `["0-01", "1-01"]`). Oznake moraju biti u `rooms.csv`. |
| `dodatne_osobe`| array | NE | Lista emailova ili imena (iz `person.csv`) koje treba dodati kao goste. **Ovim osobama se šalje pozivnica za događaj.** |
| `ponavljanje` | object | NE | Definicija ponavljanja događaja. |

**Polje `dodatne_osobe`:**
Lista stringova koja definiše goste na događaju. Svaki element može biti:
*   **Direktna email adresa:** (npr. `"kolega@etf.unsa.ba"`)
*   **Ime i prezime:** (npr. `"Drugi Kolega"`) - U ovom slučaju, skripta traži to ime u fajlu `person.csv` i koristi pripadajući `google_id` (email).

**Objekat `ponavljanje`:**
*   `frekvencija`: (string) RRULE frekvencija, npr. `"WEEKLY"`, `"DAILY"`.
*   `datum_kraj`: (string) Datum do kada traje ponavljanje `YYYY-MM-DD`.

#### Primjer JSON-a

```json
[
  {
    "osoba": "Ime Prezime",
    "predmet": "Uvod u Programiranje",
    "tip": "P",
    "grupa": "Grupa 1",
    "datum": "2026-02-15",
    "vrijeme_start": "09:00",
    "vrijeme_kraj": "12:00",
    "prostorije": ["0-01"],
    "ponavljanje": {
      "frekvencija": "WEEKLY",
      "datum_kraj": "2026-06-01"
    }
  },
  {
    "osoba": "Ime Prezime",
    "predmet": "Sastanak Katedre",
    "tip": "S",
    "datum": "2026-02-20",
    "vrijeme_start": "13:00",
    "vrijeme_kraj": "14:00",
    "dodatne_osobe": ["kolega@etf.unsa.ba", "Drugi Kolega"]
  }
]
```

## 🛠 Korištenje

Za lakše pokretanje koristi se skripta `./gws` koja automatski aktivira virtualno okruženje.

Prije prve upotrebe, osigurajte da je skripta izvršna:
```bash
chmod +x gws
```

### Sintaksa
```bash
./gws --calendar <NAZIV_KALENDARA> --events <NAZIV_FAJLA_U_DATA> [--dry-run]
```

### Argumenti
*   `--calendar`: Naziv kolone u `person_calendars.csv`. **Ova vrijednost se koristi i kao naziv Google Kalendara koji će biti kreiran.** 
    *   Ako naziv sadrži razmake, obavezno ga stavite pod navodnike.
    *   **VAŽNO:** Naziv **ne smije sadržavati zarez (`,`)** jer se koristi kao ključ u CSV fajlu.
*   `--events`: Ime JSON fajla unutar `data/` direktorija (npr. `raspored.json`).
*   `--dry-run`: (Opcionalno) Ako je navedeno, skripta **neće** praviti izmjene na Google Kalendaru. Samo će ispisati šta bi uradila i kako je parsirala događaje.
*   `--init`: Kreira potrebnu strukturu direktorija i prazne CSV fajlove.
*   `--list-calendars`: Izlistava aktivne kalendare.
*   `--delete-calendar`: Briše kalendar.

### Primjer

Pretpostavimo da želimo sinhronizovati raspored za zimski semestar pod nazivom **"XYZ Time Table: 2025/2026 WS"**.

1. **Inicijalizacija (Prvo pokretanje):**
   Ako postavljate projekat na novu mašinu, ova komanda će kreirati potrebne foldere i prazne CSV fajlove sa zaglavljima.
   ```bash
   ./gws --init
   ```

2. **Testno pokretanje (Dry Run):**
   Provjera šta će biti urađeno bez stvarnih izmjena.
   ```bash
   ./gws --calendar "XYZ Time Table: 2025/2026 WS" --events raspored_zima.json --dry-run
   ```
   *Ispis će prikazati događaje koji bi bili kreirani.*

3. **Stvarna sinhronizacija:**
   Kreiranje kalendara i upisivanje događaja.
   ```bash
   ./gws --calendar "XYZ Time Table: 2025/2026 WS" --events raspored_zima.json
   ```
   *   Skripta učitava `data/raspored_zima.json`.
   *   Za svaku osobu pronalazi ili kreira kalendar sa nazivom **"XYZ Time Table: 2025/2026 WS"**.
   *   Briše sve stare događaje iz tog kalendara.
   *   Upisuje nove događaje iz JSON-a.

4. **Brisanje kalendara (Cleanup):**
   Trajno brisanje kalendara sa Google-a i uklanjanje kolone iz `person_calendars.csv`.
   ```bash
   ./gws --calendar "XYZ Time Table: 2025/2026 WS" --delete-calendar
   ```
   *   **Oprez:** Ova akcija je nepovratna. Argument `--events` nije potreban.

5. **Pregled kalendara:**
   Izlistava sve kalendare koji su trenutno evidentirani u sistemu.
   ```bash
   # Samo suma (broj korisnika)
   ./gws --list-calendars
   
   # Detaljan ispis svih korisnika po kalendarima
   ./gws --list-calendars --verbose

   # Detaljan ispis korisnika samo za određeni kalendar
   ./gws --list-calendars --calendar "XYZ Time Table: 2025/2026 WS"
   ```

## 📄 Licenca

Ovaj projekat je otvorenog koda i licenciran pod **GNU General Public License v2.0 or later (GPL-2.0+)**.
Pogledajte fajl `LICENSE` za više detalja.
