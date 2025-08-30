# Changes

## Unreleased

- Replace regex-based parser with BeautifulSoup implementation.
- Add `convert` command to the CLI.
- Support writing `convert` output to files.
- Add YAML and XLSX output formats for `convert` command.
- Allow `--output` to accept directories and compute file name from `ver_id`.
- Parse sub-paragraphs labelled with letters within paragraphs.
- Capture document metadata (title, description, keywords) in the parser.
- Extract amendment notes for articles and paragraphs.
- Parse consolidation history and expose previous versions.
- Parse books, titles and chapters linking articles accordingly.
- Handle numbered paragraphs marked with ``S_LIT`` tags.
- Ignore hidden ``S_LIT_SHORT`` placeholders to avoid stray ellipsis in text.
- Represent article lists with article identifiers instead of full articles.
- Include sub-paragraph text in the article ``full_text`` field.
- Generate default hierarchy when chapters or sections lack parent books.
- Export each data type to its own PascalCase sheet in XLSX output with
  parent-child identifiers and Excel tables.
- Detect numeric section titles, assigning a ``level`` and nesting child
  sections under their parents.
- Include article labels parsed from ``S_ART_TTL`` without the ``Articolul``
  prefix.
- Allow `rag_legal_qdrant` to ingest parser outputs and remove its argparse CLI.
- Add optional FastAPI module exposing CLI commands as HTTP endpoints.
- List available LLM models and allow selecting the model via CLI and web API.
- Expose endpoints to list and view structured documents via FastAPI.
- Add `web` command to start FastAPI with Uvicorn.
