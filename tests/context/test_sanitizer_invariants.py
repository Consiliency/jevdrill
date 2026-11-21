"""Acceptance invariants I1 to I7 of the context sanitizer.

`redact` returns its text unchanged or refuses it; docs/sanitization-contract.md discloses
the rule. Everything here is deterministic: fixed lists and `itertools.product`. A loop over
a product sits inside one test case and reports the combinations that failed.
"""

import base64
import itertools
import json
import math
import time
from pathlib import Path
from types import SimpleNamespace

import pytest

from jevdrill import context
from jevdrill.context import redact
from jevdrill.contracts import ContractError

ROOT = Path(__file__).resolve().parents[2]
MESSAGE = "credential-like material"
VALUE = "SYNTHETIC_SENTINEL"
ZERO_WIDTH_SPACE = "\u200b"
BREAKS = ("\r\n", "\r", "\n", "\x85", "\u2028", "\u2029")
LABEL_SPELLINGS = ("password", "Secret", "api key", "api-key", "apikey", "access token")
OPERATORS = (":", "=", "<-", "->")
MILLION = 1_000_000


def refused(text):
    """I1: `redact` returns the very string it was given or raises the one ContractError."""
    try:
        result = redact(text)
    except ContractError as error:
        assert type(error) is ContractError and error.args == (MESSAGE,), repr(text)
        return True
    assert result is text, repr(text)
    return False


@pytest.fixture(scope="module")
def matrix(request):
    """The conftest matrix as plain data.

    `credential_text` is a parametrized fixture, so requesting it would collect 2,520
    cases. Its definition is read instead, and the sizes are asserted so that a change in
    pytest or in conftest fails here rather than shrinking the matrix silently.
    """
    (definition,) = request.session._fixturemanager.getfixturedefs("credential_text", request.node)
    names = definition.func.__globals__
    texts = [entry if isinstance(entry, str) else entry.values[0] for entry in definition.params]
    assert (len(texts), len(names["FORMATS"]), len(names["LABELS"])) == (2520, 409, 6)
    labels = (*names["LABELS"], *LABEL_SPELLINGS)
    return SimpleNamespace(texts=texts, formats=names["FORMATS"], labels=labels)


def test_i1_i5_matrix_entries_are_returned_unchanged_or_refused_and_the_count_is_fixed(matrix):
    assert sum(refused(text) for text in matrix.texts) == 1104
    assert refused("") is False


def full_width(text):
    return "".join(chr(ord(char) + 0xFEE0) if "!" <= char <= "~" else char for char in text)


def first_letter(label, template):
    index = next(index for index, char in enumerate(label) if char.isalpha())
    return label[:index] + template % ord(label[index]) + label[index + 1 :]


def encoded(operator, template):
    return "".join(template % ord(char) for char in operator)


GAPS = (
    "",
    " ",
    '"',
    "**",
    "}{a}",
    ")",
    " # note\n  ",
    "\n",
    " and then some filler words that carry no operator" * 6,  # 300 characters
)
TAILS = (" " + VALUE, "\n" + VALUE, "")
PREFIXES = ("", "Ordinary context.\n", "Ordinary context.\n\n")


def same(text):
    return text


# Each presentation: how the label, the operator and then the whole text are written.
PRESENTATIONS = {
    "plain": (same, same, same),
    "JSON-encoded once": (same, same, json.dumps),
    "JSON-encoded twice": (same, same, lambda text: json.dumps(json.dumps(text))),
    "first label letter as \\u": (lambda label: first_letter(label, "\\u%04x"), same, same),
    "first label letter as \\x": (lambda label: first_letter(label, "\\x%02x"), same, same),
    "operator as \\x": (same, lambda operator: encoded(operator, "\\x%02x"), same),
    "operator as %XX": (same, lambda operator: encoded(operator, "%%%02X"), same),
    "operator as &#D;": (same, lambda operator: encoded(operator, "&#%d;"), same),
    "operator as &#xH;": (same, lambda operator: encoded(operator, "&#x%X;"), same),
    "zero-width space inside the label": (
        lambda label: first_letter(label, "%c" + ZERO_WIDTH_SPACE),
        same,
        same,
    ),
    "full-width label": (full_width, same, same),
}


