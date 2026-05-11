# 1. What has been changed since the start?

## 1.1. Frontend 
- svelteKit frontend
- reusable components

## 1.2. Backend API 
- create API routes for defaults, dataset validation, training setup, training control, implementation setup, simulation execution, and result comparison (this should allow us to deploy the website in it's current state)
- added WebSocket events, wrapper around current background jobs so we can send the progress events of the runners rather than relying on the terminal logs

## 1.3. Backend model and file handling
- eworked  the paths paths so data is more intuitive
- session-based upload handling under `artifacts/uploads/`.
- added serialization so pandas/numpy results can be sent without crashes
- The original Gradio frontend is still present and works


# 2. How should we proceed
- The current backend is still built around the LAHSO transport model, so it can only really handle: delay, capacity loss, demand volume changes, and release-time changes.
- for generic disruptions: 
    - entities with different types and attributes
    - relationships between them
    - create and itialise a graph(V, E) using the entities and relations
    - and disruption functions that generate time-based events (so they work with the sim).
- changes in most of the backend `model_input.py`, `simulation_module.py`, `global_variables.py`, `model_train.py`, and `model_implementation.py`, everything is hardcoded, allowing only shipments, transport modes, terminals, and service disruptions(4 types mentioned above).

I'm not sure how this would be possible otherwise. Even if you simply want to let the user run some sort of general diruption function as Resa mentioned, and you allow them to create/upload arbitrary code, you would still be limited at the current disruption types. This would also allow us to define the schemas required for AI generation. Otherwise, it would suffer from too many halucinations, there wouldn't be a concrete format for which the llm would return the answer to, this is how most libraries that interact with llms present their interfaces too: (Pydantic, Instructor).

- treat the current LAHSO model as an instatiation of the general domain, but redesign the backend so future domains like power networks, supply chains can be added not hardcoded in.

The emphasis was not on this in the original proposal presentation, mentioning **no backend modifications required**. This is also the reason in the intial user stories the diversity of the disruptions were not mentioned on my side, the proposal made it seem that i would just use the current existing disruptions and programatically create them through an llm.

# 4. Integration with AWS 

## Minimal
- Frontend -> S3 (files, artifacts, static frontend files etc.)  + CloudFront (edge deployement runners (serverless or statefull, not sure?))
- Background jobs such as running the training or the simulation -> SQS/ECS workers, some mentions of Redis/Celery/RQ seems there are multiple ways of doing it depending on the durations of the background tasks, etc.
- Backend  -> ECS Fargate

## Users and storing files long term
- RDS Postgres -> Database
- S3 -> static files
- CloudWatch -> logs management, with this being a python app, it might be something to look into soon keep track of exepctions at runtime, etc.
