# RAS - Jezik za Opis Rasporeda

Ovaj dokument opisuje sintaksu domenski specifičnog jezika (DSL) koji koristi `tt2cal` kompajler.

## Struktura Jezika

Fajl rasporeda se sastoji od niza iskaza. Svaki iskaz mora završiti tačkom (`.`).
Komentari se pišu sa `//` (jednolinijski) ili `/* ... */` (višelinijski).

---

### 0. Konfiguracija Semestra (Opcionalno)

Definiše naziv, trajanje i nenastavne dane semestra.
Naziv semestra se koristi kao naziv kalendara (CamelCase → razmak-odvojeno).

**Sintaksa:**
```text
{Naziv} je semestar.
{Naziv} pocinje {DD.MM.YYYY}.
{Naziv} zavrsava {DD.MM.YYYY}.
{Naziv} traje {N} sedmica.
{Naziv} ima nenastavne dane {DD.MM.YYYY}, {DD.MM.YYYY}.
```

**Primjer:**
```text
ZimskiSemestar2025 je semestar.
ZimskiSemestar2025 pocinje 24.02.2025.
ZimskiSemestar2025 traje 15 sedmica.
ZimskiSemestar2025 ima nenastavne dane 01.05.2025, 02.05.2025.
```

> Umjesto `zavrsava` može se koristiti `traje N sedmica` — kompajler će izračunati kraj.

---

### 1. Definicije Vremena

**Definicija Dana:**
```text
Ponedjeljak je dan broj 1.
Utorak je dan broj 2.
```

**Definicija Termina (Slotova):**
```text
PO1 je termin broj 1 dana Ponedjeljak.
PO1A je termin broj 2 dana Ponedjeljak.
PO2 je termin broj 3 dana Ponedjeljak.
```

Broj termina odgovara rednom broju `slot_duration` intervala od `base_time`.
Npr. ako je `base_time=08:00` i `duration=30`, termin broj 3 počinje u 09:00.

---

### 2. Definicije Entiteta

**Nastavnik:**
```text
ElmedinSelmanovic je nastavnik.
```

**Predmet:**
```text
pUvodUProgramiranje je predmet.
vUvodUProgramiranje je predmet.
```
> Prefiks u imenu određuje tip nastave: `p`=Predavanje, `v`=Vježbe, `l`=Lab, `t`=Tutorijal.
> Isti predmet može imati više definicija za različite tipove.

**Prostorija:**
```text
A1 je prostorija.
0-01 je prostorija.
```

**Odjeljenje (studijska grupa):**
```text
RI1 je odjeljenje.
```

**Podgrupa:**
```text
RI1-1a je grupa odjeljenja RI1.
```

---

### 3. Definicije Tipova Nastave (Opcionalno)

Omogućava override podrazumijevanih tipova nastave iz `tt2cal.py`.

**Sintaksa:**
```text
{Kod} je tip nastave {Naziv} prioriteta {N}.
```

**Primjer:**
```text
P je tip nastave Predavanje prioriteta 0.
V je tip nastave Vjezbe prioriteta 1.
L je tip nastave LaboratorijskeVjezbe prioriteta 2.
T je tip nastave Tutorijal prioriteta 3.
```

> Naziv se piše u CamelCase formatu (LaboratorijskeVjezbe → "Laboratorijske Vjezbe").
> Prioritet određuje redoslijed prikaza u generatorima (manji = važniji).
> Ako tipovi nisu definirani u .ras fajlu, koriste se podrazumijevani iz `tt2cal.py`.

---

### 4. Dodjela Nastave

Ovo je osnovna naredba kojom se definira ko, šta, gdje i kada predaje.

**Sintaksa:**
```text
{Nastavnik} [i {Nastavnik2}...] predaje {Predmet}
    [odjeljenju {Grupa}...]
    [u prostoriji {Prostorija}...]
    [N puta sedmicno]
    [svake N sedmice]
    tacno u terminu {Slot1} {Slot2}...
```

**Primjeri:**

```text
// Osnovni zapis
VedranLjubovic predaje pRazvojSoftvera odjeljenju RI u prostoriji 0-01 tacno u terminu PO1 PO1A.

// Više nastavnika
VedranLjubovic i Asistent1 predaje vRazvojSoftvera odjeljenju RI1-1 u prostoriji 0-02 tacno u terminu UT3 UT4.

// Sa frekvencijom i intervalom
ProfesorX predaje pMatematika1 odjeljenju AE 3 puta sedmicno svake 2 sedmice tacno u terminu SR1 SR2 SR3.
```

**Prefiksi predmeta:**
| Prefiks | Tip | Primjer |
| :--- | :--- | :--- |
| `p` | Predavanje | `pMatematika1` |
| `v` | Vježbe | `vMatematika1` |
| `l` | Lab vježbe | `lProgramiranje` |
| `t` | Tutorijal | `tProgramiranje` |

---

### 5. Importovanje Fajlova (`UVEZI`)

Omogućava modularizaciju rasporeda u više fajlova. Rekurzivno razrješavanje.

```text
UVEZI: definicije/nastavnici.ras
UVEZI: definicije/vrijeme.ras
```

> Putanje su relativne u odnosu na fajl koji sadrži `UVEZI` direktivu.
> Kružni importi se detektuju i preskaču sa upozorenjem.

---

### 6. Automatsko Spajanje (Merging)

Kompajler automatski spaja događaje koji se preklapaju (isto vrijeme, isti nastavnik).

| Element | Pravilo spajanja |
| :--- | :--- |
| **Prostorije** | Unija (A1, A2) |
| **Predmeti** | Spajanje stringova (Matematika / Fizika) |
| **Grupe** | Spajanje listi |

**Prikaz grupa:**
- Zarez (`,`) — grupe definisane u istoj liniji (zajednička nastava)
- Plus (`+`) — grupe spojene iz različitih definicija (merge)

```text
// Ulaz
ProfX predaje pA odjeljenju G1, G2 tacno u terminu PO1.
ProfX predaje pA odjeljenju G3 tacno u terminu PO1.

// Rezultat: "G1, G2 + G3"
```

---

## EBNF Definicija

```ebnf
schedule       = { statement } ;

statement      = definition | assignment | import_dir ;

definition     = day_def | slot_def | teacher_def | subject_def
               | room_def | group_def | semester_def | type_def ;

day_def        = ID "je dan broj" NUMBER "." ;
slot_def       = ID "je termin broj" NUMBER "dana" ID "." ;
teacher_def    = ID "je nastavnik" "." ;
subject_def    = ID "je predmet" "." ;
room_def       = ID "je prostorija" "." ;
group_def      = ID ("je odjeljenje" | "je grupa odjeljenja" ID) "." ;
semester_def   = ID "je semestar" "." ;
semester_attr  = ID ("pocinje" DATE | "zavrsava" DATE
               | "traje" NUMBER ("sedmica" | "sedmice")
               | "ima nenastavne" ("dane" | "dana") DATE { "," DATE }) "." ;
type_def       = ID "je tip nastave" ID "prioriteta" NUMBER "." ;

assignment     = teacher_list "predaje" ID
                 { group_part } { room_part }
                 [ freq_part ] [ interval_part ]
                 slot_part "." ;

teacher_list   = ID { "i" ID } ;
group_part     = "odjeljenju" ID { ["," ] ID } ;
room_part      = ("u prostoriji" | "prostoriji") ID ;
freq_part      = NUMBER "puta sedmicno" ;
interval_part  = "svake" NUMBER "sedmice" ;
slot_part      = "tacno u terminu" { ID } ;

import_dir     = "UVEZI:" PATH ;
```
