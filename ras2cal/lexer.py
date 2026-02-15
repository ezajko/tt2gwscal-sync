import re


class Token:
    def __init__(self, type, value, line):
        self.type, self.value, self.line = type, value, line

class Lexer:
    RULES = [
        ('COMMENT',      r'//.*|/\*[\s\S]*?\*/'),
        ('PREDAJE',      r'\bpredaje\b'),
        ('TERMIN',       r'\btacno u terminu\b'),
        ('ODJELJENJU',   r'\bodjeljenju\b'),
        ('PROSTORIJI',   r'\bu prostoriji\b|\bprostoriji\b'),
        ('JE_DAN',       r'\bje dan broj\b'),
        ('JE_TERMIN',    r'\bje termin broj\b'),
        ('JE_NASTAVNIK', r'\bje nastavnik\b'),
        ('JE_PREDMET',   r'\bje predmet\b'),
        ('JE_GRUPA',     r'\bje grupa odjeljenja\b'),
        ('JE_ODJELJENJE',r'\bje odjeljenje\b'),
        ('JE_PROSTORIJA',r'\bje prostorija\b'),
        ('JE',           r'\bje\b'),
        ('TRAJE',        r'\btraje\b'),                     # NOVO
        ('IMA',          r'\bima\b'),
        ('NENASTAVNE',   r'\bnenastavne\b'),
        ('SVAKE',        r'\bsvake\b'),
        ('SEDMICE',      r'\bsedmice\b'),
        ('SEDMICA',      r'\bsedmica\b'),                   # NOVO
        ('DANA',         r'\bdana\b'),
        ('DANE',         r'\bdane\b'),
        ('SEMESTAR',     r'\bsemestar\b'),
        ('POCINJE',      r'\bpocinje\b'),
        ('ZAVRSAVA',     r'\bzavrsava\b'),
        ('I',            r'\bi\b'),
        ('DATE',         r'\d{2}\.\d{2}\.\d{4}'),
        ('NUMBER',       r'\d+'),
        ('ID',           r'[\w\-/]+'),
        ('DOT',          r'\.'),
        ('NEWLINE',      r'\n'),
        ('SKIP',         r'[ \t\r,]+'),
    ]

    def __init__(self, text):
        self.tokens = []
        line_num = 1
        regex = '|'.join(f'(?P<{name}>{pattern})' for name, pattern in self.RULES)

        for mo in re.finditer(regex, text, re.IGNORECASE):
            kind = mo.lastgroup
            if kind == 'NEWLINE':
                line_num += 1
            elif kind not in ['SKIP', 'COMMENT']:
                self.tokens.append(Token(kind, mo.group(), line_num))
