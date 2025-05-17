# Flask WebSocket Application with AWS Bedrock Integration

This is a Flask-based web application that integrates with AWS Bedrock's Nova Lite model to process user queries via a WebSocket connection. It includes an API to expose WebSocket connection details and is containerized using Docker for easy deployment.

## Features
- WebSocket-based communication with AWS Bedrock for real-time query processing.
- REST API endpoint (`/api/websocket`) to retrieve WebSocket connection details.
- Dockerized for consistent deployment across environments.
- Environment variable configuration for flexibility.

## Prerequisites
To build, run, and test the application, ensure you have the following installed:
- **Python 3.9+** (for local development)
- **Docker** (for containerized deployment)
- **AWS CLI** (optional, for configuring AWS credentials)
- **curl** or a tool like Postman (for testing the API)
- **A web browser** (for accessing the web interface)
- **Git** (to clone the repository, if applicable)

You also need an AWS account with access to the Bedrock service and valid AWS credentials.

## Project Structure
```
├── app.py                # Main Flask application
├── templates/
│   └── index.html        # Frontend template (update as needed)
├── Dockerfile            # Docker configuration
├── requirements.txt      # Python dependencies
├── .dockerignore         # Files to exclude from Docker image
├── .env                  # Environment variables (not tracked)
└── README.md             # This file
```

## Setup Instructions

### 1. Clone the Repository
If you have a Git repository, clone it:
```bash
git clone <repository-url>
cd <repository-directory>
```

Alternatively, ensure you have the project files (`app.py`, `Dockerfile`, `requirements.txt`, `.dockerignore`, and `templates/index.html`).

### 2. Configure Environment Variables
Create a `.env` file in the project root with the following content:
```
SECRET_KEY=your-secret-key
AWS_REGION=us-east-1
AWS_ACCESS_KEY_ID=your-aws-access-key
AWS_SECRET_ACCESS_KEY=your-aws-secret-key
APP_HOST=localhost
APP_PORT=5000
FLASK_ENV=development
```

- **`SECRET_KEY`**: A secure key for Flask's session management.
- **`AWS_REGION`**, **`AWS_ACCESS_KEY_ID`**, **`AWS_SECRET_ACCESS_KEY`**: Your AWS credentials for Bedrock access.
- **`APP_HOST`**, **`APP_PORT`**: The host and port for the application (default to `localhost:5000` for local development).
- **`FLASK_ENV`**: Set to `development` for local debugging or `production` for deployment.

**Note**: Do not commit the `.env` file to version control. It is excluded via `.dockerignore`.

### 3. Install Dependencies (Local Development)
For local development, install the required Python packages:
```bash
pip install -r requirements.txt
```

## Building the Application

### Build the Docker Image
To containerize the application, build the Docker image:
```bash
docker build -t flask-websocket-app .
```

This command:
- Uses the `Dockerfile` to create an image based on Python 3.9 slim.
- Installs dependencies from `requirements.txt`.
- Copies the application code into the image.

## Running the Application

### Option 1: Run Locally
To run the application without Docker:
1. Ensure dependencies are installed (see Setup Instructions).
2. Start the Flask development server:
   ```bash
   python app.py
   ```
3. Access the application:
   - Web interface: `http://localhost:5000`
   - WebSocket API: `http://localhost:5000/api/websocket`

### Option 2: Run with Docker
To run the application in a Docker container:
1. Run the container, mapping port 5000 and passing environment variables:
   ```bash
   docker run -p 5000:5000 \
       -e SECRET_KEY=your-secret-key \
       -e AWS_REGION=us-east-1 \
       -e AWS_ACCESS_KEY_ID=your-aws-access-key \
       -e AWS_SECRET_ACCESS_KEY=your-aws-secret-key \
       -e APP_HOST=0.0.0.0 \
       -e APP_PORT=5000 \
       -e FLASK_ENV=production \
       flask-websocket-app
   ```
2. Access the application:
   - Web interface: `http://localhost:5000`
   - WebSocket API: `http://localhost:5000/api/websocket`

**Note**: In production, configure a reverse proxy (e.g., Nginx) for HTTPS and update `APP_HOST` and `APP_PORT` as needed.

## Testing the Application

### 1. Test the WebSocket API
The `/api/websocket` endpoint returns the WebSocket connection URL.
- **Command**:
  ```bash
  curl http://localhost:5000/api/websocket
  ```
- **Expected Response** (in development):
  ```json
  {
      "status": "success",
      "websocket_url": "ws://localhost:5000"
  }
  ```
- **In Production**: The `websocket_url` will use `wss://` for secure connections.

### 2. Test the Web Interface
1. Open `http://localhost:5000` in a web browser.
2. Ensure the `index.html` template (in the `templates/` directory) loads correctly.
3. If you have a client-side WebSocket implementation (e.g., using Socket.IO), verify that it connects to the server and sends/receives messages.

### 3. Test WebSocket Communication
To test the WebSocket functionality, you need a client that connects to the WebSocket server and sends a `query_model` event. Below is a simple JavaScript example for testing:

```html
<script src="https://cdnjs.cloudflare.com/ajax/libs/socket.io/4.7.5/socket.io.js"></script>
<script>
    fetch('http://localhost:5000/api/websocket')
        .then(response => response.json())
        .then(data => {
            const socket = io(data.websocket_url);
            socket.on('connect', () => {
                console.log('Connected to WebSocket');
                socket.emit('query_model', { prompt: 'Hello, world!' });
            });
            socket.on('model_response', (data) => {
                console.log('Response:', data);
            });
        });
</script>
```

- Save this as `test.html`, open it in a browser, and check the console for output.
- **Expected Behavior**:
  - The client connects to the WebSocket server.
  - It sends a `query_model` event with a prompt.
  - The server responds with a `model_response` event containing the AWS Bedrock model's output or an error.

### 4. Test Error Handling
- Send an invalid prompt or use incorrect AWS credentials to verify that the application handles errors gracefully.
- Check the `model_response` event for an `error` status with a descriptive message.

## Notes
- **Security**: Keep AWS credentials and `SECRET_KEY` secure. Use a `.env` file or Docker environment variables instead of hardcoding them.
- **Production Deployment**: Use a WSGI server like Gunicorn (included in the Docker setup) and a reverse proxy for scalability and security.
- **WebSocket Client**: The `index.html` template should include Socket.IO client code to interact with the WebSocket server. Update it as needed for your use case.
- **AWS Bedrock**: Ensure your AWS account has access to the `amazon.nova-lite-v1:0` model and that credentials are correctly configured.

## Troubleshooting
- **Port Conflicts**: If port 5000 is in use, change `APP_PORT` in the `.env` file or Docker run command.
- **AWS Errors**: Verify AWS credentials and Bedrock service access in the AWS Management Console.
- **Docker Issues**: Ensure Docker is running and check build logs for errors (`docker build` output).

For additional help, refer to the Flask, Flask-SocketIO, and AWS Bedrock documentation.