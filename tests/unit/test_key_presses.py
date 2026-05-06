from __future__ import annotations


def test_shared_key_presses_do_not_export_linux_transport_details() -> None:
    import operance.key_presses as key_presses

    assert not hasattr(key_presses, "linux_args_for_supported_key")
