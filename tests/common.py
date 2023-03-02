# pylint: disable=missing-docstring,invalid-name,unused-argument
import time
import random
from typing import FrozenSet, Mapping, Sequence

from pyggp.actors import Actor, LocalActor
from pyggp.agents import Agent
from pyggp.gameclocks import GameClockConfiguration
from pyggp.gdl import Role, Ruleset, State, Move, Relation, Play, Sentence, Literal, Variable
from pyggp.interpreters import Interpreter
from pyggp.match import MatchConfiguration, Match

SLEEP_TIME: float = 0.25


class MockAgent(Agent):
    def __init__(self) -> None:
        super().__init__()
        self.called_calc_move = False
        self.called_prepare_match = False
        self.called_abort_match = False
        self.called_conclude_match = False
        self.next_move = Relation("called")

    def prepare_match(
        self,
        role: Role,
        ruleset: Ruleset,
        startclock_config: GameClockConfiguration,
        playclock_config: GameClockConfiguration,
    ) -> None:
        self.called_prepare_match = True

    def abort_match(self) -> None:
        self.called_abort_match = True

    def conclude_match(self, view: State) -> None:
        self.called_conclude_match = True

    def calculate_move(self, move_nr: int, total_time_ns: int, view: State) -> Move:
        self.called_calc_move = True
        return self.next_move


class MockTimeoutAgent(MockAgent):
    def __init__(
        self,
        timeout_prepare_match: bool = True,
        timeout_abort_match: bool = True,
        timeout_conclude_match: bool = True,
        timeout_calculate_move: bool = True,
        sleep_time: float = SLEEP_TIME,
    ):
        super().__init__()
        self.timeout_prepare_match = timeout_prepare_match
        self.timeout_abort_match = timeout_abort_match
        self.timeout_conclude_match = timeout_conclude_match
        self.timeout_calculate_move = timeout_calculate_move
        self.sleep_time = sleep_time

    def prepare_match(
        self,
        role: Role,
        ruleset: Ruleset,
        startclock_config: GameClockConfiguration,
        playclock_config: GameClockConfiguration,
    ) -> None:
        if self.timeout_prepare_match:
            time.sleep(self.sleep_time)
        super().prepare_match(role, ruleset, startclock_config, playclock_config)

    def abort_match(self) -> None:
        if self.timeout_abort_match:
            time.sleep(self.sleep_time)
        super().abort_match()

    def conclude_match(self, view: State) -> None:
        if self.timeout_conclude_match:
            time.sleep(self.sleep_time)
        super().conclude_match(view)

    def calculate_move(self, move_nr: int, total_time_ns: int, view: State) -> Move:
        if self.timeout_calculate_move:
            time.sleep(self.sleep_time)
        return super().calculate_move(move_nr, total_time_ns, view)


class MockRetentionAgent(MockAgent):
    def __init__(self):
        super().__init__()
        self.role = None
        self.ruleset = None
        self.startclock_config = None
        self.playclock_config = None
        self.move_nrs = []
        self.total_times_ns = []
        self.views = []
        self.conclusion_view = None

    def prepare_match(
        self,
        role: Role,
        ruleset: Ruleset,
        startclock_config: GameClockConfiguration,
        playclock_config: GameClockConfiguration,
    ) -> None:
        self.role = role
        self.ruleset = ruleset
        self.startclock_config = startclock_config
        self.playclock_config = playclock_config
        super().prepare_match(role, ruleset, startclock_config, playclock_config)

    def conclude_match(self, view: State) -> None:
        self.conclusion_view = view
        super().conclude_match(view)

    def calculate_move(self, move_nr: int, total_time_ns: int, view: State) -> Move:
        self.move_nrs.append(move_nr)
        self.total_times_ns.append(total_time_ns)
        self.views.append(view)
        return super().calculate_move(move_nr, total_time_ns, view)


