"""
parser.py - Sintaksna analiza RAS jezika

Prima niz tokena iz Lexer-a i gradi AST (Abstract Syntax Tree).
Svaki iskaz u .ras fajlu se pretvara u odgovarajuci AST cvor.

Podrzani iskazi:
    - Definicije: dan, termin, nastavnik, predmet, odjeljenje, grupa, prostorija
    - Semestar: deklaracija, pocetak, kraj, trajanje, nenastavni dani
    - Tipovi nastave: kod, naziv, prioritet
    - Nastava: nastavnik predaje predmet odjeljenju u prostoriji u terminu
"""
from datetime import datetime
import sys

from .models import (
    AssignmentNode,
    DayDefinitionNode,
    LectureTypeDefinitionNode,
    RoomDefinitionNode,
    Schedule,
    SemesterAttributeNode,
    SemesterDefinitionNode,
    SlotDefinitionNode,
    StudyGroupDefinitionNode,
    StudySubGroupDefinitionNode,
    SubjectDefinitionNode,
    TeacherDefinitionNode,
)
from .utils import format_camel_case, format_subject_name


class Parser:
    """Rekurzivni parser za RAS jezik.

    Koristi peek/consume mehanizam za citanje tokena.
    Svaki parse_statement() poziv pokusava prepoznati jedan iskaz."""

    def __init__(self, tokens):
        self.tokens = tokens
        self.pos = 0

    def peek(self, offset=0):
        """Vraca token na trenutnoj poziciji + offset, bez pomjeranja."""
        idx = self.pos + offset
        return self.tokens[idx] if idx < len(self.tokens) else None

    def consume(self, expected=None):
        """Konzumira sljedeci token. Ako je dat expected tip, vraca None
        ako se ne poklapa (bez pomjeranja pozicije)."""
        token = self.peek()
        if not token:
            return None
        if expected and token.type != expected:
            return None
        self.pos += 1
        return token

    def parse(self):
        """Parsira cijeli niz tokena i vraca Schedule (korijenski AST cvor)."""
        schedule = Schedule()
        while self.peek():
            node = self.parse_statement()
            if node:
                schedule.add(node)
            else:
                # Token koji nije prepoznat - ispisi upozorenje
                bad = self.peek()
                print(f"Upozorenje (linija {bad.line}): Neprepoznat token "
                      f"'{bad.value}' (tip: {bad.type}). Preskačem.",
                      file=sys.stderr)
                self.pos += 1
        return schedule

    def parse_statement(self):
        """Pokusava parsirati jedan iskaz iz trenutne pozicije.
        Vraca AST cvor ili None ako iskaz nije prepoznat."""
        t = self.peek()
        if not t:
            return None

        # --- Semestar: deklaracija ---
        # Format: {Naziv} je semestar.
        if t.type == 'ID' and self.peek(1) and self.peek(1).type == 'JE':
            if self.peek(2) and self.peek(2).type == 'SEMESTAR':
                name = self.consume('ID').value
                self.consume('JE')
                self.consume('SEMESTAR')
                self.consume('DOT')
                return SemesterDefinitionNode(name)

        # --- Semestar: atributi ---
        # Format: {Naziv} pocinje/zavrsava/traje/ima ...
        if t.type in ('ID', 'SEMESTAR'):
            nxt = self.peek(1)
            if nxt:
                name = t.value if t.type == 'ID' else "Semestar"

                # Pocetak semestra: {Naziv} pocinje DD.MM.YYYY.
                if nxt.type == 'POCINJE':
                    self.consume(t.type)
                    self.consume('POCINJE')
                    val_str = self.consume('DATE').value
                    val = datetime.strptime(val_str, "%d.%m.%Y").strftime("%Y-%m-%d")
                    self.consume('DOT')
                    return SemesterAttributeNode(name, 'start', val)

                # Kraj semestra: {Naziv} zavrsava DD.MM.YYYY.
                elif nxt.type == 'ZAVRSAVA':
                    self.consume(t.type)
                    self.consume('ZAVRSAVA')
                    val_str = self.consume('DATE').value
                    val = datetime.strptime(val_str, "%d.%m.%Y").strftime("%Y-%m-%d")
                    self.consume('DOT')
                    return SemesterAttributeNode(name, 'end', val)

                # Trajanje: {Naziv} traje N sedmica.
                elif nxt.type == 'TRAJE':
                    self.consume(t.type)
                    self.consume('TRAJE')
                    val = int(self.consume('NUMBER').value)
                    # Prihvati i 'sedmica' i 'sedmice'
                    if self.peek() and self.peek().type in ('SEDMICA', 'SEDMICE'):
                        self.consume()
                    self.consume('DOT')
                    return SemesterAttributeNode(name, 'duration', val)

                # Nenastavni dani: {Naziv} ima nenastavne dane DD.MM.YYYY, ...
                elif nxt.type == 'IMA':
                    if self.peek(2) and self.peek(2).type == 'NENASTAVNE':
                        self.consume(t.type)
                        self.consume('IMA')
                        self.consume('NENASTAVNE')
                        if self.peek().type in ('DANA', 'DANE'):
                            self.consume()

                        holidays = []
                        while self.peek() and self.peek().type != 'DOT':
                            h_str = self.consume('DATE').value
                            holidays.append(
                                datetime.strptime(h_str, "%d.%m.%Y").strftime("%Y%m%d")
                            )
                        self.consume('DOT')
                        return SemesterAttributeNode(name, 'holidays', holidays)

        # --- Definicija dana ---
        # Format: {Naziv} je dan broj {N}.
        if t.type == 'ID' and self.peek(1) and self.peek(1).type == 'JE_DAN':
            name = self.consume().value
            self.consume('JE_DAN')
            num = self.consume('NUMBER').value
            self.consume('DOT')
            return DayDefinitionNode(name, num)

        # --- Definicija termina ---
        # Format: {SlotID} je termin broj {N} dana {DanNaziv}.
        if t.type == 'ID' and self.peek(1) and self.peek(1).type == 'JE_TERMIN':
            slot_id = self.consume().value
            self.consume('JE_TERMIN')
            num = self.consume('NUMBER').value
            self.consume('DANA')
            day_name = self.consume('ID').value
            self.consume('DOT')
            return SlotDefinitionNode(slot_id, day_name, num)

        # --- Definicija nastavnika ---
        # Format: {ImePrezime} je nastavnik.
        if t.type == 'ID' and self.peek(1) and self.peek(1).type == 'JE_NASTAVNIK':
            raw_name = self.consume().value
            self.consume('JE_NASTAVNIK')
            self.consume('DOT')
            return TeacherDefinitionNode(format_camel_case(raw_name))

        # --- Definicija predmeta ---
        # Format: {tipNaziv} je predmet.  (npr. pUvodUProgramiranje)
        if t.type == 'ID' and self.peek(1) and self.peek(1).type == 'JE_PREDMET':
            raw_name = self.consume().value
            self.consume('JE_PREDMET')
            self.consume('DOT')
            subject, tipo = format_subject_name(raw_name)
            return SubjectDefinitionNode(subject, {tipo})

        # --- Definicija podgrupe (grupa odjeljenja) ---
        # Format: {Naziv} je grupa odjeljenja {Roditelj}.
        if t.type == 'ID' and self.peek(1) and self.peek(1).type == 'JE_GRUPA':
            name = self.consume().value
            self.consume('JE_GRUPA')
            parent = self.consume('ID').value
            self.consume('DOT')
            return StudySubGroupDefinitionNode(name, parent)

        # --- Definicija odjeljenja ---
        # Format: {Naziv} je odjeljenje.
        if t.type == 'ID' and self.peek(1) and self.peek(1).type == 'JE_ODJELJENJE':
            name = self.consume().value
            self.consume('JE_ODJELJENJE')
            self.consume('DOT')
            return StudyGroupDefinitionNode(name)

        # --- Definicija prostorije ---
        # Format: {Naziv} je prostorija.
        if t.type == 'ID' and self.peek(1) and self.peek(1).type == 'JE_PROSTORIJA':
            name = self.consume().value.replace("_", "")
            self.consume('JE_PROSTORIJA')
            self.consume('DOT')
            return RoomDefinitionNode(name)

        # --- Definicija tipa nastave ---
        # Format: {Kod} je tip nastave {Naziv} prioriteta {N}.
        if t.type == 'ID' and self.peek(1) and self.peek(1).type == 'JE_TIP_NASTAVE':
            code = self.consume().value
            self.consume('JE_TIP_NASTAVE')
            raw_name = self.consume('ID').value
            name = format_camel_case(raw_name)  # CamelCase -> razmak-odvojeno
            self.consume('PRIORITETA')
            priority = self.consume('NUMBER').value
            self.consume('DOT')
            return LectureTypeDefinitionNode(code, name, priority)

        # --- Iskaz nastave ---
        # Format: {Nastavnik} [i {Nastavnik2}] predaje {predmet}
        #         odjeljenju {Grupa} u prostoriji {Prostorija}
        #         [N puta sedmicno] [svake N sedmice]
        #         tacno u terminu {Slot1} {Slot2} ...
        if t.type == 'ID':
            # Provjeri da li se negdje ispred pojavljuje 'predaje'
            is_teaching = False
            i = 1
            while True:
                future = self.peek(i)
                if not future or future.type == 'DOT':
                    break
                if future.type == 'PREDAJE':
                    is_teaching = True
                    break
                i += 1

            if is_teaching:
                return self._parse_assignment()

        return None

    def _parse_assignment(self):
        """Parsira iskaz nastave (sve do tacke)."""
        # Nastavnici (prije 'predaje')
        teachers = []
        while self.peek() and self.peek().type != 'PREDAJE':
            tok = self.consume()
            if tok.value != 'i':
                teachers.append(format_camel_case(tok.value))

        self.consume('PREDAJE')

        # Predmet (jedan token sa prefiksom tipa)
        raw_subject = self.consume('ID').value
        subject, tipo = format_subject_name(raw_subject)

        # Meta-podaci (grupe, prostorije, termini, frekvencija, ...)
        meta = {
            'grupa': [],
            'rooms': [],
            'slots': [],
            'freq': None,
            'interval': None,
            'unknown': [],
        }

        while self.peek() and self.peek().type != 'DOT':
            curr = self.consume()

            if curr.type == 'ODJELJENJU':
                # Jedna ili vise grupa nakon 'odjeljenju'
                meta['grupa'].append(self.consume('ID').value)
                while self.peek() and self.peek().type == 'ID':
                    meta['grupa'].append(self.consume().value)

            elif curr.type == 'PROSTORIJI':
                meta['rooms'].append(self.consume('ID').value.replace("_", ""))

            elif curr.type == 'TERMIN':
                # Svi slotovi nakon 'tacno u terminu'
                while self.peek() and self.peek().type == 'ID':
                    meta['slots'].append(self.consume().value)

            elif curr.type == 'NUMBER':
                # Frekvencija: "6 puta sedmicno"
                if (self.peek() and self.peek().value == 'puta' and
                        self.peek(1) and self.peek(1).value == 'sedmicno'):
                    meta['freq'] = curr.value
                    self.consume()  # 'puta'
                    self.consume()  # 'sedmicno'
                else:
                    meta['unknown'].append(curr.value)

            elif curr.type == 'SVAKE':
                # Recurrence interval: "svake 2 sedmice"
                if (self.peek() and self.peek().type == 'NUMBER' and
                        self.peek(1) and self.peek(1).type == 'SEDMICE'):
                    meta['interval'] = self.consume().value
                    self.consume()  # 'sedmice'
                else:
                    meta['unknown'].append(curr.value)

            else:
                meta['unknown'].append(curr.value)

        self.consume('DOT')

        groups_list = [meta['grupa']] if meta['grupa'] else [["Svi"]]
        return AssignmentNode(
            teachers, subject, tipo, groups_list,
            meta['rooms'], meta['slots'],
            meta['freq'], meta['unknown'], meta['interval']
        )
