"""Helpers to deal with permissions."""
from functools import wraps

from typing import Callable, Dict, List, Optional, Union, cast  # noqa: F401

from .models import PermissionLookup
from .types import CategoryType, SubCategoryDict, ValueType

LookupFunc = Callable[[PermissionLookup, SubCategoryDict, str],
                      Optional[ValueType]]
SubCatLookupType = Dict[str, LookupFunc]


def lookup_all(perm_lookup: PermissionLookup, lookup_dict: SubCategoryDict,
               object_id: str) -> ValueType:
    """Look up permission for all."""
    # In case of ALL category, lookup_dict IS the schema.
    return cast(ValueType, lookup_dict)


def compile_policy(
        policy: CategoryType, subcategories: SubCatLookupType,
        perm_lookup: PermissionLookup
    ) -> Callable[[str, str], bool]:  # noqa
    """Compile policy into a function that tests policy.
    Subcategories are mapping key -> lookup function, ordered by highest
    priority first.
    """
    # None, False, empty dict
    if not policy:
        def apply_policy_deny_all(entity_id: str, key: str) -> bool:
            """Decline all."""
            return False

        return apply_policy_deny_all

    if policy is True:
        def apply_policy_allow_all(entity_id: str, key: str) -> bool:
            """Approve all."""
            return True

        return apply_policy_allow_all

    assert isinstance(policy, dict)

    funcs = []  # type: List[Callable[[str, str], Union[None, bool]]]

    for key, lookup_func in subcategories.items():
        lookup_value = policy.get(key)

        # If any lookup value is `True`, it will always be positive
        if isinstance(lookup_value, bool):
            return lambda object_id, key: True

        if lookup_value is not None:
            funcs.append(_gen_dict_test_func(
                perm_lookup, lookup_func, lookup_value))

    if len(funcs) == 1:
        func = funcs[0]

        @wraps(func)
        def apply_policy_func(object_id: str, key: str) -> bool:
            """Apply a single policy function."""
            return func(object_id, key) is True

        return apply_policy_func

    def apply_policy_funcs(object_id: str, key: str) -> bool:
        """Apply several policy functions."""
        for func in funcs:
            result = func(object_id, key)
            if result is not None:
                return result
        return False

    return apply_policy_funcs


def _gen_dict_test_func(
        perm_lookup: PermissionLookup,
        lookup_func: LookupFunc,
        lookup_dict: SubCategoryDict
    ) -> Callable[[str, str], Optional[bool]]:  # noqa
    """Generate a lookup function."""
    def test_value(object_id: str, key: str) -> Optional[bool]:
        """Test if permission is allowed based on the keys."""
        schema = lookup_func(
            perm_lookup, lookup_dict, object_id)  # type: ValueType

        if schema is None or isinstance(schema, bool):
            return schema

        assert isinstance(schema, dict)

        return schema.get(key)

    return test_value