class MockRuleset1Interpreter(Interpreter):
    def __init__(self):
        super().__init__(mock_ruleset_1)

    def get_roles(self) -> FrozenSet[Role]:
        return frozenset({Relation("p1")})

    def get_init_state(self) -> State:
        return frozenset({Relation.control(Relation("p1"))})

    def get_next_state(self, state: State, *plays: Play) -> State:
        if Relation.does(Relation("p1"), 1) in plays:
            return frozenset({Relation("won")})
        if Relation.does(Relation("p1"), 2) in plays:
            return frozenset({Relation("lost")})
        return frozenset({Relation.control(Relation("p1"))})

    def get_sees(self, state: State) -> Mapping[Role, State]:
        return {Relation("p1"): state}

    def get_legal_moves(self, state: State) -> Mapping[Role, FrozenSet[Move]]:
        return {Relation("p1"): frozenset({1, 2, 3})}

    def get_goals(self, state: State) -> Mapping[Role, int | None]:
        if Relation("won") in state:
            return {Relation("p1"): 1}
        if Relation("lost") in state:
            return {Relation("p1"): 0}
        return {Relation("p1"): None}

    def is_terminal(self, state: State) -> bool:
        return Relation("won") in state or Relation("lost") in state


mock_ruleset_1 = Ruleset(
    (
        Sentence.fact(Relation.role(Relation("p1"))),
        Sentence.fact(Relation.init(Relation.control(Relation("p1")))),
        Sentence.rule(Relation.next(Relation("won")), (Literal(Relation.does(Relation("p1"), 1)),)),
        Sentence.rule(Relation.next(Relation("lost")), (Literal(Relation.does(Relation("p1"), 2)),)),
        Sentence.rule(Relation.next(Relation.control(Relation("p1"))), (Literal(Relation.does(Relation("p1"), 3)),)),
        Sentence.fact(Relation.legal(Relation("p1"), 1)),
        Sentence.fact(Relation.legal(Relation("p1"), 2)),
        Sentence.fact(Relation.legal(Relation("p1"), 3)),
        Sentence.rule(Relation.goal(Relation("p1"), 1), (Literal(Relation("won")),)),
        Sentence.rule(Relation.goal(Relation("p1"), 0), (Literal(Relation("lost")),)),
        Sentence.rule(Relation.terminal(), (Literal(Relation("won")),)),
        Sentence.rule(Relation.terminal(), (Literal(Relation("lost")),)),
    )
)


class MockRuleset2Interpreter(Interpreter):
    def __init__(self):
        super().__init__(mock_ruleset_2)

    def get_roles(self) -> FrozenSet[Role]:
        return frozenset({Relation("p1"), Relation("p2")})

    def get_init_state(self) -> State:
        return frozenset({Relation.control(Relation("p1"))})

    def get_next_state(self, state: State, *plays: Play) -> State:
        play, *_ = plays
        role, move = play.arguments
        if move == 1:
            return frozenset({Relation("won", (role,))})
        if move == 2:
            return frozenset({Relation("lost", (role,))})
        if move == 3:
            return frozenset({Relation.control(Relation("p1"))})
        if move == 4:
            return frozenset({Relation.control(Relation("p2"))})
        raise ValueError(f"Invalid move: {move}")

    def get_sees(self, state: State) -> Mapping[Role, State]:
        return {role: state for role in self.get_roles()}

    def get_legal_moves(self, state: State) -> Mapping[Role, FrozenSet[Move]]:
        return {role: frozenset({1, 2, 3, 4}) for role in self.get_roles()}

    def get_goals(self, state: State) -> Mapping[Role, int | None]:
        default = {role: None for role in self.get_roles()}
        for relation in state:
            if isinstance(relation, Relation) and relation.match("won", 1):
                return default | {relation.arguments[0]: 1}
            if isinstance(relation, Relation) and relation.match("lost", 1):
                return default | {relation.arguments[0]: 0}
        return default

    def is_terminal(self, state: State) -> bool:
        return any(relation.match("won", 1) for relation in state if isinstance(relation, Relation)) or any(
            relation.match("lost", 1) for relation in state if isinstance(relation, Relation)
        )


