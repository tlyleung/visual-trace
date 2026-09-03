"""Every operation must leave the drawing agreeing with the data.

Nothing is inherited usefully: `list` and `dict` methods are pure C operating on
the internal array, and none of them route through a Python-level override.
Overriding `__setitem__` does not make `sort()` animate. So every method that
mutates or reads has to be written explicitly, and this walks them directly so a
method left inherited cannot quietly rejoin the set that draws a lie.
"""

import pytest

from stubs import drain, settle
from visual_trace.data_structures.dict import Dict
from visual_trace.data_structures.list import List


def make_list() -> List:
    nums = List(3, 1, 2)
    drain(nums)
    settle(nums)
    return nums


def make_dict() -> Dict:
    d = Dict(a=1, b=2)
    drain(d)
    settle(d)
    return d


MUTATIONS = [
    ("list-setitem", make_list, lambda s: s.__setitem__(0, 9)),
    ("list-swap", make_list, lambda s: (s.__setitem__(0, s[1]), s.__setitem__(1, 3))),
    ("list-delitem", make_list, lambda s: s.__delitem__(0)),
    ("list-pop", make_list, lambda s: s.pop()),
    ("list-pop-index", make_list, lambda s: s.pop(0)),
    ("list-insert", make_list, lambda s: s.insert(1, 9)),
    ("list-remove", make_list, lambda s: s.remove(1)),
    ("list-extend", make_list, lambda s: s.extend([7, 8])),
    ("list-iadd", make_list, lambda s: s.__iadd__([7])),
    ("list-clear", make_list, lambda s: s.clear()),
    ("list-reverse", make_list, lambda s: s.reverse()),
    ("list-sort", make_list, lambda s: s.sort()),
    ("dict-update-existing", make_dict, lambda s: s.update(a=9)),
    ("dict-update-new", make_dict, lambda s: s.update(c=3)),
    ("dict-pop", make_dict, lambda s: s.pop("a")),
    ("dict-popitem", make_dict, lambda s: s.popitem()),
    ("dict-setdefault-new", make_dict, lambda s: s.setdefault("z", 9)),
    ("dict-ior", make_dict, lambda s: s.__ior__({"c": 3})),
]


@pytest.mark.parametrize(
    "make,operation", [(m, o) for _, m, o in MUTATIONS], ids=[n for n, _, _ in MUTATIONS]
)
def test_a_mutation_keeps_the_drawing_in_sync(make, operation):
    structure = make()
    operation(structure)
    drain(structure)
    settle(structure)
    assert structure.drawn_values() == structure.expected_values()


READS = [
    ("list-contains", make_list, lambda s: 1 in s),
    ("list-index", make_list, lambda s: s.index(1)),
    ("list-count", make_list, lambda s: s.count(1)),
    ("dict-iter", make_dict, lambda s: [k for k in s]),
    ("dict-get", make_dict, lambda s: s.get("a")),
    ("dict-setdefault-existing", make_dict, lambda s: s.setdefault("a", 9)),
]


@pytest.mark.parametrize(
    "make,operation", [(m, o) for _, m, o in READS], ids=[n for n, _, _ in READS]
)
def test_a_read_is_visible(make, operation):
    """A read that draws nothing is indistinguishable from one that never ran."""
    structure = make()
    operation(structure)
    assert structure.animation_queue, "the read animated nothing"


DERIVED = [
    ("list-copy", make_list, lambda s: s.copy()),
    ("list-slice", make_list, lambda s: s[0:2]),
    ("list-add", make_list, lambda s: s + [9]),
    ("list-mul", make_list, lambda s: s * 2),
    ("dict-copy", make_dict, lambda s: s.copy()),
    ("dict-or", make_dict, lambda s: s | {"c": 3}),
]


@pytest.mark.parametrize(
    "make,operation", [(m, o) for _, m, o in DERIVED], ids=[n for n, _, _ in DERIVED]
)
def test_a_derived_container_is_still_animated(make, operation):
    """Otherwise `left = nums[:mid]` silently renders as flat text, not cells."""
    structure = make()
    derived = operation(structure)
    assert isinstance(derived, type(structure)), (
        f"derived container came back as {type(derived).__name__}"
    )
