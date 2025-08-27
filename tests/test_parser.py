"""Tests for the document parser."""

from leropa import parser

SAMPLE_HTML = """
<span class="S_ART" id="id_art1">
    <span class="S_ART_TTL" id="id_art1_ttl">Articolul 1</span>
    <span class="S_ART_BDY" id="id_art1_bdy">
        <span class="S_PAR" id="id_par1">First paragraph.</span>
        <span class="S_ALN" id="id_par2">
            <span class="S_ALN_TTL" id="id_par2_ttl">(1)</span>
            <span class="S_ALN_BDY" id="id_par2_bdy">Second paragraph.</span>
        </span>
        <span class="S_LIT" id="id_lit2a">
            <span class="S_LIT_TTL" id="id_lit2a_ttl">a)</span>
            <span class="S_LIT_BDY" id="id_lit2a_bdy">
                First subparagraph.
            </span>
        </span>
        <span class="S_LIT" id="id_lit2b">
            <span class="S_LIT_TTL" id="id_lit2b_ttl">b)</span>
            <span class="S_LIT_BDY" id="id_lit2b_bdy">
                Second subparagraph.
            </span>
        </span>
    </span>
</span>
"""

# Full HTML document including metadata for testing document info extraction.
SAMPLE_HTML_WITH_META = f"""
<html>
  <head>
    <title>Sample Document</title>
    <meta name="description" content="Sample description">
    <meta name="keywords" content="kw1, kw2">
  </head>
  <body>{SAMPLE_HTML}</body>
</html>
"""


SAMPLE_HTML_BODY_LABEL = """
<span class="S_ART" id="id_art2">
    <span class="S_ART_TTL" id="id_art2_ttl">Articolul 2</span>
    <span class="S_ART_BDY" id="id_art2_bdy">
        <span class="S_PAR" id="id_par3">Main paragraph.</span>
        <span class="S_LIT" id="id_lit3a">
            <span class="S_LIT_TTL" id="id_lit3a_ttl"></span>
            <span class="S_LIT_BDY" id="id_lit3a_bdy">
                a) Lettered item.
            </span>
        </span>
        <span class="S_LIT" id="id_lit3b">
            <span class="S_LIT_TTL" id="id_lit3b_ttl"></span>
            <span class="S_LIT_BDY" id="id_lit3b_bdy">
                (1) Numbered item.
            </span>
        </span>
    </span>
</span>
"""


SAMPLE_HTML_WITH_NOTES = """
<span class="S_ART" id="id_art_notes">
    <span class="S_ART_TTL" id="id_art_notes_ttl">Articolul 3</span>
    <span class="S_ART_BDY" id="id_art_notes_bdy">
        <span class="S_ALN" id="id_par_note">
            <span class="S_ALN_TTL" id="id_par_note_ttl">(1)</span>
            <span class="S_ALN_BDY" id="id_par_note_bdy">
                Paragraph text.
                <span class="S_PAR" id="id_note_par">
                    (la 01-01-2020, paragraph changed)
                </span>
            </span>
        </span>
        <span class="S_NTA" id="id_note_art">
            <span class="S_NTA_TTL">Notă</span>
            <span class="S_NTA_PAR">Article note.</span>
        </span>
    </span>
</span>
"""


SAMPLE_HTML_WITH_HISTORY = """
<html>
  <body>
    <div id="istoric_fa">
      <a title='Consolidarea din 02.07.2010'
         href='~/../../../Public/DetaliiDocument/120341'>02.07.2010</a>
      <a title='Consolidarea din 12.11.2009'
         href='~/../../../Public/DetaliiDocument/113617'>12.11.2009</a>
    </div>
  </body>
</html>
"""


def test_parse_html_extracts_articles() -> None:
    doc = parser.parse_html(SAMPLE_HTML, "123")
    assert doc["document"]["ver_id"] == "123"
    assert len(doc["articles"]) == 1
    article = doc["articles"][0]
    assert article["article_id"] == "id_art1"
    assert len(article["paragraphs"]) == 2
    assert article["paragraphs"][0]["text"] == "First paragraph."
    assert article["paragraphs"][0]["label"] is None
    second_par = article["paragraphs"][1]
    assert second_par["text"] == "Second paragraph."
    assert second_par["label"] == "(1)"
    assert len(second_par["subparagraphs"]) == 2
    assert second_par["subparagraphs"][0]["label"] == "a)"
    assert second_par["subparagraphs"][0]["text"] == "First subparagraph."


def test_labels_from_body_text() -> None:
    doc = parser.parse_html(SAMPLE_HTML_BODY_LABEL, "456")
    article = doc["articles"][0]
    paragraph = article["paragraphs"][0]
    sub_a = paragraph["subparagraphs"][0]
    assert sub_a["label"] == "a)"
    assert sub_a["text"] == "Lettered item."
    sub_b = paragraph["subparagraphs"][1]
    assert sub_b["label"] == "(1)"
    assert sub_b["text"] == "Numbered item."


def test_metadata_extraction() -> None:
    doc = parser.parse_html(SAMPLE_HTML_WITH_META, "789")
    info = doc["document"]
    assert info["title"] == "Sample Document"
    assert info["description"] == "Sample description"
    assert info["keywords"] == "kw1, kw2"


def test_parse_notes() -> None:
    doc = parser.parse_html(SAMPLE_HTML_WITH_NOTES, "999")
    article = doc["articles"][0]
    paragraph = article["paragraphs"][0]

    assert paragraph["text"].strip() == "Paragraph text."
    assert (
        paragraph["notes"][0]["text"] == "(la 01-01-2020, paragraph changed)"
    )
    assert paragraph["notes"][0]["note_id"] == "id_note_par"

    assert article["notes"][0]["text"] == "Article note."
    assert article["notes"][0]["note_id"] == "id_note_art"


def test_version_history_extraction() -> None:
    doc = parser.parse_html(SAMPLE_HTML_WITH_HISTORY, "321")
    info = doc["document"]
    assert info["history"][0]["ver_id"] == "120341"
    assert info["history"][0]["date"] == "02.07.2010"
    assert info["prev_ver"] == "120341"
    assert info["history"][1]["ver_id"] == "113617"
