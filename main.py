import asyncio
import uuid
import traceback
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

@app.get("/")
async def get(request: Request):
    """Serve the main chat interface."""
    return templates.TemplateResponse("index.html", {"request": request})

@app.websocket("/ws/chat")
async def websocket_endpoint(websocket: WebSocket):
    """Handle WebSocket connections for the chat."""
    await websocket.accept()
    session_id = str(uuid.uuid4())
    print(f"New client connected with session ID: {session_id}")

    try:
        while True:
            # Wait for a message from the client
            user_query = await websocket.receive_text()

            try:
                # Process the query using the RAG workflow
                result = await workflow.process_query_async(user_query, session_id)
                agent_response = result.get("response", "Sorry, I encountered an error.")
                
                # Send the response back to the client
                await websocket.send_text(agent_response)

            except Exception as e:
                error_message = f"Error processing query: {str(e)}"
                print(error_message)
                traceback.print_exc()
                await websocket.send_text(f"Sorry, an error occurred: {e}")

    except WebSocketDisconnect:
        print(f"Client with session ID {session_id} disconnected.")
    except Exception as e:
        print(f"An unexpected error occurred in WebSocket for session {session_id}: {e}")
        traceback.print_exc()

if __name__ == "__main__":
    import uvicorn
    # Note: Running this way is for development. 
    # For production, use a command like: uvicorn main:app --host 0.0.0.0 --port 8000
    uvicorn.run(app, host="127.0.0.1", port=8000)