# tt2cal - Kompajler Rasporeda

**tt2cal** (Text-to-Calendar) je alat komandne linije (CLI) namijenjen za konverziju tekstualnih definicija školskih rasporeda (pisanih u RAS jeziku) u strukturirane formate kao što su JSON, Markdown i HTML.

## Instalacija i Pokretanje

Alat je napisan u Python-u i ne zahtijeva dodatne biblioteke izvan standardne biblioteke.

```bash
# Pokretanje alata
python tt2cal.py -i ulazni_fajl.txt [opcije]
```

## Argumenti Komandne Linije

### Ulaz i Izlaz
| Argument | Opis |
| :--- | :--- |
| `-i`, `--input` | **Obavezno**. Putanja do ulaznog `.txt` fajla sa definicijom rasporeda. Podržava `UVEZI:` direktive. |
| `-j`, `--json` | Putanja do izlaznog JSON fajla. Sadrži strukturirane podatke pogodne za mašinsku obradu. |
| `-m`, `--md` | Putanja za generisanje čitljivog Markdown izvještaja. |
| `-w`, `--html` | Putanja do direktorija u kojem će se generisati HTML izvještaji (po predmetima, nastavnicima, prostorijama). |
| `-e`, `--export` | Putanja do direktorija za eksport validiranog i refaktorisanog RAS koda (uključujući definicije i raspored). |
| `-s`, `--stdout` | Ispisuje generisani JSON direktno na standardni izlaz (stdout). Korisno za pipe-ovanje. |
| `-a`, `--ast` | Ispisuje internu AST (Abstract Syntax Tree) strukturu na stderr (za debugiranje). |

> **Napomena:** Morate specificirati barem jedan izlazni format (`-j`, `-m`, `-w`, `-e` ili `-s`).

### Filtriranje Sadržaja
Omogućava generisanje rasporeda samo za određene kriterije. Koristi regex (regularne izraze) za pretragu.

| Argument | Opis | Primjer |
| :--- | :--- | :--- |
| `--teacher` | Filtriraj po imenu nastavnika. | `--teacher "Vahid"` |
| `--subject` | Filtriraj po nazivu predmeta. | `--subject "Matematika"` |
| `--room` | Filtriraj po nazivu prostorije. | `--room "A4"` |
| `--group` | Filtriraj po oznaci grupe. | `--group "RI1"` |

### Konfiguracija Vremena
| Argument | Opis | Default |
| :--- | :--- | :--- |
| `--start` | Datum početka semestra (YYYY-MM-DD). | `2024-09-30` |
| `--end` | Datum kraja semestra (YYYY-MM-DD). | `2025-01-15` |
| `--base-time` | Vrijeme početka prvog termina (HH:MM). | `08:00` |
| `--duration` | Trajanje jednog osnovnog vremenskog slota u minutama. | `30` |
| `--slots-per-index` | Broj slotova po indeksnom koraku (npr. od PO1 do PO2). | `2` |

## Primjeri Upotrebe

### 1. Generisanje kompletnog izvještaja
```bash
python tt2cal.py -i raspored.txt -j podaci.json -m izvjestaj.md -w html_izvjestaj
```

### 2. Filtriranje za jednog profesora (JSON na ekran)
```bash
python tt2cal.py -i raspored.txt --teacher "Elmedin" -s
```

### 3. Prilagođeno vrijeme (Školski čas 45min)
```bash
python tt2cal.py -i skola.txt --duration 45 --slots-per-index 1 -w html_skola
```

## Formati Izlaza

### JSON
Sadrži listu događaja sa spojenim informacijama. Grupe su predstavljene kao lista listi `[['G1', 'G2'], ['G3']]` kako bi se očuvala razlika između grupa definisanih zajedno (zarez) i onih spojenih merge-om (plus).

### HTML
Generiše tri fajla:
1.  `raspored_predmeti.html`: Grupisano po predmetima, sortirano po tipu nastave (P, V, L, T).
2.  `raspored_nastavnici.html`: Prikaz po nastavnicima (sa spojenim terminima).
3.  `raspored_prostorije.html`: Prikaz zauzeća prostorija.

### Markdown
Jednostavan tekstualni prikaz, pogodan za brzi pregled.
