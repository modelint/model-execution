# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

`mi-mx` (package name; import name `mx`) is a **Shlaer-Mellor Executable UML model execution engine**. It loads a *populated Shlaer-Mellor metamodel* (produced by the separate `xuml-populate` tool) and *executes* it: it drives state machines, runs state/method activities, evaluates actions, and dispatches events — the way a compiled xUML model would run, but interpreted directly against the metamodel.

The engine does not parse model files itself. It reads a serialized relational database (a `.ral` TclRAL text file) that already contains the populated metamodel, and interprets it at runtime.

## Commands

```bash
# Install for development (editable, with dev extras)
pip install -e ".[dev]"          # dev extras: bump2version, pytest
pip install -e ".[build]"        # build extras: build, twine

# Run the engine against a system directory (entry point defined in pyproject.toml)
mx -s src/mx/systems/elevator    # -s / --system: path to a system directory
mx -V                            # print version
mx -s <path> -v                  # verbose console output
mx -s <path> -L                  # keep the mx.log diagnostic file (deleted on exit otherwise)

# Version bump (updates pyproject.toml + src/mx/__init__.py, commits, tags)
bump2version patch   # or: minor / major
```

Requires Python >= 3.11. Note the code uses nested-quote f-strings (e.g. `f"{i["_instance"]}"`) that only parse on **Python 3.12+**, so develop/run on 3.12 or 3.13.

**Tests:** `pytest` is a declared dev dependency but there is currently **no test suite** in the repo. Do not assume `pytest` will find anything to run.

**README is stale:** `README.md` documents a `-s/-c/-x` (system/context/scenario) CLI and a `db_types/` layout. The actual CLI (`src/mx/__main__.py`) is `-s/-L/-v/-V`, and the current directory layout uses `models/` + `playgrounds/` (see below). Trust the code over the README.

## External dependencies (Model Integration stack)

These are sibling `modelint` packages; the engine leans on them heavily:

- **`mi-pyral`** (imported as `pyral`) — the relational runtime wrapping **TclRAL**. Nearly every operation in this codebase is a relational algebra call: `Relation.restrict / semijoin / join / project / extend / tag`, `Relvar.create_relvar`, `Database.open_session / load`. Understanding PyRAL relation-variable (rv) semantics is essential to reading almost any file here.
- **`sip-parser`** — parses `.sip` (Scenario Instance Population) files that define a domain's initial instances and states.
- **`xcm-parser`, `xsm-parser`** — class-model / state-machine parsers.
- **`mi-configurator`** — configuration loading.

## System directory layout

A "system" passed to `mx -s <dir>` is expected to look like this (see `src/mx/systems/elevator/`):

```
<system>/
  models/
    <something>.ral              # exactly ONE .ral file: the populated SM metamodel (mmdb)
    <ALIAS>_types.yaml           # per-domain user-type -> TclRAL type mapping, prefixed by domain alias
  playgrounds/
    <playground_name>/
      population/
        <ALIAS>.ral              # populated domain database, one per domain (name == domain alias)
        <ALIAS>_*.sip            # initial instance population + initial states
      scenarios/
        <name>.yaml              # scenario (stimulus/response interactions) — YAML for now
```

`System.set_mmdb_path()` requires **exactly one** `.ral` file under `models/`. The playground currently loaded is **hard-coded** (see the Model Debugger stand-in note below), not yet a CLI arg.

## Architecture

Execution is a strict containment hierarchy, each level driving the one below:

```
System (singleton)
 └─ Domain (one per modeled domain)
     └─ StateMachine  (Lifecycle / MultipleAssigner / SingleAssigner)
         └─ StateActivityExecution / MethodExecution  (an Activity)
             └─ ActionExecution subclasses  (the data-flow actions)
```

**System** (`system.py`, singleton via `__new__`) — owns the metamodel db session (`mmdb`), the dict of `Domain`s, and the top-level run loop `go()`. `go()` round-robins domains until none report `work_remaining`. It also holds `announcements` and the `suspend` flag used to hand control back to a monitoring process (see Announcements). `inject(stimulus)` is how external stimuli (signals/events) enter the running system.

**Domain** (`domain.py`) — loads its own TclRAL db (named by the domain **alias**), discovers classes/identifiers, and instantiates one `StateMachine` per instance:
- lifecycles → `LifecycleStateMachine`, keyed `self.lifecycles[class_name][int_instance_id]`
- multiple assigners → `MultipleAssignerStateMachine`, keyed by rnum/partitioning class
- single assigners → not yet implemented (stubbed `# TODO`)

Instances are indexed by tagging the class relvar with an integer `_instance` attribute (`Relation.tag`), so a state machine instance can be found from its domain-model identifier. Initial states come from the `.sip` population via `InitialStateContext`.

**StateMachine** (`state_machine.py`, base class; subclasses `lifecycle_state_machine.py`, `assigner_state_machine.py`, `single_/multiple_assigner_state_machine.py`) — queues `InteractionEvent`s and at most one `CompletionEvent`. `busy` == has pending events. `go()` processes events; `process_event()` looks up a `Transition` in the metamodel for `(from_state, event, state_model, domain)` and, on a match, calls `transition()` which sets the new state and launches a `StateActivityExecution`. Completion events always preempt interaction events.

