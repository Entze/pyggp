from typing import Optional, Sequence

import clingo
import clingo.ast as clingo_ast

_pos = clingo_ast.Position("<pyggp>", 0, 0)
_loc = clingo_ast.Location(_pos, _pos)


def create_rule(head: Optional[clingo_ast.AST] = None, body: Sequence[clingo_ast.AST] = ()) -> clingo_ast.AST:
    if head is None:
        head = clingo_ast.Disjunction(_loc, ())
    assert head.ast_type in (clingo_ast.ASTType.Literal, clingo_ast.ASTType.Disjunction, clingo_ast.ASTType.Aggregate)
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
    return clingo_ast.SymbolicAtom(symbol=symbol)


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


def create_binary_operation(
    operator_type: clingo_ast.BinaryOperator = clingo_ast.BinaryOperator.Plus,
    left: Optional[clingo_ast.AST] = None,
    right: Optional[clingo_ast.AST] = None,
) -> clingo_ast.AST:
    if left is None:
        left = create_symbolic_term()
    if right is None:
        right = create_symbolic_term()
    assert left.ast_type in (clingo_ast.ASTType.Function, clingo_ast.ASTType.SymbolicTerm, clingo_ast.ASTType.Variable)
    assert right.ast_type in (clingo_ast.ASTType.Function, clingo_ast.ASTType.SymbolicTerm, clingo_ast.ASTType.Variable)
    return clingo_ast.BinaryOperation(_loc, operator_type, left, right)


def create_program(name: str = "base", parameters: Sequence[clingo_ast.AST] = ()) -> clingo_ast.AST:
    return clingo_ast.Program(_loc, name=name, parameters=parameters)


def create_id(name: str = "") -> clingo_ast.AST:
    return clingo_ast.Id(_loc, name)


Role = create_variable("Role")
Move = create_variable("Move")
Ply = create_variable("Ply")

DOES_AT_R_M_T_FUNC = create_function("does_at", (Role, Move, Ply))
DOES_AT_R_M_T_ATOM = create_atom(DOES_AT_R_M_T_FUNC)
DOES_AT_R_M_T_LIT = create_literal(atom=DOES_AT_R_M_T_ATOM)

LEGAL_AT_R_M_T_FUNC = create_function("legal_at", (Role, Move, Ply))
LEGAL_AT_R_M_T_ATOM = create_atom(LEGAL_AT_R_M_T_FUNC)
LEGAL_AT_R_M_T_LIT = create_literal(atom=LEGAL_AT_R_M_T_ATOM)

PICK_MOVE_COND_LIT = create_conditional_literal(
    literal=DOES_AT_R_M_T_LIT,
    condition=(LEGAL_AT_R_M_T_LIT,),
)

PICK_MOVE_GUARD_LEFT = create_guard(
    comparison=clingo_ast.ComparisonOperator.LessEqual,
    term=create_symbolic_term(clingo.Number(1)),
)
PICK_MOVE_GUARD_RIGHT = create_guard(
    comparison=clingo_ast.ComparisonOperator.LessEqual,
    term=create_symbolic_term(clingo.Number(1)),
)

PICK_MOVE_AGGR = create_aggregate(
    left_guard=PICK_MOVE_GUARD_LEFT,
    elements=(PICK_MOVE_COND_LIT,),
    right_guard=PICK_MOVE_GUARD_RIGHT,
)

ROLE_R_FUNC = create_function("role", (Role,))
ROLE_R_ATOM = create_atom(ROLE_R_FUNC)
ROLE_R_LIT = create_literal(atom=ROLE_R_ATOM)

CONTROL_R_FUNC = create_function("control", (Role,))
HOLDS_AT_CONTROL_T_FUNC = create_function("holds_at", (CONTROL_R_FUNC, Ply))
HOLDS_AT_CONTROL_T_ATOM = create_atom(HOLDS_AT_CONTROL_T_FUNC)
HOLDS_AT_CONTROL_T_LIT = create_literal(atom=HOLDS_AT_CONTROL_T_ATOM)

__time = create_function("__time")


def create_ply_clamp_comp(horizon: int) -> clingo_ast.AST:
    return create_comparison(
        term=create_symbolic_term(clingo.Number(0)),
        guards=(
            create_guard(clingo_ast.ComparisonOperator.LessEqual, Ply),
            create_guard(clingo_ast.ComparisonOperator.LessThan, create_symbolic_term(clingo.Number(horizon))),
        ),
    )


def create_ply_clamp_lit(horizon: int) -> clingo_ast.AST:
    return create_literal(atom=create_ply_clamp_comp(horizon))


PLY_EQUALS_TIME_COMP = create_comparison(
    term=Ply,
    guards=(create_guard(clingo_ast.ComparisonOperator.Equal, __time),),
)

