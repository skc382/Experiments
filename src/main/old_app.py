from flask import Flask, render_template, jsonify
from flask_socketio import SocketIO, emit
import boto3
import json
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'your-secret-key')
socketio = SocketIO(app, cors_allowed_origins="*")

# Initialize AWS Bedrock client
bedrock = boto3.client(
    service_name='main-runtime',
    region_name=os.getenv('AWS_REGION', 'us-east-1'),
    aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID'),
    aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY')
)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/websocket')
def websocket_info():
    """Return WebSocket connection details."""
    host = os.getenv('APP_HOST', 'localhost')
    port = os.getenv('APP_PORT', '5000')
    protocol = 'wss' if os.getenv('FLASK_ENV') == 'production' else 'ws'
    websocket_url = f"{protocol}://{host}:{port}"
    return jsonify({
        'status': 'success',
        'websocket_url': websocket_url
    })

@socketio.on('query_model')
def handle_query(data):
    try:
        body = json.dumps({
            "schemaVersion": "messages-v1",
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {
                            "text": f"\"{data['prompt']}\""
                        }
                    ]
                }
            ],
            "inferenceConfig": {
                "maxTokens": "512",
                "temperature": "0.5",
                "topP": "0.9"
            }
        })

        # Invoke the model
        response = bedrock.invoke_model(
            modelId="amazon.nova-lite-v1:0",
            body=body
        )
        
        # Parse the response
        response_body = json.loads(response['body'].read())
        
        # Emit the response back to the client
        emit('model_response', {
            'status': 'success',
            'response': response_body['output']['message']['content'][0]['text']
        })
        
    except Exception as e:
        emit('model_response', {
            'status': 'error',
            'error': str(e)
        })

if __name__ == '__main__':
    host = os.getenv('APP_HOST', '0.0.0.0')
    port = int(os.getenv('APP_PORT', 5000))
    socketio.run(app, debug=os.getenv('FLASK_ENV') != 'production', host=host, port=port)