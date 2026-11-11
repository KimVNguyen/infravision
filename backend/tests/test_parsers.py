"""Unit tests for Tree-sitter Python and TypeScript/JavaScript AST parsers."""

import unittest
from infravision.parser.python import PythonParser
from infravision.parser.typescript import TypeScriptParser


class TestParsers(unittest.TestCase):
    def test_python_parser_symbols_and_edges(self):
        parser = PythonParser()
        code = """
class BaseService:
    def execute(self):
        pass

class UserService(BaseService):
    \"\"\"Handles user authentication and account creation.\"\"\"

    def __init__(self, db):
        self.db = db

    def create_user(self, name: str) -> bool:
        self.validate(name)
        return True

    def validate(self, name: str):
        pass
"""
        result = parser.parse_source(code, "service.py")

        symbol_names = [s.name for s in result.symbols]
        self.assertIn("BaseService", symbol_names)
        self.assertIn("UserService", symbol_names)
        self.assertIn("create_user", symbol_names)
        self.assertIn("validate", symbol_names)

        # Check docstring extraction
        user_service_sym = next(s for s in result.symbols if s.name == "UserService")
        self.assertIn("Handles user authentication", user_service_sym.docstring or "")

        # Check inheritance edge
        extends_edges = [e for e in result.edges if e.edge_type == "extends"]
        self.assertTrue(any(e.source_symbol == "UserService" and e.target_symbol == "BaseService" for e in extends_edges))

        # Check call edge (create_user calls validate)
        call_edges = [e for e in result.edges if e.edge_type == "calls"]
        self.assertTrue(any(e.source_symbol == "create_user" and e.target_symbol == "validate" for e in call_edges))

    def test_typescript_parser_symbols_and_edges(self):
        parser = TypeScriptParser()
        code = """
export interface UserPayload {
    id: string;
    email: string;
}

export type AuthToken = string;

export class AuthController extends BaseController {
    async handleLogin(req: any) {
        verifyToken(req.token);
    }
}
"""
        result = parser.parse_source(code, "auth.ts")

        symbol_names = [s.name for s in result.symbols]
        self.assertIn("UserPayload", symbol_names)
        self.assertIn("AuthToken", symbol_names)
        self.assertIn("AuthController", symbol_names)
        self.assertIn("handleLogin", symbol_names)

        # Check interface and type kinds
        interface_sym = next(s for s in result.symbols if s.name == "UserPayload")
        self.assertEqual(interface_sym.kind, "interface")

        type_sym = next(s for s in result.symbols if s.name == "AuthToken")
        self.assertEqual(type_sym.kind, "type_alias")

        # Check inheritance edge
        extends_edges = [e for e in result.edges if e.edge_type == "extends"]
        self.assertTrue(any(e.source_symbol == "AuthController" and e.target_symbol == "BaseController" for e in extends_edges))

        # Check call edge
        call_edges = [e for e in result.edges if e.edge_type == "calls"]
        self.assertTrue(any(e.source_symbol == "handleLogin" and e.target_symbol == "verifyToken" for e in call_edges))

    def test_python_import_extraction(self):
        parser = PythonParser()
        code = """
import os
from infravision.db.models import CodeFile, Symbol
from .scanner import RepositoryScanner
"""
        result = parser.parse_source(code, "test.py")
        specifiers = [imp.module_specifier for imp in result.imports]
        self.assertIn("os", specifiers)
        self.assertIn("infravision.db.models", specifiers)
        self.assertIn(".scanner", specifiers)

        models_imp = next(imp for imp in result.imports if imp.module_specifier == "infravision.db.models")
        self.assertIn("CodeFile", models_imp.imported_symbols)
        self.assertIn("Symbol", models_imp.imported_symbols)


if __name__ == "__main__":
    unittest.main()
