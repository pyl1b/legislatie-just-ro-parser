# Agent Rules

## Goals

- Generate fully-typed, tested Python code for this repo.
- Maintain compatibility with Python 3.12.
- The main way this code is used is through the console. It can also be used
  as a library.
- Read content from `https://legislatie.just.ro/Public/DetaliiDocument/$document_id`
  if the document is not already in the local cache.
- Parse the content of the document and store the structured data into yaml
  files.

## Do

- Use `ruff` formatting; run `make format`.
- Add/extend tests in `tests/` for every new module.
- Prefer stdlib and these libs only: requests, pydantic, click, attrs.
- Module names, function names and method names use snake_case.
- Class names use PascalCase.
- Qt signals use camelCase.
- Use Google-style docstrings.
- The docstring always starts with a short sentence that describes the
  purpose, on the same line as the three quote marks that start the docstring.
  It is followed by an empty line and other paragraphs for more
  detailed explanation of the purpose and workings.
- Each module, class, function or method should have a docstring describing its
  purpose.
- Each function or method should have its parameters described in docstrings
  in a section called `Args:`.
- Each function or method that returns a value should describe that value
  in docstrings in a section called `Returns:`.
- Each function or method that explicitly throws an exception describe that
  in docstrings in a section called `Throws:`.
- Each class should document all the attributes in the docstring of the class
  in a sec'ion called `Attributes:`. The Attributes defined using @property
  are documented in the docstring of the property, not inside the class
  docstring.
- Docstrings should not include type information when describing the arguments,
  attributes or the results.
- Any type has composed types (lists, dictionaries, tuples, etc) inside
  another complex type should be defined at the top of the module, after the
  imports.
- In code body use noumerous comments to describe what the line or goup of
  lines does. Place these comments above the said line of code and add an empty
  line before the comment.
  
## Don't

- Don't change public APIs without updating `CHANGELOG.md`.
- Don't introduce new deps without editing `pyproject.toml`.
- Don't read or write to the network during tests.

## Commands

- Test: `make test`
- Lint: `make lint` to discover errors
- De-lint: `make delint` to fix errors
