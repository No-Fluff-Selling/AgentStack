import asyncio
import websockets
import aiohttp
import json
import uuid

async def submit_analysis(session, submission_id):
    """Submit a new analysis request"""
    url = "http://localhost:8000/submit"
    data = {
        "submissionId": submission_id,
        "userUrl": "https://nofluffselling.com/",  # Real company URL
        "targetUrl": "https://www.bigeye.com/"  # Real company URL
    }
    async with session.post(url, json=data) as response:
        return await response.json()

async def listen_to_websocket(submission_id):
    """Listen to WebSocket updates"""
    uri = f"ws://localhost:8000/ws/{submission_id}"
    
    # Maximum number of retries
    max_retries = 3
    retry_delay = 2
    
    for attempt in range(max_retries):
        try:
            # Wait before attempting to connect
            await asyncio.sleep(retry_delay)
            
            print(f"Attempt {attempt + 1}/{max_retries} to connect to WebSocket...")
            
            # Increase connection timeout to 60 seconds
            async with websockets.connect(
                uri,
                ping_interval=20,
                ping_timeout=20,
                open_timeout=60.0,
                close_timeout=60.0
            ) as websocket:
                print(f"Connected to WebSocket for submission {submission_id}")
                while True:
                    try:
                        message = await websocket.recv()
                        print("\nReceived update:")
                        # Parse and pretty print the JSON message
                        updates = json.loads(message)
                        for update in updates:
                            print(f"\nStep {update['idx']}:")
                            print(f"Message: {update['message']}")
                            print(f"Details: {update['details']}")
                            if update.get('output'):
                                print(f"Output: {update['output']}")
                    except websockets.exceptions.ConnectionClosed:
                        print("WebSocket connection closed")
                        break
                    except Exception as e:
                        print(f"Error receiving message: {str(e)}")
                        break
        except Exception as e:
            print(f"Error connecting to WebSocket (attempt {attempt + 1}/{max_retries}): {str(e)}")
            if attempt == max_retries - 1:
                print("Max retries reached, giving up.")
                return
            continue
        # If we get here, we had a successful connection and finished normally
        break

async def main():
    # Generate a unique submission ID
    submission_id = str(uuid.uuid4())
    print(f"Testing with submission ID: {submission_id}")

    # Create a session for HTTP requests
    async with aiohttp.ClientSession() as session:
        # Submit the analysis request
        print("\nSubmitting analysis request...")
        response = await submit_analysis(session, submission_id)
        print(f"Response: {response}")

        # Wait for execution to be ready
        print("\nWaiting for execution to be ready...")
        await asyncio.sleep(5)

        # Listen to WebSocket updates
        print("\nConnecting to WebSocket...")
        await listen_to_websocket(submission_id)

if __name__ == "__main__":
    asyncio.run(main())
