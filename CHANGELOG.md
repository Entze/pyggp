## 0.1.0 (2023-04-10)

### Feat

- **pyggp.cli.commands.main**: add sys-info callback
- **pyggp.cli.commands.match**: run conclude or abort on matches that stopped
- **pyggp.match.Match**: add method for ranking after match concluded
- **pyggp.visualizers**: add presentation of result of the match
- **pyggp.match**: make module stable
- **pyggp.match**: use new \_SignalProcessor class
- **pyggp.interpreters.ClingoInterpreter**: forward clingo logs
- **pyggp.cli.commands.match**: allow loading (multiple) files
- **pyggp.agents.base_agents.HumanAgent**: improve reporting
- **pyggp.gameclocks.GameClock.get_timeout**: add special case for non-timeout clocks
- **pyggp.game_description_language**: print and convert distinct relations correctly
- **pyggp.game_description_language.grammar**: add special case for distinct
- **pyggp.\_logging.format_timedelta**: add case for infinite time
- WIP for new match code
- **pyggp.match**: rewrite match WIP
- **pyggp.game_description_language**: implement proper parser
- **games**: add gdl of games
- **pyggp.visualizers**: make module stable
- **pyggp.agents.base_agents**: make module stable
- **pyggp.agents**: make module stable
- **pyggp.gameclocks**: make module stable
- WIP current state of the project
- **pyggp.game_description_language**: add feature parity to old gdl module
- **pyggp.game_description_language**: start refactoring gdl module
- **pyggp.heuristics**: add module
- **pyggp.gameclocks**: make module stable
- **pyggp.__main__.py**: make entry point stable
- **pyggp.exceptions.node_exceptions**: add module
- **pyggp.exceptions.match_exceptions**: make module stable
- **pyggp.exceptions.interpreter_exceptions**: make module stable
- **pyggp.exceptions.agent_exceptions**: make module stable
- **pyggp.exceptions.actor_exceptions**: make module stable
- **pyggp.\_logging**: make module stable
- **pyggp.\_clingo**: add clingo helpers
- **pyggp**: add descriptive error message when python version is not supported
- **pyggp.gdl.Ruleset**: make rules arg optional
- **pyggp.actors**: add module to API
- **pyggp.agents**: add HumanAgent
- improve logging through rich methods
- **pyggp.Match**: rewrite execute_ply loop to display time left per agent
- **pyggp.actors.Actor**: expand class to accomodate human actors
- **pyggp.exceptions/actor_exceptions**: add custom TimeoutError and ValueError variants for ActorErrors
- **pyggp.gameclocks.GameClock**: add no timeout capabilities
- **pyggp.\_logging**: add inflect method
- **pyggp.agents**: add RandomAgent

### Fix

- **pyggp.interpreters.ClingoInterpreter.get_goals**: default to utility None
- **pyggp.match**: hack the type system such that it is supported by python 3.8
- **pyggp.match**: catch TimeoutError of ThreadPoolExecutor
- **pyggp.agents.base_agents**: use new ClingoInterpreter constructor
- **pyggp.visualizers.SimpleVisualizer**: correct edge cases in drawing state
- **pyggp.match**: make typechecking backwards compatible with python3.8
- make backwards compatible with python3.8
- **pyggp.heuristics**: use new gdl API
- **pyggp.agents.base_agents.HumanAgent**: use new gdl API
- **pyggp.match.Match.execute_ply**: add break condition on exceptions
- handle Random role

### Refactor

- **pyggp.agents.base_agents.Agent**: make calculate_move an abstract method
- **pyggp.interpreters**: fix ruff's suggestions
- **pyggp.agents.tree_agents**: remove unused file
- **pyggp.actors**: use unified naming of configuration instead of config
- **pyggp.agents.tree_agents**: remove old WIP code
- **pyggp.gdl**: remove old gdl API
- **pyggp.gameclocks**: run black on files
- **pyggp.games**: separate ruleset from rules
- **pyggp.actors**: use new exception names
- remove old tests
- reformat and refactor old tests
- **pyggp.actors**: clean whitespace
- backport the project to python3.8
- **pyggp.\_logging**: remove unneccessary variables
- run isort
- **pyggp.visualizers.SimpleRichVisualizer**: rename panels for end of game
- run isort on all files

## 0.0.0 (2023-03-07)

### Feat

- **pyggp.app**: add --version flag
- **pyggp.interpreters.Interpreter**: add repr
- add WIP cli
- **pyggp.gameclocks.GameClockConfiguration**: add alternative constructor to parse from str
- **pyggp.agents.Agent**: add repr and type abstract classes
- **pyggp.actors.Actor**: add repr method
- **pyggp.gdl**: add methods to repr classes
- **pyggp.Relation**: add methods to compare Relations
- **pyggp.commands**: add orchestrate_match
- **pyggp.visualizers**: add Visualizer and NullVisualizer
- **pyggp.interpreters**: add get_legal_moves_by_role
- **pyggp.agents**: add ArbitraryAgent
- **pyggp.exceptions.match_exceptions**: add move information to exception
- **pyggp.match**: add Match
- add WIP of match
- add actors and agents
- add Interpreter, with default impl and tests
- **pyggp.gdl.state**: expand state to include all subrelations
- **pyggp.games**: add minipoker
- **pyggp.gdl**: add from_clingo_symbol
- **pyggp.gdl**: add to_clingo_symbol
- **pyggp.gdl**: add to_clingo_ast
- **pyggp.gdl**: add __str__ methods for Variable,Relation,Literal
- **pyggp.games**: add nim
- **pyggp.gdl**: add additional type aliases
- **pyggp.gdl.Relation**: add gt (greater-than) and plus constructors
- add gameclocks
- add simple included games
- add python gdl representation
- **pyggp.gdl**: add variable and relation datatypes

### Fix

- add various improvements from typechecker and linter
- use lazy string substitution instead of f-strings for logs
- **pyggp.match.Match.\_initialize_agents**: replace constant 2.5 with self.\_slack
- **tests.common**: add args and kwargs to Mock Interpreters
- **pyggp.match**: correct spelling mistake in Disqualification
- **pyggp.games.minipoker_ruleset**: correct mistake in game logic
- **pyggp.games.rock_paper_scissors_ruleset**: correct mistakes in game logic
- **pyggp.games.tic_tac_toe_ruleset**: correct mistakes in game logic
- **pyggp.games.nim_ruleset**: correct mistakes in game logic
- **pyggp.gdl**: correct tests and formatting
- **pyggp.games.nim_ruleset**: correct mistake in next rules
- **pyggp.games**: correct mistake in definition of tic tac toe
- **pyggp.gdl**: add missing type annotations

### Refactor

- **pyggp.visualizers**: sort imports
- **pyggp.logging**: move module to \_logging (to make it protected)
- **pyggp.gdl.match.Match**: use dict instead of dict.keys() in iterator
- **pyggp.exceptions**: restructure exceptions to mitigate circular dependencies
- rename GameClockConfig to GameClockConfiguration and introduce default values
