from langgraph.graph import StateGraph, START, END

from graph.state import ReviewState

from graph.nodes import (
    rag_node,
    bug_review_node,
    security_review_node,
    performance_review_node,
    maintainability_review_node,
    testing_review_node,
    final_review_node,
)


builder = StateGraph(ReviewState)


# Nodes
builder.add_node("rag", rag_node)

builder.add_node("bug_review", bug_review_node)
builder.add_node("security_review", security_review_node)
builder.add_node("performance_review", performance_review_node)
builder.add_node("maintainability_review", maintainability_review_node)
builder.add_node("testing_review", testing_review_node)

builder.add_node("final_review", final_review_node)


# START → RAG
builder.add_edge(START, "rag")


# RAG → specialized agents
builder.add_edge("rag", "bug_review")
builder.add_edge("rag", "security_review")
builder.add_edge("rag", "performance_review")
builder.add_edge("rag", "maintainability_review")
builder.add_edge("rag", "testing_review")


# Specialized agents → final reviewer
builder.add_edge("bug_review", "final_review")
builder.add_edge("security_review", "final_review")
builder.add_edge("performance_review", "final_review")
builder.add_edge("maintainability_review", "final_review")
builder.add_edge("testing_review", "final_review")


# Final reviewer → END
builder.add_edge("final_review", END)


review_graph = builder.compile()