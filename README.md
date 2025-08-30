# legislatie-just-ro-parser

`leropa` reads legal documents from
[legislatie.just.ro](https://legislatie.just.ro/) and converts them into
structured data. It fetches documents on demand, caches the retrieved HTML and
parses it with BeautifulSoup into a hierarchy that includes metadata,
books, titles, chapters, sections, articles, paragraphs and notes, along with
the document's consolidation history. Sections whose titles use numeric
patterns such as ``1.2.3`` are nested under their numeric parents and expose a
``level`` attribute that reflects their depth in the hierarchy.

The resulting structure can be exported as JSON, YAML or XLSX. Spreadsheet
exports place each type of data on its own worksheet. Articles already
converted to JSON can be turned into Markdown for large language models, and
the package provides a retrieval-augmented generation (RAG) workflow that uses
Qdrant and Ollama for semantic search and question answering. An optional
FastAPI web application exposes the same capabilities over HTTP.

## Installation

Requires Python 3.11 or newer.

```bash
pip install leropa
```

Optional extras install additional features:

- `pip install leropa[llm]` – RAG commands and Markdown exporter.
- `pip install leropa[fastapi]` – FastAPI web interface.
- `pip install leropa[orjson]` – faster JSON serialization.
- `pip install leropa[dev]` – development dependencies.

## Command Line Usage

The package installs a console script named `leropa` with several commands.
The `convert` command retrieves a document by its identifier and prints the
structured representation as JSON:

```bash
leropa convert 123456
```

Downloaded HTML is cached in the user home directory to speed up subsequent
conversions. Use `--cache-dir` to specify a different location.

You can change the output format or write the result to a file:

```bash
leropa convert 123456 --format yaml --output data.yaml
leropa convert 123456 --format xlsx --output sheets.xlsx
```

When `--output` points to a directory the file name is derived from the document
identifier.

Other useful commands include:

```bash
# Export existing JSON/JSONL articles to Markdown
leropa export-md input_dir output_dir

# List locally available LLM model modules
leropa models

# Start the FastAPI application (requires [fastapi] extras)
leropa web --reload

# Manage a Qdrant/Ollama RAG pipeline (requires [llm] extras)
leropa rag recreate          # create or reset the collection
leropa rag ingest data/      # ingest JSON articles
leropa rag search "terms"   # semantic search
leropa rag ask "question"    # answer with context
```

## Library Usage

The parser can also be used programmatically:

```python
from leropa import parser

doc = parser.fetch_document("123456")
```

## Output Structure

The parser returns a dictionary containing metadata and the document body:

```js
{
    "document": ..., 
    "books": [...],
    "articles": [...]
}
```

### The document

Stores general information about the document version:

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

### The book

Groups titles, chapters, sections and articles:

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

### The title

Groups chapters, sections and articles:

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

### The chapter

Groups sections and articles:

```js
{
    "chapter_id": "...",
    "title": "...",
    "description": "...",
    "sections": [...],
    "articles": ["id_...", ...]
}
```

### The section

Groups subsections and articles:

```js
{
    "section_id": "...",
    "title": "...",
    "description": "...",
    "subsections": [...],
    "articles": ["id_...", ...]
}
```

### The subsection

Groups articles inside a section:

```js
{
    "subsection_id": "...",
    "title": "...",
    "description": "...",
    "articles": ["id_...", ...]
}
```

### The article

Contains the identifier, label, full text and its components:

```js
{
    "article_id": "...",
    "label": "...",
    "full_text": "...",
    "paragraphs": [...],
    "notes": [...]
}
```

### The paragraph

Represents an individual paragraph of an article:

```js
{
    "par_id": "...",
    "text": "...",
    "label": "...",
    "subparagraphs": [...],
    "notes": [...]
}
```

### The sub-paragraph

Lettered or numbered sub-paragraph:

```js
{
    "sub_id": "...",
    "label": "...",
    "text": "..."
}
```

### The note

Amendment note attached to an article or paragraph:

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
