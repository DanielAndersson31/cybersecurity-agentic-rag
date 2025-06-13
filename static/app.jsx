const { useState, useEffect, useRef, StrictMode } = React;

const App = () => {
  // --- STATE MANAGEMENT ---
  const [chats, setChats] = useState({});
  const [currentSessionId, setCurrentSessionId] = useState(null);
  const [isSettingsOpen, setSettingsOpen] = useState(false);
  // Default to system preference, fallback to light
  const [theme, setTheme] = useState(localStorage.getItem("theme") || "light");
  const ws = useRef(null);

  // --- EFFECTS ---
  useEffect(() => {
    // Apply theme on initial load and when it changes
    document.documentElement.classList.toggle("dark", theme === "dark");
    localStorage.setItem("theme", theme);
  }, [theme]);

  useEffect(() => {
    // Initialize WebSocket connection
    const wsProtocol = window.location.protocol === "https" ? "wss:" : "ws:";
    ws.current = new WebSocket(`${wsProtocol}//${window.location.host}/ws/chat`);

    ws.current.onopen = () => console.log("WebSocket connected");
    ws.current.onclose = () => console.log("WebSocket disconnected");
    ws.current.onerror = (err) => console.error("WebSocket error:", err);

    ws.current.onmessage = (event) => {
      const data = JSON.parse(event.data);
      const serverSessionId = data.session_id;

      setChats((prevChats) => {
        const newChats = { ...prevChats };
        const provisionalId = Object.keys(newChats).find((id) => newChats[id].isTyping);

        if (provisionalId) {
          const provisionalChatData = newChats[provisionalId];
          delete newChats[provisionalId];

          newChats[serverSessionId] = {
            ...provisionalChatData,
            history: [...provisionalChatData.history, { type: "agent", content: data }],
            isTyping: false,
          };
        } else {
          newChats[serverSessionId] = {
            ...newChats[serverSessionId],
            history: [...(newChats[serverSessionId]?.history || []), { type: "agent", content: data }],
            isTyping: false,
          };
        }

        return newChats;
      });

      setCurrentSessionId(serverSessionId);
    };

    // Start with a clean slate
    handleNewChat();

    return () => ws.current.close();
  }, []);

  // --- HANDLERS ---
  const handleSendMessage = (query) => {
    if (!query.trim() || !ws.current || ws.current.readyState !== WebSocket.OPEN) return;

    let activeId = currentSessionId;
    let sessionIdToSend = currentSessionId;

    // This is a new chat
    if (!activeId) {
      activeId = `provisional-${Date.now()}`;
      sessionIdToSend = null; // Backend will create a real ID

      setCurrentSessionId(activeId);

      setChats((prev) => ({
        ...prev,
        [activeId]: {
          title: query,
          history: [{ type: "user", content: query }],
          isTyping: true,
        },
      }));
    } else {
      // This is an existing chat
      setChats((prev) => ({
        ...prev,
        [activeId]: {
          ...prev[activeId],
          history: [...prev[activeId].history, { type: "user", content: query }],
          isTyping: true,
        },
      }));
    }

    ws.current.send(JSON.stringify({ query, session_id: sessionIdToSend }));
  };

  const handleNewChat = () => {
    setCurrentSessionId(null);
  };

  const handleClearChats = () => {
    // This could also call a backend endpoint to clear server-side history
    setChats({});
    handleNewChat();
    setSettingsOpen(false);
  };

  const handleDeleteChat = (sessionIdToDelete) => {
    setChats((prev) => {
      const newChats = { ...prev };
      delete newChats[sessionIdToDelete];
      return newChats;
    });

    // If the deleted chat was the active one, reset to new chat view
    if (currentSessionId === sessionIdToDelete) {
      setCurrentSessionId(null);
    }
  };

  // --- RENDER ---
  return (
    <div className="flex h-screen w-screen bg-white dark:bg-gray-900 font-sans">
      <Sidebar
        chats={chats}
        currentSessionId={currentSessionId}
        onChatSelect={setCurrentSessionId}
        onNewChat={handleNewChat}
        onDeleteChat={handleDeleteChat}
        onOpenSettings={() => setSettingsOpen(true)}
      />
      <ChatWindow chat={currentSessionId ? chats[currentSessionId] : null} onSendMessage={handleSendMessage} />
      {isSettingsOpen && (
        <SettingsModal
          onClose={() => setSettingsOpen(false)}
          theme={theme}
          onToggleTheme={() => setTheme((t) => (t === "light" ? "dark" : "light"))}
          onClearChats={handleClearChats}
        />
      )}
    </div>
  );
};

// --- COMPONENTS ---

