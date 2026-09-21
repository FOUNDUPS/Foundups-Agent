from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PAGE = ROOT / "frontend" / "app" / "yumori" / "page.tsx"
QR = ROOT / "frontend" / "public" / "YUMORIme-qr-code.png"
PUBLIC_ASSET_README = ROOT / "frontend" / "public" / "README.md"


def source() -> str:
    return PAGE.read_text(encoding="utf-8")


def test_yumori_landing_exists_and_is_japanese_first() -> None:
    text = source()
    assert "YUMORI.me / 湯守" in text
    assert "I am a guardian" in text
    assert "日本の地域を守り、地域のAIをつくる。" in text
    assert "準備委員会の最初の目標：1,000人" in text
    assert "JOIN YUMORI.me / 湯守になる" in text


def test_yumori_language_switcher_has_complete_english_and_portuguese_copy() -> None:
    page = source()
    switcher = (ROOT / "frontend" / "components" / "LanguageSwitcher.tsx").read_text(encoding="utf-8")

    assert "new URLSearchParams(window.location.search).get('lang')" in switcher
    assert "window.localStorage.setItem('esingularity-language', next)" in switcher
    assert "document.documentElement.lang = language === 'pt' ? 'pt-BR' : language" in switcher
    for accessibility_label in ("言語を選択", "Language selection", "Seleção de idioma"):
        assert accessibility_label in switcher

    required_copy = {
        "日本の地域を守り、地域のAIをつくる。": (
            "Protect Japan’s communities. Build community-owned AI.",
            "Proteger as comunidades do Japão. Criar uma IA que pertença à comunidade.",
        ),
        "I am a guardian.": (
            "I am a guardian.",
            "Sou um guardião.",
        ),
        "湯守は、本来、湯と場所を守る人。YUMORI.meは、その考えを地域へ広げます。AIインフラは必要です。しかし、土地・電力・知識・文化の未来を、地域の外だけで決めさせない。知る。守る。そして別の形をつくる。": (
            "A yumori traditionally protects the hot spring and the place around it.",
            "Tradicionalmente, um yumori protege as águas termais e o lugar ao seu redor.",
        ),
        "ハイパースケールは、": (
            "Hyperscale is about more than",
            "A hiperescala envolve muito mais",
        ),
        "壊す前に調べる。": (
            "Investigate before demolishing.",
            "Investigar antes de demolir.",
        ),
        "データセンターを箱で終わらせない。": (
            "Do not let a data center remain just a box.",
            "Não deixar que um data center seja apenas uma caixa.",
        ),
        "地域を守る人が、地域の未来を決める。": (
            "The people who protect a community should shape its future.",
            "Quem protege uma comunidade deve ajudar a definir seu futuro.",
        ),
    }
    for japanese, translations in required_copy.items():
        assert japanese in page
        assert japanese in switcher
        for translation in translations:
            assert translation in switcher


def test_yumori_is_pro_community_compute_not_blanket_anti_dc() -> None:
    text = source()
    assert "YUMORIはデータセンターそのものに反対する運動ではありません" in text
    assert "地域の学校、大学、農業、病院、自治体、ものづくり、企業" in text
    assert "1MWから始め、地域需要に合わせて5→10→20MW" in text
    assert "地域の知" in text


def test_yumori_remains_the_join_first_three_panel_movement_funnel() -> None:
    text = source()
    why = "01 / WHY — KNOW WHAT IS COMING"
    what = "02 / WHAT — REUSE BEFORE DEMOLITION"
    how = "03 / HOW — TURN COMPUTE INTO REVITALIZATION"
    assert text.index(why) < text.index(what) < text.index(how)
    assert text.count("<Join") == 5
    assert "ACT / 1,000 YUMORI" in text


def test_yumori_connects_jhr_esingularity_and_join_form_without_embedding() -> None:
    text = source()
    assert "'/reports/jhr'" in text
    assert "Educational Singularity Lab" in text
    assert "docs.google.com/forms" in text
    assert "embedded=true" not in text
    assert "eSingularity / 福井の実証を見る" in text


def test_yumori_truth_boundary_uses_candidate_language() -> None:
    text = source()
    assert "成立する場所では" in text
    assert "技術検証する" in text
    assert "構想です" in text


def test_yumori_official_qr_asset_is_canonical_png() -> None:
    assert QR.is_file()
    assert QR.read_bytes()[:8] == b"\x89PNG\r\n\x1a\n"
    contract = PUBLIC_ASSET_README.read_text(encoding="utf-8")
    assert "YUMORIme-qr-code.png" in contract
    assert "https://YUMORI.me" in contract
    assert "official YUMORI.me QR-code asset" in contract
