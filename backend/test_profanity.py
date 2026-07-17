import asyncio
from app.pipeline.executor import run_pipeline
from app.pipeline.context import ConversationContext

async def main():
    ctx = ConversationContext(request_id="1", session_id="test_profanity", original_query="fuck you")
    run_pipeline(ctx)
    print("Response:", ctx.response)
    print("Intent:", ctx.intent)
    for trace in ctx.trace:
        if trace.get("handled"):
            print("Handled by:", trace.get("engine"))
            print("Reason code:", trace.get("reasonCode"))
            break
            
if __name__ == "__main__":
    asyncio.run(main())
