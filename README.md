# legislatie-just-ro-parser

`leropa` reads legal documents from
[legislatie.just.ro](https://legislatie.just.ro/) and converts them into
structured data. It fetches documents on demand, caches the retrieved HTML and
parses it with BeautifulSoup into a hierarchy that includes metadata,
books, titles, chapters, sections, articles, paragraphs and notes, along with
the document's consolidation history.

The resulting structure can be exported as JSON, YAML or XLSX. Spreadsheet
exports place each type of data on its own worksheet.

## Installation

Requires Python 3.11 or newer.

```bash
pip install leropa
```

## Command Line Usage

The package installs a console script named `leropa`. The `convert` command
retrieves a document by its identifier and prints the structured representation
as JSON:

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

Contains the full text and its components:

```js
{
    "article_id": "...",
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
