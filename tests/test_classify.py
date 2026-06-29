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


def test_sports_kbo():
    assert classify_kind("KBO 한국시리즈 1차전, LG 트윈스 끝내기 승리") == "sports"


def test_sports_epl():
    assert classify_kind("Tottenham beat Arsenal in the Premier League derby") == "sports"


def test_finance_not_flagged_sports():
    # 금융 기사는 sports로 오분류되면 안 됨 (느슨한 시그널 추가 시 회귀 가드)
    assert classify_kind("Global bond yields climb as central banks signal caution") == "story"