PLY_EQUALS_TIME_LIT = create_literal(atom=PLY_EQUALS_TIME_COMP)


def create_pick_move_body(body: int) -> Sequence[clingo_ast.AST]:
    return (ROLE_R_LIT, HOLDS_AT_CONTROL_T_LIT, PLY_EQUALS_TIME_LIT, create_ply_clamp_lit(body))


def create_pick_move_rule(horizon: int) -> clingo_ast.AST:
    return create_rule(
        head=PICK_MOVE_AGGR,
        body=create_pick_move_body(horizon),
    )


PROGRAM_STATIC = create_program(name="static")
PROGRAM_DYNAMIC = create_program(name="dynamic", parameters=(create_id("__time"),))
PROGRAM_STATEMACHINE = create_program(name="statemachine", parameters=(create_id("__time"),))


def create_external(
    atom: Optional[clingo_ast.AST] = None,
    body: Sequence[clingo_ast.AST] = (),
    external_type: Optional[clingo_ast.AST] = None,
) -> clingo_ast.AST:
    if atom is None:
        atom = create_atom()
    if external_type is None:
        external_type = create_symbolic_term(symbol=clingo.Function("false"))
    assert atom.ast_type == clingo_ast.ASTType.SymbolicAtom
    assert external_type.ast_type == clingo_ast.ASTType.SymbolicTerm
    assert external_type.symbol.type == clingo.SymbolType.Function
    assert external_type.symbol.name in ("false", "true", "free")
    return clingo_ast.External(
        location=_loc,
        atom=atom,
        body=body,
        external_type=external_type,
    )


V = create_variable("V")

EXTERNAL_TRUE_INIT = create_external(
    atom=create_atom(symbol=create_function(name="true", arguments=(V,))),
    body=(create_literal(atom=create_atom(create_function(name="init", arguments=(V,)))),),
)

EXTERNAL_TRUE_NEXT = create_external(
    atom=create_atom(symbol=create_function(name="true", arguments=(V,))),
    body=(create_literal(atom=create_atom(create_function(name="next", arguments=(V,)))),),
)

EXTERNAL_DOES_ROLE_LEGAL = create_external(
    atom=create_atom(symbol=create_function(name="does", arguments=(Role, Move))),
    body=(
        create_literal(atom=create_atom(create_function(name="role", arguments=(Role,)))),
        create_literal(atom=create_atom(create_function(name="legal", arguments=(Role, Move)))),
    ),
)
EXTERNALS_TRUE = (EXTERNAL_TRUE_INIT, EXTERNAL_TRUE_NEXT)
EXTERNALS = (EXTERNAL_TRUE_INIT, EXTERNAL_TRUE_NEXT, EXTERNAL_DOES_ROLE_LEGAL)


def create_show_signature(name: str, arity: int = 0, positive=1) -> clingo_ast.AST:
    return clingo_ast.ShowSignature(location=_loc, name=name, arity=arity, positive=positive)


SHOW_ROLE = create_show_signature(name="role", arity=1)
SHOW_INIT = create_show_signature(name="init", arity=1)
SHOW_NEXT = create_show_signature(name="next", arity=1)
SHOW_SEES = create_show_signature(name="sees", arity=2)
SHOW_LEGAL = create_show_signature(name="legal", arity=2)
SHOW_GOAL = create_show_signature(name="goal", arity=2)
SHOW_TERMINAL = create_show_signature(name="terminal", arity=0)
HIDE = create_show_signature(name="", arity=0)


def create_show_term(term: Optional[clingo_ast.AST] = None, body: Sequence[clingo_ast.AST] = ()) -> clingo_ast.AST:
    if term is None:
        term = create_symbolic_term(symbol=clingo.Number(0))
    assert term.ast_type in (clingo_ast.ASTType.SymbolicTerm, clingo_ast.ASTType.Variable, clingo_ast.ASTType.Function)
    return clingo_ast.ShowTerm(location=_loc, term=term, body=body)


def get_holds_at_ply_show(ply: int) -> clingo_ast.AST:
    ply_term = create_symbolic_term(symbol=clingo.Number(ply))
    holds_at_ply = create_literal(atom=create_atom(create_function(name="holds_at", arguments=(V, ply_term))))
    return create_show_term(term=V, body=(holds_at_ply,))


def get_terminal_at_assertion(ply: int, *, invert: bool = False) -> clingo_ast.AST:
    ply_term = create_symbolic_term(symbol=clingo.Number(ply))
    sign = clingo_ast.Sign.NoSign if not invert else clingo_ast.Sign.Negation
    terminal_at_ply = create_literal(
        sign=sign,
        atom=create_atom(create_function(name="terminal_at", arguments=(ply_term,))),
    )
    return create_rule(body=(terminal_at_ply,))
