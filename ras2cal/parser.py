from datetime import datetime

from .models import (
    AssignmentNode,
    DayDefinitionNode,
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
from .utils import format_person_name, format_subject_name


class Parser:
    def __init__(self, tokens):
        self.tokens = tokens
        self.pos = 0

    def peek(self, offset=0):
        return self.tokens[self.pos + offset] if self.pos + offset < len(self.tokens) else None

    def consume(self, expected=None):
        token = self.peek()
        if not token: return None
        if expected and token.type != expected: return None
        self.pos += 1
        return token

    def parse(self):
        schedule = Schedule()
        while self.peek():
            node = self.parse_statement()
            if node:
                schedule.add(node)
            else:
                self.pos += 1
        return schedule

    def parse_statement(self):
        t = self.peek()
        if not t: return None

        # Definicija semestra (ID je SEMESTAR)
        if t.type == 'ID' and self.peek(1) and self.peek(1).type == 'JE':
             if self.peek(2) and self.peek(2).type == 'SEMESTAR':
                 name = self.consume('ID').value
                 self.consume('JE')
                 self.consume('SEMESTAR')
                 self.consume('DOT')
                 return SemesterDefinitionNode(name)

        # Atributi semestra (ID/SEMESTAR + POCINJE/ZAVRSAVA/TRAJE/IMA)
        if t.type in ['ID', 'SEMESTAR']:
            nxt = self.peek(1)
            if nxt:
                name = t.value if t.type == 'ID' else "Semestar"

                if nxt.type == 'POCINJE':
                    self.consume(t.type)
                    self.consume('POCINJE')
                    val_str = self.consume('DATE').value
                    val = datetime.strptime(val_str, "%d.%m.%Y").strftime("%Y-%m-%d")
                    self.consume('DOT')
                    return SemesterAttributeNode(name, 'start', val)

                elif nxt.type == 'ZAVRSAVA':
                    self.consume(t.type)
                    self.consume('ZAVRSAVA')
                    val_str = self.consume('DATE').value
                    val = datetime.strptime(val_str, "%d.%m.%Y").strftime("%Y-%m-%d")
                    self.consume('DOT')
                    return SemesterAttributeNode(name, 'end', val)

                elif nxt.type == 'TRAJE':
                    self.consume(t.type)
                    self.consume('TRAJE')
                    val = int(self.consume('NUMBER').value)
                    if self.peek() and self.peek().type in ['SEDMICA', 'SEDMICE']:
                        self.consume()
                    self.consume('DOT')
                    return SemesterAttributeNode(name, 'duration', val)

                elif nxt.type == 'IMA':
                    if self.peek(2) and self.peek(2).type == 'NENASTAVNE':
                        self.consume(t.type)
                        self.consume('IMA')
                        self.consume('NENASTAVNE')
                        if self.peek().type in ['DANA', 'DANE']: self.consume()

                        holidays = []
                        while self.peek() and self.peek().type != 'DOT':
                            h_str = self.consume('DATE').value
                            holidays.append(datetime.strptime(h_str, "%d.%m.%Y").strftime("%Y%m%d"))
                        self.consume('DOT')
                        return SemesterAttributeNode(name, 'holidays', holidays)

        # Definicija dana
        if t.type == 'ID' and self.peek(1) and self.peek(1).type == 'JE_DAN':
            name = self.consume().value
            self.consume('JE_DAN')
            num = self.consume('NUMBER').value
            self.consume('DOT')
            return DayDefinitionNode(name, num)

        # Definicija termina
        if t.type == 'ID' and self.peek(1) and self.peek(1).type == 'JE_TERMIN':
            slot_id = self.consume().value
            self.consume('JE_TERMIN')
            num = self.consume('NUMBER').value
            self.consume('DANA')
            day_name = self.consume('ID').value
            self.consume('DOT')
            return SlotDefinitionNode(slot_id, day_name, num)

        # Definicija nastavnika
        if t.type == 'ID' and self.peek(1) and self.peek(1).type == 'JE_NASTAVNIK':
            raw_name = self.consume().value
            self.consume('JE_NASTAVNIK')
            self.consume('DOT')
            return TeacherDefinitionNode(format_person_name(raw_name))

        # Definicija predmeta
        if t.type == 'ID' and self.peek(1) and self.peek(1).type == 'JE_PREDMET':
            raw_name = self.consume().value
            self.consume('JE_PREDMET')
            self.consume('DOT')
            subject, tipo = format_subject_name(raw_name)
            return SubjectDefinitionNode(subject, {tipo})

        # Definicija podgrupe (bivša grupa)
        if t.type == 'ID' and self.peek(1) and self.peek(1).type == 'JE_GRUPA':
            name = self.consume().value
            self.consume('JE_GRUPA')
            parent = self.consume('ID').value
            self.consume('DOT')
            return StudySubGroupDefinitionNode(name, parent)

        # Definicija studijske grupe (bivše odjeljenje)
        if t.type == 'ID' and self.peek(1) and self.peek(1).type == 'JE_ODJELJENJE':
            name = self.consume().value
            self.consume('JE_ODJELJENJE')
            self.consume('DOT')
            return StudyGroupDefinitionNode(name)

        # Definicija prostorije
        if t.type == 'ID' and self.peek(1) and self.peek(1).type == 'JE_PROSTORIJA':
            name = self.consume().value.replace("_", "")
            self.consume('JE_PROSTORIJA')
            self.consume('DOT')
            return RoomDefinitionNode(name)

        # Nastava
        if t.type == 'ID':
            is_teaching = False
            for i in range(1, 15):
                future = self.peek(i)
                if future and future.type == 'PREDAJE': is_teaching = True; break
                if not future or future.type == 'DOT': break

            if is_teaching:
                teachers = []
                while self.peek() and self.peek().type != 'PREDAJE':
                    tok = self.consume()
                    if tok.value != 'i': teachers.append(format_person_name(tok.value))

                self.consume('PREDAJE')
                raw_subject = self.consume('ID').value
                subject, tipo = format_subject_name(raw_subject)

                meta = {'grupa': [], 'rooms': [], 'slots': [], 'freq': None, 'interval': None, 'unknown': []}

                while self.peek() and self.peek().type != 'DOT':
                    curr = self.consume()
                    if curr.type == 'ODJELJENJU':
                        meta['grupa'].append(self.consume('ID').value)
                        while self.peek() and self.peek().type == 'ID':
                            meta['grupa'].append(self.consume().value)
                    elif curr.type == 'PROSTORIJI':
                        meta['rooms'].append(self.consume('ID').value.replace("_", ""))
                    elif curr.type == 'TERMIN':
                        while self.peek() and self.peek().type == 'ID':
                            meta['slots'].append(self.consume().value)
                    elif curr.type == 'NUMBER':
                        if self.peek() and self.peek().value == 'puta' and \
                           self.peek(1) and self.peek(1).value == 'sedmicno':
                            meta['freq'] = curr.value
                            self.consume()
                            self.consume()
                        else:
                            meta['unknown'].append(curr.value)
                    elif curr.type == 'SVAKE':
                        if self.peek() and self.peek().type == 'NUMBER' and \
                           self.peek(1) and self.peek(1).type == 'SEDMICE':
                            meta['interval'] = self.consume().value
                            self.consume()
                        else:
                            meta['unknown'].append(curr.value)
                    else:
                        meta['unknown'].append(curr.value)

                self.consume('DOT')

                groups_list = [meta['grupa']] if meta['grupa'] else [["Svi"]]
                return AssignmentNode(teachers, subject, tipo, groups_list, meta['rooms'], meta['slots'],
                                      meta['freq'], meta['unknown'], meta['interval'])
        return None
