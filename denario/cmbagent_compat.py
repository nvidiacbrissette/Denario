"""Compatibility helpers for cmbagent/autogen version mismatches."""

from __future__ import annotations


def patch_autogen_for_cmbagent() -> None:
    """Populate legacy autogen root attributes expected by cmbagent.

    Some cmbagent releases read `autogen.cmbagent_debug` and
    `autogen.file_search_max_num_results` from the package root, while newer
    AG2 exposes them under `autogen.cmbagent_utils`.
    """
    try:
        import autogen
        import autogen.cmbagent_utils as cmbagent_utils
    except Exception:
        return

    compatibility_attrs = {
        "cmbagent_debug": False,
        "cmbagent_disable_display": False,
        "file_search_max_num_results": 20,
    }

    for attr, default in compatibility_attrs.items():
        if not hasattr(autogen, attr):
            setattr(autogen, attr, getattr(cmbagent_utils, attr, default))