**Activity / Action execution** (`activity_execution.py`, `state_activity_execution.py`, `method_execution.py`, `dc_activity_execution.py`, `actions/`) — an Activity is a data-flow graph of Actions. `ActivityExecution` (ABC) tracks each action's state (U/E/X/C/D — Unexecuted/Enabled/eXecuting/Completed/Disabled) in a temporary PyRAL relvar and enables actions as their input **flows** become available. `ActivityExecution.execute_action` is the **dispatch table** mapping metamodel action names (`"traverse"`, `"read"`, `"signal"`, `"create"`, `"select"`, …) to the `ActionExecution` subclass in `actions/` that implements each one. To add a new action type: create `actions/<name>.py` subclassing `ActionExecution`, then register it in that table.

**Flows** — `actions/flow.py` `ActiveFlow(value, flowtype, scalar)` carries runtime data between actions. `flowtype` is `"scalar"`, `"ptype"`, or a class name (non-scalar/instance-reference flow). An action is `disabled` when a required input flow is still `None` (gates use `all`-None instead of `any`-None). Non-scalar output flows own a domain-db rv that is freed when the activity completes; the action names in `no_nsflow_output_actions` don't produce one.

**Events** (`interaction_event.py`, `completion_event.py`, `dispatched_event.py`, `delayed_event.py`) — `InteractionEvent.to_lifecycle(...)` constructs and dispatches an event to a target instance's state machine. `DelayedEventQ` (per domain) holds time-delayed events; `Domain.go()` checks it each tick and dispatches expired ones.

**EE / external signals** (`ee.py`, `actions/ext_signal.py`, `actions/signal.py`) — External Entities are the boundary to other domains/services; external signals/events are how a domain talks outward. Both are still partly placeholder.

### The metamodel-relational idiom

The single most important pattern: **the model being executed lives in relations, not Python objects.** Business logic is expressed as PyRAL queries against `mmdb` (the metamodel) and against the per-domain databases. For example, finding a transition is a `Relation.restrict` on the `Transition` relvar; reading an attribute is a `semijoin` chain through `Read Action → Attribute Read Access → Attribute`. Relation variables are namespaced by an `owner` string; code allocates rvs with `Relation.declare_rv` / the `rvname.declare_rvs` helper and frees them with `Relation.free_rvs(owner=...)` when an action/activity/domain-init phase completes. When reading any file here, expect the "real logic" to be in the restriction strings and relvar names, not in imperative Python.

`db_names.mmdb` is currently the hard-coded string `"mmdb_elevator"` — the metamodel db session name, referenced throughout.

## Announcements & the Model Debugger boundary

The engine is designed to be driven by a separate **Model Debugger (mdb)** that can step/monitor execution. That coupling works via **announcements**: as the engine runs, state entries, dispatched interaction signals, and external events append `*_Announcement` named tuples (defined in `mxtypes.py`) to `System.announcements`. When announcements are present, `StateMachine.go()` sets `System.suspend = True` and returns control up the stack, letting the supervisor inspect/format them before calling `System.go()` again. `Domain.announce_*` flags and `System.set_announce_triggers()` control what gets announced.

`src/mx/_mdb.py` is a **stand-in for that not-yet-integrated model debugger**. It is what `__main__.main()` actually invokes: `MDB` (singleton) loads the system, selects a **hard-coded playground** (`one_bank_one_shaft`), and injects a **hard-coded scenario** (the `actors`/`stimuli` literals) — used to develop the MX↔MDB control handoff before the real mdb and the scenario file format exist. When changing engine behavior, `_mdb.py` is the quickest place to exercise it end-to-end. `scenario.py` is the (still-evolving) real scenario runner that will eventually replace the hard-coded stimuli.

## Conventions & gotchas

- **Singletons**: `System`, `MDB` use the `__new__` + `_initialized` guard pattern; `get()` helpers raise if accessed before init. Don't construct a second one.
- **`mxtypes.py`** is the shared vocabulary: `ActionType`, `Direction`, `StateMachineType`, addresses (`InternalAddress`/`ExternalAddress`), the `Interaction` dataclass, all `*_Announcement` tuples, and `SCALAR_TYPE` (Python→SM base-type map). Read it before adding new inter-module data.
- **`snake()`** (from `mxtypes`) converts model names to the snake_case forms PyRAL uses for attribute access; identifier lookups routinely round-trip through it.
- **`working/`** and `*.log`, `*.ral` diagnostics dumps are git-ignored scratch output; `mx.log` is (re)generated each run and deleted on exit unless `-L`.
- Lots of `pass` statements and `# TODO`s mark in-progress areas (single assigners, ignore/can't-happen event responses, EE bridging, method activities). The engine is under active development on the `refine` branch — incomplete paths are expected, not bugs to "fix" blindly.
