"""
Symbol table for semantic analysis with lexical scoping.
"""
from dataclasses import dataclass, field
from typing import Dict, List, Optional
from src.ast.nodes import TypeNode


@dataclass
class Symbol:
    name: str
    type_node: TypeNode
    is_constant: bool = False
    is_function: bool = False
    param_types: List[TypeNode] = field(default_factory=list)
    line: int = 0
    column: int = 0
    references: int = 0


class SymbolTable:
    def __init__(self):
        self.scopes: List[Dict[str, Symbol]] = [{}] # Global scope at index 0

    def enter_scope(self) -> None:
        self.scopes.append({})

    def exit_scope(self) -> Dict[str, Symbol]:
        if len(self.scopes) > 1:
            return self.scopes.pop()
        raise RuntimeError("Cannot exit global scope")

    @property
    def current_scope_level(self) -> int:
        return len(self.scopes) - 1

    def define(self, symbol: Symbol) -> bool:
        """Defines a symbol in the current scope. Returns False if already defined in current scope."""
        cur = self.scopes[-1]
        if symbol.name in cur:
            return False
        cur[symbol.name] = symbol
        return True

    def lookup(self, name: str) -> Optional[Symbol]:
        """Looks up a symbol from innermost to outermost scope."""
        for scope in reversed(self.scopes):
            if name in scope:
                return scope[name]
        return None

    def lookup_local(self, name: str) -> Optional[Symbol]:
        """Looks up a symbol strictly within the current scope."""
        return self.scopes[-1].get(name)

    def mark_referenced(self, name: str) -> bool:
        sym = self.lookup(name)
        if sym:
            sym.references += 1
            return True
        return False
