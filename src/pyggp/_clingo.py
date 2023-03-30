from typing import Optional, Sequence

import clingo
import clingo.ast as clingo_ast

_pos = clingo_ast.Position("<pyggp>", 0, 0)
_loc = clingo_ast.Location(_pos, _pos)


def create_rule(head: Optional[clingo_ast.AST] = None, body: Sequence[clingo_ast.AST] = ()) -> clingo_ast.AST:
    if head is None:
        head = clingo_ast.Disjunction(_loc, ())
    assert head.ast_type in (clingo_ast.ASTType.Literal, clingo_ast.ASTType.Aggregate)
    assert all(body_literal.ast_type == clingo_ast.ASTType.Literal for body_literal in body)
    return clingo_ast.Rule(_loc, head, body)


def create_aggregate(
    left_guard: Optional[clingo_ast.AST] = None,
    elements: Sequence[clingo_ast.AST] = (),
    right_guard: Optional[clingo_ast.AST] = None,
) -> clingo_ast.AST:
    assert left_guard is None or left_guard.ast_type == clingo_ast.ASTType.Guard
    assert all(element.ast_type == clingo_ast.ASTType.ConditionalLiteral for element in elements)
    assert right_guard is None or right_guard.ast_type == clingo_ast.ASTType.Guard
    return clingo_ast.Aggregate(_loc, left_guard, elements, right_guard)


def create_guard(
    comparison: clingo_ast.ComparisonOperator = clingo_ast.ComparisonOperator.Equal,
    term: Optional[clingo_ast.AST] = None,
) -> clingo_ast.AST:
    if term is None:
        term = create_function()
    return clingo_ast.Guard(comparison, term)


def create_conditional_literal(
    literal: Optional[clingo_ast.AST] = None,
    condition: Sequence[clingo_ast.AST] = (),
) -> clingo_ast.AST:
    if literal is None:
        literal = create_literal()
    assert literal.ast_type == clingo_ast.ASTType.Literal
    assert all(condition_literal.ast_type == clingo_ast.ASTType.Literal for condition_literal in condition)
    return clingo_ast.ConditionalLiteral(_loc, literal, condition)


def create_literal(
    sign: clingo_ast.Sign = clingo_ast.Sign.NoSign,
    atom: Optional[clingo_ast.AST] = None,
) -> clingo_ast.AST:
    if atom is None:
        atom = create_atom()
    assert atom.ast_type in (clingo_ast.ASTType.SymbolicAtom, clingo_ast.ASTType.Comparison)
    return clingo_ast.Literal(_loc, sign, atom)


def create_comparison(term: Optional[clingo_ast.AST] = None, guards: Sequence[clingo_ast.AST] = ()) -> clingo_ast.AST:
    if term is None:
        term = create_function()
    assert term.ast_type in (clingo_ast.ASTType.Function, clingo_ast.ASTType.SymbolicTerm, clingo_ast.ASTType.Variable)
    assert all(guard.ast_type == clingo_ast.ASTType.Guard for guard in guards)
    return clingo_ast.Comparison(term, guards)


def create_atom(symbol: Optional[clingo_ast.AST] = None) -> clingo_ast.AST:
    if symbol is None:
        symbol = create_function()
    return clingo_ast.SymbolicAtom(symbol)


def create_function(
    name: str = "",
    arguments: Sequence[clingo_ast.AST] = (),
    external: int = False,
) -> clingo_ast.AST:
    return clingo_ast.Function(_loc, name, arguments, external)


def create_symbolic_term(symbol: Optional[clingo.Symbol] = None) -> clingo_ast.AST:
    if symbol is None:
        symbol = clingo.Number(0)
    return clingo_ast.SymbolicTerm(_loc, symbol)


def create_variable(name: str = "") -> clingo_ast.AST:
    return clingo_ast.Variable(_loc, name)
