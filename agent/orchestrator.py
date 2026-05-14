"""LangGraph orchestrator — builds and runs the pipeline graph.

Wires all 7 nodes (6 after image picker replaces prompt generator)
into a linear LangGraph StateGraph:

    idea_generator → script_writer → image_picker → asset_fetcher
    → video_assembler → metadata_generator → queue_manager

Each node receives the full VideoState dict and returns it with
updates. Error propagation: if any node sets state["error"],
all downstream nodes skip via validate_state_for_node().

No logic implemented yet — placeholder for Phase 4.
"""

# import logging
#
# from langgraph.graph import StateGraph, START, END
#
# from agent.state import VideoState
# from agent.nodes.idea_generator import generate_idea
# from agent.nodes.script_writer import write_script
# from agent.nodes.image_picker import pick_images
# from agent.nodes.asset_fetcher import fetch_assets
# from agent.nodes.video_assembler import assemble_video
# from agent.nodes.metadata_generator import generate_metadata
# from agent.nodes.queue_manager import manage_queue
