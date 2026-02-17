"""
models.py - AST (Abstract Syntax Tree) modeli

Definise sve cvorove koji nastaju kao rezultat parsiranja .ras fajlova.
Schedule je korijenski cvor koji agregira sve ostale.

LectureType je ovdje (a ne u ir.py) jer se koristi i na AST nivou
(za merge konfiguracije u tt2cal.py) i na IR nivou (za generisanje izlaza).
"""
from dataclasses import dataclass


# ---------------------------------------------------------------------------
# Tip nastave (konfiguracijski objekat, dijeli se izmedju AST i IR)
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class LectureType:
    """Tip nastave sa kodom, nazivom i prioritetom.

    Prioritet odredjuje redoslijed prikaza u generatorima (manji = vazniji).
    Definise se u tt2cal.py kao LECTURE_TYPES konstanta, a moze se
    override-ovati u .ras fajlu putem LectureTypeDefinitionNode."""
    code: str       # "P", "V", "L", "T", "N"
    name: str       # "Predavanje", "Vjezbe", ...
    priority: int   # 0 = najvisji prioritet

    @property
    def css_class(self):
        """CSS klasa za vizualni prikaz u HTML generatorima."""
        return f"tag-{self.code}"


# ---------------------------------------------------------------------------
# Bazna klasa za AST cvorove
# ---------------------------------------------------------------------------
class ASTNode:
    """Bazna klasa za sve AST cvorove.
    Pruza standardni __repr__ koji ispisuje sve atribute."""
    def __repr__(self):
        return f"{self.__class__.__name__}({vars(self)})"


# ---------------------------------------------------------------------------
# SemesterInfo (dict sa lijepim __repr__)
# ---------------------------------------------------------------------------
class SemesterInfo(dict):
    """Rjecnik sa semestralnim meta-podacima koji se ispisuje kao AST cvor.
    Nasljedjuje dict za potpunu kompatibilnost (.get(), [], .items(), itd.)
    ali daje konzistentan ispis: SemesterInfo(name=..., start_date=..., ...)"""

    def __repr__(self):
        parts = [f"{k}={v!r}" for k, v in self.items()]
        return f"SemesterInfo({', '.join(parts)})"


# ---------------------------------------------------------------------------
# Definicijski cvorovi (nastaju iz "X je ..." iskaza)
# ---------------------------------------------------------------------------
class DayDefinitionNode(ASTNode):
    """Dan u sedmici: 'Ponedjeljak je dan broj 1.'"""
    def __init__(self, name, number):
        self.name = name
        self.number = int(number)


class SlotDefinitionNode(ASTNode):
    """Termin: 'PO1 je termin broj 1 dana Ponedjeljak.'"""
    def __init__(self, slot_id, day_name, number):
        self.slot_id = slot_id
        self.day_name = day_name
        self.number = int(number)


class TeacherDefinitionNode(ASTNode):
    """Nastavnik: 'ImePrezime je nastavnik.'"""
    def __init__(self, name):
        self.name = name


class SubjectDefinitionNode(ASTNode):
    """Predmet: 'pNazivPredmeta je predmet.'
    Tip (code) je izvucen iz prefiksa (p=P, v=V, l=L, itd.)."""
    def __init__(self, name, types=None):
        self.name = name
        self.types = types if types else set()


class StudyGroupDefinitionNode(ASTNode):
    """Odjeljenje (studijska grupa): 'RI1 je odjeljenje.'"""
    def __init__(self, name):
        self.name = name


class StudySubGroupDefinitionNode(ASTNode):
    """Podgrupa odjeljenja: 'RI1oop-1 je grupa odjeljenja RI1.'"""
    def __init__(self, name, parent=None):
        self.name = name
        self.parent = parent


class RoomDefinitionNode(ASTNode):
    """Prostorija: 'R0-01 je prostorija.'"""
    def __init__(self, name):
        self.name = name


class SemesterDefinitionNode(ASTNode):
    """Deklaracija semestra: 'Semestar2026 je semestar.'"""
    def __init__(self, name):
        self.name = name


class SemesterAttributeNode(ASTNode):
    """Atribut semestra: pocetak, kraj, trajanje, nenastavni dani.
    Primjeri:
        'Semestar2026 pocinje 01.10.2026.'
        'Semestar2026 traje 15 sedmica.'
        'Semestar2026 ima nenastavne dane 01.01.2027, ...'
    """
    def __init__(self, semester_name, attr_type, value):
        self.semester_name = semester_name
        self.attr_type = attr_type  # 'start', 'end', 'duration', 'holidays'
        self.value = value


class LectureTypeDefinitionNode(ASTNode):
    """Definicija tipa nastave: 'P je tip nastave Predavanje prioriteta 0.'
    Ovo omogucava override tipova iz .ras fajla umjesto koristenja
    podrazumijevanih vrijednosti iz tt2cal.py."""
    def __init__(self, code, name, priority):
        self.code = code            # "P", "V", "L"
        self.name = name            # "Predavanje" (formatirano iz CamelCase)
        self.priority = int(priority)


