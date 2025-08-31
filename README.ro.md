# legislatie-just-ro-parser

[English](README.md) | Română

`leropa` citește documente legale de pe [legislatie.just.ro](https://legislatie.just.ro/) și le convertește în date structurate. Documentele sunt preluate la cerere, HTML-ul este memorat în cache și parsat cu BeautifulSoup într-o ierarhie ce include metadate, cărți, titluri, capitole, secțiuni, articole, paragrafe și note, împreună cu istoricul de consolidare al documentului. Secțiunile ale căror titluri folosesc modele numerice precum `1.2.3` sunt plasate sub părinții lor numerici și expun un atribut `level` ce reflectă adâncimea în ierarhie.

Structura rezultată poate fi exportată ca JSON, YAML sau XLSX. Exporturile către foi de calcul plasează fiecare tip de date pe un worksheet separat. Articolele deja convertite în JSON pot fi transformate în Markdown pentru modele de limbaj, iar pachetul oferă un flux de lucru RAG (retrieval-augmented generation) care folosește Qdrant și Ollama pentru căutare semantică și întrebări-răspuns. O aplicație FastAPI opțională expune aceleași capabilități prin HTTP.

## Instalare

Necesită Python 3.11 sau mai nou.

```bash
pip install leropa
```

Opțional, se pot instala extra dependențe pentru funcționalități suplimentare:

- `pip install leropa[llm]` – comenzi RAG și exportator Markdown.
- `pip install leropa[fastapi]` – interfață web FastAPI.
- `pip install leropa[orjson]` – serializare JSON mai rapidă.
- `pip install leropa[dev]` – dependențe pentru dezvoltare.

## Utilizare din linia de comandă

Pachetul instalează un script `leropa` cu mai multe comenzi. Comanda `convert` preia un document după identificator și afișează reprezentarea structurată ca JSON:

```bash
leropa convert 123456
```

HTML-ul descărcat este memorat în directorul home al utilizatorului pentru a accelera conversiile ulterioare. Folosiți `--cache-dir` pentru a specifica o altă locație.

Puteți schimba formatul de ieșire sau salva rezultatul într-un fișier:

```bash
leropa convert 123456 --format yaml --output date.yaml
leropa convert 123456 --format xlsx --output foi.xlsx
```

Când `--output` indică un director, numele fișierului este derivat din identificatorul documentului.

Alte comenzi utile includ:

```bash
# Exportă articole JSON/JSONL existente în Markdown
leropa export-md input_dir output_dir

# Listează modulele de modele LLM disponibile local
leropa models

# Pornește aplicația FastAPI (necesită extra [fastapi])
leropa web --reload

# Gestionează un pipeline RAG Qdrant/Ollama (necesită extra [llm])
leropa rag recreate          # creează sau resetează colecția
leropa rag ingest data/      # încarcă articole JSON
leropa rag search "termeni"   # căutare semantică
leropa rag ask "întrebare"    # răspunde cu context
```

## Utilizare ca bibliotecă

Parserul poate fi folosit și programatic:

```python
from leropa import parser

doc = parser.fetch_document("123456")
```

## Structura de ieșire

Parserul returnează un dicționar ce conține metadate și corpul documentului:

```js
{
    "document": ...,
    "books": [...],
    "articles": [...]
}
```

### Documentul

Stochează informații generale despre versiunea documentului:

```js
{
    "source": "https://legislatie.just.ro/Public/DetaliiDocument/...",
    "ver_id": "...",
    "title": "...",
    "description": "...",
    "keywords": "...",
    "history": [
        {"ver_id": "...", "date": "..."},
        ...
    ],
    "prev_ver": "...",
    "next_ver": "..."
}
```

### Cartea

Grupează titluri, capitole, secțiuni și articole:

```js
{
    "book_id": "...",
    "title": "...",
    "description": "...",
    "titles": [...],
    "chapters": [...],
    "sections": [...],
    "articles": ["id_...", ...]
}
```

### Titlul

Grupează capitole, secțiuni și articole:

```js
{
    "title_id": "...",
    "title": "...",
    "description": "...",
    "chapters": [...],
    "sections": [...],
    "articles": ["id_...", ...]
}
```

### Capitolul

Grupează secțiuni și articole:

```js
{
    "chapter_id": "...",
    "title": "...",
    "description": "...",
    "sections": [...],
    "articles": ["id_...", ...]
}
```

### Secțiunea

Grupează subsecțiuni și articole:

```js
{
    "section_id": "...",
    "title": "...",
    "description": "...",
    "subsections": [...],
    "articles": ["id_...", ...]
}
```

### Subsecțiunea

Grupează articole în interiorul unei secțiuni:

```js
{
    "subsection_id": "...",
    "title": "...",
    "description": "...",
    "articles": ["id_...", ...]
}
```

### Articolul

Conține identificatorul, eticheta, textul complet și componentele acestuia:

```js
{
    "article_id": "...",
    "label": "...",
    "full_text": "...",
    "paragraphs": [...],
    "notes": [...]
}
```

### Paragraful

Reprezintă un paragraf individual al unui articol:

```js
{
    "par_id": "...",
    "text": "...",
    "label": "...",
    "subparagraphs": [...],
    "notes": [...]
}
```

### Subparagraful

Paragraf literă sau numerotat:

```js
{
    "sub_id": "...",
    "label": "...",
    "text": "..."
}
```

### Nota

Notă de modificare atașată unui articol sau paragraf:

```js
{
    "note_id": "...",
    "text": "...",
    "date": "...",
    "subject": "...",
    "law_number": "...",
    "law_date": "...",
    "monitor_number": "...",
    "monitor_date": "...",
    "replaced": "...",
    "replacement": "..."
}
```
