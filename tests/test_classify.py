from newsstore.enrich.classify import classify_kind


def test_digest_more_suffix():
    assert classify_kind("SpaceX IPO, US Vows Interim Deal Will Reopen Hormuz, More") == "digest"


def test_digest_podcast():
    assert classify_kind("Balance of Power: SpaceX Jumps After Record IPO (Podcast)") == "digest"


def test_spam_lawfirm():
    assert classify_kind("FS KKR CAPITAL ALERT: Bragar Eagel Reminds Investors",
                         "lead plaintiff role with the firm") == "spam"


def test_spam_clickbait():
    assert classify_kind("$1000 Invested In KLA 15 Years Ago Would Be Worth This Much Today") == "spam"


def test_normal_story():
    assert classify_kind("Fed holds rates steady amid inflation concerns",
                         "The Federal Reserve kept rates unchanged.") == "story"