def test_i2_a_label_then_an_operator_is_refused_in_every_presentation(matrix):
    assert len(GAPS[-1]) == 300
    calls = 0
    returned = []
    for (name, (write_label, write_operator, write_text)), *parts in itertools.product(
        PRESENTATIONS.items(), PREFIXES, matrix.labels, GAPS, OPERATORS, TAILS
    ):
        prefix, label, gap, operator, tail = parts
        calls += 1
        text = write_text(prefix + write_label(label) + gap + write_operator(operator) + tail)
        if not refused(text):
            returned.append((name, *parts))
    assert calls == 42768
    assert not returned[:5], f"{len(returned)} of {calls} were returned"


def test_i2_scheme_tokens_and_private_key_markers_are_refused():
    leads = ("", *("Ordinary context." + ending for ending in BREAKS), 'value "', "value '")
    schemes = ("Bearer", "BEARER", "bearer", "Basic", "BASIC", "basic")
    texts = [
        f"{lead}{indent}{scheme} {VALUE}"
        for lead, indent, scheme in itertools.product(leads, ("", "  ", "\t"), schemes)
    ]
    texts += [
        "-----BEGIN PRIVATE KEY-----",
        "-----BEGIN RSA PRIVATE KEY-----",
        "-----BEGIN OPENSSH PRIVATE KEY-----",
        "-----begin encrypted private key-----",
    ]
    assert len(texts) == 9 * 3 * 6 + 4
    assert [text for text in texts if not refused(text)] == []


def test_i3_text_outside_the_rule_is_returned(matrix):
    cases = json.loads((ROOT / "research/evaluation/cases.json").read_text(encoding="utf-8"))
    tasks = [case["task"] for case in cases]
    twins = [
        formatter(name)
        for name in ("display_name", "Content-Type")
        for formatter in matrix.formats.values()
    ]
    mentions = [
        template % label
        for label in matrix.labels
        for template in (
            "Rotate the %s before the release.",  # in a sentence with no operator
            "%s",  # alone as a string
            "mode = strict, then rotate the %s",  # after an operator, with none following
        )
    ]
    fields = ["authorization_revision", "authorization_digest", "requires_authorization"]
    assert (len(tasks), len(twins), len(mentions)) == (36, 818, 36)
    texts = [*tasks, *twins, *mentions, *fields]
    assert [text for text in texts if refused(text)][:5] == []


def base64_form(text):
    return base64.b64encode(text.encode("utf-8")).decode("ascii")