const Sidebar = ({ chats, currentSessionId, onChatSelect, onNewChat, onDeleteChat, onOpenSettings }) => (
  <div className="w-[300px] bg-gray-50 dark:bg-black/20 flex flex-col p-4 border-r border-gray-200 dark:border-gray-700">
    <button
      onClick={onNewChat}
      className="w-full mb-4 px-4 py-2.5 text-md font-semibold rounded-lg border border-blue-500 text-blue-500 hover:bg-blue-500 hover:text-white transition-colors duration-200 flex items-center justify-center gap-2"
    >
      <i className="fas fa-plus"></i> New Chat
    </button>
    <ul className="flex-grow overflow-y-auto -mr-2 pr-2">
      {Object.keys(chats).map((sid) => (
        <li
          key={sid}
          onClick={() => onChatSelect(sid)}
          className={`group flex justify-between items-center p-3 my-1 rounded-lg cursor-pointer truncate font-medium text-gray-700 dark:text-gray-300 ${
            currentSessionId === sid ? "bg-blue-500 text-white" : "hover:bg-gray-200 dark:hover:bg-gray-700/50"
          }`}
        >
          <span className="truncate">{chats[sid]?.title}</span>
          <button
            onClick={(e) => {
              e.stopPropagation(); // Prevent li's onClick from firing
              onDeleteChat(sid);
            }}
            className="ml-2 opacity-0 group-hover:opacity-100 text-gray-500 hover:text-red-500 dark:text-gray-400 dark:hover:text-red-400 transition-opacity"
          >
            <i className="fas fa-trash-alt"></i>
          </button>
        </li>
      ))}
    </ul>
    <button
      onClick={onOpenSettings}
      className="w-full mt-4 px-4 py-2.5 text-md font-semibold rounded-lg border border-gray-500 dark:border-gray-600 text-gray-600 dark:text-gray-300 hover:bg-gray-600 hover:text-white transition-colors duration-200 flex items-center justify-center gap-2"
    >
      <i className="fas fa-cog"></i> Settings
    </button>
  </div>
);

const ChatWindow = ({ chat, onSendMessage }) => {
  const messagesEndRef = useRef(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [chat?.history, chat?.isTyping]);

  const WelcomeMessage = () => (
    <div className="text-gray-600 dark:text-gray-300">
      <div className="p-6 rounded-lg bg-gray-100 dark:bg-gray-700/50">
        <p className="font-semibold text-lg mb-2">👋 Hello! I'm your cybersecurity assistant. I can help you with:</p>
        <ul className="list-disc list-inside space-y-1">
          <li>Incident response procedures</li>
          <li>Threat intelligence analysis</li>
          <li>Security prevention strategies</li>
        </ul>
        <p className="mt-4">What would you like to know?</p>
      </div>
    </div>
  );

  return (
    <div className="flex-1 flex flex-col h-screen bg-white dark:bg-gray-800">
      <Header />
      <main className="flex-1 overflow-y-auto p-6 space-y-6">
        {!chat ? <WelcomeMessage /> : chat.history.map((msg, index) => <Message key={index} message={msg} />)}
        {chat?.isTyping && <TypingIndicator />}
        <div ref={messagesEndRef} />
      </main>
      <InputArea onSendMessage={onSendMessage} />
    </div>
  );
};

const Header = () => (
  <header className="bg-gray-800 dark:bg-gray-900 text-white p-6 text-center shadow-md z-10">
    <h1 className="text-2xl font-bold flex items-center justify-center gap-3">
      <i className="fas fa-shield-alt text-blue-400"></i>
      Cybersecurity RAG Assistant
    </h1>
    <p className="text-gray-300 mt-1">
      Get expert help with incident response, threat intelligence, and security prevention
    </p>
  </header>
);

const InputArea = ({ onSendMessage }) => {
  const [input, setInput] = useState("");
  const suggestionChips = ["Security Breach", "Ransomware Intel", "Prevention Tips"];

  const handleFormSubmit = (e) => {
    e.preventDefault();
    onSendMessage(input);
    setInput("");
  };

  const handleChipClick = (chipText) => {
    setInput(chipText);
  };

  return (
    <footer className="bg-white dark:bg-gray-800 p-4 border-t border-gray-200 dark:border-gray-700">
      <div className="flex justify-center gap-2 mb-3">
        {suggestionChips.map((chip) => (
          <button
            key={chip}
            onClick={() => handleChipClick(chip)}
            className="px-4 py-1.5 bg-gray-200 dark:bg-gray-700 text-sm font-medium text-gray-700 dark:text-gray-200 rounded-full hover:bg-gray-300 dark:hover:bg-gray-600 transition-colors"
          >
            {chip}
          </button>
        ))}
      </div>
      <form onSubmit={handleFormSubmit} className="flex gap-4 items-center">
        <input
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Ask your cybersecurity question..."
          className="flex-1 p-4 w-full text-md rounded-full border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 focus:outline-none focus:ring-2 focus:ring-blue-500 transition-shadow"
        />
        <button
          type="submit"
          className="w-14 h-14 bg-blue-600 text-white font-semibold rounded-full hover:bg-blue-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center"
          disabled={!input.trim()}
        >
          <i className="fas fa-paper-plane text-xl"></i>
        </button>
      </form>
    </footer>
  );
};

