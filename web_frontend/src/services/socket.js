import { io } from "socket.io-client";

const URL = "ws://localhost:8000"; // Your backend WebSocket URL
let socket;

export const connectSocket = (userId, onMessageCallback) => {
  // Disconnect previous socket if it exists
  if (socket) {
      socket.disconnect();
  }

  // Pass user_id in query for initial connection auth
  socket = io(URL, { 
    transports: ['websocket'],
    query: { userId } // Pass user ID for backend to map connection
  });

  socket.on("connect", () => {
    console.log(`Socket connected with ID: ${socket.id} for user ${userId}`);
  });
  
  // A generic event for server-pushed messages
  socket.on("notification", (data) => {
    console.log("Notification received:", data);
    if(onMessageCallback) {
        onMessageCallback(data);
    }
  });

  socket.on("disconnect", () => {
    console.log("Socket disconnected");
  });
};

export const disconnectSocket = () => {
  if (socket) {
    socket.disconnect();
  }
};
