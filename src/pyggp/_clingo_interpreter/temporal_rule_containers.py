import collections
from dataclasses import dataclass
from typing import Iterator, Mapping, MutableMapping, Optional, Sequence, Set, Tuple, Union

import clingo
from clingo import ast as clingo_ast
from typing_extensions import Self

from pyggp import _clingo as clingo_helper
from pyggp import game_description_language as gdl


@dataclass(frozen=True)
class TemporalInformation:
    name: str
    time: Union[int, str, None] = None
    timeshift: Optional[int] = None

    @classmethod
    def static(cls, name: str) -> Self:
        return cls(name=f"{name}_static", time=None)

    @classmethod
    def dynamic(cls, name: str, time: Union[int, str] = "__time", timeshift: Optional[int] = None) -> Self:
        return cls(name=f"{name}_at", time=time, timeshift=timeshift)


Categorization = Mapping[gdl.Relation.Signature, TemporalInformation]
MutableCategorization = MutableMapping[gdl.Relation.Signature, TemporalInformation]
role_signature = gdl.Relation.Signature(name="role", arity=1)
init_signature = gdl.Relation.Signature(name="init", arity=1)
next_signature = gdl.Relation.Signature(name="next", arity=1)
true_signature = gdl.Relation.Signature(name="true", arity=1)
does_signature = gdl.Relation.Signature(name="does", arity=2)
sees_signature = gdl.Relation.Signature(name="sees", arity=2)
legal_signature = gdl.Relation.Signature(name="legal", arity=2)
goal_signature = gdl.Relation.Signature(name="goal", arity=2)
terminal_signature = gdl.Relation.Signature(name="terminal", arity=0)
base_static_categorization: Categorization = {
    role_signature: TemporalInformation(name="role"),
    init_signature: TemporalInformation(name="holds_at", time=0, timeshift=None),
}
base_statemachine_categorization: Categorization = {
    next_signature: TemporalInformation(name="holds_at", time="__time", timeshift=1),
}
base_dynamic_categorization: Categorization = {
    true_signature: TemporalInformation(name="holds_at", time="__time"),
    does_signature: TemporalInformation(name="does_at", time="__time"),
    sees_signature: TemporalInformation(name="sees_at", time="__time"),
    legal_signature: TemporalInformation(name="legal_at", time="__time"),
    goal_signature: TemporalInformation(name="goal_at", time="__time"),
    terminal_signature: TemporalInformation(name="terminal_at", time="__time"),
}


def create_temporal_function(
    name: str,
    arguments: Sequence[clingo_ast.AST],
    time_: Union[int, str, None],
    timeshift: Optional[int],
) -> clingo_ast.AST:
    if time_ is None:
        return clingo_helper.create_function(name=name, arguments=arguments)
    if isinstance(time_, str):
        time_ast = clingo_helper.create_function(name=time_)
    else:
        assert isinstance(time_, int)
        time_ast = clingo_helper.create_symbolic_term(symbol=clingo.Number(time_))

    if timeshift is not None:
        timeshift_ast = clingo_helper.create_symbolic_term(symbol=clingo.Number(timeshift))
        time_ast = clingo_helper.create_binary_operation(
            operator_type=clingo_ast.BinaryOperator.Plus,
            left=time_ast,
            right=timeshift_ast,
        )
    return clingo_helper.create_function(name=name, arguments=(*arguments, time_ast))


