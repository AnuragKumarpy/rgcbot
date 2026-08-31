from src.utils.text_formatter import escape_html, get_karma_tier, mention_html


def test_escape_html():
    assert escape_html("<b>Test & Fun</b>") == "&lt;b&gt;Test &amp; Fun&lt;/b&gt;"
    assert escape_html(None) == ""


def test_mention_html():
    mention = mention_html(12345, "Alice <Script>")
    assert 'href="tg://user?id=12345"' in mention
    assert "&lt;Script&gt;" in mention


def test_get_karma_tier():
    assert "Grandmaster" in get_karma_tier(6000)
    assert "Ascendant" in get_karma_tier(3000)
    assert "Vanguard" in get_karma_tier(1500)
    assert "Master" in get_karma_tier(600)
    assert "Initiate" in get_karma_tier(5)
    assert "Restricted" in get_karma_tier(-5)
