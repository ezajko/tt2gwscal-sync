from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional, Set

# --- Models ---

@dataclass(frozen=True)
class LectureType:
    code: str       # "P", "V", "L"
    name: str       # "Predavanje"
    priority: int   # 0, 1, 2

    @property
    def css_class(self):
        return f"tag-{self.code}"

@dataclass
class Person:
    id: str         # Originalni ID (npr. NekoNeko)
    name: str       # Formatirano ime (npr. Neko Neko)
    email: Optional[str] = None

@dataclass
class Room:
    id: str         # "0-01"
    name: str       # "0-01" (za sada isto)
    capacity: Optional[int] = None

@dataclass
class Group:
    id: str         # "RI1"
    name: str       # "RI1"
    parent: Optional['Group'] = None
    subgroups: List['Group'] = field(default_factory=list)

    def get_all_descendants(self) -> Set['Group']:
        desc = set(self.subgroups)
        for sub in self.subgroups:
            desc.update(sub.get_all_descendants())
        return desc

    def get_all_ancestors(self) -> Set['Group']:
        if not self.parent: return set()
        ancestors = {self.parent}
        ancestors.update(self.parent.get_all_ancestors())
        return ancestors

    def __hash__(self):
        return hash(self.id)

    def __repr__(self):
        return f"Group({self.id}, parent={self.parent.id if self.parent else None})"

@dataclass
class Subject:
    id: str
    name: str
    types: Set[LectureType] = field(default_factory=set)

@dataclass
class Event:
    uid: str        # Unique ID for tracking
    subject: Subject
    type: LectureType
    teachers: List[Person]
    groups: List[Group]
    rooms: List[Room]

    # Time info (Enriched)
    day_name: str
    start_time_str: str # HH:MM
    end_time_str: str   # HH:MM
    start_dt: datetime  # Prvo pojavljivanje (datum + vrijeme)
    end_dt: datetime    # Prvo pojavljivanje (datum + vrijeme)

    # Recurrence
    frequency: str = "WEEKLY"
    interval: int = 1
    until_date: Optional[str] = None # YYYY-MM-DD
    exdates: List[str] = field(default_factory=list) # List of YYYYMMDD strings

@dataclass
class ScheduleModel:
    semester_name: str
    start_date: str # YYYY-MM-DD
    end_date: str   # YYYY-MM-DD
    holidays: List[str]

    events: List[Event] = field(default_factory=list)

    # Lookups
    people: Dict[str, Person] = field(default_factory=dict)
    rooms: Dict[str, Room] = field(default_factory=dict)
    groups: Dict[str, Group] = field(default_factory=dict)
    subjects: Dict[str, Subject] = field(default_factory=dict)

# --- Defaults ---
DEFAULT_TYPES = {
    "P": LectureType("P", "Predavanje", 0),
    "V": LectureType("V", "Vježbe", 1),
    "L": LectureType("L", "Laboratorijske vježbe", 2),
    "T": LectureType("T", "Tutorijal", 3),
}
