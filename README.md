# legislatie-just-ro-parser

The purpose of this library is to read legal documents from
[legislatie.just.ro](https://legislatie.just.ro/) and convert them into
structured data.

The user provides the unique ID the legal document version that needs to be
converted. The library look into the local cache to see if that document
has already been downloaded and, if not, it retrieves the html source for it
using the requests library.

The content is then stripped of css and js, and what is left is parsed into
the structure defined below.

The output can be saved into json or yaml formats.

## Command Line Usage

The package installs a console script named `leropa`. The `convert` command
retrieves a document by its identifier and prints the structured representation
as JSON:

```bash
leropa convert 123456
```

The command caches downloaded HTML in the user home directory to speed up
subsequent conversions.

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
