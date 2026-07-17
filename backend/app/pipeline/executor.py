"""Pipeline executor.

Loops over engines in sequence, measures execution time, logs traces,
and short-circuits execution when an engine successfully handles a query.
"""

import time

from app.pipeline.context import ConversationContext
from app.pipeline.pipeline import PIPELINE
from app.utils.logger import logger


def run_pipeline(context: ConversationContext) -> ConversationContext:
    """Execute the conversation context through the pipeline of engines.

    Args:
        context: Context containing input query and execution history.

    Returns:
        Mutated context with populated traces and response.
    """
    for engine in PIPELINE:
        start_time = time.perf_counter()
        query_in = context.expanded_query or context.resolved_query or context.normalized_query or context.original_query

        try:
            result = engine.execute(context)
            duration_ms = round((time.perf_counter() - start_time) * 1000, 2)
            query_out = context.expanded_query or context.resolved_query or context.normalized_query or context.original_query

            # Record trace info
            trace_entry = {
                "engine": engine.name,
                "input": query_in,
                "output": query_out,
                "handled": result.handled,
                "reasonCode": result.reason_code,
                "executionTimeMs": duration_ms,
                **result.metadata,
            }
            context.trace.append(trace_entry)

            # Log detailing standard properties as requested
            logger.info(
                "\n%s\nINPUT\n%s\nOUTPUT\n%s\nhandled=%s\nreason=%s\nduration=%sms\n",
                engine.name,
                query_in,
                query_out,
                str(result.handled).lower(),
                result.reason_code,
                duration_ms,
                extra={
                    "request_id": context.request_id,
                    "engine_name": engine.name,
                },
            )

            # Stop pipeline if engine flags resolved
            if result.handled:
                logger.info(
                    "Pipeline execution short-circuited by engine: %s",
                    engine.name,
                    extra={"request_id": context.request_id},
                )
                break

        except Exception as e:
            # Fatal engine exceptions should halt the pipeline execution flow
            duration_ms = round((time.perf_counter() - start_time) * 1000, 2)
            logger.error(
                "Exception in engine %s - Duration: %sms | Error: %s",
                engine.name,
                duration_ms,
                str(e),
                exc_info=True,
                extra={
                    "request_id": context.request_id,
                    "engine_name": engine.name,
                },
            )
            # Re-raise to let the process wrapper handle and build error response
            raise e

    return context
