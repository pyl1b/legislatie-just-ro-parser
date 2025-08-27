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
            <span class="S_LIT_BDY" id="id_lit2a_bdy">First subparagraph.</span>
        </span>
        <span class="S_LIT" id="id_lit2b">
            <span class="S_LIT_TTL" id="id_lit2b_ttl">b)</span>
            <span class="S_LIT_BDY" id="id_lit2b_bdy">Second subparagraph.</span>
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
    second_par = article["paragraphs"][1]
    assert second_par["text"] == "Second paragraph."
    assert len(second_par["subparagraphs"]) == 2
    assert second_par["subparagraphs"][0]["label"] == "a)"
    assert second_par["subparagraphs"][0]["text"] == "First subparagraph."
