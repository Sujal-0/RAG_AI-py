import asyncio
from app.pipeline.executor import run_pipeline
from app.pipeline.context import ConversationContext
from app.utils.session import SessionStore

async def main():
    ctx = ConversationContext(request_id="1", session_id="test3", original_query="hii sujal singh", resolved_query="hi sujal singh")
    run_pipeline(ctx)
    print("Response:", ctx.response)
    print("Intent:", ctx.intent)
    print("Name saved in session:", SessionStore.get_name("test3"))
            
if __name__ == "__main__":
    asyncio.run(main())
