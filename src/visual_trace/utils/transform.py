# import ast
# import inspect
# from typing import Tuple


# class ListToCustomListTransformer(ast.NodeTransformer):
#     def visit_Name(self, node):
#         # Transform instances of `list` to `List`
#         if node.id == "list":
#             return ast.Name(id="List", ctx=node.ctx)
#         return node

#     def visit_FunctionDef(self, node):
#         # Visit function arguments
#         node.args = self.visit(node.args)
#         # Visit the body of the function
#         node.body = [self.visit(stmt) for stmt in node.body]
#         return node

#     def visit_arguments(self, node):
#         # Visit all arguments, including default values and annotations
#         if node.args:
#             node.args = [self.visit(arg) for arg in node.args]
#         if node.kwonlyargs:
#             node.kwonlyargs = [self.visit(arg) for arg in node.kwonlyargs]
#         if node.defaults:
#             node.defaults = [self.visit(default) for default in node.defaults]
#         if node.kw_defaults:
#             node.kw_defaults = [
#                 self.visit(default) if default is not None else None
#                 for default in node.kw_defaults
#             ]
#         return node

#     def visit_AnnAssign(self, node):
#         # Handle type annotations
#         node.annotation = self.visit(node.annotation)
#         return node

#     def visit_arg(self, node):
#         # Handle type annotations for arguments
#         if node.annotation:
#             node.annotation = self.visit(node.annotation)
#         return node


# def transform_code(func) -> Tuple[str, str]:
#     """
#     Transform both the function code and its arguments to use List instead of list.
#     Returns tuple of (transformed_func_code, transformed_args_code)
#     """
#     # Get source code for the function
#     func_source = inspect.getsource(func)

#     # Parse the source code into an AST
#     func_tree = ast.parse(func_source)

#     # Transform the AST
#     transformer = ListToCustomListTransformer()
#     modified_func_tree = transformer.visit(func_tree)

#     # Add the import statement to the transformed AST
#     import_stmt = ast.ImportFrom(
#         module="visualtrace.data_structures.list",
#         names=[ast.alias(name="List", asname=None)],
#         level=0,
#     )
#     modified_func_tree.body.insert(0, import_stmt)

#     # Return the transformed code
#     return ast.unparse(modified_func_tree)
