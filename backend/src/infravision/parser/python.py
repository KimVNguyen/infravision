"""Tree-sitter AST parser for Python source code."""

from typing import List, Optional
import tree_sitter
import tree_sitter_python

from infravision.parser.base import (
    BaseLanguageParser,
    ParseResult,
    ParsedChunk,
    ParsedEdge,
    ParsedImport,
    ParsedSymbol,
)


class PythonParser(BaseLanguageParser):
    """Extracts symbols, docstrings, calls, and imports from Python code."""

    def __init__(self) -> None:
        self.language = tree_sitter.Language(tree_sitter_python.language())
        self.parser = tree_sitter.Parser(self.language)

    def parse_source(self, code: str, file_path: str = "") -> ParseResult:
        result = ParseResult()
        code_bytes = code.encode("utf-8")
        tree = self.parser.parse(code_bytes)
        root = tree.root_node

        self._walk_node(
            node=root,
            code_bytes=code_bytes,
            current_scope=[],
            result=result,
        )

        # Generate chunks for each extracted symbol
        lines = code.splitlines()
        for symbol in result.symbols:
            start = max(0, symbol.start_line - 1)
            end = min(len(lines), symbol.end_line)
            chunk_content = "\n".join(lines[start:end])
            if chunk_content.strip():
                result.chunks.append(
                    ParsedChunk(
                        start_line=symbol.start_line,
                        end_line=symbol.end_line,
                        content=chunk_content,
                        symbol_name=symbol.name,
                    )
                )

        return result

    def _walk_node(
        self,
        node: tree_sitter.Node,
        code_bytes: bytes,
        current_scope: List[str],
        result: ParseResult,
    ) -> None:
        node_type = node.type

        if node_type == "class_definition":
            name_node = node.child_by_field_name("name")
            class_name = (
                code_bytes[name_node.start_byte : name_node.end_byte].decode("utf-8")
                if name_node
                else "AnonymousClass"
            )

            scope_str = ".".join(current_scope + [class_name])
            docstring = self._extract_docstring(node, code_bytes)

            result.symbols.append(
                ParsedSymbol(
                    name=class_name,
                    kind="class",
                    start_line=node.start_point.row + 1,
                    end_line=node.end_point.row + 1,
                    signature=f"class {class_name}",
                    docstring=docstring,
                    scope_path=scope_str,
                )
            )

            # Check superclasses for inheritance edges
            superclasses = node.child_by_field_name("superclasses")
            if superclasses:
                for child in superclasses.children:
                    if child.type == "identifier":
                        parent_name = code_bytes[
                            child.start_byte : child.end_byte
                        ].decode("utf-8")
                        result.edges.append(
                            ParsedEdge(
                                source_symbol=class_name,
                                target_symbol=parent_name,
                                edge_type="extends",
                            )
                        )

            # Recurse with class in scope
            body = node.child_by_field_name("body")
            if body:
                for child in body.children:
                    self._walk_node(child, code_bytes, current_scope + [class_name], result)
            return

        elif node_type in ("function_definition", "async_function_definition"):
            name_node = node.child_by_field_name("name")
            fn_name = (
                code_bytes[name_node.start_byte : name_node.end_byte].decode("utf-8")
                if name_node
                else "anonymous_fn"
            )

            is_method = len(current_scope) > 0
            kind = "method" if is_method else "function"
            scope_str = ".".join(current_scope + [fn_name])
            docstring = self._extract_docstring(node, code_bytes)

            params_node = node.child_by_field_name("parameters")
            params = (
                code_bytes[params_node.start_byte : params_node.end_byte].decode("utf-8")
                if params_node
                else "()"
            )

            return_type_node = node.child_by_field_name("return_type")
            ret_type = (
                f" -> {code_bytes[return_type_node.start_byte : return_type_node.end_byte].decode('utf-8')}"
                if return_type_node
                else ""
            )

            prefix = "async def " if node_type == "async_function_definition" else "def "
            sig = f"{prefix}{fn_name}{params}{ret_type}"

            result.symbols.append(
                ParsedSymbol(
                    name=fn_name,
                    kind=kind,
                    start_line=node.start_point.row + 1,
                    end_line=node.end_point.row + 1,
                    signature=sig,
                    docstring=docstring,
                    scope_path=scope_str,
                )
            )

            # Recurse inside function body to find calls
            body = node.child_by_field_name("body")
            if body:
                for child in body.children:
                    self._walk_node(child, code_bytes, current_scope + [fn_name], result)
            return

        elif node_type == "call":
            # Extract function call
            fn_call_node = node.child_by_field_name("function")
            if fn_call_node and current_scope:
                caller = current_scope[-1]
                callee_name = code_bytes[
                    fn_call_node.start_byte : fn_call_node.end_byte
                ].decode("utf-8")
                if "." in callee_name:
                    callee_name = callee_name.split(".")[-1]
                result.edges.append(
                    ParsedEdge(
                        source_symbol=caller,
                        target_symbol=callee_name,
                        edge_type="calls",
                    )
                )

        elif node_type == "import_from_statement":
            # from foo.bar import baz, qux
            mod_node = node.child_by_field_name("module_name")
            imported_names = []
            for child in node.children:
                if child.type == "dotted_name" and child != mod_node:
                    imported_names.append(code_bytes[child.start_byte : child.end_byte].decode("utf-8"))
                elif child.type == "import_from_specifier":
                    name_child = child.child_by_field_name("name")
                    if name_child:
                        imported_names.append(code_bytes[name_child.start_byte : name_child.end_byte].decode("utf-8"))
                elif child.type == "identifier" and child != mod_node:
                    imported_names.append(code_bytes[child.start_byte : child.end_byte].decode("utf-8"))
            
            raw_mod = code_bytes[mod_node.start_byte : mod_node.end_byte].decode("utf-8") if mod_node else ""
            if raw_mod:
                result.imports.append(
                    ParsedImport(
                        module_specifier=raw_mod,
                        imported_symbols=imported_names,
                    )
                )

        elif node_type == "import_statement":
            # import foo, bar
            for child in node.children:
                if child.type in ("dotted_name", "aliased_import"):
                    raw_mod = code_bytes[child.start_byte : child.end_byte].decode("utf-8")
                    result.imports.append(
                        ParsedImport(
                            module_specifier=raw_mod.split(" as ")[0].strip(),
                            imported_symbols=[],
                        )
                    )

        # Walk children
        for child in node.children:
            self._walk_node(child, code_bytes, current_scope, result)

    def _extract_docstring(
        self, node: tree_sitter.Node, code_bytes: bytes
    ) -> Optional[str]:
        body = node.child_by_field_name("body")
        if not body:
            return None
        for child in body.children:
            if child.type == "expression_statement":
                first_expr = child.children[0] if child.children else None
                if first_expr and first_expr.type == "string":
                    raw = code_bytes[first_expr.start_byte : first_expr.end_byte].decode(
                        "utf-8"
                    )
                    return raw.strip("\"' \n\t")
            elif child.type not in ("comment",):
                break
        return None
