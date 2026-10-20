# Validador LER — Etapa 1

Analizador léxico del Lenguaje de Eventos de Reparto (LER) para eventos logísticos de última milla en Lima Metropolitana. Curso Teoría de la Computación 2026-02.

- Backend: Python + Flask (`app.py`, `lexer.py` con el módulo `re`)
- Frontend: HTML/CSS/JS (`templates/`, `static/`)
- Entrada: texto manual, archivo `.txt` o ejemplo precargado

## Ejecutar
```
python -m venv .venv && .venv/bin/pip install -r requirements.txt
.venv/bin/python app.py
```
Pruebas: `.venv/bin/pip install pytest && .venv/bin/pytest`

Desplegable en Vercel (detecta `app.py` automáticamente).
