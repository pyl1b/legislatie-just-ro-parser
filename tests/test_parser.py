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


SAMPLE_HTML_STRUCTURE = """
<span class="S_CRT_TTL" id="id_book1_ttl">Cartea I</span>
<span class="S_CRT_DEN">Book description</span>
<span class="S_CRT_BDY" id="id_book1_bdy">
    <span class="S_TTL_TTL" id="id_title1_ttl">Titlul I</span>
    <span class="S_TTL_DEN">Title description</span>
    <span class="S_TTL_BDY" id="id_title1_bdy">
        <span class="S_CAP_TTL" id="id_chap1_ttl">Capitolul I</span>
        <span class="S_CAP_DEN">Chapter description</span>
        <span class="S_CAP_BDY" id="id_chap1_bdy">
            <span class="S_ART" id="id_art1">
                <span class="S_ART_TTL" id="id_art1_ttl">Articolul 1</span>
                <span class="S_ART_BDY" id="id_art1_bdy">
                    <span class="S_PAR" id="id_par1">Paragraph.</span>
                </span>
            </span>
        </span>
    </span>
</span>
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


SAMPLE_HTML_LIT_PARAGRAPHS = """
<span class="S_ART" id="id_art_lit">
    <span class="S_ART_TTL" id="id_art_lit_ttl">Articolul LIT</span>
    <span class="S_ART_BDY" id="id_art_lit_bdy">
        <span class="S_LIT" id="id_lit_par1">
            <span class="S_LIT_BDY" id="id_lit_par1_bdy">
                (1) Intro paragraph.
            </span>
        </span>
        <span class="S_LIT" id="id_lit_sub1">
            <span class="S_LIT_BDY" id="id_lit_sub1_bdy">
                a) First item.
            </span>
        </span>
        <span class="S_LIT" id="id_lit_sub2">
            <span class="S_LIT_BDY" id="id_lit_sub2_bdy">
                b) Second item.
            </span>
        </span>
        <span class="S_LIT" id="id_lit_par2">
            <span class="S_LIT_BDY" id="id_lit_par2_bdy">
                (2) Second paragraph.
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
                    (la 01-01-2020,
                    Alin. (2) al art. 287 a fost modificat de art. IX din
                    LEGEA nr. 60 din 10 aprilie 2012, publicată în
                    MONITORUL OFICIAL nr. 255 din 17 aprilie 2012,
                    prin înlocuirea sintagmei "serviciul de stare civilă" cu
                    sintagma "serviciul public comunitar local de evidență a
                    persoanelor".
                    )
                </span>
            </span>
        </span>
        <span class="S_NTA" id="id_note_art">
            <span class="S_NTA_TTL">Notă</span>
            <span class="S_NTA_PAR">
                Article note.
            </span>
        </span>
    </span>
</span>
"""


SAMPLE_HTML_WITH_LINK = (
    '<span class="S_ART" id="id_art_link">'
    '    <span class="S_ART_TTL" id="id_art_link_ttl">Articolul Link</span>'
    '    <span class="S_ART_BDY" id="id_art_link_bdy">'
    '        <span class="S_LIT" id="id_lit_link">'
    '            <span class="S_LIT_BDY" id="id_lit_link_bdy">(1) '
    "Este anulabilă căsătoria încheiată fără "
    "încuviinţările sau autorizarea prevăzute la "
    "<a href='#'>art. 272</a> alin. (2), (4) şi (5).</span>"
    "        </span>"
    "    </span>"
    "</span>"
)


SAMPLE_HTML_WITH_SHORT = """
<span class="S_ART" id="id_art_short">
    <span class="S_ART_TTL" id="id_art_short_ttl">Articolul Short</span>
    <span class="S_ART_BDY" id="id_art_short_bdy">
        <span class="S_PAR" id="id_par_short">Intro paragraph.</span>
        <span class="S_LIT" id="id_lit_short">
            <span class="S_LIT_TTL" id="id_lit_short_ttl">a)</span>
            <span class="S_LIT_SHORT" id="id_lit_short_short"
                  style="display: none"> ... </span>
            <span class="S_LIT_BDY" id="id_lit_short_bdy">
                Subparagraph text.
            </span>
        </span>
    </span>
</span>
"""


SAMPLE_HTML_WITH_LINE_ITEMS = """
<span class="S_ART" id="id_art_lin">
    <span class="S_ART_TTL" id="id_art_lin_ttl">Articolul Lin</span>
    <span class="S_ART_BDY" id="id_art_lin_bdy">
        <span class="S_PAR" id="id_par_lin">
            Termeni utilizați:
            <span class="S_LIN" id="id_lin1">
                <span class="S_LIN_TTL" id="id_lin1_ttl">– </span>
                <span class="S_LIN_BDY" id="id_lin1_bdy">First item;</span>
                <span class="S_LIN_SHORT" id="id_lin1_short"
                      style="display: none"> ... </span>
            </span>
            <span class="S_LIN" id="id_lin2">
                <span class="S_LIN_TTL" id="id_lin2_ttl">– </span>
                <span class="S_LIN_BDY" id="id_lin2_bdy">Second item;</span>
            </span>
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


