"""
lexer.py - Leksicka analiza RAS jezika

Pretvara sirovi tekst u niz tokena koristeci regularne izraze.
Tokeni se koriste kao ulaz za Parser.

Pravila su definisana kao lista (naziv, regex) parova.
Redoslijed pravila je bitan - duza pravila trebaju biti ispred kracih
(npr. 'je tip nastave' mora biti ispred 'je').
"""
import re


class Token:
    """Jedan token sa tipom, vrijednoscu i brojem linije."""
    def __init__(self, type, value, line):
        self.type = type
        self.value = value
        self.line = line

    def __repr__(self):
        return f"Token({self.type}, {self.value!r}, line={self.line})"


class Lexer:
    """Leksicki analizator za RAS jezik.

    Koristi regex-based tokenizaciju sa definisanim pravilima.
    Komentari (// i /* */) i whitespace se odbacuju.
    Svi identifikatori se matchuju case-insensitive."""

    # Pravila tokenizacije (redoslijed je bitan!)
    RULES = [
        # Komentari (jednoliniski i viselinijski)
        ('COMMENT',       r'//.*|/\*[\s\S]*?\*/'),

        # Kljucne rijeci za nastavu
        ('PREDAJE',       r'\bpredaje\b'),
        ('TERMIN',        r'\btacno u terminu\b'),
        ('ODJELJENJU',    r'\bodjeljenju\b'),
        ('PROSTORIJI',    r'\bu prostoriji\b|\bprostoriji\b'),

        # Definicijski iskazi ("X je Y") - duzi obrasci prvo!
        ('JE_DAN',        r'\bje dan broj\b'),
        ('JE_TERMIN',     r'\bje termin broj\b'),
        ('JE_NASTAVNIK',  r'\bje nastavnik\b'),
        ('JE_PREDMET',    r'\bje predmet\b'),
        ('JE_GRUPA',      r'\bje grupa odjeljenja\b'),
        ('JE_ODJELJENJE', r'\bje odjeljenje\b'),
        ('JE_PROSTORIJA', r'\bje prostorija\b'),
        ('JE_TIP_NASTAVE', r'\bje tip nastave\b'),
        ('JE',            r'\bje\b'),

        # Semesterski iskazi
        ('TRAJE',         r'\btraje\b'),
        ('IMA',           r'\bima\b'),
        ('NENASTAVNE',    r'\bnenastavne\b'),
        ('SEMESTAR',      r'\bsemestar\b'),
        ('POCINJE',       r'\bpocinje\b'),
        ('ZAVRSAVA',      r'\bzavrsava\b'),

        # Frekvencija i recurrence
        ('SVAKE',         r'\bsvake\b'),
        ('SEDMICE',       r'\bsedmice\b'),
        ('SEDMICA',       r'\bsedmica\b'),

        # Nenastavni dani
        ('DANA',          r'\bdana\b'),
        ('DANE',          r'\bdane\b'),

        # Prioritet tipa nastave
        ('PRIORITETA',    r'\bprioriteta\b'),

        # Veznik
        ('I',             r'\bi\b'),

        # Literali
        ('DATE',          r'\d{2}\.\d{2}\.\d{4}'),
        ('NUMBER',        r'\d+'),
        ('ID',            r'[\w\-/]+'),

        # Interpunkcija i whitespace
        ('DOT',           r'\.'),
        ('NEWLINE',       r'\n'),
        ('SKIP',          r'[ \t\r,]+'),
    ]

    def __init__(self, text):
        """Tokenizira ulazni tekst."""
        self.tokens = []
        line_num = 1

        # Kompajliraj sva pravila u jedan regex sa imenovanim grupama
        regex = '|'.join(f'(?P<{name}>{pattern})' for name, pattern in self.RULES)

        for mo in re.finditer(regex, text, re.IGNORECASE):
            kind = mo.lastgroup
            if kind == 'NEWLINE':
                line_num += 1
            elif kind not in ('SKIP', 'COMMENT'):
                self.tokens.append(Token(kind, mo.group(), line_num))
