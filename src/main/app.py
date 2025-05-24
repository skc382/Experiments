import asyncio
import json
import logging
import os
from datetime import datetime
from typing import Dict
import boto3
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from langchain_community.graphs import Neo4jGraph
from langchain_core.prompts import PromptTemplate
from pydantic import BaseModel

from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# FastAPI app
app = FastAPI()

# Environment variables (set in AWS or .env)
NEO4J_URI = os.getenv("NEO4J_URI", "neo4j+s://6a91c5ff.databases.neo4j.io")
NEO4J_USERNAME = os.getenv("NEO4J_USERNAME", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD")
AWS_REGION = os.getenv("AWS_REGION", "us-east-1")

# Initialize Neo4j
graph = Neo4jGraph(url=NEO4J_URI, username=NEO4J_USERNAME, password=NEO4J_PASSWORD)

# Initialize Bedrock client
bedrock_client = boto3.client("bedrock-runtime", region_name=AWS_REGION,
                              aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID'),
                              aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY'))

# Pydantic model for prompt
class PromptRequest(BaseModel):
    child_id: str
    prompt: str
    session_id: str  # For WebSocket auth

# GraphRAG query to retrieve context
def get_graph_context(child_id: str) -> str:
    try:
        query = f"""
        MATCH (c:Child {{child_id: '{child_id}'}})-[:ASSIGNED]->(h:Homework),
              (c)-[:PARTICIPATED]->(a:Activity), (h)-[:COVERS]->(con:Concept), 
              (c)-[:EXPERIENCED]->(em:Emotion)-[:RELATED_TO]->(a:Activity) 
        RETURN DISTINCT c.name, h.title, h.status, h.difficulty, em.name, em.trigger, con.name, a.name 
        LIMIT 10
        """

        result = graph.query(query)
        if not result:
            return f"No data found for child {child_id}."
        context = []
        for record in result:
            context.append(
                f"{record['c.name']} is working on {record['h.title']} (Status: {record['h.status']}, "
                f"Difficulty: {record['h.difficulty']}),  , "
                f"covering concept {record['con.name']}. "
                f"Also felt {record['em.name']} due to participating in {record['a.name']} activity because of '{record['em.trigger']}'."
            )
        return "\n".join(context)
    except Exception as e:
        logger.error(f"Graph query error: {str(e)}")
        return "Error retrieving graph context."

# Call Bedrock Nova Lite
async def call_bedrock(context: str, prompt: str) -> str:
    try:
        prompt_template = PromptTemplate(
            template="Context: {context}\nInstruction: {prompt}\nRespond in 4–6 sentences, empathetic tone, parent-friendly.",
            input_variables=["context", "prompt"]
        )
        formatted_prompt = prompt_template.format(context=context, prompt=prompt)
        request = {
            "schemaVersion": "messages-v1",
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {
                            "text": formatted_prompt
                         }
                    ]
                }
            ],
            "inferenceConfig": {
                "maxTokens": "512",
                "temperature": "0.7"
            }
        }
        response = bedrock_client.invoke_model(
            body=json.dumps(request),
            modelId="amazon.nova-lite-v1:0"
        )
        # Parse the response
        response_body = json.loads(response['body'].read())
        return response_body['output']['message']['content']
    except Exception as e:
        logger.error(f"Bedrock error: {str(e)}")
        return "Error generating response from Bedrock."

# WebSocket connection manager
class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}

    async def initialize(self, websocket: WebSocket):
        await websocket.accept()
        logger.info(f"Connected opened, awaiting session object")

    async def connect(self, websocket: WebSocket, session_id: str):
        # await websocket.accept()
        self.active_connections[session_id] = websocket
        logger.info(f"Connected: {session_id}")

    def disconnect(self, session_id: str):
        if session_id in self.active_connections:
            del self.active_connections[session_id]
            logger.info(f"Disconnected: {session_id}")

    async def send_message(self, session_id: str, message: str):
        if session_id in self.active_connections:
            await self.active_connections[session_id].send_text(message)

manager = ConnectionManager()

# WebSocket endpoint
@app.websocket("/ws/graphrag")
async def websocket_endpoint(websocket: WebSocket):
    await manager.initialize(websocket)
    try:
        # Receive initial connection data
        data = await websocket.receive_json()
        session_id = data.get("session_id")
        child_id = data.get("child_id")

        # Basic authentication (extend with JWT or OAuth for production)
        if not session_id or not child_id:
            await websocket.send_text(json.dumps({"error": "Invalid session_id or child_id"}))
            await websocket.close()
            return

        # Connect WebSocket
        await manager.connect(websocket, session_id)

        while True:
            try:
                # Receive prompt
                message = await websocket.receive_json()
                prompt = message.get("prompt")
                if not prompt:
                    await manager.send_message(session_id, json.dumps({"error": "No prompt provided"}))
                    continue

                logger.info(f"Received prompt for {child_id}: {prompt}")

                # Get graph context
                context = get_graph_context(child_id)
                if "Error" in context:
                    await manager.send_message(
                        session_id,
                        json.dumps({"error": context})
                    )
                    continue

                # Call Bedrock
                response = await call_bedrock(context, prompt)
                if "Error" in response:
                    await manager.send_message(
                        session_id,
                        json.dumps({"error": response})
                    )
                    continue

                # Send response
                await manager.send_message(
                    session_id,
                    json.dumps({"response": response, "source": "bedrock"})
                )

            except WebSocketDisconnect:
                manager.disconnect(session_id)
                break
            except Exception as e:
                logger.error(f"WebSocket error: {str(e)}")
                await manager.send_message(
                    session_id,
                    json.dumps({"error": "Internal server error"})
                )

    except Exception as e:
        logger.error(f"Connection error: {str(e)}")
        await websocket.close()

# Health check endpoint
@app.get("/health")
async def health_check():
    return {"status": "healthy"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)