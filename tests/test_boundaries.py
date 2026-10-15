"""Structural checks on the boundaries: the sandbox policy and the migrations."""

import pathlib
import re

import yaml

ROOT = pathlib.Path(__file__).resolve().parents[1]


def test_sandbox_policy_grants_one_network_surface_for_one_binary():
    policy = yaml.safe_load((ROOT / "sandbox/policy.template.yaml").read_text())
    rules = policy["network_policies"]
    assert list(rules) == ["oracle_ai_database"]
    assert [b["path"] for b in rules["oracle_ai_database"]["binaries"]] == ["/usr/local/bin/python3.12"]
    assert policy["process"]["run_as_user"] != "0"


def test_provider_profile_allows_only_the_openai_compatible_path():
    profile = yaml.safe_load((ROOT / "sandbox/profile/oci-genai-python.yaml").read_text())
    paths = {rule["allow"]["path"] for ep in profile["endpoints"] for rule in ep.get("rules", [])}
    assert paths == {"/openai/v1/**"}


def test_every_migration_can_be_reversed():
    for path in sorted((ROOT / "migrations/versions").glob("0*.py")):
        source = path.read_text()
        assert re.search(r"^def downgrade\(\)", source, re.M), path.name
        assert "pass" not in source.split("def downgrade()")[1].split("\n\n\n")[0].split("\n")[1], path.name


def test_schema_accepts_synthetic_patients_only():
    schema = (ROOT / "migrations/versions/0001_clinical_schema.py").read_text()
    assert "SYN-%" in schema and "is_synthetic" in schema
