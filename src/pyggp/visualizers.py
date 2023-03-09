from typing import MutableSequence, Set

import rich.panel
import rich.pretty
import rich.table
from rich import print  # pylint: disable=redefined-builtin

from pyggp.gdl import Relation, Signature, State, Subrelation
from pyggp.match import MatchResult


class Visualizer:
    def __init__(self):
        self._states: MutableSequence[State | None] = []

    def update_state(self, state: State, move_nr: int | None = None) -> None:
        if move_nr is None:
            self._states.append(state)
            return
        if move_nr >= len(self._states):
            self._states.extend([None] * ((move_nr + 1) - len(self._states)))

        self._states[move_nr] = state

    def update_result(self, result: MatchResult) -> None:
        raise NotImplementedError

    def update_abort(self) -> None:
        raise NotImplementedError

    def draw(self) -> None:
        raise NotImplementedError


class NullVisualizer(Visualizer):  # pragma: no cover
    def update_state(self, state: State, move_nr: int | None = None) -> None:
        pass

    def update_result(self, result: MatchResult) -> None:
        pass

    def update_abort(self) -> None:
        pass

    def draw(self) -> None:
        pass


def _add_relation_to_subtable(
    subtable: rich.table.Table,
    signature: Signature | int | str,
    relations: Set[Subrelation],
    new_relations: Set[Subrelation],
    old_relations: Set[Subrelation],
    shorthand: bool = True,
) -> None:
    for relation in sorted((relations | old_relations)):
        if shorthand and isinstance(signature, Signature):
            if signature.arity > 1:
                display = str(relation.arguments)
            else:
                display = str(relation.arguments[0])
        else:
            display = str(relation)
        if relation not in old_relations:
            if relation in new_relations:
                prefix = "+ "
                style = "green"
            else:
                prefix = "  "
                style = "white"

            col1 = f"{prefix}{display}"
            col2 = ""
            if old_relations:
                cols = (col1, col2)
            else:
                cols = (col1,)
        else:
            col1 = ""
            col2 = f"- {display}"
            style = "red"
            cols = (col1, col2)
        subtable.add_row(*cols, style=style)


def _add_mutably_exclusive_relation_to_subtable(
    subtable: rich.table.Table,
    signature: Signature | int | str,
    relations: Set[Subrelation],
    new_relations: Set[Subrelation],
    old_relations: Set[Subrelation],
) -> None:
    new_relation = next(iter(relations), None)
    if new_relation in new_relations:
        new_prefix = "+ "
        new_style = "green"
    else:
        new_prefix = "  "
        new_style = "white"
    old_relation = next(iter(old_relations), None)
    if old_relation is not None:
        old_prefix = "- "
        old_style = "red"
    else:
        old_prefix = ""
        old_style = "white"
    if new_relation is not None:
        if signature.arity > 1:
            new_relation_str = str(new_relation.arguments)
        else:
            new_relation_str = str(new_relation.arguments[0])
    else:
        new_relation_str = ""
    if old_relation is not None:
        if signature.arity > 1:
            old_relation_str = str(old_relation.arguments)
        else:
            old_relation_str = str(old_relation.arguments[0])
    else:
        old_relation_str = ""
    if old_relation is not None:
        subtable.add_row(
            f"[{new_style}]{new_prefix}{new_relation_str}",
            f"[{old_style}]{old_prefix}{old_relation_str}",
        )
    else:
        subtable.add_row(f"[{new_style}]{new_prefix}{new_relation_str}")


