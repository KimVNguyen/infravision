"""Tree-sitter AST parser for TypeScript, TSX, and JavaScript source code."""

from typing import List, Optional
import tree_sitter
import tree_sitter_typescript

from infravision.parser.base import (
    BaseLanguageParser,
    ParseResult,
    ParsedChunk,
    ParsedEdge,
    ParsedImport,
    ParsedSymbol,
)


class TypeScriptParser(BaseLanguageParser):
    """Extracts symbols, interfaces, types, calls, JSX usage, and imports from TS/JS code."""

    def __init__(self, is_tsx: bool = True) -> None:
        lang_func = (
            tree_sitter_typescript.language_tsx
            if is_tsx
            else tree_sitter_typescript.language_typescript
        )
        self.language = tree_sitter.Language(lang_func())
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

        # Interface declaration: interface Foo { ... }
        if node_type == "interface_declaration":
            name_node = node.child_by_field_name("name")
            name = (
                code_bytes[name_node.start_byte : name_node.end_byte].decode("utf-8")
                if name_node
                else "AnonymousInterface"
            )
            result.symbols.append(
                ParsedSymbol(
                    name=name,
                    kind="interface",
                    start_line=node.start_point.row + 1,
                    end_line=node.end_point.row + 1,
                    signature=f"interface {name}",
                    scope_path=".".join(current_scope + [name]),
                )
            )

        # Type alias: type Bar = ...
        elif node_type == "type_alias_declaration":
            name_node = node.child_by_field_name("name")
            name = (
                code_bytes[name_node.start_byte : name_node.end_byte].decode("utf-8")
                if name_node
                else "AnonymousType"
            )
            result.symbols.append(
                ParsedSymbol(
                    name=name,
                    kind="type_alias",
                    start_line=node.start_point.row + 1,
                    end_line=node.end_point.row + 1,
                    signature=f"type {name}",
                    scope_path=".".join(current_scope + [name]),
                )
            )

        # Class declaration: class UserService extends BaseService
        elif node_type == "class_declaration":
            name_node = node.child_by_field_name("name")
            class_name = (
                code_bytes[name_node.start_byte : name_node.end_byte].decode("utf-8")
                if name_node
                else "AnonymousClass"
            )

            result.symbols.append(
                ParsedSymbol(
                    name=class_name,
                    kind="class",
                    start_line=node.start_point.row + 1,
                    end_line=node.end_point.row + 1,
                    signature=f"class {class_name}",
                    scope_path=".".join(current_scope + [class_name]),
                )
            )

            # Class heritage (extends / implements)
            for child in node.children:
                if child.type == "class_heritage":
                    for heritage_child in child.children:
                        if heritage_child.type in (
                            "extends_clause",
                            "implements_clause",
                        ):
                            edge_type = (
                                "extends"
                                if heritage_child.type == "extends_clause"
                                else "implements"
                            )
                            for target in heritage_child.children:
                                if target.type in ("identifier", "type_identifier"):
                                    parent_name = code_bytes[
                                        target.start_byte : target.end_byte
                                    ].decode("utf-8")
                                    result.edges.append(
                                        ParsedEdge(
                                            source_symbol=class_name,
                                            target_symbol=parent_name,
                                            edge_type=edge_type,
                                        )
                                    )

            body = node.child_by_field_name("body")
            if body:
                for child in body.children:
                    self._walk_node(
                        child, code_bytes, current_scope + [class_name], result
                    )
            return

        # Function declaration: function doSomething()
        elif node_type == "function_declaration":
            name_node = node.child_by_field_name("name")
            fn_name = (
                code_bytes[name_node.start_byte : name_node.end_byte].decode("utf-8")
                if name_node
                else "anonymous_fn"
            )
            result.symbols.append(
                ParsedSymbol(
                    name=fn_name,
                    kind="function",
                    start_line=node.start_point.row + 1,
                    end_line=node.end_point.row + 1,
                    signature=f"function {fn_name}",
                    scope_path=".".join(current_scope + [fn_name]),
                )
            )
            body = node.child_by_field_name("body")
            if body:
                for child in body.children:
                    self._walk_node(child, code_bytes, current_scope + [fn_name], result)
            return

        # Method definition: async handle() { ... }
        elif node_type == "method_definition":
            name_node = node.child_by_field_name("name")
            method_name = (
                code_bytes[name_node.start_byte : name_node.end_byte].decode("utf-8")
                if name_node
                else "method"
            )
            result.symbols.append(
                ParsedSymbol(
                    name=method_name,
                    kind="method",
                    start_line=node.start_point.row + 1,
                    end_line=node.end_point.row + 1,
                    signature=method_name,
                    scope_path=".".join(current_scope + [method_name]),
                )
            )
            body = node.child_by_field_name("body")
            if body:
                for child in body.children:
                    self._walk_node(
                        child, code_bytes, current_scope + [method_name], result
                    )
            return

        # Arrow function assigned to const/let: const myFunc = () => { ... }
        elif node_type == "lexical_declaration":
            for child in node.children:
                if child.type == "variable_declarator":
                    val = child.child_by_field_name("value")
                    if val and val.type == "arrow_function":
                        name_node = child.child_by_field_name("name")
                        fn_name = (
                            code_bytes[
                                name_node.start_byte : name_node.end_byte
                            ].decode("utf-8")
                            if name_node
                            else "arrow_fn"
                        )
                        result.symbols.append(
                            ParsedSymbol(
                                name=fn_name,
                                kind="function",
                                start_line=node.start_point.row + 1,
                                end_line=node.end_point.row + 1,
                                signature=f"const {fn_name} = () =>",
                                scope_path=".".join(current_scope + [fn_name]),
                            )
                        )
                        body = val.child_by_field_name("body")
                        if body:
                            for b_child in body.children:
                                self._walk_node(
                                    b_child,
                                    code_bytes,
                                    current_scope + [fn_name],
                                    result,
                                )

        # Function call expression: callee(...)
        elif node_type == "call_expression":
            fn_node = node.child_by_field_name("function")
            if fn_node and current_scope:
                caller = current_scope[-1]
                callee_name = code_bytes[
                    fn_node.start_byte : fn_node.end_byte
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

        # JSX component rendering: <Component /> or <Component>...</Component>
        elif node_type in ("jsx_element", "jsx_self_closing_element"):
            if current_scope:
                caller = current_scope[-1]
                comp_name = None
                if node_type == "jsx_self_closing_element":
                    for c in node.children:
                        if c.type == "identifier":
                            comp_name = code_bytes[c.start_byte : c.end_byte].decode("utf-8")
                            break
                else:
                    open_tag = node.child_by_field_name("open_tag")
                    if open_tag:
                        for c in open_tag.children:
                            if c.type == "identifier":
                                comp_name = code_bytes[c.start_byte : c.end_byte].decode("utf-8")
                                break
                if comp_name and comp_name[0].isupper():
                    result.edges.append(
                        ParsedEdge(
                            source_symbol=caller,
                            target_symbol=comp_name,
                            edge_type="calls",
                        )
                    )

        # Import statement: import { foo, bar } from './module'
        elif node_type == "import_statement":
            source_node = node.child_by_field_name("source")
            if source_node:
                raw_spec = code_bytes[source_node.start_byte : source_node.end_byte].decode("utf-8").strip("\"'")
                imported_names = []
                for child in node.children:
                    if child.type == "import_clause":
                        for sub in child.children:
                            if sub.type == "identifier":
                                imported_names.append(code_bytes[sub.start_byte : sub.end_byte].decode("utf-8"))
                            elif sub.type == "named_imports":
                                for spec in sub.children:
                                    if spec.type == "import_specifier":
                                        alias = spec.child_by_field_name("alias")
                                        orig = spec.child_by_field_name("name")
                                        picked = alias or orig
                                        if picked:
                                            imported_names.append(code_bytes[picked.start_byte : picked.end_byte].decode("utf-8"))
                result.imports.append(
                    ParsedImport(
                        module_specifier=raw_spec,
                        imported_symbols=imported_names,
                    )
                )

        # Export statement re-exporting from another module: export { foo } from './bar'
        elif node_type == "export_statement":
            source_node = node.child_by_field_name("source")
            if source_node:
                raw_spec = code_bytes[source_node.start_byte : source_node.end_byte].decode("utf-8").strip("\"'")
                result.imports.append(
                    ParsedImport(
                        module_specifier=raw_spec,
                        imported_symbols=[],
                    )
                )

        # Recurse children
        for child in node.children:
            self._walk_node(child, code_bytes, current_scope, result)
