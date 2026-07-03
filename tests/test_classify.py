from newsstore.contracts.classify import classify_kind


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


def test_kbo_inside_english_word_not_sports():
    # 'kbo'가 경계 없이 매칭되면 checkbook/backbone 등 흔한 영단어를 오분류한다
    assert classify_kind("Buffett's checkbook is ready for big deals") == "story"
    assert classify_kind("AI is the backbone of the new economy") == "story"
    assert classify_kind("Workbook apps rally after earnings") == "story"


def test_kbo_korean_compound_still_sports():
    # 'KBO리그'처럼 뒤에 한글이 붙는 복합어는 계속 잡아야 한다(선행 경계만 요구)
    assert classify_kind("KBO리그 개막전 매진 행렬") == "sports"
    assert classify_kind("KBO 정규시즌 개막") == "sports"


def test_body_only_spam_signal_not_flagged():
    # #19: 본문에만 있는 스팸 신호로 멀쩡한 기사를 spam 처리하지 않는다(제목 기준)
    assert classify_kind("Fed holds rates steady amid inflation",
                         "a class action lawsuit was also mentioned") == "story"


def test_body_only_sports_signal_not_flagged():
    # #19: 본문에만 있는 스포츠 신호도 오분류하지 않는다
    assert classify_kind("Markets rally on strong tech earnings",
                         "separately, the world cup final aired last night") == "story"


def test_title_signal_still_classified():
    # 제목에 신호가 있으면 여전히 분류(회귀 가드)
    assert classify_kind("Bragar Eagel Reminds Investors of deadline") == "spam"
    assert classify_kind("Tottenham win the Premier League") == "sports"