class SimpleRichVisualizer(Visualizer):
    def __init__(self):
        super().__init__()
        self.aborted = False
        self.result = None
        self.last_drawn_state = -1
        self.known_signatures: Set[Signature] = set()
        self.singleton_signatures: Set[Signature] = set()

    @property
    def over(self) -> bool:
        return self.result is not None or self.aborted

    def draw(self) -> None:
        for i in range(self.last_drawn_state + 1, len(self._states) - 1):
            if self._states[i] is not None:
                self._draw_state(
                    self._states[i], self._states[i - 1] if i > 0 else self._states[0], len(self._states) - 1
                )
                self.last_drawn_state = i
        if self._states[-1] is not None and self.last_drawn_state < len(self._states) - 1:
            if len(self._states) == 1 and not self.over:
                self._draw_state(self._states[0], self._states[0], 0)
                self.last_drawn_state = 0
            if len(self._states) > 1:
                self._draw_state(self._states[-1], self._states[-2], len(self._states) - 1)
                self.last_drawn_state = len(self._states) - 1
        self.last_drawn_state = len(self._states) - 1
        if self.over:
            self._draw_state(self._states[-1], self._states[-1], len(self._states) - 1)
            self.last_drawn_state = len(self._states) - 1
            if self.aborted:
                panel_title = "[bold red]Aborted match[/bold red]"
            else:
                panel_title = "[bold green]Finished match[/bold green]"
            panel = rich.panel.Panel(rich.pretty.Pretty(self.result.utilities), title=panel_title, title_align="center")
            print(panel)

    def update_result(self, result: MatchResult) -> None:
        self.result = result

    def update_abort(self) -> None:
        self.aborted = True

    def _draw_state(self, state: State, last_state: State | None, move_nr: int) -> None:
        if last_state is None:
            last_state = set()
        signatures_sequence = tuple(
            relation.signature if isinstance(relation, Relation) else relation for relation in state
        )
        signatures_count_map = {signature: signatures_sequence.count(signature) for signature in signatures_sequence}
        self.known_signatures.update(relation.signature for relation in state)
        self.singleton_signatures.update(signature for signature, count in signatures_count_map.items() if count <= 1)
        self.singleton_signatures.difference_update(
            signature for signature, count in signatures_count_map.items() if count > 1
        )

        control_signature = Signature("control", 1)
        self.singleton_signatures.discard(control_signature)
        self.known_signatures.discard(control_signature)
        if len(self.singleton_signatures) == 1 and len(self.known_signatures) == 1:
            self.singleton_signatures.clear()
        view = rich.table.Table(title=f"State@{move_nr}", expand=False)
        subtables = []

        for signature in (control_signature, *sorted(self.known_signatures)):
            if signature not in self.singleton_signatures:
                view.add_column(signature, justify="center")
                relations = set(
                    relation
                    for relation in state
                    if (isinstance(relation, Relation) and relation.signature == signature) or (relation == signature)
                )
                new_relations = set(relation for relation in state - last_state if relation.signature == signature)
                old_relations = set(relation for relation in last_state - state if relation.signature == signature)
                subtable = rich.table.Table(show_header=False, expand=False)
                subtable.add_column("", style="white", justify="right")
                if old_relations:
                    subtable.add_column("-", style="red", justify="left")
                if len(relations) > 1 or len(old_relations) > 1:
                    _add_relation_to_subtable(subtable, signature, relations, new_relations, old_relations)
                else:
                    _add_mutably_exclusive_relation_to_subtable(
                        subtable, signature, relations, new_relations, old_relations
                    )

                subtables.append(subtable)

        if self.singleton_signatures:
            view.add_column("True", justify="center")
            relations = set(
                relation
                for relation in state
                if (isinstance(relation, Relation) and relation.signature in self.singleton_signatures)
                or relation in self.singleton_signatures
            )
            new_relations = set(
                relation
                for relation in state - last_state
                if (isinstance(relation, Relation) and relation.signature in self.singleton_signatures)
                or relation in self.singleton_signatures
            )
            old_relations = set(
                relation
                for relation in last_state - state
                if (isinstance(relation, Relation) and relation.signature in self.singleton_signatures)
                or relation in self.singleton_signatures
            )
            subtable = rich.table.Table(show_header=False, expand=False)
            subtable.add_column("", style="white", justify="right")
            if old_relations:
                subtable.add_column("-", style="red", justify="left")
            _add_relation_to_subtable(
                subtable, Signature("True", 0), relations, new_relations, old_relations, shorthand=False
            )

            subtables.append(subtable)

        view.add_row(*subtables)

        print(view)
