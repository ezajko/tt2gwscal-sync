"""
ir.py - Intermediate Representation (IR) modeli

IR je srednji sloj izmedju AST-a i izlaznih generatora.
AST sadrzi sirove podatke iz parsiranja, a IR sadrzi obogacene
objekte sa razrijesenim referencama (vremena, datumi, grupe sa hijerarhijom).

Kompajler (compiler.py) pretvara AST u IR.
Generatori (generators/) citaju iz IR-a.
"""
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional, Set

# LectureType je definisan u models.py (AST nivo) ali se koristi i ovdje
from .models import LectureType


# ---------------------------------------------------------------------------
# Entiteti (osobe, prostorije, grupe, predmeti)
# ---------------------------------------------------------------------------
@dataclass
class Person:
    """Nastavnik sa originalnim ID-om i formatiranim imenom."""
    id: str             # originalni ID (npr. "ImePrezime")
    name: str           # formatirano ime (npr. "Ime Prezime")
    email: Optional[str] = None


@dataclass
class Room:
    """Prostorija sa ID-om i opcionalnim kapacitetom."""
    id: str             # "0-01"
    name: str           # "0-01" (za sada isto kao id)
    capacity: Optional[int] = None


@dataclass
class Group:
    """Studijska grupa sa hijerarhijom (roditelj/podgrupe).

    Hijerarhija se koristi za nasljedjivanje evenata u HTML generatoru:
    podgrupa nasljedjuje evente svog roditelja."""
    id: str
    name: str
    parent: Optional['Group'] = None
    subgroups: List['Group'] = field(default_factory=list)

    def get_all_descendants(self) -> Set['Group']:
        """Vraca sve podgrupe rekurzivno (djeca, unuci, itd.)."""
        desc = set(self.subgroups)
        for sub in self.subgroups:
            desc.update(sub.get_all_descendants())
        return desc

    def get_all_ancestors(self) -> Set['Group']:
        """Vraca sve roditeljske grupe rekurzivno do korijena."""
        if not self.parent:
            return set()
        ancestors = {self.parent}
        ancestors.update(self.parent.get_all_ancestors())
        return ancestors

    def __hash__(self):
        return hash(self.id)

    def __repr__(self):
        parent_id = self.parent.id if self.parent else None
        return f"Group({self.id}, parent={parent_id})"


@dataclass
class Subject:
    """Predmet sa nazivom i skupom tipova nastave."""
    id: str
    name: str
    types: Set[LectureType] = field(default_factory=set)


# ---------------------------------------------------------------------------
# Event (jedan blok nastave sa svim IR podacima)
# ---------------------------------------------------------------------------
@dataclass
class Event:
    """Jedan blok nastave sa potpuno razrijesenim podacima.
    Nastaje kompajliranjem AssignmentNode-a iz AST-a."""
    uid: str                    # jedinstveni ID (npr. "EV-42")
    subject: Subject
    type: LectureType
    teachers: List[Person]
    groups: List[Group]
    rooms: List[Room]

    # Vrijeme (razrijeseno iz slot definicija)
    day_name: str               # "Ponedjeljak"
    start_time_str: str         # "08:00"
    end_time_str: str           # "09:00"
    start_dt: datetime          # datum + vrijeme prvog pojavljivanja
    end_dt: datetime            # datum + vrijeme prvog pojavljivanja

    # Ponavljanje (recurrence)
    frequency: str = "WEEKLY"
    interval: int = 1           # svake N sedmice
    until_date: Optional[str] = None    # kraj ponavljanja (YYYY-MM-DD)
    exdates: List[str] = field(default_factory=list)  # nenastavni dani (YYYYMMDD)


# ---------------------------------------------------------------------------
# ScheduleModel (korijenski IR objekat)
# ---------------------------------------------------------------------------
@dataclass
class ScheduleModel:
    """Korijenski IR objekat koji drzi cijeli kompajlirani raspored.
    Sadrzi lookup rjecnike za brz pristup entitetima po kljucu."""
    semester_name: str
    start_date: str             # YYYY-MM-DD
    end_date: str               # YYYY-MM-DD
    holidays: List[str]         # lista YYYYMMDD stringova

    # Kompajlirani eventi
    events: List[Event] = field(default_factory=list)

    # Lookup rjecnici (popunjava ih compiler)
    people: Dict[str, Person] = field(default_factory=dict)
    rooms: Dict[str, Room] = field(default_factory=dict)
    groups: Dict[str, Group] = field(default_factory=dict)
    subjects: Dict[str, Subject] = field(default_factory=dict)
    days: Dict[str, str] = field(default_factory=dict)  # dan_naziv -> broj

    # Tipovi nastave (koriste ih html_gen i grid_gen za CSS klase i sortiranje)
    default_types: Dict[str, LectureType] = field(default_factory=dict)
