"""LangGraph orchestrator — builds and runs the pipeline graph.

Wires all 7 nodes into a proper LangGraph StateGraph.
If any node sets state["error"], the pipeline routes to END immediately.
"""

import logging
from pathlib import Path
from typing import Any

from langgraph.graph import StateGraph, END

from agent.state import VideoState, create_initial_state
from agent.nodes.idea_generator import generate_idea
from agent.nodes.script_writer import generate_script
from agent.nodes.image_picker import pick_images
from agent.nodes.asset_fetcher import generate_all_audio
from agent.nodes.video_assembler import assemble_video
from agent.nodes.metadata_generator import generate_metadata
from agent.nodes.queue_manager import manage_queue

logger = logging.getLogger(__name__)


# --- Node Wrappers to inject config from state ---

async def idea_generator(state: VideoState) -> VideoState:
    return await generate_idea(state, state["config"])

async def script_writer(state: VideoState) -> VideoState:
    return await generate_script(state, state["config"])

async def image_picker(state: VideoState) -> VideoState:
    return await pick_images(state, state["config"])

async def asset_fetcher(state: VideoState) -> VideoState:
    config = state["config"]
    temp_dir = Path(config["paths"]["temp"])
    voice_map = {
        state["character_a"]: state["character_a_voice"],
        state["character_b"]: state["character_b_voice"],
    }
    return await generate_all_audio(state, voice_map, temp_dir)

async def video_assembler(state: VideoState) -> VideoState:
    return await assemble_video(state, state["config"])

async def metadata_generator(state: VideoState) -> VideoState:
    return await generate_metadata(state, state["config"])

async def queue_manager(state: VideoState) -> VideoState:
    return await manage_queue(state, state["config"])


# --- Routing ---

def should_continue(state: VideoState) -> str:
    """Conditional edge routing: stop immediately on error."""
    if state.get("error"):
        return END
    return "continue"


# --- Graph Building ---

def build_graph():
    """Build the LangGraph StateGraph."""
    graph = StateGraph(VideoState)
    
    # Add all 7 nodes
    graph.add_node("idea_generator", idea_generator)
    graph.add_node("script_writer", script_writer)
    graph.add_node("image_picker", image_picker)
    graph.add_node("asset_fetcher", asset_fetcher)
    graph.add_node("video_assembler", video_assembler)
    graph.add_node("metadata_generator", metadata_generator)
    graph.add_node("queue_manager", queue_manager)
    
    # Set entry point
    graph.set_entry_point("idea_generator")
    
    # Add conditional edges after EVERY node
    graph.add_conditional_edges(
        "idea_generator", 
        should_continue, 
        {"continue": "script_writer", END: END}
    )
    graph.add_conditional_edges(
        "script_writer", 
        should_continue, 
        {"continue": "image_picker", END: END}
    )
    graph.add_conditional_edges(
        "image_picker", 
        should_continue, 
        {"continue": "asset_fetcher", END: END}
    )
    graph.add_conditional_edges(
        "asset_fetcher", 
        should_continue, 
        {"continue": "video_assembler", END: END}
    )
    graph.add_conditional_edges(
        "video_assembler", 
        should_continue, 
        {"continue": "metadata_generator", END: END}
    )
    graph.add_conditional_edges(
        "metadata_generator", 
        should_continue, 
        {"continue": "queue_manager", END: END}
    )
    graph.add_conditional_edges(
        "queue_manager", 
        should_continue, 
        {"continue": END, END: END}
    )
    
    return graph.compile()


async def run_pipeline(config: dict, run_id: str = None) -> VideoState:
    """Run one complete video generation pipeline.
    
    Args:
        config: Loaded config dict from load_config()
        run_id: Optional custom run ID. Auto-generated if None.
    
    Returns:
        Final VideoState after all nodes complete (or fail).
    """
    graph = build_graph()
    initial_state = create_initial_state(run_id)
    
    # Store config in state so nodes can access it
    initial_state["config"] = config
    
    final_state = await graph.ainvoke(initial_state)
    
    # Log final status
    if final_state.get("error"):
        logger.error(
            f"[pipeline] FAILED at {final_state.get('failed_node')} "
            f"— {final_state['error']}"
        )
        from agent.alerts import alert_pipeline_failure
        await alert_pipeline_failure(
            run_id=final_state["run_id"],
            failed_node=final_state.get("failed_node", "unknown"),
            error=final_state["error"]
        )
    else:
        logger.info(
            f"[pipeline] SUCCESS — "
            f"video: {final_state.get('final_video')} "
            f"upload slot: {final_state.get('scheduled_upload_time')}"
        )
    
    return final_state