SAMPLE_HTML_WITH_SECTIONS = """
<span class="S_CRT_TTL" id="id_book1_ttl">Cartea I</span>
<span class="S_CRT_BDY" id="id_book1_bdy">
    <span class="S_CAP_TTL" id="id_chap1_ttl">Capitolul I</span>
    <span class="S_CAP_BDY" id="id_chap1_bdy">
        <span class="S_SEC_TTL" id="id_sec1_ttl">Secţiunea 1</span>
        <span class="S_SEC_BDY" id="id_sec1_bdy">
            <span class="S_SSEC_TTL" id="id_sub1_ttl">Paragraf 1</span>
            <span class="S_SSEC_BDY" id="id_sub1_bdy">
                <span class="S_ART" id="id_art1">
                    <span class="S_ART_TTL" id="id_art1_ttl">Articolul 1</span>
                    <span class="S_ART_BDY" id="id_art1_bdy">
                        <span class="S_PAR" id="id_par1">Paragraph.</span>
                    </span>
                </span>
            </span>
        </span>
    </span>
</span>
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


def test_s_lit_paragraphs() -> None:
    doc = parser.parse_html(SAMPLE_HTML_LIT_PARAGRAPHS, "101")
    article = doc["articles"][0]
    paragraphs = article["paragraphs"]
    assert len(paragraphs) == 2
    first_par = paragraphs[0]
    assert first_par["label"] == "(1)"
    assert first_par["text"] == "Intro paragraph."
    assert len(first_par["subparagraphs"]) == 2
    assert first_par["subparagraphs"][0]["label"] == "a)"
    assert first_par["subparagraphs"][0]["text"] == "First item."
    second_par = paragraphs[1]
    assert second_par["label"] == "(2)"
    assert second_par["text"] == "Second paragraph."


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
    note = paragraph["notes"][0]
    expected_text = (
        "(la 01-01-2020, Alin. (2) al art. 287 a fost modificat de "
        "art. IX din LEGEA nr. 60 din 10 aprilie 2012, publicată în "
        "MONITORUL OFICIAL nr. 255 din 17 aprilie 2012, prin "
        'înlocuirea sintagmei "serviciul de stare civilă" cu '
        'sintagma "serviciul public comunitar local de evidență a '
        'persoanelor".)'
    )
    assert note["text"] == expected_text
    assert note["note_id"] == "id_note_par"
    assert note["date"] == "01-01-2020"
    assert note["subject"] == "Alin. (2) al art. 287"
    assert note["law_number"] == "60"
    assert note["law_date"] == "10 aprilie 2012"
    assert note["monitor_number"] == "255"
    assert note["monitor_date"] == "17 aprilie 2012"
    assert note["replaced"] == "serviciul de stare civilă"
    assert (
        note["replacement"]
        == "serviciul public comunitar local de evidență a persoanelor"
    )

    art_note = article["notes"][0]
    assert art_note["text"] == "Article note."
    assert art_note["note_id"] == "id_note_art"
    assert art_note["date"] is None
    assert art_note["law_number"] is None


def test_preserves_space_around_links() -> None:
    """Ensure spaces are preserved when parsing inline links."""

    doc = parser.parse_html(SAMPLE_HTML_WITH_LINK, "314")
    paragraph = doc["articles"][0]["paragraphs"][0]
    expected = (
        "Este anulabilă căsătoria încheiată fără încuviinţările "
        "sau autorizarea prevăzute la art. 272 alin. (2), (4) şi (5)."
    )
    assert paragraph["label"] == "(1)"
    assert paragraph["text"] == expected


def test_removes_short_span() -> None:
    """Ignore hidden short spans that only contain ellipsis."""

    doc = parser.parse_html(SAMPLE_HTML_WITH_SHORT, "515")
    article = doc["articles"][0]
    assert article["full_text"] == "Intro paragraph. a) Subparagraph text."
    paragraph = article["paragraphs"][0]
    assert paragraph["subparagraphs"][0]["text"] == "Subparagraph text."
    assert "..." not in article["full_text"]


def test_line_items_become_subparagraphs() -> None:
    """Convert line items into subparagraphs."""

    doc = parser.parse_html(SAMPLE_HTML_WITH_LINE_ITEMS, "616")
    article = doc["articles"][0]
    paragraph = article["paragraphs"][0]
    assert paragraph["text"] == "Termeni utilizați:"
    assert len(paragraph["subparagraphs"]) == 2
    first = paragraph["subparagraphs"][0]
    assert first["label"] == "–"
    assert first["text"] == "First item;"


def test_version_history_extraction() -> None:
    doc = parser.parse_html(SAMPLE_HTML_WITH_HISTORY, "321")
    info = doc["document"]
    assert info["history"][0]["ver_id"] == "120341"
    assert info["history"][0]["date"] == "02.07.2010"
    assert info["prev_ver"] == "120341"
    assert info["history"][1]["ver_id"] == "113617"


def test_hierarchical_parsing() -> None:
    doc = parser.parse_html(SAMPLE_HTML_STRUCTURE, "888")
    books = doc["books"]
    assert len(books) == 1
    book = books[0]
    assert book["book_id"] == "id_book1_bdy"
    assert book["titles"][0]["title_id"] == "id_title1_bdy"
    chapter = book["titles"][0]["chapters"][0]
    assert chapter["chapter_id"] == "id_chap1_bdy"
    assert chapter["articles"][0] == "id_art1"
    assert doc["articles"][0]["article_id"] == "id_art1"


def test_section_and_subsection_parsing() -> None:
    doc = parser.parse_html(SAMPLE_HTML_WITH_SECTIONS, "777")
    book = doc["books"][0]
    chapter = book["chapters"][0]
    section = chapter["sections"][0]
    assert section["section_id"] == "id_sec1_bdy"
    subsection = section["subsections"][0]
    assert subsection["subsection_id"] == "id_sub1_bdy"
    assert subsection["articles"][0] == "id_art1"
