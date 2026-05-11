# 2. How should we proceed

## Previous plan

| Reference to Proposal | User Story | Dev hours | Timeline (8h/week) | My own notes (at current understanding) | Maybes | Where to look in code | Notes to self (dev tasks) |
|---|---|---:|---|---|---|---|---|
| Internal | As a developer, I want a stable local Flask run/debug workflow so I can build features safely. | 12 | W1-W2 | Learn Flask basics (route, request, jsonify, session); run app end-to-end; fix current env loading; document "decisive" run steps; move hardcoded secrets out of code/bring to internet hostable state |  | Reuse run_web.py, app.py, pyproject.toml | Learn Flask basics (route, request, jsonify, session); run app end-to-end; fix current env loading; document "decisive" run steps; move hardcoded secrets out of code/bring to internet hostable state |
| US-A1-01 | As a analyst, I want a clear disruption schema so natural language can be transformed into valid model input. | 8 | W3 | Create mapping between user language prompt and LLM output looks like a json schema, Impact Type, duration bounds, capacity bounds, location, lambda; create validation rules + defaults |  | Use disruption fields expected in model_input.py and CSV formats in Disruption_Profiles | Define JSON schema for service + demand disruptions; map NL terms to Impact Type, duration bounds, capacity bounds, location, lambda; create validation rules + defaults. |
| US-A1-02 | As a developer, I want a LLM API adapter so the app can make reliable LLM calls. | 10 | W4-W5 | Undersand existing SDKs, present options to, stakeholders. Add retry/error/tiemout handling, add prompt template for users. Maybe add versioning to the prompts. Verify a few basic calls |  | No current LLM module; extend from app.py pattern | Understand Gemini SDK/auth; create minimal ai_client module; add timeout/retry/error handling; add prompt template versioning; verify one basic call from Flask endpoint. |
| US-A1-03 | As a analyst, I want to describe a disruption in plain language and receive a structured scenario draft. | 14 | W6-W7 | Current understanding: Build POST /api/ai/scenario/draft; pass prompt + schema, return JSON + confidence + missing fields; add frontend form + response preview. |  | Add new /api/ai/* routes in app.py, wire UI in index.html | Build POST /api/ai/scenario/draft; pass prompt + schema; return JSON + confidence + missing fields; add frontend form + response preview. |
| US-A1-04 | As a analyst, I want conversational refinement so I can iteratively improve a scenario. | 18 | W8-W10 | Current understanding: Store conversation state in session; add refine endpoint; implement “what changed” diff in response | Add steering so that the model doesn't start halucinating | Session structure exists in LAHSOSession in app.py | Store conversation state in session; add refine endpoint; implement “what changed” diff in response; add guardrails against drift/hallucinated parameters. |
| US-A1-05 | As a analyst, I want automated parameter extraction with validation so scenarios are simulation-ready. | 16 | W11-W12 | Build extractor/normalizer; enforce numeric ranges and enum values; add missing-field clarification questions | Add missing-field clarification questions; add fallback manual edit form before run. Makes it way more usable. | Validation target comes from model_input.py and runtime behavior in simulation_module.py | Build extractor/normalizer; enforce numeric ranges and enum values; add missing-field clarification questions; add fallback manual edit form before run. |
| US-A1-06 | As a analyst, I want to save AI scenarios as LAHSO disruption files so I can run the engine unchanged. | 14 | W13-W14 | Implement CSV writer for generated profiles; store in Datasets/Disruption_Profiles/generated; add scenario selector in UI | Add timestamps to the files and maybe a UI for the user to see the different timestamp files of the same "scenario/request" | Reuse config paths in config.py and training/implementation config routes in app.py | Implement CSV writer for generated profiles; store in Datasets/Disruption_Profiles/generated; add scenario selector in UI; prevent overwrite collisions with timestamped filenames. |
| US-A2-01 | As an analyst, I want AI-generated scenarios to run through the resilience engine/q learning pipeline | 8 | W15 | Add only orchestration glue; run regression checks on baseline outputs; confirm no modification needed in simulation/optimization internals. |  | Engine already in model_implementation.py, model_train.py, optimization_module.py | Add only orchestration glue; run regression checks on baseline outputs; confirm no modification needed in simulation/optimization internals. |
| US-A4-01 | As a decision-maker, I want real scenario comparison charts (not demo data) to compare policy outcomes. | 18 | W16-W18 | Replace hardcoded values; dashboard; implement actual file upload/selection; API calls |  | Backend compare endpoint exists in app.py; logic in bar_chart_plot.py; frontend currently hardcoded in index.html | Replace hardcoded gpData/awData; implement actual file upload/selection; call /api/comparison/compare; bind returned deltas to charts. |
| US-A4-02 | As a decision-maker, I want recovery policy suggestions so I know which policy to apply after disruption. | 12 | W19-W20 | Rule-based approach first; define scoring weights (cost, delay, undelivered, late); show top recommendations and explanation | Maybe an ML model could be used, something that still keeps explainability such as linear regression | Use metrics from global_variables.py and simulation outputs in csv_output | Build rule-based suggestion engine first (no extra ML); define scoring weights (cost, delay, undelivered, late departures); show top recommendation + rationale in dashboard. |
| US-A4-03 | As a decision-maker, I want intervention prioritization so I can act on highest-impact actions first. | 14 | W21-W22 | Add prioritized interventions table (action, expected impact, confidence); include filters and scenario switcher; add explanation text per item. |  | Use comparison deltas + output metrics from bar_chart_plot.py and global_variables.py | Add prioritized interventions table (action, expected impact, confidence); include filters and scenario switcher; add explanation text per item. |
| Internal | As a developer, I want end-to-end reliability checks and demo script so the proposal demo is defensible. | 16 | W23-W24 | Add Flask API tests for AI routes and compare route; add previous code tests; write demo script (happy path + fallback path); create troubleshooting checklist; prepare for handoff | I would spend more time here, to rewrite the other frontend code and deliver a user-ready product; as I would have already changed some of the code, it shouldn't be too much, 8-12 more hours | Existing tests are placeholder in tests/test_main.py | Add Flask API tests for AI routes and compare route; add golden test scenarios; write demo script (happy path + fallback path); create troubleshooting checklist. |

## Current comment
Hey Reza, when you mentioned that the user should be able to modify the scenario model, to what degree were you referring to? Do you have some concrete examples of what these modifications might be? Currently, both service and request disruption look something like this: they can affect the duration, they have a percentage of occuring per year. They apply to all paths and transits equally and can occur at any time while the simulator is running: 
 
Personally, the way I see it, an approach could be allowing the user to select disruptions for only parts of the graph between the transport hubs "Euromax - Moerdijk" only on certain transportation methods, such as "Trains" and also at specific times rather than random: "the 7th day in the env from 10:00 to 21:00". I think this would be a good goal, what do you think? 
Professor: 
Hi Rafael, the disruption model should be a function ideally with arbitrary number and type of inputs and outputs. Usually disruptions lead to change of load or capacity of a system. They break a pattern that system is used to experience and make it unstable. I believe the current code models types of disruptions that affect good transit routes. What I would like to be able to model is for example disruptions in power network, transit infrastructure, supply chain and so on that affect maintenance planning and execution. Unfortunately I can tell the functions and parameters for each of these cases, that’s why I would like to be able to have a scenario generator that receives a function, randomise the input parameters given a feasible range, cross check the feasibility across all the parameters and generate the output based on the given model.

### My conclusion on the current comment
If we were to allow for this kind of flexibility, we would need to rewrite the backend such that:
- We allow for the creation of objects with different properties and different types, routes, supporting infrastructure, metheorogical local data
- We create a graph representation that we pass to the python discrete step simulator 
- we introduce fractional steps such that we can simulate things that happen along the routes
- We allow attaching types of disruptions either to the nodes of the graph, or to the edges, the nodes can be a combination of (transportNodes, weatherNodes etc) similar the edges can have attached types of elements to them (routeWeather, trafic, etc.)
- We create a Frontened for this graph view that the user can use and create their own scenarios
- Based on this graph using the following stack and an ai agent that can create the disruption scenario, based on the current graph model and the constraints that come with it
    Pydantic   = define/validate your disruption schema
    Instructor = make the LLM return that schema reliably
    LiteLLM    = call Gemini/OpenAI/Anthropic/Ollama through one interface

## Feasibility assessment after the supervisor clarification

My original solution is feasible, but only for the narrower interpretation: using AI to create valid disruption scenarios for the existing LAHSO transport simulation. It is a reasonable and useful implementation path if the project goal is: "make the current LAHSO model easier to configure, run, and compare under generated transport disruptions."

However, it is not fully aligned with the supervisor's clarified vision. The clarification is not just asking for a natural-language wrapper around the current disruption CSVs. It asks for a more general scenario generator that can receive a disruption function, randomise its input parameters within feasible ranges, check feasibility across parameters, and generate outputs from that model. That is a different abstraction level.

The current codebase is built around a fixed synchromodal transport model:

- `ModelInput` reads a fixed set of network, schedule, demand, cost, and disruption CSV files.
- Service disruptions use a fixed schema: profile, impact type, duration bounds, capacity bounds, location, and lambda.
- Demand disruptions use a fixed schema: profile, impact type, time or volume bounds, and lambda.
- The simulator has hard-coded assumptions about shipments, service lines, terminals, capacities, release times, and route replanning.

Because of this, an LLM-to-CSV feature would work technically, but it would still be constrained by the existing service and demand disruption types. It would not let a user model arbitrary power-network, supply-chain, infrastructure, or maintenance-planning disruptions unless those effects are first translated into the LAHSO transport variables.

### Is the current approach the correct way?

The current approach is correct as a first MVP only if it is reframed as:

> AI-assisted scenario generation for the existing LAHSO transport resilience engine.

It is not the correct approach if the expected deliverable is:

> A general disruption-function platform for arbitrary infrastructure systems.

For the supervisor's vision, I should not start by rewriting the whole simulator, adding a graph editor, introducing fractional simulation steps, and modelling every possible domain. That would become a new multi-domain simulation platform and is too large and risky for the current project scope.

The better compromise is to build a "scenario function layer" on top of the current system:

- Define a `ScenarioFunctionSpec` with typed inputs, ranges, units, distributions, constraints, and outputs.
- Add a feasibility/sampling engine that generates candidate parameter sets and rejects invalid combinations.
- Add a LAHSO adapter that maps valid function outputs into the current service disruption and demand disruption CSV formats.
- Let the LLM help draft the function spec and missing assumptions, but keep validation deterministic with Pydantic-style schemas and explicit constraints.
- Keep arbitrary Python execution out of the first version unless it is sandboxed or restricted to approved templates.
- Use the current LAHSO model as the first supported domain adapter, then describe power networks, maintenance planning, or supply chains as future adapters.

This gives the supervisor the main conceptual direction they asked for without turning the thesis into a complete rewrite of the backend and simulator.

### Recommended scope to present

I would present the revised project scope as follows:

> The deliverable will be a generic scenario-function generator with LAHSO as the first executable backend. Users define or AI-draft a disruption function through a structured schema. The system samples feasible inputs, validates cross-parameter constraints, converts accepted scenarios into LAHSO-compatible disruption files, runs the existing resilience engine, and compares the resulting policies.

This is stronger than the original LLM-to-disruption-file plan because it introduces the function, feasibility, and sampling concepts from the supervisor's vision. It is also much safer than promising arbitrary multi-domain simulation.

The graph-based, multi-object, multi-domain simulator should be positioned as future work unless the supervisor explicitly confirms that the project should become a simulator rewrite.

## Revised timeline after the supervisor clarification

This revised timeline keeps the 8 hours per week assumption. The overall duration stays close to the previous 24-week plan for a feasible MVP, but the work changes significantly: schema/function design and feasibility sampling move earlier, while conversational AI and recommendations move later. A full graph-based multi-domain rewrite would likely exceed this plan by a large margin.

| Phase | User-facing outcome | Main development work | Dev hours | Timeline (8h/week) | Change from previous plan |
|---|---|---|---:|---|---|
| 1. Scope alignment and examples | A clear agreement on what "receives a function" means for the demo | Collect 2-3 concrete supervisor examples; define accepted input/output boundary; decide whether LAHSO is the only executable backend for this project | 8 | W1 | New first step before building AI endpoints |
| 2. Scenario function schema | A structured function spec can be saved and validated | Define typed inputs, units, ranges, distributions, output schema, and cross-parameter constraints using Pydantic-style models | 18 | W2-W3 | Expands the previous disruption schema task |
| 3. Feasibility sampler | The system can generate valid parameter sets and explain rejected ones | Implement random sampling with fixed seeds, constraint checks, rejection reporting, and validation summaries | 20 | W4-W6 | New core work from the supervisor clarification |
| 4. LAHSO adapter | Valid function outputs can become current LAHSO disruption files | Map generic outputs into service and demand disruption CSVs; manage generated scenario files; add regression checks against existing model input expectations | 22 | W7-W9 | Replaces the simpler AI scenario CSV writer |
| 5. Function templates and demo cases | Users can start from transport disruption templates | Create templates for service capacity reduction, terminal delay, demand volume change, and release-time change; document assumptions and limitations | 14 | W10-W11 | New work, but keeps the first demo realistic |
| 6. AI-assisted drafting | The LLM can draft a function spec, but validation remains deterministic | Add LiteLLM or direct provider adapter; use structured output; ask missing-field questions; prevent the model from inventing unsupported backend behaviour | 18 | W12-W14 | Moves later than the old plan because the schema must exist first |
| 7. Scenario builder UI | Users can edit function inputs, ranges, constraints, and preview generated scenarios | Add Svelte UI for function specs, feasibility errors, sampled scenarios, and generated LAHSO files | 24 | W15-W17 | Expands the previous plain-language scenario form |
| 8. Run and compare generated scenarios | Selected scenarios can run through LAHSO and produce comparison charts | Wire generated scenarios into training/implementation flow; reuse comparison endpoint; show cost, delay, undelivered, and late-departure deltas | 22 | W18-W20 | Combines previous orchestration and comparison work |
| 9. Basic recommendations | Users get simple, explainable policy suggestions | Add rule-based scoring over comparison outputs; show rationale and ranked actions; avoid extra ML unless time remains | 12 | W21-W22 | Similar to the previous recommendation task, but smaller |
| 10. Reliability, report, and demo | The project is defensible in a supervisor presentation | Add tests for schemas, sampling, adapters, and API routes; prepare happy-path and failure-path demo; write limitations and future-work section | 24 | W23-W25 | Slightly larger final validation phase |

Total estimated MVP effort: about 182 hours, or roughly 23 weeks at 8 hours per week plus a small buffer. Compared with the previous plan, the timeline increases slightly, but more importantly the risk moves earlier: if the supervisor rejects the LAHSO-adapter boundary in Phase 1, then the project is no longer a 24-25 week extension and should be rescoped as a larger simulation-platform project.
