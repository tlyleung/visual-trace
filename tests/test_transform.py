"""Rewriting plain containers into animated ones.

The rewrite happens on the AST and is compiled with the original filename, so
the user keeps writing `list` and `dict` while the trace sees `List` and `Dict`.
Line numbers must survive that untouched -- the code panel and the tracer both
read them straight from the file on disk.
"""

import ast
import inspect

import pytest

from visual_trace.data_structures.dict import Dict
from visual_trace.data_structures.list import List
from visual_trace.utils.loader import load_script
from visual_trace.utils.transform import rewrite


def run(source: str, filename: str = "<test>") -> dict:
    namespace = {"List": List, "Dict": Dict}
    exec(rewrite(source, filename), namespace)
    return namespace


def value_of(source: str, expression: str = "x"):
    return run(f"x = {source}\n")[expression]


#
# What gets rewritten
#


@pytest.mark.parametrize(
    "source,expected",
    [
        ("[1, 2, 3]", [1, 2, 3]),
        ("[]", []),
        ("[y for y in range(3)]", [0, 1, 2]),
        ("list()", []),
        ("list(range(3))", [0, 1, 2]),
        ("list('ab')", ["a", "b"]),
    ],
)
def test_a_list_becomes_an_animated_list(source, expected):
    result = value_of(source)
    assert isinstance(result, List), f"{source} stayed a plain list"
    assert list(list.__iter__(result)) == expected


@pytest.mark.parametrize(
    "source,expected",
    [
        ("{}", {}),
        ("{'a': 1}", {"a": 1}),
        ("{1: 'x'}", {1: "x"}),
        ("{k: k * 2 for k in range(2)}", {0: 0, 1: 2}),
        ("dict()", {}),
        ("dict(a=1)", {"a": 1}),
        ("dict({'a': 1}, b=2)", {"a": 1, "b": 2}),
    ],
)
def test_a_dict_becomes_an_animated_dict(source, expected):
    result = value_of(source)
    assert isinstance(result, Dict), f"{source} stayed a plain dict"
    assert dict(dict.items(result)) == expected


def test_nested_containers_are_rewritten_throughout():
    result = value_of("{'a': [1, 2]}")
    assert isinstance(result, Dict)
    assert isinstance(dict.__getitem__(result, "a"), List)


#
# What deliberately is not
#


def test_isinstance_still_tests_the_builtin():
    """`List` is a subclass, so rewriting the second argument narrows the test.

    Tested against a value the rewriter cannot reach -- `sorted` returns a plain
    list. Using a literal would rewrite *both* arguments and pass either way.
    """
    namespace = run("result = isinstance(sorted([3, 1]), list)\n")
    assert namespace["result"] is True


def test_issubclass_still_tests_the_builtin():
    namespace = run("result = issubclass(type(sorted([1])), list)\n")
    assert namespace["result"] is True


def test_an_annotation_is_left_alone():
    """Annotations never affect the values that get drawn."""
    tree = ast.parse("def f(a: list) -> dict:\n    return {}\n")
    rewritten = ast.dump(ast.parse(ast.unparse(_transformed(tree))))
    assert "'list'" in rewritten and "'dict'" in rewritten


def _transformed(tree):
    from visual_trace.utils.transform import _Rewriter

    return ast.fix_missing_locations(_Rewriter().visit(tree))


def test_a_module_that_rebinds_list_is_skipped_entirely():
    namespace = run("list = tuple\nx = [1, 2]\n")
    assert not isinstance(namespace["x"], List), "rewrote a module that shadows list"


def test_a_store_target_is_not_rewritten():
    namespace = run("[a, b] = [1, 2]\n")
    assert namespace["a"] == 1 and namespace["b"] == 2


#
# Line numbers -- the property the code panel and tracer depend on
#


def test_line_numbers_survive_the_rewrite():
    source = "\n".join(
        ["# leading comment", "", "def f():", "    xs = [1, 2]", "    return xs", ""]
    )
    namespace = {"List": List, "Dict": Dict}
    exec(rewrite(source, "<lines>"), namespace)
    assert namespace["f"].__code__.co_firstlineno == 3

    plain = {}
    exec(compile(source, "<lines>", "exec"), plain)
    assert (
        namespace["f"].__code__.co_firstlineno == plain["f"].__code__.co_firstlineno
    ), "the rewrite moved the function"


def test_the_original_source_is_what_gets_shown(tmp_path):
    """`inspect.getsource` must read the file, not the rewrite."""
    path = tmp_path / "user.py"
    path.write_text("def f():\n    return [1, 2]\n")
    namespace = {"List": List, "Dict": Dict, "__file__": str(path)}
    exec(rewrite(path.read_text(), str(path)), namespace)

    assert "List(" not in inspect.getsource(namespace["f"])
    assert "[1, 2]" in inspect.getsource(namespace["f"])
    assert isinstance(namespace["f"](), List)


def test_a_module_that_imports_the_containers_itself_is_undisturbed(tmp_path):
    """An explicit import must rebind the seeded names, not fight them.

    `List` and `Dict` are seeded into the exec globals rather than injected as
    an import node, precisely so the rewrite adds no lines. A user who writes
    the import themselves therefore gets back the same two objects, keeps their
    own line numbers, and still has their plain literals rewritten around it.
    `examples/two_sum.py` covered this incidentally until every example was
    converted to plain containers.
    """
    path = tmp_path / "user.py"
    path.write_text(
        "from visual_trace.data_structures.dict import Dict\n"
        "from visual_trace.data_structures.list import List\n"
        "\n"
        "\n"
        "def f():\n"
        "    return List(1, 2), Dict(a=1), [3], {'b': 2}\n"
    )
    module = load_script(path)

    assert module.List is List, "the import bound a different List"
    assert module.Dict is Dict, "the import bound a different Dict"
    assert module.f.__code__.co_firstlineno == 5, "the rewrite moved the function"

    written_list, written_dict, literal_list, literal_dict = module.f()
    assert isinstance(written_list, List) and isinstance(written_dict, Dict)
    assert isinstance(literal_list, List), "the import suppressed the rewrite"
    assert isinstance(literal_dict, Dict), "the import suppressed the rewrite"
