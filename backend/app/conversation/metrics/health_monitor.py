"""Health Monitor.

Tracks the status of critical dependencies (LLM, Redis, Vector DB) and exposes 
the state to the Conversation Planner to allow graceful degradation (e.g., skip 
Vector DB if it's down and serve from Cache).
"""

import logging
from typing import Dict

logger = logging.getLogger("app")


class HealthMonitor:
    """Monitors infrastructure readiness."""
    
    @classmethod
    def check_health(cls) -> Dict[str, str]:
        """Ping critical infrastructure."""
        # Simulated pings
        status = {
            "llm": "ONLINE",
            "redis": "OFFLINE", # Falling back to memory
            "vector_db": "ONLINE",
            "reranker": "ONLINE"
        }
        
        logger.debug("Health Check Performed", extra={"structured_log": True, "stage": "HealthMonitor", "status": status})
        return status
