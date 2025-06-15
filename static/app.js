import React, { useState, useEffect, useRef } from "https://esm.sh/react@18.2.0";
import ReactDOM from "https://esm.sh/react-dom@18.2.0";
import { marked } from "https://esm.sh/marked@4.0.12";

const App = () => {
  const [messages, setMessages] = useState([]);
  const [sessionId, setSessionId] = useState(localStorage.getItem("sessionId") || null);
  const [socket, setSocket] = useState(null);
  const [query, setQuery] = useState("");
  const [isThinking, setIsThinking] = useState(false);
  const [model, setModel] = useState(localStorage.getItem("model") || "openai_mini");
  const [agent, setAgent] = useState(localStorage.getItem("agent") || "auto");
  const messagesEndRef = useRef(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    if (!sessionId) {
      const newId = crypto.randomUUID();
      setSessionId(newId);
      localStorage.setItem("sessionId", newId);
    } else {
      // Fetch history
      fetch(`/chat_history/${sessionId}`)
        .then((res) => res.json())
        .then((data) => {
          if (data.history) {
            setMessages(
              data.history.map((msg) => ({
                ...msg,
                type: msg.type === "human" ? "user" : "ai",
              }))
            );
          }
        });
    }
  }, [sessionId]);

  useEffect(scrollToBottom, [messages]);

  useEffect(() => {
    const ws = new WebSocket(`ws://${window.location.host}/ws/chat`);
    setSocket(ws);

    ws.onopen = () => console.log("WebSocket connected");
    ws.onmessage = (event) => {
      const data = JSON.parse(event.data);
      setIsThinking(false);
      setMessages((prev) => [...prev, { ...data, type: "ai" }]);
    };
    ws.onclose = () => console.log("WebSocket disconnected");
    ws.onerror = (error) => console.error("WebSocket Error:", error);

    return () => ws.close();
  }, [sessionId]);

  const handleSendMessage = (e) => {
    e.preventDefault();
    if (query.trim() && socket && socket.readyState === WebSocket.OPEN) {
      setMessages((prev) => [...prev, { type: "user", content: query }]);
      socket.send(JSON.stringify({ query, session_id: sessionId, model, agent }));
      setQuery("");
      setIsThinking(true);
    }
  };

  useEffect(() => {
    localStorage.setItem("model", model);
    localStorage.setItem("agent", agent);
  }, [model, agent]);

  const agentOptions = [
    { value: "auto", label: "Auto-Route" },
    { value: "incident_response", label: "Incident Response" },
    { value: "threat_intelligence", label: "Threat Intelligence" },
    { value: "prevention", label: "Prevention" },
  ];

  const modelOptions = [
    { value: "openai_mini", label: "GPT-4o Mini" },
    { value: "gpt4o", label: "GPT-4o" },
    { value: "claude_sonnet", label: "Claude 3.5 Sonnet" },
  ];

  return (
    <div className="flex flex-col h-screen bg-light-bg">
      <Header />
      <div className="flex-1 overflow-y-auto p-4 md:p-6 space-y-6">
        {messages.map((msg, index) => (
          <ChatMessage key={index} message={msg} />
        ))}
        {isThinking && <ThinkingBubble />}
        <div ref={messagesEndRef} />
      </div>
      <InputArea
        query={query}
        setQuery={setQuery}
        handleSendMessage={handleSendMessage}
        isThinking={isThinking}
        agent={agent}
        setAgent={setAgent}
        model={model}
        setModel={setModel}
        agentOptions={agentOptions}
        modelOptions={modelOptions}
      />
    </div>
  );
};

const Header = () => (
  <header className="bg-white shadow-md p-4 flex items-center justify-between z-10">
    <div className="flex items-center space-x-3">
      <i className="fas fa-shield-alt text-2xl text-primary"></i>
      <h1 className="text-xl font-bold text-dark-text">Cybersecurity RAG Agent</h1>
    </div>
    <a href="https://github.com/dandero/cybersecurity-agentic-rag" target="_blank" rel="noopener noreferrer">
      <i className="fab fa-github text-2xl text-gray-500 hover:text-primary transition-colors"></i>
    </a>
  </header>
);

