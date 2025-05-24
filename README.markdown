# Flask WebSocket Application with AWS Bedrock Integration

This is a FastApi web-service, which provides access to aws bedrock model over a websocket

## Setup Instructions

### Configure Environment Variables
Create a `.env` file in the project root with the following content:
```
AWS_REGION=us-east-1
AWS_ACCESS_KEY_ID=your-aws-access-key
AWS_SECRET_ACCESS_KEY=your-aws-secret-key
NEO4J_PASSWORD=your-password-for-neo4j-db
```

### Install Dependencies (Local Development)
For local development, install the required Python packages:
```bash
pip install -r requirements.txt
```

## Building the Application

### Build the Docker Image
To containerize the application, build the Docker image:
```bash
docker compose up -d
```

## Running the Application

### Option 1: Run Locally
To run the application without Docker:
1. Ensure dependencies are installed (see Setup Instructions).
2. Start the Fastapi development server:
   ```bash
   python app.py
   ```

### Option 2: Run with Docker
To run the application in a Docker container:
1. Run the container, mapping port 5000 and passing environment variables:
   ```bash
   docker compose up 
   ```
   
## Testing the Application

### 1. Test the WebSocket API
The `/ws/graphrag` endpoint returns the WebSocket connection URL.
- **Command**:
  ```bash
  $ wscat -c ws://localhost:8000/ws/graphrag
  $ Connected (press CTRL+C to quit)
  > {"session_id": "sess123", "child_id": "C001"}
  > {"prompt": "Explain Aarav’s doing in extra-curricular classes"}
  ```
- **Expected Response** (in development):
  ```bash
  {"response": [{"text": "It's wonderful to see Aarav Sharma engaging in a variety of activities both 
  in and out of the classroom. In addition to his academic pursuits, Aarav has shown a strong interest 
  in Indian Classical Dance, which is a fantastic way to express creativity and cultural pride. Completing 
  a dance performance must have filled him with a sense of accomplishment and joy. This involvement not
   only enhances his artistic skills but also boosts his confidence and sense of community. 
  It's great to see how Aarav balances his studies with enriching extracurricular activities, which contribute to his overall growth and development."
  }], "source": "bedrock"}
  ```
  