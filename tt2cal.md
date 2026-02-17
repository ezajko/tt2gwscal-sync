# tt2cal - Kompajler Rasporeda

**tt2cal** (Text-to-Calendar) je CLI alat koji pretvara tekstualne definicije rasporeda (pisane u RAS jeziku) u JSON, Markdown, HTML i grid formate.

## Instalacija i Pokretanje

Alat je napisan u Python-u i ne zahtijeva dodatne biblioteke (samo standardna biblioteka).

```bash
python tt2cal.py -i raspored.ras [opcije]
```

## Argumenti Komandne Linije

### Ulaz i Izlaz
| Argument | Opis |
| :--- | :--- |
| `-i`, `--input` | **Obavezno**. Putanja do ulaznog `.ras` fajla. Podržava `UVEZI:` direktive za modularizaciju. |
| `-j`, `--json` | Putanja do izlaznog JSON fajla. |
| `-m`, `--md` | Putanja za Markdown izvještaj. |
| `-w`, `--html` | Direktorij za HTML izvještaje (po predmetima, nastavnicima, grupama, prostorijama). |
| `-g`, `--grid` | Direktorij za tradicionalni grid (tabelarni) HTML izvještaj. |
| `-e`, `--export` | Direktorij za eksport refaktorisanog RAS koda (uključujući definicije i raspored). |
| `-s`, `--stdout` | Ispisuje JSON direktno na standardni izlaz. Korisno za pipe-ovanje. |
| `-a`, `--ast` | Ispisuje AST strukturu na stdout (za debug). Moze se pipe-ati (`\| head`, `\| grep`). |

> **Napomena:** Morate specificirati barem jedan izlazni format (`-j`, `-m`, `-w`, `-g`, `-e`, `-s` ili `-a`).

### Filtriranje Sadržaja
Regex-bazirano filtriranje za generisanje podskupa rasporeda.

| Argument | Opis | Primjer |
| :--- | :--- | :--- |
| `--teacher` | Filtriraj po nastavniku. | `--teacher "Vahid"` |
| `--subject` | Filtriraj po predmetu. | `--subject "Matematika"` |
| `--room` | Filtriraj po prostoriji. | `--room "A4"` |
| `--group` | Filtriraj po grupi. | `--group "RI1"` |

### Konfiguracija Semestra
| Argument | Opis | Default |
| :--- | :--- | :--- |
| `--semestar-start` | Početak semestra (YYYY-MM-DD ili DD.MM.YYYY). | Iz .ras fajla ili 01.10.tekuća_godina |
| `--semestar-end` | Kraj semestra (YYYY-MM-DD ili DD.MM.YYYY). | Iz .ras fajla ili izračunato iz trajanja |
| `--semestar-duration` | Trajanje u sedmicama. | `15` |
| `--semestar-title` | Naziv semestra (koristi se kao naziv kalendara). | Iz .ras fajla ili "Semestar YYYY" |

### Konfiguracija Vremena
| Argument | Opis | Default |
| :--- | :--- | :--- |
| `--base-time` | Vrijeme početka prvog termina (HH:MM). | `08:00` |
| `--duration` | Trajanje jednog slota u minutama. | `30` |
| `--slots-per-index` | Broj slotova po indeksu (npr. od PO1 do PO2). | `2` |

## Hijerarhija Konfiguracije

Konfiguracija se razrješava po prioritetu (veći broj = jači):

1. **LECTURE_TYPES konstanta** u `tt2cal.py` (fallback)
2. **CLI argumenti** (`--semestar-start`, `--base-time`, ...)
3. **Definicije iz .ras fajla** (najjači prioritet)

Tipovi nastave koji su eksplicitno definirani u `.ras` fajlu imaju prednost nad defaultima iz `tt2cal.py`.

## Tipovi Nastave

Podrazumijevani tipovi (definirani u `tt2cal.py`):

| Kod | Naziv | Prioritet |
| :--- | :--- | :--- |
| `P` | Predavanje | 0 |
| `V` | Vježbe | 1 |
| `L` | Laboratorijske vježbe | 2 |
| `T` | Tutorijal | 3 |
| `N` | Nepoznato | 9 |

Tipovi se mogu override-ovati u `.ras` fajlu (vidi `ras.md`).

## Primjeri Upotrebe

### 1. Kompletni run (svi formati)
```bash
python tt2cal.py -i raspored.ras -j podaci.json -m izvjestaj.md -w html/ -g grid/ -e export/
```

### 2. Filtriranje za jednog profesora
```bash
python tt2cal.py -i raspored.ras --teacher "Elmedin" -s
```

### 3. AST inspekcija sa filterom
```bash
python tt2cal.py -i raspored.ras -a --teacher "Raca" | grep "ASSIGNMENTS" -A20
```

### 4. Prilagođeno vrijeme (školski čas 45min)
```bash
python tt2cal.py -i skola.ras --duration 45 --slots-per-index 1 -w html/
```

### 5. Eksplicitni datumi semestra
```bash
python tt2cal.py -i raspored.ras --semestar-start 2025-02-24 --semestar-duration 15 -j izlaz.json
```

## Formati Izlaza

### JSON
Lista događaja sa spojenim informacijama. Grupe su lista listi `[["G1", "G2"], ["G3"]]` (zarez = zajednička nastava, plus = merge). Sadrži i meta-podatke (naziv kalendara, datumi, nenastavni dani).

### HTML (-w)
Četiri fajla sa navigacijom između pogleda:
1. `{semestar}_predmeti.html` — po predmetima (sortirano po tipu P, V, L, T)
2. `{semestar}_nastavnici.html` — po nastavnicima
3. `{semestar}_grupe.html` — po grupama (sa nasljeđivanjem od roditelja)
4. `{semestar}_prostorije.html` — po prostorijama

### Grid HTML (-g)
Tradicionalni tabelarni prikaz (dani × termini) sa sekcijama za svakog nastavnika. Optimiziran za A4 landscape print sa page-break-ovima.

### Markdown
Jednostavan tekstualni izvještaj za brzi pregled.

### Eksport (-e)
Refaktorisani RAS kod u strukturiranom direktoriju:
```
export/
  raspored.ras              # glavni fajl sa UVEZI direktivama
  definicije/
    semestar.ras             # konfiguracija semestra
    vrijeme.ras              # dani i termini
    tipovi.ras               # tipovi nastave (merged)
    nastavnici.ras           # definicije nastavnika
    predmeti.ras             # definicije predmeta
    prostorije.ras           # definicije prostorija
    grupe.ras                # odjeljenja i podgrupe
  nevalidno.ras              # nevalidni unosi (ako postoje)
```

## Pipeline

```
.ras fajl → Lexer → Parser → AST → [Filteri] → Compiler → IR → Generatori
                                          ↑                          ↓
                                    tt2cal.py              JSON / MD / HTML / Grid
                                  (konfiguracija)
```
