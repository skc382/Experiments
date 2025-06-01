import base64
import json
import logging
import os
from typing import Dict
from typing import Tuple, Union

import boto3
from dotenv import load_dotenv
from fastapi import FastAPI, WebSocket, HTTPException, UploadFile
from fastapi import File
from fastapi import WebSocketDisconnect
from fastapi.responses import JSONResponse
from langchain_community.graphs import Neo4jGraph
from langchain_core.prompts import PromptTemplate
from pydantic import BaseModel
from types import SimpleNamespace
from utils.json_validations import validate_and_load, SchemaOneModel, SchemaTwoModel
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

def template_request_body():
    system_list = [
        {
            "text": "You are an empathetic loving ai assistant. Respond to the prompt within 1-2 sentences, "
                    "try to be helpful and caring."
        }
    ]

    return {
        "schemaVersion": "messages-v1",
        "system": system_list,
        "messages": [
            {
                "role": "user",
                "content": []
            }
        ],
        "inferenceConfig": {
            "maxTokens": "512",
            "temperature": "0.7"
        }
    }


# Pydantic model for prompt
class PromptRequest(BaseModel):
    child_id: str
    prompt: str
    session_id: str  # For WebSocket auth

# GraphRAG query to retrieve context
def build_graph_context(child_id: str) -> str:
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
async def call_bedrock(context: str, **kwargs) -> str:
    try:
        request_body = template_request_body()
        prompt = kwargs.get('prompt')

        prompt_template = PromptTemplate(
            template="Context: {context}\nInstruction: {prompt}\nRespond in 2-3 sentences, empathetic tone, parent-friendly.",
            input_variables=["context", "prompt"]
        )
        formatted_prompt = prompt_template.format(context=context, prompt=prompt)

        if  kwargs.get('image_hex'):
            image_hex_bytes = kwargs.get('image_hex')
            request_body["messages"][0]["content"].append(
                {
                    "image": {
                        "format": "jpeg",
                        "source": {
                            "bytes": image_hex_bytes
                        }
                    }
                }
            )


        request_body["messages"][0]["content"].append(
            {
                "text": formatted_prompt
            }
        )

        response = bedrock_client.invoke_model(
            body=json.dumps(request_body),
            modelId="amazon.nova-lite-v1:0"
        )
        # Parse the response
        response_body = json.loads(response['body'].read())
        return response_body['output']['message']['content']
    except Exception as e:
        logger.error(f"Bedrock error: {str(e)}")
        return "Error generating response from Bedrock."

# WebSocket connection manager
class SessionManager:
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}
        self.active_contexts: Dict[str, str] = {}

    async def initialize(self, websocket: WebSocket):
        await websocket.accept()
        logger.info(f"Connected opened, awaiting session object")
        await websocket.send_text(json.dumps({"msg": "To setup session, Send session-id with child-id"}))

    async def connect(self, websocket: WebSocket, session_id: str):
        # await websocket.accept()
        self.active_connections[session_id] = websocket
        logger.info(f"Connected: {session_id}")

    def disconnect(self, session_id: str):
        if session_id in self.active_connections:
            del self.active_connections[session_id]
            logger.info(f"Disconnected: {session_id}")

    def set_graph_context(self, session_id: str, context: str):
        if session_id in self.active_connections and session_id not in self.active_contexts:
            self.active_contexts[session_id] = context

        if session_id not in self.active_connections and session_id in self.active_contexts:
            del self.active_contexts[session_id]
            logger.info(f"Deleted dangling context from session: {session_id}")

    def get_graph_context(self, session_id: str):
        return self.active_contexts.get(session_id)


    async def send_message(self, session_id: str, message: str):
        if session_id in self.active_connections:
            await self.active_connections[session_id].send_text(message)

manager = SessionManager()

@app.post("/uploadfile/")
async def create_upload_file(file: UploadFile = File(...)):
    return {"filename": file.filename, "content_type": file.content_type}

@app.post("/image-base64/")
async def upload_image(file: UploadFile = File(...)):
    contents = await file.read()
    encoded_image = base64.b64encode(contents).decode("utf-8")
    return {"image_data": encoded_image}

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
                await manager.send_message(session_id, json.dumps({"msg": "Enter prompt"}))
                input_json = await websocket.receive_json()
                schema_ns, payload = validate_and_load(input_json)

                # prompt_data = payload.prompt
                #
                # await manager.send_message(session_id, json.dumps({
                #     "msg": """Enter image as base64 string, if not press enter. format json: {"image_data": "image_base64_string"}"""}))

                if not payload.prompt:
                    await manager.send_message(session_id, json.dumps({"error": "No prompt provided"}))
                    continue

                logger.info(f"Received prompt for {child_id}: {payload.prompt}, "
                            f"Image: {'Yes' if isinstance(payload, SchemaTwoModel) and payload.image_data else 'No'}")

                # Get graph context
                if not manager.get_graph_context(session_id):
                    ctx = build_graph_context(child_id)
                    manager.set_graph_context(session_id, ctx)

                context = manager.get_graph_context(session_id)
                if "Error" in context:
                    await manager.send_message(
                        session_id,
                        json.dumps({"error": context})
                    )
                    continue

                image_data_hex_value=None
                # Add image if provided
                if isinstance(payload, SchemaTwoModel) and payload.image_data:
                    try:
                        image_data = payload.image_data
                        # Decode base64 image
                        image_bytes = base64.b64decode(
                            image_data.split(",")[1] if "," in image_data else image_data)
                        # image_data_hex_value=image_bytes.hex()
                        image_data_hex_value=image_data

                    except Exception as e:
                        await websocket.send_text(json.dumps({"error": f"Invalid image data: {str(e)}"}))
                        continue

                response = await call_bedrock(context, prompt=payload.prompt, image_hex=image_data_hex_value)

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
                    json.dumps({"error": f"Internal server error: {str(e)}"})
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