REFUSED, RETURNED = True, False
# I4: one row for each example in docs/sanitization-contract.md and for each worked example
# of the S3 design ruling. A row that changes result means the code and the contract
# disagree: the contract changes, with its owner's agreement, in the same commit as the row.
DISCLOSED = (
    # Worked examples of the S3 design ruling (its section 2.6).
    (f"api_key = {VALUE}", REFUSED),
    (f"Authorization: Bearer {VALUE}", REFUSED),
    (f'{{"password": "{VALUE}"}}', REFUSED),
    (f"--password={VALUE}", REFUSED),
    (f"password%3D{VALUE}", REFUSED),
    (f"password&#x3D;{VALUE}", REFUSED),
    (f"password\\u003d{VALUE}", REFUSED),
    (f"pass%77ord%3D{VALUE}", REFUSED),
    (f"&#112;assword: {VALUE}", REFUSED),
    (f"{full_width('password')}: {VALUE}", REFUSED),
    (f"pass{ZERO_WIDTH_SPACE}word: {VALUE}", REFUSED),
    (f"**password**\n: {VALUE}", REFUSED),
    ("Add a password reset flow; see https://example.test/spec", REFUSED),
    ("Basic plan costs $5", REFUSED),
    ("-----BEGIN RSA PRIVATE KEY-----", REFUSED),
    ("Escape " + "\\" * 32 + " in the path", REFUSED),
    ("Add a password reset flow to the login page.", RETURNED),
    ("authorization_revision", RETURNED),
    ("k8s/secrets.yaml", RETURNED),
    (f"the password is {VALUE}", RETURNED),
    (f"--password {VALUE}", RETURNED),
    (f"machine h login u password {VALUE}", RETURNED),
    (f'[["X-API-Key", "{VALUE}"]]', RETURNED),
    (f'"{VALUE}" -> password', RETURNED),
    (f"**password**\n\n: {VALUE}", RETURNED),
    (f"GITHUB_TOKEN={VALUE}", RETURNED),
    (f"token = {VALUE}", RETURNED),
    (f"'pass' + 'word' = {VALUE}", RETURNED),
    (base64_form(f"api_key = {VALUE}"), RETURNED),
    (base64_form(f"Authorization: Bearer {VALUE}"), RETURNED),
    # The contract, "What is refused": the five names and the four signs.
    (f"authorization: {VALUE}", REFUSED),
    (f"api key = {VALUE}", REFUSED),
    (f"access token <- {VALUE}", REFUSED),
    (f"secret -> {VALUE}", REFUSED),
    (f"PASSWORD: {VALUE}", REFUSED),
    (f"access_token={VALUE}", REFUSED),
    (f"api-key: {VALUE}", REFUSED),
    (f"apikey={VALUE}", REFUSED),
    (f"DB_PASSWORD={VALUE}", REFUSED),
    (f"X-API-Key: {VALUE}", REFUSED),
    # Bearer or Basic at the start of a line or directly after a quotation mark.
    (f"Request log\nBearer {VALUE}", REFUSED),
    (f'curl -H "Basic {VALUE}"', REFUSED),
    ("Use basic arithmetic.", RETURNED),
    # The first line of a PEM private key.
    (f"-----BEGIN OPENSSH PRIVATE KEY-----\n{VALUE}", REFUSED),
    # Seen through escapes and codes (the other forms are in the worked examples).
    (f"pass\\x77ord = {VALUE}", REFUSED),
    (f"password&#61;{VALUE}", REFUSED),
    # The contract, "What is not detected".
    (f"passwd: {VALUE}", RETURNED),
    (f"credential = {VALUE}", RETURNED),
    (f"private_key: {VALUE}", RETURNED),
    (f"auth = {VALUE}", RETURNED),
    (f"Cookie: session={VALUE}", RETURNED),
    (VALUE, RETURNED),
    (f"kid={VALUE}", RETURNED),
    ("postgres://user:pass@host", RETURNED),
    (f'["X-API-Key", "{VALUE}"]', RETURNED),
    # The contract, "Also know": ordinary text that is refused.
    ("Add a password reset flow. Note: it must send an email.", REFUSED),
    ("Pricing\nBasic plan costs $5", REFUSED),
)
assert len(DISCLOSED) <= 60
DISCLOSED_IDS = [
    f"{row:02d}-{'refused' if expected else 'returned'}"
    for row, (_, expected) in enumerate(DISCLOSED, 1)
]


@pytest.mark.parametrize(("text", "expected"), DISCLOSED, ids=DISCLOSED_IDS)
def test_i4_the_disclosed_examples_behave_as_stated(text, expected):
    assert refused(text) is expected, repr(text)


# Edges of the rule that the products and the disclosed examples do not reach. Each row pins
# one clause of the rule; without it a one-line change to that clause passes every other test.
EDGES = (
    # Breaks and blank lines.
    (f"**password**\n \t\n: {VALUE}", RETURNED),  # a whitespace-only line is a blank line
    (f"password\r\n: {VALUE}", REFUSED),  # CRLF is one break, not an empty line
    (f"password\v\n: {VALUE}", REFUSED),  # vertical tab and form feed are not breaks
    (f"password\f\n: {VALUE}", REFUSED),
    (f"Ordinary context.\vBearer {VALUE}", RETURNED),
    (f"api\n\nkey: {VALUE}", REFUSED),  # the paragraph is measured from the end of the label
    # Every label is examined, not only the first.
    (f"password secret\n\napi_key: {VALUE}", REFUSED),
    # The text as written is checked before normalization composes it.
    (f"secret\N{COMBINING CEDILLA}: {VALUE}", REFUSED),
    (f"password =\N{COMBINING LONG SOLIDUS OVERLAY} {VALUE}", REFUSED),
    # Normalization removes each of the four categories: Cf, Mn, Mc and Me.
    (f"pass\N{SOFT HYPHEN}word: {VALUE}", REFUSED),
    (f"pass\N{COMBINING GRAPHEME JOINER}word: {VALUE}", REFUSED),
    (f"pass\N{DEVANAGARI SIGN VISARGA}word: {VALUE}", REFUSED),
    (f"pass\N{COMBINING ENCLOSING CIRCLE}word: {VALUE}", REFUSED),
    # A character that decoding reveals is normalized before its view is checked.
    (f"pass\\u200bword: {VALUE}", REFUSED),
    # The escape forms that no presentation above uses.
    (f"password\\U0000003d{VALUE}", REFUSED),
    (f"password\\075{VALUE}", REFUSED),
    (f"password&#X3D;{VALUE}", REFUSED),
    # A code above 0x10FFFF is not a character: the escape stays as written.
    ("\\U00110000", RETURNED),
    ("&#x110000;", RETURNED),
    ("&#9999999;", RETURNED),
)


