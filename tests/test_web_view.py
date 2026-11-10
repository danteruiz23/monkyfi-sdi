"""Phase 3 web view (D45, D47): no hardcoded strings, every key it uses exists in both locales, and
the stage rules it reads are the 11 stages of SPEC section 6 with equal weights.

Rendering is checked with Node, from web/:  npm run build && npm run render-check
"""

import re

from conftest import ROOT, load

WEB = ROOT / "web"
SOURCES = sorted(p for d in ("app", "lib") for p in (WEB / d).rglob("*.ts*"))
EN, ES = load(ROOT / "locales" / "en.json"), load(ROOT / "locales" / "es.json")
JSX_TEXT = re.compile(r">([^<>{}]*[A-Za-zÀ-ÿ]{2,}[^<>{}]*)<")
TEXT_ATTRIBUTE = re.compile(r'\b(?:title|alt|placeholder|aria-label|label)="([^"]*[A-Za-z]{2,}[^"]*)"')
KEY = re.compile(r'\bt\(\s*["`]([a-z_]+\.[A-Za-z0-9_.${}\- ]+?)["`]')
STAGES = ["presales", "order_received", "order_validated", "design_and_dependencies", "provisioning",
          "ready_for_testing", "testing_completed", "delivered_pending_acceptance", "accepted", "hypercare", "closed"]


def strip_comments(source: str) -> str:
    source = re.sub(r"/\*.*?\*/", "", source, flags=re.S)
    return re.sub(r"^\s*//.*$", "", source, flags=re.M)


def test_view_sources_exist():
    assert len([p for p in SOURCES if p.suffix == ".tsx"]) >= 3


def test_no_hardcoded_user_facing_strings():
    for path in SOURCES:
        if path.suffix != ".tsx":
            continue
        source = strip_comments(path.read_text(encoding="utf-8"))
        # Type annotations such as Promise<{ lang: string }> are not JSX text.
        texts = [m for m in JSX_TEXT.findall(source) if "=>" not in m and ":" not in m and ";" not in m]
        assert not texts, f"{path.name}: text outside locales/: {texts}"
        assert not TEXT_ATTRIBUTE.findall(source), f"{path.name}: text attribute outside locales/"


def test_every_key_used_by_the_view_exists_in_both_locales():
    used = set()
    for path in SOURCES:
        used |= set(KEY.findall(path.read_text(encoding="utf-8")))
    assert len(used) > 50
    for key in used:
        area, _, name = key.partition(".")
        for locale in (EN, ES):
            assert area in locale, key
            if "${" not in name:
                assert name in locale[area], key


def test_stage_rules_are_the_11_stages_with_equal_weights():
    stages = load(ROOT / "rules" / "stages.json")["stages"]
    assert [s["key"] for s in stages] == STAGES
    assert {s["weight"] for s in stages} == {1}
    assert [s["key"] for s in stages if s.get("assumed_complete")] == ["presales"]  # D47
    assert stages[1]["exit_gate"] == "G1"
    for locale in (EN, ES):
        assert set(locale["stage"]) == set(STAGES)
        assert set(locale["stage_assumption"]) == {s["assumed_complete"] for s in stages if s.get("assumed_complete")}
        groups = {f["group"] for name in ("fields.common.json", "fields.epl.json", "fields.wavelength.json")
                  for f in load(ROOT / "rules" / name)["fields"]}
        assert groups | {"customer_scoping"} <= set(locale["field_group"])


def test_view_is_read_only_and_shows_the_synthetic_mark():
    layout = (WEB / "app" / "[lang]" / "layout.tsx").read_text(encoding="utf-8")
    assert 't("app.synthetic_mark")' in layout
    everything = "\n".join(strip_comments(p.read_text(encoding="utf-8")) for p in SOURCES)
    for forbidden in ("writeFile", "appendFile", "unlink", "fetch(", '"use server"', "<form", "method=\"post\""):
        assert forbidden not in everything, forbidden