mock_ruleset_2 = Ruleset(
    (
        Sentence.fact(Relation.role(Relation("p1"))),
        Sentence.fact(Relation.role(Relation("p2"))),
        Sentence.fact(Relation.init(Relation.control(Relation("p1")))),
        Sentence.rule(Relation.next(Relation("won", (Relation("p1"),))), (Literal(Relation.does(Relation("p1"), 1)),)),
        Sentence.rule(Relation.next(Relation("lost", (Relation("p1"),))), (Literal(Relation.does(Relation("p1"), 2)),)),
        Sentence.rule(Relation.next(Relation.control(Relation("p1"))), (Literal(Relation.does(Relation("p1"), 3)),)),
        Sentence.rule(Relation.next(Relation.control(Relation("p2"))), (Literal(Relation.does(Relation("p1"), 4)),)),
        Sentence.rule(Relation.next(Relation("won", (Relation("p2"),))), (Literal(Relation.does(Relation("p2"), 1)),)),
        Sentence.rule(Relation.next(Relation("lost", (Relation("p2"),))), (Literal(Relation.does(Relation("p2"), 2)),)),
        Sentence.rule(Relation.next(Relation.control(Relation("p1"))), (Literal(Relation.does(Relation("p2"), 3)),)),
        Sentence.rule(Relation.next(Relation.control(Relation("p2"))), (Literal(Relation.does(Relation("p2"), 4)),)),
        Sentence.fact(Relation.legal(Relation("p1"), 1)),
        Sentence.fact(Relation.legal(Relation("p1"), 2)),
        Sentence.fact(Relation.legal(Relation("p1"), 3)),
        Sentence.fact(Relation.legal(Relation("p1"), 4)),
        Sentence.fact(Relation.legal(Relation("p2"), 1)),
        Sentence.fact(Relation.legal(Relation("p2"), 2)),
        Sentence.fact(Relation.legal(Relation("p2"), 3)),
        Sentence.fact(Relation.legal(Relation("p2"), 4)),
        Sentence.rule(Relation.goal(Relation("p1"), 1), (Literal(Relation("won", (Relation("p1"),))),)),
        Sentence.rule(Relation.goal(Relation("p1"), 0), (Literal(Relation("lost", (Relation("p1"),))),)),
        Sentence.rule(Relation.goal(Relation("p2"), 1), (Literal(Relation("won", (Relation("p2"),))),)),
        Sentence.rule(Relation.goal(Relation("p2"), 0), (Literal(Relation("lost", (Relation("p2"),))),)),
        Sentence.rule(Relation.terminal(), (Literal(Relation("won", (Variable("_P"),))),)),
        Sentence.rule(Relation.terminal(), (Literal(Relation("lost", (Variable("_P"),))),)),
    )
)


class MockRuleset3Interpreter(Interpreter):
    def __init__(self):
        super().__init__(mock_ruleset_3)

    def get_roles(self) -> FrozenSet[Role]:
        return frozenset({Relation("p1"), Relation("p2"), Relation("p3")})

    def get_init_state(self) -> State:
        return frozenset(
            {Relation.control(Relation("p1")), Relation.control(Relation("p2")), Relation.control(Relation("p3"))}
        )

    def get_next_state(self, state: State, *plays: Play) -> State:
        return frozenset({Relation("dibbed", (role,)) for role in self.get_roles()})

    def get_sees(self, state: State) -> Mapping[Role, State]:
        return {role: state for role in self.get_roles()}

    def get_legal_moves(self, state: State) -> Mapping[Role, FrozenSet[Move]]:
        return {role: frozenset({Relation("dibs")}) for role in self.get_roles()}

    def get_goals(self, state: State) -> Mapping[Role, int | None]:
        return {role: 1 for role in self.get_roles()}

    def is_terminal(self, state: State) -> bool:
        return True


