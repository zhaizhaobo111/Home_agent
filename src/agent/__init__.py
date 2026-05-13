"""New LangGraph Agent.

This module defines a custom graph.
"""
from src.agent.extend import extend_graph
from src.agent.graph import graph
from src.agent.recommend import recommend_graph
from src.agent.reserve import reserve_graph

__all__ = ["graph","recommend_graph","reserve_graph","extend_graph"]



