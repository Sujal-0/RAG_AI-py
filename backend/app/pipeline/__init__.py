"""Pipeline infrastructure.

Contains the core pipeline execution machinery:
- ConversationContext: Pydantic model carrying request state through the pipeline
- EngineResult: Pydantic model representing engine execution outcomes
- BaseEngine: Abstract base class defining the engine contract
- executor: Pipeline execution function that drives engines in sequence
"""