const Message = ({ message }) => {
  const isUser = message.type === "user";
  const content = isUser ? message.content : message.content.response;
  const agentData = isUser ? null : message.content;

  return (
    <div className={`flex items-start gap-3 ${isUser ? "justify-end" : "justify-start"}`}>
      {!isUser && (
        <span className="w-8 h-8 rounded-full bg-gray-700 flex items-center justify-center text-white flex-shrink-0">
          <i className="fas fa-robot"></i>
        </span>
      )}
      <div
        className={`p-4 rounded-lg max-w-2xl prose dark:prose-invert prose-p:my-2 prose-ul:my-2 ${
          isUser ? "bg-blue-600 text-white" : "bg-gray-100 dark:bg-gray-700 text-gray-800 dark:text-gray-100"
        }`}
      >
        <div dangerouslySetInnerHTML={{ __html: marked.parse(content || "") }} />
        {agentData?.was_collaboration && (
          <details className="mt-3 border-t border-gray-300/50 dark:border-gray-500/50 pt-2 text-sm">
            <summary className="cursor-pointer font-semibold">Collaboration Details</summary>
            <ul className="list-disc pl-5 mt-1 text-xs">
              <li>
                <strong>Mode:</strong> {agentData.collaboration_mode}
              </li>
              <li>
                <strong>Primary Agent:</strong> {agentData.primary_agent || "N/A"}
              </li>
              <li>
                <strong>Consulting Agents:</strong> {agentData.consulting_agents.join(", ")}
              </li>
              {agentData.thought_process && (
                <li className="mt-2">
                  <strong>Thought Process:</strong>
                  <ul className="list-disc pl-5 mt-1">
                    {agentData.thought_process.map((step, index) => (
                      <li key={index}>{step}</li>
                    ))}
                  </ul>
                </li>
              )}
            </ul>
          </details>
        )}
      </div>
    </div>
  );
};

const TypingIndicator = () => (
  <div className="flex items-start gap-3 justify-start">
    <span className="w-8 h-8 rounded-full bg-gray-700 flex items-center justify-center text-white flex-shrink-0">
      <i className="fas fa-robot"></i>
    </span>
    <div className="p-4 rounded-lg bg-gray-100 dark:bg-gray-700 flex items-center space-x-2">
      <span className="h-2.5 w-2.5 bg-gray-500 rounded-full animate-bounce [animation-delay:-0.3s]"></span>
      <span className="h-2.5 w-2.5 bg-gray-500 rounded-full animate-bounce [animation-delay:-0.15s]"></span>
      <span className="h-2.5 w-2.5 bg-gray-500 rounded-full animate-bounce"></span>
    </div>
  </div>
);

const SettingsModal = ({ onClose, theme, onToggleTheme, onClearChats }) => (
  <div className="fixed inset-0 bg-black bg-opacity-60 flex justify-center items-center z-50 transition-opacity">
    <div className="bg-white dark:bg-gray-800 rounded-lg shadow-xl p-6 w-full max-w-md mx-4">
      <div className="flex justify-between items-center border-b pb-3 dark:border-gray-700">
        <h2 className="text-2xl font-bold text-gray-800 dark:text-gray-100">Settings</h2>
        <button onClick={onClose} className="text-2xl text-gray-500 hover:text-red-500 dark:hover:text-red-400">
          &times;
        </button>
      </div>
      <div className="mt-6 space-y-6">
        <div className="flex justify-between items-center">
          <label className="text-lg text-gray-700 dark:text-gray-200">Dark Mode</label>
          <label className="relative inline-flex items-center cursor-pointer">
            <input type="checkbox" checked={theme === "dark"} onChange={onToggleTheme} className="sr-only peer" />
            <div className="w-11 h-6 bg-gray-200 peer-focus:outline-none rounded-full peer dark:bg-gray-700 peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all dark:border-gray-600 peer-checked:bg-blue-600"></div>
          </label>
        </div>
        <div className="flex justify-between items-center">
          <label className="text-lg text-gray-700 dark:text-gray-200">Manage Data</label>
          <button
            onClick={onClearChats}
            className="px-4 py-2 bg-red-600 text-white font-semibold rounded-lg hover:bg-red-700 transition-colors"
          >
            Clear All Chats
          </button>
        </div>
      </div>
    </div>
  </div>
);

const root = ReactDOM.createRoot(document.getElementById("root"));
root.render(
  <StrictMode>
    <App />
  </StrictMode>
);
