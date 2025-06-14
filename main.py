import asyncio
import uuid
import traceback
import json
from datetime import datetime
from fastapi import FastAPI, WebSocket, Request, WebSocketDisconnect
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from pathlib import Path

from agents.workflow import CybersecurityRAGWorkflow

app = FastAPI()

# Mount static files
static_path = Path(__file__).parent / "static"
app.mount("/static", StaticFiles(directory=static_path), name="static")

# Setup templates
templates_path = Path(__file__).parent / "templates"
templates = Jinja2Templates(directory=templates_path)

# Global workflow instance
workflow = None

@app.on_event("startup")
async def startup_event():
    """Initialize the workflow on application startup."""
    global workflow
    print("Initializing workflow...")
    workflow = CybersecurityRAGWorkflow()
    await workflow.initialize()
    print("Workflow initialized.")

@app.on_event("shutdown")
async def shutdown_event():
    """Clean up resources on application shutdown."""
    if workflow:
        print("Closing workflow resources...")
        await workflow.close()
        print("Workflow closed.")

@app.get("/")
async def get(request: Request):
    """Serve the main chat interface."""
    return templates.TemplateResponse("index.html", {"request": request, "now": datetime.utcnow})

# This is a new endpoint to fetch history.
@app.get("/chat_history/{session_id}")
async def get_chat_history(session_id: str):
    if not workflow or not workflow.checkpointer:
        return {"error": "Workflow not initialized"}, 404
    
    try:
        # Retrieve the conversation state from the checkpointer
        config = {"configurable": {"thread_id": session_id}}
        async with workflow.checkpointer as checkpointer:
            state = await workflow.app.aget_state(config)
        
        if state and state.values:
            # Convert message objects to a serializable format
            history = []
            for msg in state.values.get("messages", []):
                if hasattr(msg, 'type') and hasattr(msg, 'content'):
                     history.append({"type": msg.type, "content": msg.content})
            return {"history": history}
        else:
            return {"history": []}
            
    except Exception as e:
        print(f"Error fetching history for {session_id}: {e}")
        return {"error": "Could not retrieve chat history"}, 500

@app.websocket("/ws/chat")
async def websocket_endpoint(websocket: WebSocket):
    """Handle WebSocket connections for the chat."""
    await websocket.accept()
    
    active_connections: list[WebSocket] = []
    active_connections.append(websocket)
    
    print("New client connected.")

    try:
        while True:
            # Wait for a message from the client (now expecting JSON)
            data = await websocket.receive_json()
            user_query = data.get("query")
            session_id = data.get("session_id") # Can be null for new chats
            model_choice = data.get("model", "openai_mini")  # Default to openai_mini
            agent_choice = data.get("agent", "auto")  # Default to auto

            if not user_query:
                continue

            try:
                # Create client config for the new API
                client_config = {
                    "configurable": {"thread_id": session_id or str(uuid.uuid4())},
                    "preferred_llm_choice": model_choice,
                    "preferred_agent": agent_choice if agent_choice != "auto" else None
                }
                
                # Use the new process_query_async API
                result = await workflow.process_query_async(user_query, client_config)
                
                # Add model and agent info to result
                result["model_used"] = model_choice
                result["agent_choice"] = agent_choice
                
                # Send the full result object as JSON
                await websocket.send_json(result)

            except Exception as e:
                error_message = f"Error processing query: {str(e)}"
                print(error_message)
                traceback.print_exc()
                await websocket.send_json({
                    "response": f"Sorry, an error occurred: {e}", 
                    "agent_type": "Error", 
                    "session_id": session_id or str(uuid.uuid4()), 
                    "model_used": model_choice, 
                    "agent_choice": agent_choice
                })

    except WebSocketDisconnect:
        print(f"Client disconnected.")
        active_connections.remove(websocket)
    except Exception as e:
        print(f"An unexpected error occurred in WebSocket: {e}")
        traceback.print_exc()
        if websocket in active_connections:
            active_connections.remove(websocket)

if __name__ == "__main__":
    import uvicorn
    # Note: Running this way is for development. 
    # For production, use a command like: uvicorn main:app --host 0.0.0.0 --port 8000
    uvicorn.run(app, host="127.0.0.1", port=8000)