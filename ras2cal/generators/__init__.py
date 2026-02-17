"""
generators - Izlazni generatori za raspored

Dostupni generatori:
    JSONScheduleGenerator  - JSON format za sync sa GWS kalendarom
    MarkdownReportGenerator - Markdown izvjestaj
    HTMLScheduleGenerator   - HTML po nastavnicima/predmetima/grupama/prostorijama
    GridGenerator           - Tradicionalni grid (tabelarni) HTML format
"""
from .grid_gen import GridGenerator
from .html_gen import HTMLScheduleGenerator
from .json_gen import JSONScheduleGenerator
from .md_gen import MarkdownReportGenerator
