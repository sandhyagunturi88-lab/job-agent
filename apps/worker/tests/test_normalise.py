from worker.normalise import detect_ir35, map_adzuna_contract, strip_html


def test_strip_html_handles_escaped_and_raw():
    assert strip_html("&lt;p&gt;Hello &amp; welcome&lt;/p&gt;") == "Hello & welcome"
    assert strip_html("<ul><li>Python</li><li>Postgres</li></ul>") == "Python Postgres"


def test_detect_ir35():
    assert detect_ir35("This role is Outside IR35.") is False
    assert detect_ir35("Engagement is inside IR 35") is True
    assert detect_ir35("A permanent role") is None


def test_map_adzuna_contract():
    assert map_adzuna_contract("permanent", "full_time") == "permanent"
    assert map_adzuna_contract("contract", None) == "contract"
    assert map_adzuna_contract("permanent", "part_time") == "part_time"
    assert map_adzuna_contract(None, None) is None
