# RAS 2.0 - Specifikacija Jezika

RAS 2.0 (Raspored Alokacija Resursa) je moderna evolucija DSL-a za definisanje akademskih rasporeda. Dizajniran je da eliminiše redundansu, poveća čitljivost i omogući strožiju validaciju podataka.

## Ključne Promjene u odnosu na v1

1.  **Ukidanje Prefiksa:** Nema više `pMatematika` vs `vMatematika`. Postoji samo `Matematika`, a tip nastave (P, V) je atribut dodjele.
2.  **Eksplicitne Definicije:** Svi entiteti (nastavnici, predmeti, sale) se moraju definisati prije upotrebe.
3.  **Atributi i Metapodaci:** Mogućnost definisanja dodatnih informacija (npr. kapacitet sale, email nastavnika).
4.  **Hijerarhija:** Prirodna podrška za odsjeke i grupe kroz blokovsku strukturu.

---

## 1. Definicije Entiteta

RAS 2.0 koristi blokovsku sintaksu `{ ... }` za definisanje svojstava entiteta.

### Predmeti
Predmet se definiše jedinstvenim imenom. Unutar bloka se definišu dozvoljeni tipovi nastave.

```ras
predmet InzenjerskaFizika {
    naziv: "Inženjerska Fizika 1";
    tipovi: P, V, L; // Predavanje, Vježbe, Lab
    semestar: 1;
}

predmet RPR {
    naziv: "Razvoj Softverskih Rješenja";
    tipovi: P, V, T;
}
```

### Nastavnici
Moguće je dodati metapodatke poput titule ili emaila.

```ras
nastavnik VedranLjubovic {
    email: "vljubovic@etf.unsa.ba";
    titula: "Vanr. Prof.";
}
```

### Prostorije
Definisanje kapaciteta i tipa sale (Amfiteatar, Lab...).

```ras
prostorija 0-01 {
    kapacitet: 150;
    tip: Amfiteatar;
}

prostorija 0-02 {
    kapacitet: 60;
    tip: Ucionica;
}
```

### Organizacija (Odsjeci i Grupe)
Hijerarhijska definicija grupa.

```ras
odsjek RI {
    grupa RI1 {
        podgrupa RI1-1;
        podgrupa RI1-2;
    }
    grupa RI2;
}
```

---

## 2. Definicija Vremena

Zadržavamo koncept slotova radi kompatibilnosti, ali uvodimo i mogućnost "pravog" vremena.

```ras
// Globalna konfiguracija
konfiguracija {
    pocetak: 08:00;
    trajanje_slota: 30min;
}

dan Ponedjeljak;
dan Utorak;

// Slotovi se mogu automatski generisati ili eksplicitno imenovati
termin PO1 = Ponedjeljak @ 08:00;
termin PO2 = Ponedjeljak @ 09:00;
```

---

## 3. Raspored (Assignments)

Ovo je srce jezika. Sintaksa je pročišćena da bude što čitljivija.

**Sintaksa:**
`{Nastavnik} drzi {Predmet} ({Tip}) za {Grupe} u {Soba} : {Termini}`

### Primjeri

**Osnovni zapis:**
```ras
VedranLjubovic drzi RPR (P) 
    za RI2 
    u 0-01 
    : PO1, PO2;
```

**Više nastavnika i grupa:**
```ras
Asistent1, Asistent2 drzi RPR (T) 
    za RI2-1, RI2-2 
    u 0-02 
    : UT3, UT4;
```

**Kompaktni zapis (u jednoj liniji):**
```ras
ProfesorX drzi Matematika (V) za G1 u S1 : SR1-SR3;
```

---

## 4. Poređenje: RAS v1 vs RAS 2.0

| Koncept | RAS v1 (Legacy) | RAS 2.0 (Modern) |
| :--- | :--- | :--- |
| **Predmet** | `pMatematika`, `vMatematika` | `Matematika (P)`, `Matematika (V)` |
| **Definicija** | `pMatematika je predmet.` | `predmet Matematika { ... }` |
| **Grupe** | `odjeljenju G1, G2` | `za G1, G2` |
| **Nastava** | `Prof predaje pPredmet ...` | `Prof drzi Predmet (P) ...` |
| **Atributi** | Nema podrške | Podržano (kapacitet, email...) |

## 5. EBNF Skica

```ebnf
program = { definition | assignment } ;

definition = subject_def | teacher_def | room_def | org_def ;

subject_def = "predmet" ID "{" properties "}" ;
teacher_def = "nastavnik" ID "{" properties "}" ;

assignment = teacher_list "drzi" ID "(" type_id ")" 
             "za" group_list 
             "u" room_list 
             ":" slot_list ";" ;

teacher_list = ID { "," ID } ;
group_list   = ID { "," ID } ;
type_id      = "P" | "V" | "L" | "T" ;
```