mock_ruleset_3 = Ruleset(
    (
        Sentence.fact(Relation.role(Relation("p1"))),
        Sentence.fact(Relation.role(Relation("p2"))),
        Sentence.fact(Relation.role(Relation("p3"))),
        Sentence.fact(Relation.init(Relation.control(Relation("p1")))),
        Sentence.fact(Relation.init(Relation.control(Relation("p2")))),
        Sentence.fact(Relation.init(Relation.control(Relation("p3")))),
        Sentence.rule(
            Relation.next(Relation("dibbed", (Variable("R"),))),
            (Literal(Relation.role(Variable("R"))), Literal(Relation.does(Variable("R"), Relation("dibs")))),
        ),
        Sentence.rule(Relation.legal(Variable("R"), Relation("dibs")), (Literal(Relation.role(Variable("R"))),)),
        Sentence.rule(
            Relation.goal(Variable("R"), 1),
            (Literal(Relation.role(Variable("R"))), Literal(Relation("dibbed", (Variable("R"),)))),
        ),
        Sentence.rule(
            Relation.terminal(), (Literal(Relation.role(Variable("R"))), Literal(Relation("dibbed", (Variable("R"),))))
        ),
    )
)


def mock_match_configuration(
    ruleset: Ruleset | None = None,
    interpreter: Interpreter | None = None,
    agents: Sequence[Agent] = (),
    actors: Sequence[Actor] = (),
    startclock_configs: Mapping[Role, GameClockConfiguration] | None = None,
    playclock_configs: Mapping[Role, GameClockConfiguration] | None = None,
) -> MatchConfiguration:
    if ruleset is None:
        ruleset = mock_ruleset_1
    if interpreter is None:
        interpreter = MockRuleset1Interpreter()
    if not agents:
        agents = (MockAgent(),)
    if not actors:
        actors = tuple(LocalActor(agent) for agent in agents)
    if startclock_configs is None:
        startclock_configs = {
            Relation(f"p{n}"): GameClockConfiguration(total_time=0.0, increment=0.0, delay=60.0)
            for n in range(1, len(actors) + 1)
        }
    if playclock_configs is None:
        playclock_configs = {
            Relation(f"p{n}"): GameClockConfiguration(total_time=0.0, increment=0.0, delay=60.0)
            for n in range(1, len(actors) + 1)
        }

    return MatchConfiguration(
        ruleset=ruleset,
        interpreter=interpreter,
        role_actor_map={Relation(f"p{n}"): actor for n, actor in enumerate(actors, start=1)},
        startclock_configs=startclock_configs,
        playclock_configs=playclock_configs,
    )


def mock_match(
    ruleset: Ruleset | None = None,
    interpreter: Interpreter | None = None,
    agents: Sequence[Agent] = (),
    actors: Sequence[Actor] = (),
    startclock_configs: Mapping[Role, GameClockConfiguration] | None = None,
    playclock_configs: Mapping[Role, GameClockConfiguration] | None = None,
    slack: float = 2.5,
    start_match: bool = True,
    finish_match: bool = False,
) -> Match:
    match = Match(
        match_configuration=mock_match_configuration(
            ruleset, interpreter, agents, actors, startclock_configs, playclock_configs
        ),
        slack=slack,
    )
    if start_match:
        match.start_match()

    if finish_match:
        while not match.is_finished:
            role_move_map = match._interpreter.get_legal_moves(match.states[-1])
            for role, move in role_move_map.items():
                actor = match._role_actor_map[role]
                if isinstance(actor, LocalActor) and isinstance(actor.agent, MockAgent):
                    actor.agent.next_move = random.choice(tuple(role_move_map[role]))
            match.execute_ply()
    return match
