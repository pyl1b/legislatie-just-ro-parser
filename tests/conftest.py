"""Test configuration and compatibility helpers.

This file amends pytest's monkeypatch to support a commonly used
``setattr(module_path: str, name: str, value: object, raising: bool)``
form, resolving the dotted module path automatically. Some pytest
versions only resolve dotted paths when ``value`` is omitted. The
compat layer below preserves original behavior and adds this missing
case to avoid teardown errors when undoing patches.
"""

from __future__ import annotations

from _pytest.monkeypatch import MonkeyPatch, notset, resolve  # type: ignore

_original_setattr = MonkeyPatch.setattr


def _compat_setattr(
    self: MonkeyPatch,
    target: str,
    name: str,
    value: object = notset,
    raising: bool = True,
) -> object:
    # If a dotted module path string is provided as target and a real value is
    # given, resolve the module object and perform the assignment there. This
    # mirrors the behavior pytest applies when only ``target`` and ``value``
    # are provided.
    if (
        isinstance(target, str)
        and isinstance(name, str)
        and value is not notset
    ):
        mod_obj = resolve(target)
        oldval = getattr(mod_obj, name, notset)
        if raising and oldval is not notset:
            # Record previous value for proper undo.
            self._setattr.append((mod_obj, name, oldval))
        else:
            self._setattr.append((mod_obj, name, notset))
        setattr(mod_obj, name, value)
        return None

    # Fallback to the original implementation for all other cases.
    return _original_setattr(self, target, name, value, raising)


# Install the compatibility shim.
MonkeyPatch.setattr = _compat_setattr  # type: ignore[assignment]
