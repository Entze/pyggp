"""Provides the `Ruleset` class and supporting classes and functions."""
import collections
from dataclasses import dataclass, field
from typing import Iterable, Optional, Sequence

from typing_extensions import Self

from pyggp.game_description_language.sentences import Sentence


def get_related_rules(rules: Sequence[Sentence], name: Optional[str] = None, arity: int = 0) -> Sequence[Sentence]:
    """Gets all the rules that are related to the given name and arity.

    A rule is related if its head matches the signature defined by name and arity, or any of the related rules'
    relations in the body literals' atoms match its head.

    Args:
        rules: The rules to search through.
        name: The name of the relation to match.
        arity: The arity of the relation to match.

    """
    related_rules = {rule for rule in rules if rule.head.matches_signature(name, arity)}
    visited_rules = collections.defaultdict(bool, {rule: True for rule in related_rules})
    worked_relations = {rule.head for rule in related_rules}
    stack = [literal.atom for rule in related_rules for literal in rule.body]
    while stack:
        relation = stack.pop()
        if relation in worked_relations:
            continue
        worked_relations.add(relation)
        for rule in rules:
            if visited_rules[rule]:
                continue
            if rule.head.unifies(relation):
                related_rules.add(rule)
                visited_rules[rule] = True
                stack.extend(literal.atom for literal in rule.body if literal.atom not in worked_relations)

    return sorted(related_rules, key=rules.index)


@dataclass(frozen=True)
class Ruleset:
    """Representation of a ruleset.

    Rulesets are a sequence of sentences (rules).

    """

    # region Attributes and Properties

    rules: Sequence[Sentence] = field(default_factory=tuple)
    "Rules of the ruleset in the original order."
    role_rules: Sequence[Sentence] = field(default_factory=tuple, repr=False)
    "Subsequence of `rules` that are role rules."
    init_rules: Sequence[Sentence] = field(default_factory=tuple, repr=False)
    "Subsequence of `rules` that are init rules."
    next_rules: Sequence[Sentence] = field(default_factory=tuple, repr=False)
    "Subsequence of `rules` that are next rules."
    sees_rules: Sequence[Sentence] = field(default_factory=tuple, repr=False)
    "Subsequence of `rules` that are sees rules."
    legal_rules: Sequence[Sentence] = field(default_factory=tuple, repr=False)
    "Subsequence of `rules` that are legal rules."
    goal_rules: Sequence[Sentence] = field(default_factory=tuple, repr=False)
    "Subsequence of `rules` that are goal rules."
    terminal_rules: Sequence[Sentence] = field(default_factory=tuple, repr=False)
    "Subsequence of `rules` that are terminal rules."

    @property
    def infix_str(self) -> str:
        """Infix string representation of the ruleset."""
        return "\n".join(rule.infix_str for rule in self.rules)

    # endregion

    # region Constructors

    @classmethod
    def from_rules(cls, rules: Iterable[Sentence] = ()) -> Self:
        """Create a ruleset from a sequence of rules.

        This is the preferred constructor for `Ruleset` as it takes care of sorting the rules into the correct
        subsequences.

        """
        rules = tuple(rules)
        role_rules = tuple(get_related_rules(rules, "role", 1))
        init_rules = tuple(get_related_rules(rules, "init", 1))
        next_rules = tuple(get_related_rules(rules, "next", 1))
        sees_rules = tuple(get_related_rules(rules, "sees", 2))
        legal_rules = tuple(get_related_rules(rules, "legal", 2))
        goal_rules = tuple(get_related_rules(rules, "goal", 2))
        terminal_rules = tuple(get_related_rules(rules, "terminal", 0))
        return cls(
            rules=rules,
            role_rules=role_rules,
            init_rules=init_rules,
            next_rules=next_rules,
            sees_rules=sees_rules,
            legal_rules=legal_rules,
            goal_rules=goal_rules,
            terminal_rules=terminal_rules,
        )

    # endregion

    # region Magic Methods

    def __str__(self) -> str:
        """Return the infix string representation of the ruleset.

        Returns:
            String representation of the ruleset

        """
        return self.infix_str

    def __rich__(self) -> str:
        return f"Ruleset\\[#rules={len(self.rules)}]()"
