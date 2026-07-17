"""Conversation Graph.

A lightweight, O(1) in-memory data structure for tracking conversational state.
Replaces heavy graph databases (like Neo4j) to enforce the <25ms latency budget.
"""

import logging
from typing import Dict, List, Set
from dataclasses import dataclass, field

logger = logging.getLogger("app")


@dataclass
class GraphNode:
    node_id: str
    node_type: str  # "Entity", "Topic", "Task"
    value: str
    aliases: Set[str] = field(default_factory=set)

@dataclass
class ConversationGraph:
    """DTO-backed adjacency list graph."""
    
    nodes: Dict[str, GraphNode] = field(default_factory=dict)
    
    # Adjacency lists for fast relationship traversal
    entity_edges: Dict[str, List[str]] = field(default_factory=dict)
    topic_edges: Dict[str, List[str]] = field(default_factory=dict)
    reference_edges: Dict[str, List[str]] = field(default_factory=dict)
    
    # Active Stacks for O(1) recent contextual pops
    active_entity_stack: List[str] = field(default_factory=list)
    active_topic_stack: List[str] = field(default_factory=list)
    
    def add_entity(self, value: str, aliases: List[str] = None) -> str:
        node_id = f"ent_{value.lower().replace(' ', '_')}"
        if node_id not in self.nodes:
            self.nodes[node_id] = GraphNode(node_id=node_id, node_type="Entity", value=value, aliases=set(aliases or []))
        
        # Maintain Active Stack (push to top)
        if node_id in self.active_entity_stack:
            self.active_entity_stack.remove(node_id)
        self.active_entity_stack.append(node_id)
        
        return node_id
        
    def get_most_recent_entity(self) -> GraphNode | None:
        """O(1) pop to get the current focal entity for reference resolution."""
        if self.active_entity_stack:
            return self.nodes[self.active_entity_stack[-1]]
        return None
