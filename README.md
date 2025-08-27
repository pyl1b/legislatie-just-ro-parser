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

The top level object for each document level version is a dictionary
with the following keys:

```js
{
    "document": ...,
    "articles": [
        ...
    ]
}
```

### The document

The document object is a dictionary that stores general information about the
document version from which the data was extracted:

```js
{
    "source": "https://legislatie.just.ro/Public/DetaliiDocument/...",
    "ver_id": "...",
    "prev_ver": "...",
    "next_ver": "..."
}
```

### The article

Each article object is a dictionary with the following structure:

```js
{
    "article_id": "...",
    "full_text": "...",
    "paragraphs": [
        {"par_id": "id_...", "text": "..."},
        {"par_id": "id_...", "text": "..."},
    ]
}
```
