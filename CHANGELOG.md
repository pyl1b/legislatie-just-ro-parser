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
