from typing import Optional, Sequence

import clingo.ast

_pos = clingo.ast.Position("<pyggp>", 0, 0)
_loc = clingo.ast.Location(_pos, _pos)


def _create_rule(head: Optional[clingo.ast.AST] = None, body: Sequence[clingo.ast.AST] = ()) -> clingo.ast.AST:
    if head is None:
        head = clingo.ast.Disjunction(_loc, ())
    assert head.ast_type in (clingo.ast.ASTType.Literal, clingo.ast.ASTType.Aggregate)
    assert all(body_literal.ast_type == clingo.ast.ASTType.Literal for body_literal in body)
    return clingo.ast.Rule(_loc, head, body)


def _create_aggregate(
    left_guard: Optional[clingo.ast.AST] = None,
    elements: Sequence[clingo.ast.AST] = (),
    right_guard: Optional[clingo.ast.AST] = None,
) -> clingo.ast.AST:
    assert left_guard is None or left_guard.ast_type == clingo.ast.ASTType.Guard
    assert all(element.ast_type == clingo.ast.ASTType.ConditionalLiteral for element in elements)
    assert right_guard is None or right_guard.ast_type == clingo.ast.ASTType.Guard
    return clingo.ast.Aggregate(_loc, left_guard, elements, right_guard)


def _create_guard(
    comparison: clingo.ast.ComparisonOperator = clingo.ast.ComparisonOperator.Equal,
    term: Optional[clingo.ast.AST] = None,
) -> clingo.ast.AST:
    if term is None:
        term = _create_function()
    return clingo.ast.Guard(comparison, term)


def _create_conditional_literal(
    literal: Optional[clingo.ast.AST] = None,
    condition: Sequence[clingo.ast.AST] = (),
) -> clingo.ast.AST:
    if literal is None:
        literal = _create_literal()
    assert literal.ast_type == clingo.ast.ASTType.Literal
    assert all(condition_literal.ast_type == clingo.ast.ASTType.Literal for condition_literal in condition)
    return clingo.ast.ConditionalLiteral(_loc, literal, condition)


def _create_literal(
    sign: clingo.ast.Sign = clingo.ast.Sign.NoSign,
    atom: Optional[clingo.ast.AST] = None,
) -> clingo.ast.AST:
    if atom is None:
        atom = _create_atom()
    assert atom.ast_type in (clingo.ast.ASTType.SymbolicAtom, clingo.ast.ASTType.Comparison)
    return clingo.ast.Literal(_loc, sign, atom)


def _create_comparison(term: Optional[clingo.ast.AST] = None, guards: Sequence[clingo.ast.AST] = ()) -> clingo.ast.AST:
    if term is None:
        term = _create_function()
    assert term.ast_type in (clingo.ast.ASTType.Function, clingo.ast.ASTType.SymbolicTerm, clingo.ast.ASTType.Variable)
    assert all(guard.ast_type == clingo.ast.ASTType.Guard for guard in guards)
    return clingo.ast.Comparison(term, guards)


def _create_atom(symbol: Optional[clingo.ast.AST] = None) -> clingo.ast.AST:
    if symbol is None:
        symbol = _create_function()
    return clingo.ast.SymbolicAtom(symbol)


def _create_function(
    name: str = "",
    arguments: Sequence[clingo.ast.AST] = (),
    external: int = False,
) -> clingo.ast.AST:
    return clingo.ast.Function(_loc, name, arguments, external)


def _create_symbolic_term(symbol: Optional[clingo.Symbol] = None) -> clingo.ast.AST:
    if symbol is None:
        symbol = clingo.Number(0)
    return clingo.ast.SymbolicTerm(_loc, symbol)


def _create_variable(name: str = "") -> clingo.ast.AST:
    return clingo.ast.Variable(_loc, name)