const ChatMessage = ({ message }) => {
  const isUser = message.type === "user";
  const parsedContent = isUser ? message.content : marked.parse(message.content || "");

  const icon = isUser ? (
    <i className="fas fa-user-circle text-2xl text-secondary"></i>
  ) : (
    <i className="fas fa-robot text-2xl text-accent"></i>
  );

  const metadata = !isUser && (
    <div className="text-xs text-gray-500 mt-2 flex items-center space-x-4">
      {message.agent_type && (
        <span>
          <i className="fas fa-cogs mr-1"></i>
          {message.agent_type}
        </span>
      )}
      {message.confidence_score && (
        <span>
          <i className="fas fa-check-circle mr-1"></i>Confidence: {message.confidence_score.toFixed(2)}
        </span>
      )}
      {message.model_used && (
        <span>
          <i className="fas fa-brain mr-1"></i>
          {message.model_used}
        </span>
      )}
    </div>
  );

  return (
    <div className={`flex items-start gap-4 ${isUser ? "justify-end" : ""}`}>
      {!isUser && <div className="flex-shrink-0">{icon}</div>}
      <div className={`max-w-2xl w-full p-4 rounded-lg shadow-sm ${isUser ? "bg-secondary text-white" : "bg-white"}`}>
        <div className="prose max-w-none" dangerouslySetInnerHTML={{ __html: parsedContent }}></div>
        {metadata}
      </div>
      {isUser && <div className="flex-shrink-0">{icon}</div>}
    </div>
  );
};

const ThinkingBubble = () => (
  <div className="flex items-start gap-4">
    <i className="fas fa-robot text-2xl text-accent"></i>
    <div className="max-w-2xl w-full p-4 rounded-lg shadow-sm bg-white flex items-center space-x-2">
      <div className="w-2 h-2 bg-gray-400 rounded-full animate-pulse"></div>
      <div className="w-2 h-2 bg-gray-400 rounded-full animate-pulse [animation-delay:0.2s]"></div>
      <div className="w-2 h-2 bg-gray-400 rounded-full animate-pulse [animation-delay:0.4s]"></div>
    </div>
  </div>
);

const InputArea = ({
  query,
  setQuery,
  handleSendMessage,
  isThinking,
  agent,
  setAgent,
  model,
  setModel,
  agentOptions,
  modelOptions,
}) => (
  <div className="bg-white border-t border-gray-200 p-4">
    <div className="max-w-4xl mx-auto">
      <div className="flex items-center space-x-2 mb-2">
        <Select value={agent} onChange={(e) => setAgent(e.target.value)} options={agentOptions} icon="fa-cogs" />
        <Select value={model} onChange={(e) => setModel(e.target.value)} options={modelOptions} icon="fa-brain" />
      </div>
      <form onSubmit={handleSendMessage} className="flex items-center space-x-2">
        <input
          type="text"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="Ask a cybersecurity question..."
          className="flex-1 p-3 border border-gray-300 rounded-full focus:outline-none focus:ring-2 focus:ring-primary"
          disabled={isThinking}
        />
        <button
          type="submit"
          className="bg-primary text-white rounded-full h-12 w-12 flex items-center justify-center hover:bg-blue-800 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-primary disabled:bg-gray-400 transition-colors"
          disabled={isThinking || !query.trim()}
        >
          <i className="fas fa-paper-plane"></i>
        </button>
      </form>
    </div>
  </div>
);

const Select = ({ value, onChange, options, icon }) => (
  <div className="relative">
    <i className={`fas ${icon} absolute top-1/2 left-3 transform -translate-y-1/2 text-gray-400`}></i>
    <select
      value={value}
      onChange={onChange}
      className="pl-9 pr-8 py-2 text-sm border border-gray-300 rounded-full appearance-none focus:outline-none focus:ring-2 focus:ring-primary bg-white"
    >
      {options.map((opt) => (
        <option key={opt.value} value={opt.value}>
          {opt.label}
        </option>
      ))}
    </select>
  </div>
);

ReactDOM.render(<App />, document.getElementById("root"));
