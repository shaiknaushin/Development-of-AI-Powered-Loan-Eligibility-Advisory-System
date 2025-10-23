import socketio

# Create the Socket.IO asynchronous server.
# This is the crucial fix: we explicitly tell the Socket.IO server to NOT handle
# CORS, because the main FastAPI application will manage it. This prevents the
# "multiple values" error.
sio = socketio.AsyncServer(async_mode='asgi', cors_allowed_origins=[])

# A dictionary to map authenticated user IDs to their unique session IDs (sid).
user_sids = {}

@sio.event
async def connect(sid, environ, auth):
    """
    Handles a new client connection.
    """
    print(f"Client connected: {sid}")
    user_id = auth.get('userId') if auth else None
    if user_id:
        user_sids[user_id] = sid
        print(f"User {user_id} has been mapped to session ID {sid}")

@sio.event
async def disconnect(sid):
    """
    Handles a client disconnection.
    """
    for user_id, mapped_sid in list(user_sids.items()):
        if mapped_sid == sid:
            del user_sids[user_id]
            print(f"User {user_id} (sid: {sid}) has disconnected and been unmapped.")
            break
    print(f"Client disconnected: {sid}")

class ConnectionManager:
    """
    A helper class to manage sending messages from the API routers.
    """
    async def broadcast(self, message: str):
        await sio.emit('notification', {'message': message})
        print(f"Broadcasted message: '{message}'")

    async def send_personal_message(self, message: str, user_id: int, data: dict = None):
        sid = user_sids.get(user_id)
        payload = {'message': message}
        if data:
            payload.update(data)
        
        if sid:
            await sio.emit('notification', payload, to=sid)
            print(f"Sent personal message to user {user_id} (sid: {sid}): '{message}'")
        else:
            print(f"Could not send personal message: User {user_id} is not connected.")

manager = ConnectionManager()

