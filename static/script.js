document.addEventListener("DOMContentLoaded", () => {
  const messageForm = document.getElementById("message-form");
  const messageInput = document.getElementById("message-input");
  const messagesContainer = document.getElementById("messages");

  // Establish WebSocket connection
  const wsProtocol = window.location.protocol === "https:" ? "wss:" : "ws:";
  const ws = new WebSocket(`${wsProtocol}//${window.location.host}/ws/chat`);

  const addMessage = (content, type) => {
    const messageElement = document.createElement("div");
    messageElement.classList.add("message", `${type}-message`);
    messageElement.textContent = content;
    messagesContainer.appendChild(messageElement);
    // Scroll to the bottom
    messagesContainer.scrollTop = messagesContainer.scrollHeight;
  };

  ws.onopen = (event) => {
    console.log("WebSocket connection established");
    addMessage("Connected to the Cybersecurity RAG Assistant!", "bot");
  };

  ws.onmessage = (event) => {
    console.log("Message from server: ", event.data);
    addMessage(event.data, "bot");
  };

  ws.onclose = (event) => {
    console.log("WebSocket connection closed");
    addMessage("Connection closed.", "bot");
  };

  ws.onerror = (error) => {
    console.error("WebSocket error: ", error);
    addMessage("An error occurred with the connection.", "bot");
  };

  messageForm.addEventListener("submit", (event) => {
    event.preventDefault();
    const message = messageInput.value.trim();
    if (message && ws.readyState === WebSocket.OPEN) {
      addMessage(message, "user");
      ws.send(message);
      messageInput.value = "";
    }
  });
});
