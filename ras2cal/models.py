# AST (Abstract Syntax Tree) Čvorovi

class ASTNode:
    """Bazna klasa za sve AST čvorove."""
    def __repr__(self):
        return f"{self.__class__.__name__}({vars(self)})"

class DayDefinitionNode(ASTNode):
    def __init__(self, name, number):
        self.name = name
        self.number = int(number)

class SlotDefinitionNode(ASTNode):
    def __init__(self, slot_id, day_name):
        self.slot_id = slot_id
        self.day_name = day_name

class TeacherDefinitionNode(ASTNode):
    def __init__(self, name):
        self.name = name

class SubjectDefinitionNode(ASTNode):
    def __init__(self, name, types=None):
        self.name = name
        self.types = types if types else set()

class StudyGroupDefinitionNode(ASTNode):
    def __init__(self, name):
        self.name = name

class StudySubGroupDefinitionNode(ASTNode):
    def __init__(self, name, parent=None):
        self.name = name
        self.parent = parent

class RoomDefinitionNode(ASTNode):
    def __init__(self, name):
        self.name = name

class SemesterDefinitionNode(ASTNode):
    """Predstavlja deklaraciju: {Name} je semestar."""
    def __init__(self, name):
        self.name = name

class SemesterAttributeNode(ASTNode):
    """Predstavlja atribute semestra: pocinje, zavrsava, traje, ima nenastavne dane."""
    def __init__(self, semester_name, attr_type, value):
        self.semester_name = semester_name
        self.attr_type = attr_type # 'start', 'end', 'duration', 'holidays'
        self.value = value

class AssignmentNode(ASTNode):
    def __init__(self, teachers, subject, type, groups, rooms, slots, frequency_hint=None, unknown_tokens=None, recurrence_interval=None):
        self.teachers = teachers
        self.subject = subject
        self.type = type
        self.groups = groups
        self.rooms = rooms
        self.slots = slots
        self.frequency_hint = int(frequency_hint) if frequency_hint else None
        self.unknown_tokens = unknown_tokens if unknown_tokens else []
        self.recurrence_interval = int(recurrence_interval) if recurrence_interval else 1

class Schedule(ASTNode):
    """Korijenski čvor koji sadrži cijeli raspored."""
    def __init__(self):
        self.days = {}      # name -> DayDefinitionNode
        self.slots = {}     # slot_id -> SlotDefinitionNode
        self.teachers = {}  # name -> TeacherDefinitionNode
        self.subjects = {}  # name -> SubjectDefinitionNode
        self.study_groups = {} # name -> StudyGroupDefinitionNode
        self.subgroups = {}    # name -> StudySubGroupDefinitionNode
        self.rooms = {}     # name -> RoomDefinitionNode
        self.assignments = [] # List[AssignmentNode]

        # Semester info (consolidated)
        self.semester_info = {
            'name': None,
            'start_date': None,
            'end_date': None,
            'duration_weeks': None, # or days
            'holidays': []
        }

    @property
    def start_date(self): return self.semester_info['start_date']
    @property
    def end_date(self): return self.semester_info['end_date']
    @property
    def holidays(self): return self.semester_info['holidays']

    def add(self, node):
        if isinstance(node, DayDefinitionNode):
            self.days[node.name] = node
        elif isinstance(node, SlotDefinitionNode):
            self.slots[node.slot_id] = node
        elif isinstance(node, TeacherDefinitionNode):
            self.teachers[node.name] = node
        elif isinstance(node, SubjectDefinitionNode):
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

    def __repr__(self):
        return f"Schedule(days={len(self.days)}, slots={len(self.slots)}, teachers={len(self.teachers)}, subjects={len(self.subjects)}, study_groups={len(self.study_groups)}, subgroups={len(self.subgroups)}, rooms={len(self.rooms)}, assignments={len(self.assignments)})"
