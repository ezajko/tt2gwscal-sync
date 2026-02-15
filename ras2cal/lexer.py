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
        ('JE',           r'\bje\b'),                        # NOVO (mora biti poslije JE_...)
        ('U',            r'\bu\b'),                         # NOVO
        ('AKADEMSKOJ',   r'\bakademskoj\b'),                # NOVO
        ('GODINI',       r'\bgodini\b'),                    # NOVO
        ('KAO',          r'\bkao\b'),                       # NOVO
        ('IMA',          r'\bima\b'),                       # NOVO
        ('NENASTAVNE',   r'\bnenastavne\b'),                # NOVO
        ('SVAKE',        r'\bsvake\b'),                     # NOVO
        ('SEDMICE',      r'\bsedmice\b'),                   # NOVO
        ('DANA',         r'\bdana\b'),
        ('DANE',         r'\bdane\b'),                      # NOVO
        ('SEMESTAR',     r'\bsemestar\b'),
        ('POCINJE',      r'\bpocinje\b'),
        ('ZAVRSAVA',     r'\bzavrsava\b'),
        ('I',            r'\bi\b'),
        ('DATE',         r'\d{2}\.\d{2}\.\d{4}'),
        ('ACAD_YEAR_VAL',r'\d{4}/\d{4}'),                   # NOVO
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