@dataclass(frozen=True)
class TemporalRuleContainer:
    static: Sequence[clingo_ast.AST]
    dynamic: Sequence[clingo_ast.AST]
    statemachine: Sequence[clingo_ast.AST]

    @property
    def rules(self) -> Iterator[clingo_ast.AST]:
        yield from self.static
        yield from self.dynamic
        yield from self.statemachine

    @classmethod
    def from_ruleset(cls, ruleset: gdl.Ruleset) -> Self:
        static_categorization, dynamic_categorization = TemporalRuleContainer.categorize_signatures(ruleset.rules)
        return cls.transform_sentences(
            sentences=ruleset.rules,
            static_categorization=static_categorization,
            dynamic_categorization=dynamic_categorization,
        )

    @classmethod
    def transform_sentences(
        cls,
        sentences: Sequence[gdl.Sentence],
        static_categorization: Categorization,
        dynamic_categorization: Categorization,
    ) -> Self:
        visitor = TemporalTransformer(
            static=static_categorization,
            dynamic=dynamic_categorization,
            statemachine=base_statemachine_categorization,
        )

        static = (
            clingo_helper.PROGRAM_STATIC,
            *(
                visitor.visit(sentence.as_clingo_ast())
                for sentence in sentences
                if sentence.head.signature in static_categorization
            ),
        )
        statemachine = (
            clingo_helper.PROGRAM_STATEMACHINE,
            *(
                visitor.visit(sentence.as_clingo_ast())
                for sentence in sentences
                if sentence.head.signature in base_statemachine_categorization
            ),
        )
        dynamic = (
            clingo_helper.PROGRAM_DYNAMIC,
            *(
                visitor.visit(sentence.as_clingo_ast())
                for sentence in sentences
                if sentence.head.signature in dynamic_categorization
            ),
        )
        return TemporalRuleContainer(static=static, dynamic=dynamic, statemachine=statemachine)

    @staticmethod
    def categorize_signatures(
        sentences: Sequence[gdl.Sentence],
    ) -> Tuple[Categorization, Categorization]:
        static_categorization: MutableCategorization = {**base_static_categorization}
        dynamic_categorization: MutableCategorization = {**base_dynamic_categorization}
        body_only_signatures: Set[gdl.Relation.Signature] = set()
        bodysignature_to_headsignatures: MutableMapping[
            gdl.Relation.Signature,
            Set[gdl.Relation.Signature],
        ] = collections.defaultdict(set)
        for sentence in sentences:
            head, body = sentence.head, sentence.body
            for literal in body:
                bodysignature_to_headsignatures[literal.atom.signature].add(head.signature)
                if not any(
                    literal.atom.signature in categorization
                    for categorization in (
                        static_categorization,
                        dynamic_categorization,
                        base_statemachine_categorization,
                    )
                ):
                    body_only_signatures.add(literal.atom.signature)

        dynamic_signatures = set(dynamic_categorization.keys())
        changes = True
        while changes:
            dynamic_signature_len = len(dynamic_signatures)
            for signature, signatures in bodysignature_to_headsignatures.items():
                if signature in dynamic_signatures:
                    dynamic_signatures.update(signatures)
            changes = dynamic_signature_len < len(dynamic_signatures)

        for sentence in sentences:
            head = sentence.head
            body_only_signatures.discard(head.signature)
            if any(
                head.signature in signatures
                for signatures in (static_categorization, dynamic_categorization, base_statemachine_categorization)
            ):
                continue
            if head.signature in dynamic_signatures:
                dynamic_categorization[head.signature] = TemporalInformation.dynamic(name=head.name)
            else:
                static_categorization[head.signature] = TemporalInformation.static(name=head.name)

        for signature in body_only_signatures:
            static_categorization[signature] = TemporalInformation(name=signature.name)

        assert set(static_categorization.keys()).isdisjoint(
            dynamic_categorization.keys(),
        ), "Guarantee: categorizations are disjoint"
        return static_categorization, dynamic_categorization


@dataclass(frozen=True)
class TemporalTransformer(clingo_ast.Transformer):
    static: Mapping[gdl.Relation.Signature, TemporalInformation]
    dynamic: Mapping[gdl.Relation.Signature, TemporalInformation]
    statemachine: Mapping[gdl.Relation.Signature, TemporalInformation]

    def visit_Function(self, function: clingo_ast.AST) -> clingo_ast.AST:
        original_name = function.name if function.name != "" else None
        original_arity = len(function.arguments)
        original_signature = gdl.Relation.Signature(name=original_name, arity=original_arity)
        temporal_information = None
        for mapping in (self.static, self.dynamic, self.statemachine):
            if original_signature in mapping:
                temporal_information = mapping[original_signature]
                break
        if temporal_information is None:
            return function
        return create_temporal_function(
            name=temporal_information.name,
            arguments=function.arguments,
            time_=temporal_information.time,
            timeshift=temporal_information.timeshift,
        )
