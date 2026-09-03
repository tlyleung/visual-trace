"""Rewrite plain containers into animated ones.

A user should be able to write `list` and `dict` and still get cells rather than
flat text. This rewrites the module's AST before it runs, so `[1, 2]` becomes
`List(1, 2)` and `{}` becomes `Dict()`.

The rewrite is compiled with the **original filename** and never unparsed, so
node locations survive: `inspect.getsource` still reads the user's file from
disk, and `frame.f_lineno` still points at the line they wrote. The code panel
and the tracer's line arithmetic need to know nothing about any of this. Adding
an import node would be the obvious way to make `List` and `Dict` available and
is exactly what would break that, so they are seeded into the exec globals
instead -- see `utils.loader`.
"""

import ast

LIST, DICT = "List", "Dict"


def _name(identifier: str) -> ast.Name:
    return ast.Name(id=identifier, ctx=ast.Load())


def _call(identifier: str, args: list, keywords: list | None = None) -> ast.Call:
    return ast.Call(func=_name(identifier), args=args, keywords=keywords or [])


class _Rebinds(ast.NodeVisitor):
    """Whether a module uses `list` or `dict` as a name of its own.

    Rewriting a module that shadows either would change what its own name means.
    Rather than guess at scope, the whole module is left alone.
    """

    def __init__(self):
        self.found = False

    def _check(self, name) -> None:
        if name in (LIST.lower(), DICT.lower()):
            self.found = True

    def visit_Name(self, node):
        if isinstance(node.ctx, (ast.Store, ast.Del)):
            self._check(node.id)
        self.generic_visit(node)

    def visit_arg(self, node):
        self._check(node.arg)
        self.generic_visit(node)

    def visit_alias(self, node):
        self._check(node.asname or node.name.split(".")[0])

    def visit_FunctionDef(self, node):
        self._check(node.name)
        self.generic_visit(node)

    visit_AsyncFunctionDef = visit_FunctionDef

    def visit_ClassDef(self, node):
        self._check(node.name)
        self.generic_visit(node)


class _Rewriter(ast.NodeTransformer):
    """Replace container literals and constructors, in place."""

    def visit_List(self, node):
        self.generic_visit(node)
        # `[a, b] = ...` is a List node too, and is a target, not a value.
        if not isinstance(node.ctx, ast.Load):
            return node
        return ast.copy_location(_call(LIST, node.elts), node)

    def visit_ListComp(self, node):
        self.generic_visit(node)
        starred = ast.copy_location(ast.Starred(value=node, ctx=ast.Load()), node)
        return ast.copy_location(_call(LIST, [starred]), node)

    def visit_Dict(self, node):
        self.generic_visit(node)
        # Passed whole, as a mapping: keys need not be identifiers.
        return ast.copy_location(_call(DICT, [node]), node)

    def visit_DictComp(self, node):
        self.generic_visit(node)
        return ast.copy_location(_call(DICT, [node]), node)

    def visit_Call(self, node):
        self.generic_visit(node)
        if not isinstance(node.func, ast.Name):
            return node

        if node.func.id == "list":
            # List takes its elements, so an iterable has to be splatted.
            args = (
                [ast.copy_location(ast.Starred(value=node.args[0], ctx=ast.Load()), node)]
                if node.args
                else []
            )
            return ast.copy_location(_call(LIST, args), node)

        if node.func.id == "dict":
            # Dict mirrors dict's signature, so arguments pass straight through.
            return ast.copy_location(_call(DICT, node.args, node.keywords), node)

        return node

    #
    # Annotations are skipped: they never affect the values that get drawn, and
    # rewriting them was the whole of an earlier attempt -- which is why it
    # changed nothing.
    #

    def visit_FunctionDef(self, node):
        node.body = [self.visit(statement) for statement in node.body]
        node.decorator_list = [self.visit(d) for d in node.decorator_list]
        node.args = self._visit_defaults(node.args)
        return node

    visit_AsyncFunctionDef = visit_FunctionDef

    def _visit_defaults(self, arguments: ast.arguments) -> ast.arguments:
        arguments.defaults = [self.visit(d) for d in arguments.defaults]
        arguments.kw_defaults = [
            self.visit(d) if d is not None else None for d in arguments.kw_defaults
        ]
        return arguments

    def visit_AnnAssign(self, node):
        if node.value is not None:
            node.value = self.visit(node.value)
        return node


def rewrite(source: str, filename: str):
    """Compile `source` with plain containers replaced by animated ones.

    Returns a code object. Compiled against `filename` so everything that reads
    the source afterwards -- the code panel, the tracer, tracebacks -- sees the
    file the user actually wrote.
    """
    tree = ast.parse(source, filename=filename)

    rebinds = _Rebinds()
    rebinds.visit(tree)
    if not rebinds.found:
        tree = _Rewriter().visit(tree)
        ast.fix_missing_locations(tree)

    return compile(tree, filename, "exec")
