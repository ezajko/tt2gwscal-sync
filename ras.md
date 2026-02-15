# RAS - Jezik za Opis Rasporeda

Ovaj dokument opisuje sintaksu i strukturu domenski specifičnog jezika (DSL) koji koristi `tt2cal` kompajler.

## Struktura Jezika

Fajl rasporeda se sastoji od niza naredbi koje se izvršavaju sekvencijalno. Svaka naredba mora završiti tačkom (`.`).

### 0. Konfiguracija Semestra (Opcionalno)
Definiše početak i kraj semestra za generisanje datuma u kalendaru. Ako nije navedeno, koriste se default vrijednosti ili argumenti komandne linije.

**Jednostavna Sintaksa:**
`Semestar pocinje {DatumPocetka} i zavrsava {DatumKraja}.`

**Napredna Sintaksa (preporučeno):**
Omogućava definisanje imena semestra, akademske godine i praznika (nenastavnih dana).

1. `Semestar je {Ime} [kao {Tip}] [u akademskoj {Godina} godini].`
2. `{Ime} pocinje {DatumPocetka} i zavrsava {DatumKraja}.`
3. `{Ime} ima nenastavne dane {Datum1}, {Datum2}...`

**Primjer:**
```text
Semestar je Zimski kao redovni u akademskoj 2025/2026 godini.
Zimski pocinje 24.02.2025 i zavrsava 15.06.2025.
Zimski ima nenastavne dane 01.05.2025, 02.05.2025.
```

### 1. Definicije Vremena
Definišu osnovni vremenski okvir rasporeda.

**Definicija Dana:**
`{ImeDana} je dan broj {Broj}.`
```text
Ponedjeljak je dan broj 1.
```

**Definicija Termina (Slotova):**
`{KodTermina} je termin broj {Indeks} dana {ImeDana}.`
```text
PO1 je termin broj 1 dana Ponedjeljak.
```

### 2. Definicije Entiteta (Opcionalno)
Služe za eksplicitnu deklaraciju nastavnika, predmeta, prostorija i grupa.

**Definicija Nastavnika:**
`{ImeNastavnika} je nastavnik.`
```text
ElmedinSelmanovic je nastavnik.
```

**Definicija Predmeta:**
`{ImePredmeta} je predmet.`
```text
pUvodUProgramiranje je predmet.
```
> **Napomena:** Prefiks u imenu predmeta (p, v, l, t) određuje tip nastave za tu definiciju.

**Definicija Prostorije:**
`{ImeProstorije} je prostorija.`
```text
A1 je prostorija.
```

**Definicija Odjeljenja (Studijske Grupe):**
`{Ime} je odjeljenje.`
```text
RI1 je odjeljenje.
```

**Definicija Podgrupe:**
`{Ime} je grupa odjeljenja {Odjeljenje}.`
```text
RI1-1a je grupa odjeljenja RI1.
```

### 3. Dodjela Nastave
Ovo je osnovna naredba kojom se definiše ko, šta, gdje i kada predaje.

**Sintaksa:**
`{Nastavnik} [i {Nastavnik2}...] predaje {Predmet} [odjeljenju {Grupa}...] [u prostoriji {Prostorija}...] [3 puta sedmicno] [svake 2 sedmice] [tacno u terminu {Slot1} {Slot2}...].`

*   **Nastavnik**: Ime nastavnika. Može se navesti više nastavnika razdvojenih sa `i`.
*   **Predmet**: Naziv predmeta. Prefiksi određuju tip nastave:
    *   `p`: Predavanje
    *   `v`: Vježbe
    *   `l`: Laboratorijske vježbe
    *   `t`: Tutorijal
*   **Grupa** (Opcionalno): Oznaka grupe. Može se navesti više grupa (npr. `odjeljenju G1, G2`).
*   **Prostorija** (Opcionalno): Lista prostorija.
*   **Modifikatori** (Opcionalno):
    *   `{N} puta sedmicno`: Definiše očekivanu učestalost (validacija).
    *   `svake {N} sedmice`: Definiše interval ponavljanja.
*   **Termini**: Lista kodova termina.

**Primjer:**
```text
VedranLjubovic predaje pRazvojSoftvera odjeljenju RI u prostoriji 0-01 3 puta sedmicno tacno u terminu PO1 PO1A.
```

### 4. Importovanje Fajlova (`UVEZI`)
Omogućava modularizaciju.
`UVEZI: {PutanjaDoFajla}`

### 5. Napredno: Automatsko Spajanje (Merging)
Kompajler automatski spaja događaje koji se preklapaju (isto vrijeme, isti nastavnik).

**Pravilo Spajanja:**
*   **Prostorije**: Unija (A1, A2).
*   **Predmeti**: Spajanje stringova (Matematika / Fizika).
*   **Grupe**: Spajanje listi (`G1, G2` + `G3`).

**Prikaz Grupa:**
*   Zarez (`,`) označava grupe definisane u istoj liniji (zajednička nastava).
*   Plus (`+`) označava grupe spojene iz različitih definicija (merge).

```text
ProfX predaje A odjeljenju G1, G2 ...
ProfX predaje A odjeljenju G3 ...
// Rezultat: "G1, G2 + G3"
```

---

## EBNF Definicija

```ebnf
schedule     = { statement } ;

statement    = definition | assignment | import_dir ;

definition   = day_def | slot_def | teacher_def | subject_def | room_def | group_def ;

day_def      = ID "je dan broj" NUMBER "." ;
slot_def     = ID "je termin broj" NUMBER "dana" ID "." ;
teacher_def  = ID "je nastavnik" "." ;
subject_def  = ID "je predmet" "." ;
room_def     = ID "je prostorija" "." ;
group_def    = ID ("je odjeljenje" | "je grupa odjeljenja" ID) "." ;

assignment   = teacher_list "predaje" ID {group_part} {room_part} [freq_part] [interval_part] {slot_part} "." ;

teacher_list = ID { "i" ID } ;
group_part   = "odjeljenju" ID { [","] ID } ;
room_part    = ("u prostoriji" | "prostoriji") ID ;
freq_part    = NUMBER "puta sedmicno" ;
interval_part = "svake" NUMBER "sedmice" ;
slot_part    = "tacno u terminu" { ID } ;

import_dir   = "UVEZI:" path_string ;
```
