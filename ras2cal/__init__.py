"""
ras2cal - Kompajler za raspored nastave (RAS DSL)

Pipeline:  .ras fajl -> Lexer -> Parser -> AST -> Compiler -> IR -> Generatori

Modul ne sadrzi nikakve podrazumijevane vrijednosti (tipovi nastave,
vremena termina, itd). Sva konfiguracija dolazi iz pozivatelja (tt2cal.py).

Autor: Ernedin Zajko <ezajko@root.ba>
"""