# ---------------------------------------------------------------------------
# Assignment cvor (nastava)
# ---------------------------------------------------------------------------
class AssignmentNode(ASTNode):
    """Iskaz nastave: 'Nastavnik predaje predmet odjeljenju ...'
    Sadrzi sve informacije o jednom bloku nastave."""
    def __init__(self, teachers, subject, type, groups, rooms, slots,
                 frequency_hint=None, unknown_tokens=None,
                 recurrence_interval=None):
        self.teachers = teachers                # lista imena nastavnika
        self.subject = subject                  # naziv predmeta
        self.type = type                        # kod tipa nastave (P, V, L, T)
        self.groups = groups                    # lista lista grupa
        self.rooms = rooms                      # lista prostorija
        self.slots = slots                      # lista ID-ova termina
        self.frequency_hint = int(frequency_hint) if frequency_hint else None
        self.unknown_tokens = unknown_tokens if unknown_tokens else []
        self.recurrence_interval = int(recurrence_interval) if recurrence_interval else 1


# ---------------------------------------------------------------------------
# Schedule (korijenski AST cvor)
# ---------------------------------------------------------------------------
class Schedule(ASTNode):
    """Korijenski cvor koji sadrzi cijeli raspored kao AST.
    Sve definicije se cuvaju u rjecnicima za brz pristup po kljucu."""

    def __init__(self):
        # Definicije (popunjava ih Parser)
        self.days = {}              # name -> DayDefinitionNode
        self.slots = {}             # slot_id -> SlotDefinitionNode
        self.teachers = {}          # name -> TeacherDefinitionNode
        self.subjects = {}          # name -> SubjectDefinitionNode
        self.study_groups = {}      # name -> StudyGroupDefinitionNode
        self.subgroups = {}         # name -> StudySubGroupDefinitionNode
        self.rooms = {}             # name -> RoomDefinitionNode
        self.lecture_types = {}     # code -> LectureTypeDefinitionNode
        self.assignments = []       # lista AssignmentNode-ova

        # Semestar info (konsolidiran iz razlicitih SemesterAttributeNode-ova)
        self.semester_info = SemesterInfo({
            'name': None,
            'start_date': None,
            'end_date': None,
            'duration_weeks': None,
            'holidays': [],
        })

        # Konfiguracija (postavlja je tt2cal.py, NE parser)
        self.base_time = None           # str, npr. '08:00'
        self.slot_duration = None       # int, npr. 30 (minuta)
        self.slots_per_index = None     # int, npr. 2
        self.default_types = {}         # Dict[str, LectureType] - merged tipovi

    # Convenience svojstva za cest pristup
    @property
    def start_date(self):
        return self.semester_info['start_date']

    @property
    def end_date(self):
        return self.semester_info['end_date']

    @property
    def holidays(self):
        return self.semester_info['holidays']

    def add(self, node):
        """Dodaje AST cvor u odgovarajucu kolekciju.
        Poziva je Parser za svaki uspjesno parsirani iskaz."""
        if isinstance(node, DayDefinitionNode):
            self.days[node.name] = node
        elif isinstance(node, SlotDefinitionNode):
            self.slots[node.slot_id] = node
        elif isinstance(node, TeacherDefinitionNode):
            self.teachers[node.name] = node
        elif isinstance(node, SubjectDefinitionNode):
            # Predmet se moze pojaviti vise puta (razliciti tipovi nastave)
            if node.name in self.subjects:
                self.subjects[node.name].types.update(node.types)
            else:
                self.subjects[node.name] = node
        elif isinstance(node, StudyGroupDefinitionNode):
            self.study_groups[node.name] = node
        elif isinstance(node, StudySubGroupDefinitionNode):
            self.subgroups[node.name] = node
        elif isinstance(node, RoomDefinitionNode):
            self.rooms[node.name] = node
        elif isinstance(node, AssignmentNode):
            self.assignments.append(node)
        elif isinstance(node, SemesterDefinitionNode):
            self.semester_info['name'] = node.name
        elif isinstance(node, SemesterAttributeNode):
            if node.attr_type == 'start':
                self.semester_info['start_date'] = node.value
            elif node.attr_type == 'end':
                self.semester_info['end_date'] = node.value
            elif node.attr_type == 'duration':
                self.semester_info['duration_weeks'] = node.value
            elif node.attr_type == 'holidays':
                self.semester_info['holidays'].extend(node.value)
        elif isinstance(node, LectureTypeDefinitionNode):
            self.lecture_types[node.code] = node

    def __repr__(self):
        return (
            f"Schedule("
            f"days={len(self.days)}, "
            f"slots={len(self.slots)}, "
            f"teachers={len(self.teachers)}, "
            f"subjects={len(self.subjects)}, "
            f"study_groups={len(self.study_groups)}, "
            f"subgroups={len(self.subgroups)}, "
            f"rooms={len(self.rooms)}, "
            f"lecture_types={len(self.lecture_types)}, "
            f"assignments={len(self.assignments)})"
        )
