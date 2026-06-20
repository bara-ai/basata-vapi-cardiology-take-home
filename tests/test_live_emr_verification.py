import re


def test_build_test_identity_is_synthetic_and_deterministic() -> None:
    from scripts.live_emr_verification import build_test_identity

    identity = build_test_identity("20260620T200000Z-a1b2c3d4")

    assert identity == {
        "first_name": "Basata",
        "last_name": "Sandbox20260620T200000ZA1B2C3D4",
        "date_of_birth": "1990-01-01",
        "phone": "+1555" + identity["phone"][-7:],
    }
    assert re.fullmatch(r"\+1555\d{7}", identity["phone"])


def test_each_run_id_produces_a_separate_test_identity() -> None:
    from scripts.live_emr_verification import build_test_identity

    first = build_test_identity("20260620T200000Z-a1b2c3d4")
    second = build_test_identity("20260620T200001Z-e5f6a7b8")

    assert first["last_name"] != second["last_name"]
    assert first["phone"] != second["phone"]


def test_runner_does_not_expose_or_use_reset_configuration() -> None:
    from scripts.live_emr_verification import run_live_verification

    assert "reset" not in run_live_verification.__code__.co_names