@pytest.mark.parametrize(("text", "expected"), EDGES, ids=range(1, len(EDGES) + 1))
def test_i2_i3_edges_of_the_rule(text, expected):
    assert refused(text) is expected, repr(text)


def repeated(unit):
    return (unit * (MILLION // len(unit) + 1))[:MILLION]


LONG_INPUTS = {
    "prose": (lambda: repeated("Refactor the billing module and add tests. "), RETURNED),
    "password repeated": (lambda: repeated("password "), RETURNED),
    "backslashes": (lambda: "\\" * MILLION, REFUSED),
    "api and underscores": (lambda: "api" + "_" * (MILLION - 3), RETURNED),
    "%41 repeated": (lambda: repeated("%41"), RETURNED),
    "non-ASCII prose": (lambda: repeated("caf\u00e9 na\u00efve "), RETURNED),
    "a label in each of 100,000 paragraphs": (lambda: "password\n\n" * 100_000, RETURNED),
}


@pytest.mark.parametrize("name", LONG_INPUTS)
def test_i6_one_million_characters_take_linear_time(name):
    build, expected = LONG_INPUTS[name]
    text = build()
    assert len(text) == MILLION
    started = time.perf_counter()
    outcome = refused(text)
    elapsed = time.perf_counter() - started
    assert outcome is expected
    # Linear cost is a fraction of a second; the bound only catches a non-linear scan.
    assert elapsed < 5, f"{elapsed:.2f} seconds"


def test_i6_a_past_deadline_never_returns_text():
    with pytest.raises(TimeoutError, match="^context sanitization deadline exceeded$"):
        redact("Refactor the billing module and add tests.", -math.inf)
    with pytest.raises((TimeoutError, ContractError)):
        redact(f"password: {VALUE}", -math.inf)


class Clock:
    """Stands in for `monotonic`: before the deadline until the given call, past it afterwards."""

    def __init__(self, expires_at_call=math.inf):
        self.calls = 0
        self.expires_at_call = expires_at_call

    def __call__(self):
        self.calls += 1
        return 2.0 if self.calls >= self.expires_at_call else 0.0


@pytest.mark.parametrize(
    ("text", "listed_checks"),
    [
        ("Refactor the billing module and add tests.", 3),  # steps 1, 3 and the first decode
        ("a" + "\\" * 16 + "b", 11),  # steps 1 and 3, two in each of four decodes, step 5
    ],
    ids=["no-escapes", "four-decodes"],
)
def test_i6_every_deadline_check_stops_redact(monkeypatch, text, listed_checks):
    clock = Clock()
    monkeypatch.setattr(context, "monotonic", clock)
    assert redact(text, 1.0) is text
    assert clock.calls >= listed_checks
    for failing_call in range(1, clock.calls + 1):
        monkeypatch.setattr(context, "monotonic", Clock(failing_call))
        with pytest.raises(TimeoutError):
            redact(text, 1.0)


def layered(text, layers):
    """Write the first letter as `\\xHH`, then escape that backslash `layers - 1` more times."""
    return "\\" * 2 ** (layers - 1) + f"x{ord(text[0]):02x}" + text[1:]


def test_i7_escape_depth():
    for label, layers in itertools.product(("password", "Authorization"), range(1, 6)):
        text = "Set " + layered(f"{label} = {VALUE}", layers)
        assert label not in text
        assert refused(text), (label, layers)
    # The same layers over a word that is not a label: four decodes reach plain text and
    # return it, so the refusals above come from the label. The fifth is still changing.
    for layers in range(1, 6):
        assert refused("Set " + layered("priority = high", layers)) is (layers == 5), layers
    assert refused("a" + "\\" * 16 + "b") is False
    assert refused("a" + "\\" * 32 + "b") is True
