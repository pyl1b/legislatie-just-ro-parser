from pathlib import Path
from unittest.mock import Mock, patch

from leropa import parser


def test_fetch_document_uses_cache(tmp_path: Path) -> None:
    """Fetches document from network only once and caches the HTML."""

    html = "<html><head><title>t</title></head><body></body></html>"
    ver_id = "123"
    response = Mock(text=html)

    with patch("requests.get", return_value=response) as mock_get:
        result = parser.fetch_document(ver_id, cache_dir=tmp_path)
        assert mock_get.called

    assert (tmp_path / "123.html").exists()
    assert result["document"]["ver_id"] == ver_id

    with patch("requests.get", return_value=response) as mock_get:
        parser.fetch_document(ver_id, cache_dir=tmp_path)
        mock_get.assert_not_called()
