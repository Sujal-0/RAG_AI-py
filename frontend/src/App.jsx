import { useState, useEffect, useRef } from "react";
import ReactMarkdown from "react-markdown";
import { MessageSquare, Folder, Settings, Wrench, RefreshCw, X, Minimize2, Maximize2, ChevronLeft, Building, Shield, Globe, Briefcase, Paperclip } from "lucide-react";
import LandingPage from "./components/LandingPage";

function App() {
  // Persisted States via localStorage
  const [workspace, setWorkspace] = useState(() => localStorage.getItem("workspace") || "chat");
  const [devMode, setDevMode] = useState(() => localStorage.getItem("devMode") === "true");
  const [selectedDocId, setSelectedDocId] = useState(() => localStorage.getItem("selectedDocId") || null);
  const [sidebarOpen, setSidebarOpen] = useState(() => {
    const saved = localStorage.getItem("sidebarOpen");
    return saved !== null ? saved === "true" : true;
  });
  const [similarityThreshold, setSimilarityThreshold] = useState(() => {
    const saved = localStorage.getItem("similarityThreshold");
    return saved !== null ? parseFloat(saved) : 0.42;
  });

  // Chat State
  const [chatMode, setChatMode] = useState("widget"); // "widget" | "fullscreen"
  const widgetRef = useRef(null);

  useEffect(() => {
    function handleClickOutside(event) {
      if (widgetRef.current && !widgetRef.current.contains(event.target) && chatMode === "widget") {
        setChatMode("collapsed");
      }
    }
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, [chatMode]);
  const [messages, setMessages] = useState(() => {
    try {
      const saved = localStorage.getItem("chatMessages");
      return saved ? JSON.parse(saved) : [];
    } catch (e) {
      return [];
    }
  });
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [selectedMessage, setSelectedMessage] = useState(null);
  const [copiedId, setCopiedId] = useState(null);
  const [expandedTraceId, setExpandedTraceId] = useState({});

  // Knowledge Base State
  const [documents, setDocuments] = useState([]);
  const [selectedDocDetails, setSelectedDocDetails] = useState(null);
  const [uploadingFile, setUploadingFile] = useState(null);
  const [activeJobId, setActiveJobId] = useState(null);
  const [activeJobStatus, setActiveJobStatus] = useState(null);
  const [knowledgeError, setKnowledgeError] = useState(null);
  const [dragOver, setDragOver] = useState(false);

  // Persistence Effects
  useEffect(() => {
    localStorage.setItem("workspace", workspace);
  }, [workspace]);

  useEffect(() => {
    localStorage.setItem("devMode", devMode ? "true" : "false");
  }, [devMode]);

  useEffect(() => {
    if (selectedDocId) {
      localStorage.setItem("selectedDocId", selectedDocId);
    } else {
      localStorage.removeItem("selectedDocId");
    }
  }, [selectedDocId]);

  useEffect(() => {
    localStorage.setItem("sidebarOpen", sidebarOpen ? "true" : "false");
  }, [sidebarOpen]);

  useEffect(() => {
    localStorage.setItem("similarityThreshold", similarityThreshold.toString());
  }, [similarityThreshold]);

  useEffect(() => {
    localStorage.setItem("chatMessages", JSON.stringify(messages));
  }, [messages]);

  const messagesContainerRef = useRef(null);
  const textareaRef = useRef(null);
  const fileInputRef = useRef(null);

  // Auto-focus input on mount
  useEffect(() => {
    if (workspace === "chat") {
      textareaRef.current?.focus();
    }
  }, [workspace]);

  // Handle auto-scroll logic for chat
  const [userHasScrolledUp, setUserHasScrolledUp] = useState(false);

  const handleScroll = () => {
    const container = messagesContainerRef.current;
    if (!container) return;

    const threshold = 150;
    const distanceFromBottom =
      container.scrollHeight - container.scrollTop - container.clientHeight;
    setUserHasScrolledUp(distanceFromBottom > threshold);
  };

  const scrollToBottom = (force = false) => {
    const container = messagesContainerRef.current;
    if (!container) return;

    if (force || !userHasScrolledUp) {
      container.scrollTo({
        top: container.scrollHeight,
        behavior: "smooth",
      });
    }
  };

  useEffect(() => {
    if (workspace === "chat") {
      scrollToBottom();
    }
  }, [messages, loading, workspace]);

  // Sync selected message with the latest bot response
  useEffect(() => {
    const botMessages = messages.filter((m) => m.sender === "bot" && m.debugInfo);
    if (botMessages.length > 0) {
      setSelectedMessage(botMessages[botMessages.length - 1]);
    } else {
      setSelectedMessage(null);
    }
  }, [messages]);

  // Fetch documents for the knowledge base
  const fetchDocuments = async () => {
    try {
      setKnowledgeError(null);
      const response = await fetch("http://localhost:8000/api/v1/documents");
      if (!response.ok) throw new Error("Failed to fetch documents list.");
      const data = await response.json();
      setDocuments(data);
    } catch (err) {
      console.error(err);
      setKnowledgeError("Could not retrieve documents from the server.");
    }
  };

  // Fetch document details (including versions, chunks)
  const fetchDocumentDetails = async (docId) => {
    try {
      setKnowledgeError(null);
      const response = await fetch(`http://localhost:8000/api/v1/documents/${docId}`);
      if (!response.ok) throw new Error("Failed to fetch document metadata.");
      const data = await response.json();
      setSelectedDocDetails(data);
    } catch (err) {
      console.error(err);
      setKnowledgeError("Could not retrieve document chunks and metrics.");
    }
  };

  // Refresh database list on mount and workspace transition
  useEffect(() => {
    fetchDocuments();
  }, [workspace]);

  // Poll active processing job progress
  useEffect(() => {
    let intervalId;
    if (activeJobId) {
      console.log("Started polling for job ID:", activeJobId);
      const checkJobProgress = async () => {
        try {
          const response = await fetch(`http://localhost:8000/api/v1/documents/jobs/${activeJobId}`);
          if (!response.ok) throw new Error("Failed to query job progress.");
          const job = await response.json();
          console.log("Polling progress for job ID:", activeJobId, "status:", job.status, "progress:", job.progress);
          setActiveJobStatus(job);

          if (job.status === "completed" || job.status === "failed") {
            console.log("Polling complete for job ID:", activeJobId, "status:", job.status);
            setActiveJobId(null);
            // Refresh list
            fetchDocuments();
            if (selectedDocId) {
              fetchDocumentDetails(selectedDocId);
            }
          }
        } catch (err) {
          console.error("Polling error:", err);
        }
      };
      // Poll every 1.5 seconds
      intervalId = setInterval(checkJobProgress, 1500);
      checkJobProgress(); // Trigger immediately
    }
    return () => {
      if (intervalId) clearInterval(intervalId);
    };
  }, [activeJobId]);

  // Triggers detail fetch on doc select
  useEffect(() => {
    if (selectedDocId) {
      fetchDocumentDetails(selectedDocId);
    } else {
      setSelectedDocDetails(null);
    }
  }, [selectedDocId]);

  // Handle Drag & Drop uploading
  const handleDragOver = (e) => {
    e.preventDefault();
    setDragOver(true);
  };

  const handleDragLeave = () => {
    setDragOver(false);
  };

  const handleDrop = (e) => {
    e.preventDefault();
    setDragOver(false);
    const files = e.dataTransfer.files;
    if (files.length > 0) {
      triggerUpload(files[0]);
    }
  };

  const handleFileChange = (e) => {
    const files = e.target.files;
    if (files.length > 0) {
      triggerUpload(files[0]);
    }
  };

  const triggerUpload = async (file) => {
    console.log("File selected:", file.name);
    setUploadingFile(file.name);
    setKnowledgeError(null);
    setActiveJobStatus(null);

    const formData = new FormData();
    formData.append("file", file);

    console.log("Upload started. Calling fetch() with url: http://localhost:8000/api/v1/documents/upload");
    try {
      const response = await fetch("http://localhost:8000/api/v1/documents/upload", {
        method: "POST",
        body: formData,
      });

      console.log("Fetch returned with status:", response.status);
      if (response.status === 409) {
        throw new Error("Duplicate document detected. This exact file checksum has already been ingested.");
      }
      if (!response.ok) {
        const errorDetail = await response.json();
        throw new Error(errorDetail.detail || `Upload failed: ${response.status}`);
      }

      const resData = await response.json();
      console.log("Received response:", resData);
      console.log("Received job ID:", resData.jobId);
      
      setActiveJobId(resData.jobId);
      setSelectedDocId(resData.documentId);
    } catch (err) {
      console.error("Upload error:", err);
      setKnowledgeError(err.message || "Failed to ingest document file.");
      setUploadingFile(null);
    } finally {
      setUploadingFile(null);
    }
  };

  // Delete Document
  const handleDeleteDocument = async (docId, e) => {
    if (e) e.stopPropagation();
    if (!confirm("Are you sure you want to delete this document? All versions, chunks, and embeddings will be removed.")) {
      return;
    }

    try {
      const response = await fetch(`http://localhost:8000/api/v1/documents/${docId}`, {
        method: "DELETE",
      });
      if (!response.ok) throw new Error("Failed to delete document.");
      
      if (selectedDocId === docId) {
        setSelectedDocId(null);
      }
      fetchDocuments();
    } catch (err) {
      console.error(err);
      setKnowledgeError("Could not delete document from the server.");
    }
  };

  const handleSend = async (e, customText = null) => {
    if (e) e.preventDefault();

    const queryText = customText !== null ? customText.trim() : input.trim();
    if (!queryText || loading) return;

    setInput("");
    setError(null);
    setUserHasScrolledUp(false);

    // Add user message to history
    const userMsgId = Date.now();
    const userMessage = {
      sender: "user",
      text: queryText,
      id: userMsgId,
      timestamp: new Date().toLocaleTimeString([], {
        hour: "2-digit",
        minute: "2-digit",
      }),
      debugInfo: null,
    };

    setMessages((prev) => [...prev, userMessage]);
    setLoading(true);

    setTimeout(() => {
      textareaRef.current?.focus();
    }, 50);

    try {
      const response = await fetch("http://localhost:8000/api/v1/chat", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          query: queryText,
          sessionId: "sess-manual-chat-test-1234",
          similarityThreshold: similarityThreshold,
        }),
      });

      if (!response.ok) {
        throw new Error(`Server error: ${response.status}`);
      }

      const data = await response.json();

      if (data && data.answer) {
        const botMessage = {
          sender: "bot",
          text: data.answer,
          id: Date.now() + 1,
          timestamp: new Date().toLocaleTimeString([], {
            hour: "2-digit",
            minute: "2-digit",
          }),
          debugInfo: {
            intent: data.intent,
            displayIntent: data.displayIntent,
            confidence: data.confidence,
            normalizedQuery: data.normalizedQuery,
            resolvedQuery: data.resolvedQuery,
            matchedKeywords: data.matchedKeywords,
            requestId: data.requestId,
            timestamp: data.timestamp,
            trace: data.trace,
            metadata: data.metadata,
          },
        };

        setMessages((prev) => [...prev, botMessage]);
      } else {
        throw new Error("Invalid response schema from backend.");
      }
    } catch (err) {
      console.error(err);
      setError("Failed to connect to the backend server.");
      setMessages((prev) => [
        ...prev,
        {
          sender: "bot",
          text: "Error: Could not reach the AI platform backend. Please make sure the server is running on port 8000.",
          id: Date.now() + 2,
          timestamp: new Date().toLocaleTimeString([], {
            hour: "2-digit",
            minute: "2-digit",
          }),
          debugInfo: null,
        },
      ]);
    } finally {
      setLoading(false);
      setTimeout(() => {
        textareaRef.current?.focus();
      }, 50);
    }
  };

  const handlePromptClick = (promptText) => {
    handleSend(null, promptText);
  };

  const handleCopyText = (text, id) => {
    navigator.clipboard.writeText(text);
    setCopiedId(id);
    setTimeout(() => setCopiedId(null), 2000);
  };

  const handleRetry = (msgIndex) => {
    for (let i = msgIndex - 1; i >= 0; i--) {
      if (messages[i].sender === "user") {
        handleSend(null, messages[i].text);
        break;
      }
    }
  };

  const clearChat = () => {
    setMessages([]);
    setSelectedMessage(null);
    setError(null);
    setInput("");
    setTimeout(() => {
      textareaRef.current?.focus();
    }, 50);
  };

  const handleKeyDown = (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const toggleTraceNode = (nodeId) => {
    setExpandedTraceId((prev) => ({
      ...prev,
      [nodeId]: !prev[nodeId],
    }));
  };

  const getIntentBadge = (intent, displayIntent) => {
    const rawVal = (displayIntent || intent || "").toUpperCase();
    let label = displayIntent || intent || "Unknown Query";

    if (rawVal.includes("COMPANY_VISION") || rawVal.includes("COMPANY_INFO") || rawVal.includes("VISION")) {
      label = "Company Information";
    } else if (rawVal.includes("CAREERS")) {
      label = "HR & Recruitment";
    } else if (rawVal.includes("SECURITY_POLICY") || rawVal.includes("SECURITY")) {
      label = "Security";
    } else if (rawVal.includes("LEAVE_POLICY") || rawVal.includes("LEAVE")) {
      label = "HR Policies";
    } else if (rawVal.includes("OFFICE_LOCATIONS") || rawVal.includes("LOCATIONS")) {
      label = "Locations";
    } else if (rawVal.includes("PRODUCTS")) {
      label = "Products";
    } else if (rawVal.includes("TECHNOLOGIES") || rawVal.includes("TECHNOLOGY")) {
      label = "Technology";
    } else if (rawVal.includes("UPLOAD_SEARCH") || rawVal.includes("KNOWLEDGE_RETRIEVED")) {
      label = "Knowledge Search";
    } else if (rawVal.includes("FALLBACK")) {
      label = "Unknown Query";
    }

    const colors = {
      "Company Information": "bg-indigo-950/40 text-indigo-300 border-indigo-500/30",
      "HR & Recruitment": "bg-pink-950/40 text-pink-300 border-pink-500/30",
      "Security": "bg-rose-950/40 text-rose-300 border-rose-500/30",
      "HR Policies": "bg-pink-950/40 text-pink-300 border-pink-500/30",
      "Locations": "bg-emerald-950/40 text-emerald-300 border-emerald-500/30",
      "Products": "bg-amber-950/40 text-amber-300 border-amber-500/30",
      "Technology": "bg-purple-950/40 text-purple-300 border-purple-500/30",
      "Knowledge Search": "bg-violet-950/40 text-violet-300 border-violet-500/30",
      "Unknown Query": "bg-slate-800 text-slate-300 border-slate-700",
      "Greeting": "bg-sky-950/40 text-sky-300 border-sky-500/30",
      "Goodbye": "bg-red-950/40 text-red-300 border-red-500/30",
      "Thanks": "bg-green-950/40 text-green-300 border-green-500/30",
      "Small Talk": "bg-fuchsia-950/40 text-fuchsia-300 border-fuchsia-500/30",
    };

    const colorClass =
      colors[label] || "bg-slate-850 text-slate-300 border-slate-700";

    return (
      <span
        className={`text-[10px] px-2.5 py-0.5 rounded-full border font-mono tracking-wider font-bold uppercase transition-all duration-200 ${colorClass}`}
      >
        {label}
      </span>
    );
  };

  const getDocTypeIcon = (type) => {
    const ext = type.toLowerCase();
    if (ext === "pdf") return "📄 (PDF)";
    if (ext === "docx") return "📝 (DOCX)";
    if (ext === "md" || ext === "markdown") return "Ⓜ️ (MD)";
    return "📝 (TXT)";
  };

  return (
    <div className="h-screen w-screen overflow-hidden flex bg-slate-950 text-slate-100 font-sans">
      {/* Persistent Left Sidebar Nav */}
      {(sidebarOpen && (workspace !== "chat" || chatMode === "fullscreen")) ? (
        <div className="w-64 bg-slate-900/90 border-r border-slate-800/80 flex flex-col justify-between flex-shrink-0 h-full backdrop-blur-md z-30 transition-all duration-300">
          <div className="flex-1 flex flex-col">
            {/* Brand header */}
            <div className="p-6 border-b border-slate-850 flex items-center justify-between">
              <div className="flex items-center gap-3">
                <div className="p-1.5 bg-white rounded-lg shadow-md shadow-black/20 flex items-center justify-center">
                  <img src="/logos/mobiloitte-ai-logo.png" alt="Mobiloitte AI Logo" className="w-6 h-6 object-contain" />
                </div>
                <div>
                  <h1 className="text-sm font-bold tracking-tight text-white leading-tight">Mobiloitte AI</h1>
                  <p className="text-[9px] text-slate-500 uppercase tracking-wider font-semibold font-mono">Platform v3.0</p>
                </div>
              </div>
              <button
                onClick={() => setSidebarOpen(false)}
                className="text-slate-500 hover:text-slate-350 cursor-pointer text-xs p-1 hover:bg-slate-850 rounded"
                title="Collapse Sidebar"
              >
                <ChevronLeft size={14} />
              </button>
            </div>

            {/* Menu list */}
            <nav className="p-4 space-y-1.5 flex-1">
              <button
                onClick={() => setWorkspace("chat")}
                className={`w-full flex items-center gap-3 px-3.5 py-2.5 rounded-lg text-xs font-semibold border transition-all duration-150 cursor-pointer text-left ${
                  workspace === "chat"
                    ? "bg-indigo-600/90 border-indigo-500 text-white shadow-lg shadow-indigo-600/20"
                    : "bg-transparent border-transparent text-slate-400 hover:bg-slate-800 hover:text-slate-200"
                }`}
              >
                <MessageSquare size={16} />
                <span>Chat Console</span>
              </button>

              <button
                onClick={() => setWorkspace("knowledge")}
                className={`w-full flex items-center gap-3 px-3.5 py-2.5 rounded-lg text-xs font-semibold border transition-all duration-150 cursor-pointer text-left ${
                  workspace === "knowledge"
                    ? "bg-indigo-600/90 border-indigo-500 text-white shadow-lg shadow-indigo-600/20"
                    : "bg-transparent border-transparent text-slate-400 hover:bg-slate-800 hover:text-slate-200"
                }`}
              >
                <Folder size={16} />
                <span>Document Library</span>
              </button>

              <button
                onClick={() => setWorkspace("settings")}
                className={`w-full flex items-center gap-3 px-3.5 py-2.5 rounded-lg text-xs font-semibold border transition-all duration-150 cursor-pointer text-left ${
                  workspace === "settings"
                    ? "bg-indigo-600/90 border-indigo-500 text-white shadow-lg shadow-indigo-600/20"
                    : "bg-transparent border-transparent text-slate-400 hover:bg-slate-800 hover:text-slate-200"
                }`}
              >
                <Settings size={16} />
                <span>System Settings</span>
              </button>
            </nav>
          </div>

          {/* Footer Info */}
          <div className="p-4 border-t border-slate-850 space-y-3">
            <button
              onClick={() => setDevMode(!devMode)}
              className={`w-full flex items-center justify-between px-3 py-2 rounded-lg text-[10px] font-mono border transition-all duration-150 cursor-pointer uppercase ${
                devMode
                  ? "bg-purple-950/40 border-purple-800 text-purple-300 font-bold"
                  : "bg-slate-950 border-slate-850 text-slate-500 hover:bg-slate-900"
              }`}
            >
              <div className="flex items-center gap-2"><Wrench size={12} /><span>DEV PANEL</span></div>
              <span>{devMode ? "ON" : "OFF"}</span>
            </button>
            <div className="text-[9px] text-slate-600 text-center font-mono uppercase tracking-wider">
              Python RAG • Neon DB
            </div>
          </div>
        </div>
      ) : (workspace !== "chat" || chatMode === "fullscreen") ? (
        <div className="w-16 bg-slate-900/90 border-r border-slate-800/80 flex flex-col justify-between flex-shrink-0 h-full backdrop-blur-md z-30 transition-all duration-300 items-center py-6">
          <div className="flex flex-col items-center gap-8 w-full">
            {/* Brand logo */}
            <button
              onClick={() => setSidebarOpen(true)}
              className="p-1.5 bg-white rounded-lg shadow-md shadow-black/20 cursor-pointer hover:scale-105 transition-transform flex items-center justify-center"
              title="Expand Sidebar"
            >
              <img src="/logos/mobiloitte-ai-logo.png" alt="Mobiloitte AI Logo" className="w-6 h-6 object-contain" />
            </button>

            {/* Menu list icons */}
            <nav className="space-y-4 w-full flex flex-col items-center">
              <button
                onClick={() => setWorkspace("chat")}
                className={`p-2.5 rounded-lg border transition-all duration-150 cursor-pointer text-sm ${
                  workspace === "chat"
                    ? "bg-indigo-600/90 border-indigo-500 text-white shadow-lg"
                    : "bg-transparent border-transparent text-slate-500 hover:bg-slate-800 hover:text-slate-300"
                }`}
                title="Chat Console"
              ><MessageSquare size={20} className="mx-auto" /></button>

              <button
                onClick={() => setWorkspace("knowledge")}
                className={`p-2.5 rounded-lg border transition-all duration-150 cursor-pointer text-sm ${
                  workspace === "knowledge"
                    ? "bg-indigo-600/90 border-indigo-500 text-white shadow-lg"
                    : "bg-transparent border-transparent text-slate-500 hover:bg-slate-800 hover:text-slate-300"
                }`}
                title="Document Library"
              ><Folder size={20} className="mx-auto" /></button>

              <button
                onClick={() => setWorkspace("settings")}
                className={`p-2.5 rounded-lg border transition-all duration-150 cursor-pointer text-sm ${
                  workspace === "settings"
                    ? "bg-indigo-600/90 border-indigo-500 text-white shadow-lg"
                    : "bg-transparent border-transparent text-slate-500 hover:bg-slate-800 hover:text-slate-300"
                }`}
                title="System Settings"
              ><Settings size={20} className="mx-auto" /></button>
            </nav>
          </div>

          {/* Footer Info collapsed */}
          <div className="flex flex-col items-center gap-3 w-full">
            <button
              onClick={() => setDevMode(!devMode)}
              className={`p-2 rounded-lg border transition-all duration-150 cursor-pointer text-xs ${
                devMode
                  ? "bg-purple-950/40 border-purple-800 text-purple-400"
                  : "bg-slate-950 border-slate-850 text-slate-600 hover:bg-slate-900"
              }`}
              title="Toggle Dev Panel"
            ><Wrench size={16} className="mx-auto" /></button>
          </div>
        </div>
      ) : null}

      {/* Main Content Area */}
      <div className="flex-1 flex flex-col h-full overflow-hidden">
        {/* Header */}
        {(workspace !== "chat" || chatMode === "fullscreen") && (
        <header className="bg-slate-900/90 border-b border-slate-800/80 py-3.5 px-6 flex items-center justify-between shadow-lg backdrop-blur-md z-10 flex-shrink-0">
          <div className="flex items-center gap-3">
            <div>
              <h1 className="text-base font-bold tracking-tight text-white flex items-center gap-2">
                {workspace === "chat" ? "Chat Workspace" : workspace === "knowledge" ? "Document Library" : "System Settings"}
                <span className="text-[10px] bg-slate-800 text-slate-400 font-semibold px-2 py-0.5 rounded-md border border-slate-700/50">
                  v3.0
                </span>
              </h1>
              <p className="text-[10px] text-slate-500 font-medium">
                {workspace === "chat"
                  ? "Stateless Conversational Console"
                  : workspace === "knowledge"
                  ? "Ingested Document Metadata & Chunk Divisions"
                  : "Retrieval & Answer Generation Customizations"}
              </p>
            </div>
          </div>

          <div className="flex items-center gap-3">
            {workspace === "chat" && chatMode === "fullscreen" && (
              <button
                onClick={() => setChatMode("widget")}
                aria-label="Exit Fullscreen"
                className="text-xs px-3.5 py-1.5 rounded-full font-semibold border transition-all duration-200 bg-slate-800 border-slate-700 text-slate-300 hover:text-white hover:bg-slate-700 flex items-center gap-2 cursor-pointer shadow-lg"
              >
                <Minimize2 size={14} /> Exit Fullscreen
              </button>
            )}
            <button
              onClick={() => setDevMode(!devMode)}
              aria-label="Toggle Developer Tools"
              className={`text-xs px-3.5 py-1.5 rounded-full font-semibold border transition-all duration-200 flex items-center gap-2 cursor-pointer ${
                devMode
                  ? "bg-indigo-600/90 border-indigo-500 text-white shadow-lg shadow-indigo-600/20"
                  : "bg-slate-880 border-slate-750 text-slate-300 hover:bg-slate-800 hover:text-white"
              }`}
            >
              <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 20l4-16m4 4l4 4-4 4M6 16l-4-4 4-4" />
              </svg>
              Developer Mode
            </button>

            {workspace === "chat" && messages.length > 0 && (
              <button
                onClick={clearChat}
                aria-label="Clear Conversation"
                className="p-1.5 bg-slate-800 hover:bg-slate-700 border border-slate-700 rounded-lg text-slate-400 hover:text-red-400 transition-all duration-200 cursor-pointer"
              >
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                </svg>
              </button>
            )}
          </div>
        </header>
        )}

        {/* Main Container */}
        <div className="flex-1 flex overflow-hidden w-full relative">
        {workspace === "chat" ? (
          <div className="w-full h-full relative flex">
             {chatMode !== "fullscreen" && <LandingPage />}
             {/* Widget container */}
             <div className={`${
                 chatMode === "fullscreen" ? "relative flex-1 h-full w-full flex flex-col overflow-hidden bg-slate-950" : chatMode === "widget" ? "absolute transition-all duration-300 flex flex-col overflow-hidden bg-slate-950 shadow-[0_8px_40px_rgb(0,0,0,0.4)] bottom-6 right-6 w-[400px] h-[650px] rounded-2xl z-50 border border-slate-700/50" : "absolute transition-all duration-300 flex flex-col overflow-hidden bg-blue-600 shadow-[0_8px_30px_rgb(37,99,235,0.4)] bottom-6 right-6 w-16 h-16 rounded-full cursor-pointer hover:scale-105 z-50 border-none"
             }`}>
                {chatMode === "collapsed" ? (
                   <button onClick={() => setChatMode("widget")} className="w-full h-full rounded-full flex items-center justify-center relative overflow-hidden group border-2 border-white/20 bg-white shadow-inner hover:shadow-[0_0_20px_rgba(37,99,235,0.6)] transition-all duration-300">
                      <div className="absolute inset-0 bg-white/20 scale-0 group-hover:scale-100 transition-transform rounded-full"></div>
                      <img src="/logos/mobiloitte-ai-logo.png" className="w-6 h-6 object-contain relative z-10 group-hover:scale-110 transition-transform duration-300 group-hover:drop-shadow-[0_0_8px_rgba(255,255,255,0.8)]" />
                   </button>
                ) : (
                   <>
                     {/* Custom Header for Chat Widget */}
                     {chatMode === "widget" && (
                     <header className="px-4 py-3 bg-blue-600 border-b border-blue-700 flex items-center justify-between shrink-0 shadow-md">
                        <div className="flex items-center gap-3">
                          <div className="w-8 h-8 bg-white rounded-full p-1 flex items-center justify-center shadow-sm">
                             <img src="/logos/mobiloitte-ai-logo.png" className="w-full h-full object-contain" />
                          </div>
                          <div>
                            <h3 className="text-sm font-bold text-white leading-tight">Mobiloitte AI</h3>
                            <div className="text-[10px] text-blue-100 flex items-center gap-1.5 font-medium mt-0.5">
                               <div className="w-1.5 h-1.5 rounded-full bg-green-400 shadow-[0_0_5px_#4ade80]"></div> We're online!
                            </div>
                          </div>
                        </div>
                        <div className="flex items-center gap-1.5">
                           {messages.length > 0 && (
                             <button onClick={clearChat} className="p-1.5 text-blue-100 hover:text-white hover:bg-red-500 rounded transition-colors" title="Start Fresh"><RefreshCw size={16} /></button>
                           )}
                           <button onClick={() => setWorkspace("knowledge")} className="p-1.5 text-blue-100 hover:text-white hover:bg-blue-500 rounded transition-colors" title="Document Library"><Folder size={20} className="mx-auto" /></button>
                           <button onClick={() => setWorkspace("settings")} className="p-1.5 text-blue-100 hover:text-white hover:bg-blue-500 rounded transition-colors" title="System Settings"><Settings size={20} className="mx-auto" /></button>
                           <button onClick={() => setDevMode(!devMode)} className={`p-1.5 rounded transition-colors ${devMode ? "text-white bg-blue-500 shadow-inner" : "text-blue-100 hover:text-white hover:bg-blue-500"}`} title="Toggle Dev Mode"><Wrench size={16} className="mx-auto" /></button>
                           <button onClick={() => setChatMode(chatMode === "fullscreen" ? "widget" : "fullscreen")} className="p-1.5 text-blue-100 hover:text-white hover:bg-blue-500 rounded transition-colors" title={chatMode === "fullscreen" ? "Minimize to Widget" : "Expand to Fullscreen"}>
                              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d={chatMode === "fullscreen" ? "M6 18L18 6M6 6l12 12" : "M4 8V4m0 0h4M4 4l5 5m11-1V4m0 0h-4m4 0l-5 5M4 16v4m0 0h4m-4 0l5-5m11 5l-5-5m5 5v-4m0 4h-4"} /></svg>
                           </button>
                           {chatMode === "widget" && (
                             <button onClick={() => setChatMode("collapsed")} className="p-1.5 text-blue-100 hover:text-white hover:bg-blue-500 rounded transition-colors" title="Close Chat">
                                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" /></svg>
                             </button>
                           )}
                        </div>
                     </header>
                     )}
                     {/* Chat Pane */}
                     <div className="flex-1 flex flex-col h-full overflow-hidden bg-slate-950 relative">
              <div
                ref={messagesContainerRef}
                onScroll={handleScroll}
                className="flex-1 overflow-y-auto px-4 py-8 md:px-8 space-y-6"
              >
                {messages.length === 0 ? (
                  // Empty State Welcome Screen
                  <div className="max-w-2xl mx-auto py-12 md:py-20 flex flex-col items-center justify-center text-center space-y-8">
                    <div className="relative group">
                      <div className="absolute -inset-1.5 rounded-full bg-gradient-to-tr from-indigo-500 to-violet-500 opacity-20 blur-lg group-hover:opacity-40 transition duration-300"></div>
                      <div className="relative p-6 bg-slate-900 border border-slate-800 rounded-full shadow-xl">
                        <svg
                          className="w-12 h-12 text-indigo-400"
                          fill="none"
                          stroke="currentColor"
                          viewBox="0 0 24 24"
                        >
                          <path
                            strokeLinecap="round"
                            strokeLinejoin="round"
                            strokeWidth={1.5}
                            d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z"
                          />
                        </svg>
                      </div>
                    </div>

                    <div className="space-y-3">
                      <h2 className="text-2xl font-extrabold tracking-tight text-white md:text-3xl">
                        How can I assist you today?
                      </h2>
                      <p className="text-sm text-slate-400 max-w-lg mx-auto leading-relaxed">
                        Welcome to the Mobiloitte Conversational Console. This version
                        utilizes our Python-native pipeline with deterministic token expansion
                        and confidence-based query matching.
                      </p>
                    </div>

                    {/* Grid of suggested prompt cards */}
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4 w-full pt-4">
                      {[
                        {
                          title: "Company Overview",
                          subtitle: "Learn what Mobiloitte does",
                          prompt: "Tell me about Mobiloitte",
                          icon: <Building size={20} className="text-indigo-400" />,
                        },
                        {
                          title: "Our Capabilities",
                          subtitle: "Explore AI & Blockchain services",
                          prompt: "What solutions do you provide?",
                          icon: "🤖",
                        },
                        {
                          title: "Office Locations",
                          subtitle: "Find our global branch addresses",
                          prompt: "Where are you located?",
                          icon: "📍",
                        },
                        {
                          title: "Hiring & Careers",
                          subtitle: "See hiring & student programs",
                          prompt: "Are you hiring?",
                          icon: <Briefcase size={20} className="text-indigo-400" />,
                        },
                      ].map((card, idx) => (
                        <button
                          key={idx}
                          onClick={() => handlePromptClick(card.prompt)}
                          className="group p-4 bg-slate-900/60 hover:bg-slate-800/80 border border-slate-900 hover:border-slate-800 rounded-xl text-left transition-all duration-200 cursor-pointer shadow-sm hover:shadow-md"
                        >
                          <div className="flex gap-3">
                            <span className="text-xl">{card.icon}</span>
                            <div>
                              <h3 className="text-sm font-semibold text-slate-200 group-hover:text-white transition-colors">
                                {card.title}
                              </h3>
                              <p className="text-xs text-slate-500 group-hover:text-slate-400 transition-colors mt-0.5">
                                {card.subtitle}
                              </p>
                            </div>
                          </div>
                        </button>
                      ))}
                    </div>
                  </div>
                ) : (
                  // Chat conversation log list
                  <div className="max-w-3xl mx-auto space-y-6">
                    {messages.map((msg, idx) => (
                      <div key={msg.id} className="group relative flex gap-4 w-full">
                        {/* Avatar */}
                        <div className="flex-shrink-0">
                          {msg.sender === "user" ? (
                            <div className="w-8 h-8 rounded-full bg-gradient-to-br from-violet-600 to-indigo-500 flex items-center justify-center text-white text-xs font-bold shadow-md shadow-indigo-500/10 border border-indigo-400/20">
                              U
                            </div>
                          ) : (
                            <div className="w-8 h-8 rounded-full bg-white border border-slate-700/60 flex items-center justify-center text-xs shadow-md overflow-hidden p-1">
                              <img src="/logos/mobiloitte-ai-logo.png" alt="Bot Logo" className="w-full h-full object-contain" />
                            </div>
                          )}
                        </div>

                        {/* Content Container */}
                        <div className="flex-1 space-y-1.5 overflow-hidden">
                          <div className="flex items-center gap-2 flex-wrap">
                            <span className="text-xs font-bold text-slate-300">
                              {msg.sender === "user" ? "You" : "Mobiloitte Assistant"}
                            </span>
                            <span className="text-[10px] text-slate-500">
                              {msg.timestamp}
                            </span>

                            {msg.sender === "bot" &&
                              msg.debugInfo &&
                              getIntentBadge(msg.debugInfo.intent, msg.debugInfo.displayIntent)}
                          </div>

                          <div className="text-sm leading-relaxed text-slate-200 max-w-full overflow-hidden">
                            <ReactMarkdown
                              components={{
                                p: ({node, ...props}) => <p className="mb-4 last:mb-0" {...props} />,
                                strong: ({node, ...props}) => <strong className="font-bold text-white" {...props} />,
                                ul: ({node, ...props}) => <ul className="list-disc list-inside mb-4 space-y-1" {...props} />,
                                ol: ({node, ...props}) => <ol className="list-decimal list-inside mb-4 space-y-1" {...props} />,
                                li: ({node, ...props}) => <li className="pl-1" {...props} />,
                                a: ({node, ...props}) => <a className="text-indigo-400 hover:text-indigo-300 underline" {...props} />,
                                h1: ({node, ...props}) => <h1 className="font-bold text-white text-xl mb-2 mt-4" {...props} />,
                                h2: ({node, ...props}) => <h2 className="font-bold text-white text-lg mb-2 mt-4" {...props} />,
                                h3: ({node, ...props}) => <h3 className="font-bold text-white text-base mb-2 mt-4" {...props} />,
                                h4: ({node, ...props}) => <h4 className="font-bold text-white text-sm mb-2 mt-4" {...props} />,
                                pre: ({node, ...props}) => <pre className="bg-slate-900 p-3 rounded-lg overflow-x-auto mb-4 border border-slate-700/50 text-slate-300 text-sm font-mono [&>code]:bg-transparent [&>code]:text-inherit [&>code]:p-0" {...props} />,
                                code: ({node, className, ...props}) => <code className={`${className || ''} bg-slate-800 text-indigo-300 px-1.5 py-0.5 rounded text-[0.8em] font-mono`} {...props} />,
                                blockquote: ({node, ...props}) => <blockquote className="border-l-4 border-indigo-500 pl-4 italic text-slate-400 mb-4" {...props} />,
                                table: ({node, ...props}) => <div className="overflow-x-auto mb-4"><table className="w-full border-collapse" {...props} /></div>,
                                th: ({node, ...props}) => <th className="border border-slate-700 bg-slate-800 px-3 py-2 text-left font-semibold text-slate-200" {...props} />,
                                td: ({node, ...props}) => <td className="border border-slate-700 px-3 py-2 text-left text-slate-300" {...props} />
                              }}
                            >
                              {msg.text}
                            </ReactMarkdown>
                          </div>

                          {/* Bot Actions Panel on hover */}
                          {msg.sender === "bot" && (
                            <div className="pt-2 flex items-center gap-2.5 opacity-0 group-hover:opacity-100 transition-opacity duration-200">
                              {/* Copy Button */}
                              <button
                                onClick={() => handleCopyText(msg.text, msg.id)}
                                className="flex items-center gap-1.5 text-[10px] text-slate-500 hover:text-slate-300 bg-slate-900 hover:bg-slate-800 px-2.5 py-1 rounded-md border border-slate-800 cursor-pointer transition-all"
                                title="Copy message to clipboard"
                              >
                                {copiedId === msg.id ? (
                                  <>
                                    <svg
                                      className="w-3 h-3 text-green-400 animate-pulse"
                                      fill="none"
                                      stroke="currentColor"
                                      viewBox="0 0 24 24"
                                    >
                                      <path
                                        strokeLinecap="round"
                                        strokeLinejoin="round"
                                        strokeWidth={2.5}
                                        d="M5 13l4 4L19 7"
                                      />
                                    </svg>
                                    <span className="text-green-400 font-bold">Copied!</span>
                                  </>
                                ) : (
                                  <>
                                    <svg
                                      className="w-3 h-3"
                                      fill="none"
                                      stroke="currentColor"
                                      viewBox="0 0 24 24"
                                    >
                                      <path
                                        strokeLinecap="round"
                                        strokeLinejoin="round"
                                        strokeWidth={2}
                                        d="M8 5H6a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2v-1M8 5a2 2 0 002 2h2a2 2 0 002-2M8 5a2 2 0 012-2h2a2 2 0 012 2m0 0h2a2 2 0 012 2v3m2 4H10m0 0l3-3m-3 3l3 3"
                                      />
                                    </svg>
                                    <span>Copy</span>
                                  </>
                                )}
                              </button>

                              {/* Retry Button */}
                              {idx > 0 && (
                                <button
                                  onClick={() => handleRetry(idx)}
                                  className="flex items-center gap-1.5 text-[10px] text-slate-500 hover:text-slate-300 bg-slate-900 hover:bg-slate-800 px-2.5 py-1 rounded-md border border-slate-800 cursor-pointer transition-all"
                                  title="Regenerate this request"
                                >
                                  <svg
                                    className="w-3 h-3"
                                    fill="none"
                                    stroke="currentColor"
                                    viewBox="0 0 24 24"
                                  >
                                    <path
                                      strokeLinecap="round"
                                      strokeLinejoin="round"
                                      strokeWidth={2}
                                      d="M4 4v5h.582m15.356 2A8.001 8.001 0 1121.21 3.89M9 11l3-3m0 0l3 3m-3-3v8"
                                    />
                                  </svg>
                                  Retry
                                </button>
                              )}

                              {/* Inspect details in Developer Panel */}
                              {devMode && msg.debugInfo && (
                                <button
                                  onClick={() => setSelectedMessage(msg)}
                                  className={`flex items-center gap-1.5 text-[10px] px-2.5 py-1 rounded-md border cursor-pointer transition-all ${
                                    selectedMessage?.id === msg.id
                                      ? "bg-indigo-950/60 text-indigo-300 border-indigo-700/50 font-bold"
                                      : "bg-slate-900 border-slate-800 text-slate-500 hover:text-indigo-400 hover:border-indigo-800/40"
                                  }`}
                                >
                                  <svg
                                    className="w-3 h-3"
                                    fill="none"
                                    stroke="currentColor"
                                    viewBox="0 0 24 24"
                                  >
                                    <path
                                      strokeLinecap="round"
                                      strokeLinejoin="round"
                                      strokeWidth={2}
                                      d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"
                                    />
                                    <path
                                      strokeLinecap="round"
                                      strokeLinejoin="round"
                                      strokeWidth={2}
                                      d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z"
                                    />
                                  </svg>
                                  Inspect Trace
                                </button>
                              )}
                            </div>
                          )}
                        </div>
                      </div>
                    ))}
                  </div>
                )}

                {loading && (
                  <div className="max-w-3xl mx-auto flex gap-4 w-full">
                    <div className="w-8 h-8 rounded-full bg-gradient-to-br from-slate-800 to-slate-900 border border-slate-700/60 flex items-center justify-center">
                      <svg
                        className="w-4 h-4 text-indigo-400 animate-spin"
                        fill="none"
                        stroke="currentColor"
                        viewBox="0 0 24 24"
                      >
                        <path
                          strokeLinecap="round"
                          strokeLinejoin="round"
                          strokeWidth={2}
                          d="M4 4v5h.582m15.356 2A8.001 8.001 0 1121.21 3.89M9 11l3-3m0 0l3 3m-3-3v8"
                        />
                      </svg>
                    </div>
                    <div className="flex-1 space-y-2">
                      <span className="text-[10px] text-slate-500 font-bold">
                        Mobiloitte is thinking...
                      </span>
                      <div className="bg-slate-900/65 text-slate-400 border border-slate-800/80 rounded-lg px-4.5 py-3 shadow-inner flex items-center gap-2.5 w-16">
                        <span
                          className="w-1.5 h-1.5 bg-indigo-400 rounded-full animate-bounce"
                          style={{ animationDelay: "0ms" }}
                        />
                        <span
                          className="w-1.5 h-1.5 bg-indigo-400 rounded-full animate-bounce"
                          style={{ animationDelay: "150ms" }}
                        />
                        <span
                          className="w-1.5 h-1.5 bg-indigo-400 rounded-full animate-bounce"
                          style={{ animationDelay: "300ms" }}
                        />
                      </div>
                    </div>
                  </div>
                )}

                {error && (
                  <div className="bg-red-950/20 border border-red-500/25 text-red-300 text-xs px-4 py-3 rounded-lg text-center max-w-md mx-auto shadow-lg shadow-red-950/10">
                    ⚠️ {error}
                  </div>
                )}
              </div>

              {/* Sticky Input Footer */}
              <footer className="bg-slate-900/80 border-t border-slate-800/50 py-4 px-6 flex-shrink-0 z-10 backdrop-blur-md">
                <div className="max-w-3xl mx-auto relative">
                  {(uploadingFile || (activeJobStatus && activeJobStatus.status !== "completed" && activeJobStatus.status !== "failed")) && (
                    <div className="mb-3 px-3 py-2 bg-indigo-950/40 border border-indigo-500/30 rounded-lg flex items-center gap-3 text-xs w-full">
                      <RefreshCw size={14} className="animate-spin text-indigo-400" />
                      <div className="flex-1">
                        <div className="text-slate-300 font-medium flex justify-between">
                          <span>{uploadingFile ? `Uploading ${uploadingFile}...` : 'Processing document...'}</span>
                          {activeJobStatus && activeJobStatus.status !== "completed" && activeJobStatus.status !== "failed" && (
                            <span className="text-indigo-300">{activeJobStatus.progress}%</span>
                          )}
                        </div>
                        {activeJobStatus && activeJobStatus.status !== "completed" && activeJobStatus.status !== "failed" && (
                          <div className="w-full bg-slate-800 h-1.5 rounded-full mt-1.5 overflow-hidden">
                            <div className="bg-indigo-500 h-full transition-all duration-300" style={{ width: `${activeJobStatus.progress}%` }}></div>
                          </div>
                        )}
                      </div>
                    </div>
                  )}
                  <div className="flex items-end gap-3.5 bg-slate-950 border border-slate-800 rounded-xl p-2 focus-within:border-indigo-500/50 focus-within:ring-1 focus-within:ring-indigo-500/40 transition-all duration-200">
                    <input
                      ref={fileInputRef}
                      type="file"
                      accept=".pdf,.docx,.txt,.md,.markdown"
                      onChange={handleFileChange}
                      className="hidden"
                    />
                    <button
                      onClick={() => fileInputRef.current?.click()}
                      className="p-2 text-slate-400 hover:text-indigo-400 transition-colors flex-shrink-0"
                      title="Upload Document"
                    >
                      <Paperclip size={20} />
                    </button>
                    <textarea
                      ref={textareaRef}
                    rows={1}
                    value={input}
                    onChange={(e) => setInput(e.target.value)}
                    onKeyDown={handleKeyDown}
                    disabled={loading}
                    placeholder="Message Mobiloitte..."
                    style={{ resize: "none" }}
                    className="flex-1 bg-transparent border-0 outline-none text-slate-100 placeholder-slate-500 text-sm px-3 py-2 disabled:opacity-50 min-h-[38px] max-h-[180px] overflow-y-auto leading-relaxed"
                  />
                  <button
                    onClick={() => handleSend()}
                    disabled={loading || !input.trim()}
                    aria-label="Send query"
                    className="bg-indigo-600 hover:bg-indigo-500 text-white font-bold p-2.5 rounded-lg transition-all duration-150 disabled:opacity-30 disabled:hover:bg-indigo-600 cursor-pointer shadow-md shadow-indigo-600/10 flex-shrink-0"
                  >
                    <svg
                      className="w-4 h-4"
                      fill="none"
                      stroke="currentColor"
                      viewBox="0 0 24 24"
                    >
                      <path
                        strokeLinecap="round"
                        strokeLinejoin="round"
                        strokeWidth={2.5}
                        d="M12 19V5m0 0l-7 7m7-7l7 7"
                      />
                    </svg>
                  </button>
                  </div>
                  <p className="text-[10px] text-center text-slate-600 mt-2">
                    Press Enter to send. Shift+Enter for new line.
                  </p>
                </div>
              </footer>
            </div>
            </>
           )}
          </div>
         </div>
        ) : workspace === "knowledge" ? (
          // Knowledge Base Workspace View
          <div className="flex-1 flex h-full overflow-hidden w-full bg-slate-950 text-slate-100">
            {/* Left Sidebar Pane: File list & upload drag/drop */}
            <div className="w-[380px] h-full border-r border-slate-800/80 bg-slate-900/10 flex flex-col flex-shrink-0 overflow-hidden">
              {/* Drag & Drop File Upload Area */}
              <div className="p-5 flex-shrink-0">
                <div
                  onDragOver={handleDragOver}
                  onDragLeave={handleDragLeave}
                  onDrop={handleDrop}
                  onClick={() => fileInputRef.current?.click()}
                  className={`border-2 border-dashed rounded-xl p-6 text-center cursor-pointer transition-all duration-200 flex flex-col items-center justify-center gap-3 ${
                    dragOver
                      ? "border-indigo-500 bg-indigo-950/20"
                      : "border-slate-880 bg-slate-900/30 hover:border-slate-700 hover:bg-slate-900/20"
                  }`}
                >
                  <input
                    ref={fileInputRef}
                    type="file"
                    accept=".pdf,.docx,.txt,.md,.markdown"
                    onChange={handleFileChange}
                    className="hidden"
                  />
                  <div className="p-3 bg-slate-800/50 rounded-lg text-slate-450">
                    📂
                  </div>
                  <div>
                    <p className="text-xs font-semibold text-slate-200">
                      Drag & Drop document here
                    </p>
                    <p className="text-[10px] text-slate-500 mt-1">
                      PDF, DOCX, TXT, MD up to 10MB
                    </p>
                  </div>
                </div>

                {uploadingFile && (
                  <div className="mt-3 p-3 bg-slate-900/50 border border-slate-800 rounded-lg flex items-center gap-3 text-xs">
                    <span className="animate-spin">🔄</span>
                    <span className="text-slate-300 truncate flex-1">
                      Uploading {uploadingFile}...
                    </span>
                  </div>
                )}

                {activeJobStatus && activeJobStatus.status !== "completed" && activeJobStatus.status !== "failed" && (
                  <div className="mt-3 p-3 bg-indigo-950/20 border border-indigo-900/30 rounded-lg space-y-2 text-xs">
                    <div className="flex justify-between items-center text-[10px] font-mono text-indigo-300">
                      <span className="uppercase tracking-wider">Indexing Job</span>
                      <span className="font-bold">{activeJobStatus.progress}%</span>
                    </div>
                    <div className="w-full bg-slate-800 h-1.5 rounded-full overflow-hidden">
                      <div
                        className="bg-indigo-500 h-full rounded-full transition-all duration-300"
                        style={{ width: `${activeJobStatus.progress}%` }}
                      />
                    </div>
                    <p className="text-[10px] text-slate-400 uppercase tracking-tight">
                      Current stage: <strong className="text-indigo-200">{activeJobStatus.status}</strong>
                    </p>
                  </div>
                )}

                {knowledgeError && (
                  <div className="mt-3 p-3 bg-red-950/20 border border-red-500/30 text-red-300 text-xs rounded-lg shadow-sm">
                    ⚠️ {knowledgeError}
                  </div>
                )}
              </div>

              {/* Header List */}
              <div className="px-5 py-2 border-b border-slate-850 flex items-center justify-between text-xs text-slate-500 font-mono">
                <span>INGESTED DOCUMENTS ({documents.length})</span>
                <button
                  onClick={fetchDocuments}
                  className="hover:text-slate-300 text-[10px] font-bold cursor-pointer"
                >
                  REFRESH 🔄
                </button>
              </div>

              {/* Scrollable Document List */}
              <div className="flex-1 overflow-y-auto p-4 space-y-2.5">
                {documents.length === 0 ? (
                  <div className="text-center py-10 text-slate-600 text-xs italic">
                    No documents ingested yet.
                  </div>
                ) : (
                  documents.map((doc) => {
                    const isSelected = selectedDocId === doc.id;
                    return (
                      <div
                        key={doc.id}
                        onClick={() => setSelectedDocId(doc.id)}
                        className={`group p-3.5 rounded-xl border transition-all duration-200 cursor-pointer flex items-center justify-between shadow-sm ${
                          isSelected
                            ? "bg-slate-900 border-indigo-500/50 shadow-indigo-950/10"
                            : "bg-slate-900/50 border-slate-850 hover:bg-slate-900/80 hover:border-slate-800"
                        }`}
                      >
                        <div className="space-y-1 overflow-hidden pr-2">
                          <p className="text-xs font-semibold text-slate-200 truncate">
                            {doc.filename}
                          </p>
                          <div className="flex items-center gap-2 text-[10px] text-slate-500">
                            <span>{getDocTypeIcon(doc.file_type)}</span>
                            <span>•</span>
                            <span>v{doc.latest_version}</span>
                            <span>•</span>
                            <span>{(doc.file_size / 1024).toFixed(1)} KB</span>
                          </div>
                        </div>

                        <div className="flex items-center gap-2">
                          {doc.status === "processing" ? (
                            <span className="w-2.5 h-2.5 bg-yellow-500 rounded-full animate-pulse" title="Processing Ingestion" />
                          ) : doc.status === "ready_for_search" ? (
                            <span className="w-2.5 h-2.5 bg-green-500 rounded-full" title="Indexed & Ready" />
                          ) : (
                            <span className="w-2.5 h-2.5 bg-red-500 rounded-full" title="Ingestion Failed" />
                          )}

                          <button
                            onClick={(e) => handleDeleteDocument(doc.id, e)}
                            className="p-1 hover:bg-slate-800 rounded text-slate-500 hover:text-red-400 opacity-0 group-hover:opacity-100 transition-opacity"
                            title="Delete document"
                          >
                            ❌
                          </button>
                        </div>
                      </div>
                    );
                  })
                )}
              </div>
            </div>

            {/* Right Pane: Document details & chunks list */}
            <div className="flex-1 h-full overflow-y-auto bg-slate-950 p-6 space-y-6">
              {selectedDocDetails ? (
                <div className="max-w-4xl mx-auto space-y-6">
                  {/* Title Header Card */}
                  <div className="bg-slate-900/40 border border-slate-850 p-5 rounded-xl flex justify-between items-start flex-wrap gap-4 shadow-sm">
                    <div className="space-y-1">
                      <span className="text-[10px] font-mono text-slate-500 uppercase tracking-widest">
                        Document Inspector
                      </span>
                      <h2 className="text-lg font-bold text-white tracking-tight">
                        {selectedDocDetails.filename}
                      </h2>
                      <p className="text-[10px] text-slate-500 font-mono">
                        UUID: {selectedDocDetails.id}
                      </p>
                    </div>

                    <div className="flex gap-2">
                      <span className="bg-slate-800 text-slate-300 font-mono text-[10px] font-bold px-3 py-1 rounded border border-slate-700/50 uppercase">
                        {selectedDocDetails.file_type}
                      </span>
                      {selectedDocDetails.versions[0]?.status === "ready_for_search" ? (
                        <span className="bg-green-950/40 text-green-300 border border-green-500/30 font-mono text-[10px] font-bold px-3 py-1 rounded">
                          READY_FOR_SEARCH
                        </span>
                      ) : selectedDocDetails.versions[0]?.status === "processing" ? (
                        <span className="bg-yellow-950/40 text-yellow-300 border border-yellow-500/30 font-mono text-[10px] font-bold px-3 py-1 rounded animate-pulse">
                          PROCESSING
                        </span>
                      ) : (
                        <span className="bg-red-950/40 text-red-300 border border-red-500/30 font-mono text-[10px] font-bold px-3 py-1 rounded">
                          FAILED
                        </span>
                      )}
                    </div>
                  </div>

                  {/* Dev Mode Real-time Ingestion Stage Progress Line */}
                  {devMode && selectedDocDetails.versions[0] && (
                    <div className="bg-slate-900/30 border border-slate-850 p-5 rounded-xl space-y-5 shadow-sm">
                      <div className="text-[10px] font-mono text-slate-500 border-b border-slate-800 pb-2 uppercase tracking-wider">
                        Developer Mode — Ingestion Timeline & Telemetry
                      </div>

                      {/* Horizontal timeline steps visualizer */}
                      <div className="grid grid-cols-5 gap-3 pt-2">
                        {[
                          {
                            name: "Upload",
                            desc: "Checksum & saving",
                            time: `${selectedDocDetails.versions[0].upload_time_ms}ms`,
                            done: true,
                          },
                          {
                            name: "Extraction",
                            desc: "Text parsed per page",
                            time: `${selectedDocDetails.versions[0].extraction_time_ms}ms`,
                            done: selectedDocDetails.versions[0].extraction_time_ms > 0,
                          },
                          {
                            name: "Cleaning",
                            desc: "Hyphenation & headers",
                            time: `${selectedDocDetails.versions[0].cleaning_time_ms}ms`,
                            done: selectedDocDetails.versions[0].cleaning_time_ms > 0,
                          },
                          {
                            name: "Chunking",
                            desc: "Semantic parsing",
                            time: `${selectedDocDetails.versions[0].chunking_time_ms}ms`,
                            done: selectedDocDetails.versions[0].chunking_time_ms > 0,
                          },
                          {
                            name: "Embedding",
                            desc: "MiniLM-L6 vectors",
                            time: `${selectedDocDetails.versions[0].embedding_time_ms}ms`,
                            done: selectedDocDetails.versions[0].embedding_time_ms > 0,
                          },
                        ].map((step, idx) => (
                          <div key={idx} className="relative bg-slate-950/50 border border-slate-850 p-3 rounded-lg flex flex-col justify-between min-h-[90px]">
                            <div className="flex items-center justify-between">
                              <span className="text-[10px] font-bold text-slate-200">
                                {step.name}
                              </span>
                              <span className={step.done ? "text-green-400 text-xs" : "text-slate-600 text-xs"}>
                                {step.done ? "✔" : "⏳"}
                              </span>
                            </div>
                            <p className="text-[9px] text-slate-500 leading-tight my-1">
                              {step.desc}
                            </p>
                            <span className="text-[10px] font-mono text-indigo-400 font-bold self-end">
                              {step.time}
                            </span>
                          </div>
                        ))}
                      </div>

                      {/* Extended db storage telemetry */}
                      <div className="grid grid-cols-3 gap-4 text-xs font-mono bg-slate-950/60 p-4 rounded-xl border border-slate-850">
                        <div>
                          <span className="text-[10px] text-slate-500 block">DB Operations</span>
                          <span className="text-slate-300 font-semibold">{selectedDocDetails.versions[0].database_time_ms}ms</span>
                        </div>
                        <div>
                          <span className="text-[10px] text-slate-500 block">Total Processing</span>
                          <span className="text-slate-300 font-semibold">{selectedDocDetails.versions[0].processing_time_ms}ms</span>
                        </div>
                        <div>
                          <span className="text-[10px] text-slate-500 block">Embedding Dimensions</span>
                          <span className="text-teal-400 font-bold">384 Dimensions</span>
                        </div>
                      </div>
                    </div>
                  )}

                  {/* Document Versions & Version details cards */}
                  <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                    <div className="bg-slate-900/20 border border-slate-850 p-4 rounded-xl space-y-1">
                      <span className="text-[10px] text-slate-500 block font-mono">FILE CHECKSUM (SHA-256)</span>
                      <span className="text-xs text-slate-300 font-semibold font-mono truncate block" title={selectedDocDetails.versions[0]?.checksum}>
                        {selectedDocDetails.versions[0]?.checksum || "N/A"}
                      </span>
                    </div>

                    <div className="bg-slate-900/20 border border-slate-850 p-4 rounded-xl space-y-1">
                      <span className="text-[10px] text-slate-500 block font-mono">TOTAL CHUNKS COUNT</span>
                      <span className="text-xs text-slate-300 font-bold font-mono">
                        {selectedDocDetails.versions[0]?.chunk_count || 0} Chunks
                      </span>
                    </div>

                    <div className="bg-slate-900/20 border border-slate-850 p-4 rounded-xl space-y-1">
                      <span className="text-[10px] text-slate-500 block font-mono">MODEL / DIMENSIONS</span>
                      <span className="text-xs text-indigo-300 font-bold font-mono truncate block" title={selectedDocDetails.versions[0]?.embedding_model}>
                        MiniLM-L6 (384d)
                      </span>
                    </div>
                  </div>

                  {/* Document Chunks Inspector list */}
                  <div className="space-y-4">
                    <div className="text-xs text-slate-400 font-mono uppercase tracking-wider">
                      Semantic Chunk Inspector ({selectedDocDetails.versions[0]?.chunks.length} total segments)
                    </div>

                    <div className="space-y-3.5">
                      {selectedDocDetails.versions[0]?.chunks.length === 0 ? (
                        <div className="text-center py-10 text-slate-600 text-xs italic">
                          No chunks extracted yet.
                        </div>
                      ) : (
                        selectedDocDetails.versions[0].chunks.map((chunk, cIdx) => (
                          <div key={chunk.id} className="bg-slate-900/40 border border-slate-850 rounded-xl p-4.5 space-y-3 shadow-inner hover:border-slate-800 transition-colors">
                            {/* Metadata */}
                            <div className="flex justify-between items-center text-[10px] font-mono text-slate-500 border-b border-slate-850/80 pb-2 flex-wrap gap-2">
                              <div className="flex items-center gap-3">
                                <span className="text-indigo-400 font-bold">CHUNK #{chunk.chunk_index + 1}</span>
                                <span>•</span>
                                <span>Page {chunk.page_number}</span>
                                <span>•</span>
                                <span>Para {chunk.paragraph_number}</span>
                              </div>
                              <div className="flex items-center gap-3">
                                <span>Tokens: <strong className="text-slate-300">{chunk.token_count}</strong></span>
                                <span>•</span>
                                <span>Range: {chunk.char_range_start}-{chunk.char_range_end}</span>
                              </div>
                            </div>

                            {/* Section Headings */}
                            {(chunk.heading || chunk.section) && (
                              <div className="flex items-center gap-2 text-[10px] text-slate-400 font-medium">
                                <span className="bg-slate-800 px-2 py-0.5 rounded border border-slate-700/50">
                                  H: {chunk.heading || "No Heading"}
                                </span>
                                {chunk.section && chunk.section !== chunk.heading && (
                                  <span className="bg-slate-800 px-2 py-0.5 rounded border border-slate-700/50">
                                    S: {chunk.section}
                                  </span>
                                )}
                              </div>
                            )}

                            {/* Text content block */}
                            <p className="text-sm leading-relaxed text-slate-300 font-sans whitespace-pre-wrap">
                              {chunk.text}
                            </p>

                            {/* Bottom ID line */}
                            <div className="text-[8px] text-slate-600 font-mono text-right truncate">
                              HASH: {chunk.hash} | ID: {chunk.id}
                            </div>
                          </div>
                        ))
                      )}
                    </div>
                  </div>
                </div>
              ) : (
                <div className="h-full flex flex-col items-center justify-center text-center text-slate-500 text-xs py-40 max-w-md mx-auto">
                  <div className="p-4 bg-slate-900/50 rounded-full border border-slate-800 mb-4 text-2xl animate-pulse">
                    📁
                  </div>
                  <h3 className="font-bold text-slate-300 text-sm">No Document Selected</h3>
                  <p className="text-slate-500 mt-1 leading-relaxed">
                    Select an ingested document from the sidebar to inspect its versions, metadata, and chunk text divisions.
                  </p>
                </div>
              )}
            </div>
          </div>
        ) : (
          // System Settings Workspace View
          <div className="flex-1 h-full overflow-y-auto bg-slate-950 p-6 space-y-6">
            <div className="max-w-3xl mx-auto space-y-6">
              {/* Header card */}
              <div className="bg-slate-900/40 border border-slate-850 p-6 rounded-xl space-y-2 shadow-sm">
                <span className="text-[10px] font-mono text-slate-500 uppercase tracking-widest">
                  System Settings
                </span>
                <h2 className="text-xl font-bold text-white tracking-tight">
                  Mobiloitte AI Platform Configurations
                </h2>
                <p className="text-xs text-slate-400 leading-relaxed">
                  Customize the behavior of the conversational and retrieval engines of your platform.
                </p>
              </div>

              {/* RAG Settings Card */}
              <div className="bg-slate-900/20 border border-slate-850 p-6 rounded-xl space-y-4 shadow-sm">
                <div className="text-xs font-mono text-slate-300 uppercase tracking-wider border-b border-slate-850 pb-2">
                  Retrieval-Augmented Generation (RAG) Config
                </div>
                <div className="space-y-4">
                  <div className="flex justify-between items-center">
                    <div>
                      <label className="text-xs font-semibold text-slate-200">
                        RAG Similarity Threshold
                      </label>
                      <p className="text-[10px] text-slate-500 mt-0.5">
                        Minimum cosine similarity score required to retrieve document chunks.
                      </p>
                    </div>
                    <span className="text-sm font-bold font-mono text-teal-400 bg-slate-900/80 px-2.5 py-1.5 rounded border border-slate-800">
                      {similarityThreshold.toFixed(2)}
                    </span>
                  </div>
                  <input
                    type="range"
                    min="0.0"
                    max="1.0"
                    step="0.01"
                    value={similarityThreshold}
                    onChange={(e) => setSimilarityThreshold(parseFloat(e.target.value))}
                    className="w-full h-1.5 bg-slate-800 rounded-lg appearance-none cursor-pointer accent-indigo-500"
                  />
                  <div className="flex justify-between text-[9px] font-mono text-slate-600">
                    <span>0.00 (Retrieve everything)</span>
                    <span>0.42 (Recommended Default)</span>
                    <span>1.00 (Strict exact match)</span>
                  </div>
                </div>
              </div>

              {/* Diagnostics Card */}
              <div className="bg-slate-900/20 border border-slate-850 p-6 rounded-xl space-y-4 shadow-sm">
                <div className="text-xs font-mono text-slate-300 uppercase tracking-wider border-b border-slate-850 pb-2">
                  System Diagnostics & Status
                </div>
                <div className="grid grid-cols-2 gap-4 text-xs font-mono">
                  <div className="bg-slate-950/40 p-3 rounded-lg border border-slate-850 flex items-center justify-between">
                    <span className="text-slate-500 text-[10px]">Database Engine</span>
                    <span className="text-green-400 font-bold">READY (Neon PG)</span>
                  </div>
                  <div className="bg-slate-950/40 p-3 rounded-lg border border-slate-850 flex items-center justify-between">
                    <span className="text-slate-500 text-[10px]">pgvector Indexing</span>
                    <span className="text-green-400 font-bold">ACTIVE (IVFFLAT)</span>
                  </div>
                  <div className="bg-slate-950/40 p-3 rounded-lg border border-slate-850 flex items-center justify-between">
                    <span className="text-slate-500 text-[10px]">Embedding Model</span>
                    <span className="text-indigo-400 font-bold">all-MiniLM-L6-v2</span>
                  </div>
                  <div className="bg-slate-950/40 p-3 rounded-lg border border-slate-850 flex items-center justify-between">
                    <span className="text-slate-500 text-[10px]">Vector Dimensions</span>
                    <span className="text-teal-400 font-bold">384 Coordinates</span>
                  </div>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Unified Developer Side Panel */}
        {devMode && (
          <div className="w-full md:w-[420px] h-full overflow-y-auto border-l border-slate-850 bg-slate-900/40 flex-shrink-0 flex flex-col p-5 space-y-6 z-20 backdrop-blur-lg relative shadow-2xl">
            {/* Dev Panel Header */}
            <div className="flex items-center justify-between border-b border-slate-800 pb-4 flex-shrink-0">
              <div className="flex items-center gap-2">
                <div className="p-1 bg-purple-950/60 text-purple-300 rounded border border-purple-800/40">
                  <svg
                    className="w-4 h-4"
                    fill="none"
                    stroke="currentColor"
                    viewBox="0 0 24 24"
                  >
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      strokeWidth={2}
                      d="M9 3v2m6-2v2M9 19v2m6-2v2M5 9H3m2 6H3m18-6h-2m2 6h-2M7 19h10a2 2 0 002-2V7a2 2 0 00-2-2H7a2 2 0 00-2 2v10a2 2 0 002 2zM9 9h6v6H9V9z"
                    />
                  </svg>
                </div>
                <div>
                  <h2 className="text-xs font-bold uppercase tracking-wider text-slate-200">
                    Engine Inspector
                  </h2>
                  <p className="text-[10px] text-slate-500">
                    Detailed telemetry and pipeline state
                  </p>
                </div>
              </div>

              <button
                onClick={() => setDevMode(false)}
                className="text-slate-500 hover:text-slate-300 p-1 hover:bg-slate-800 rounded-md transition-colors"
                title="Hide Inspector"
              >
                <svg
                  className="w-4 h-4"
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M6 18L18 6M6 6l12 12"
                  />
                </svg>
              </button>
            </div>

            {selectedMessage ? (
              <div className="space-y-6 animate-fadeIn">
                {/* Fallback explanation if final intent is FALLBACK / UNKNOWN */}
                {(selectedMessage.debugInfo.intent === "FALLBACK" || selectedMessage.debugInfo.intent === "UNKNOWN" || selectedMessage.debugInfo.intent === "UNKNOWN_QUERY") && (
                  <div className="bg-red-950/20 border border-red-500/30 p-4.5 rounded-xl space-y-2 shadow-sm animate-fadeIn text-xs">
                    <div className="flex items-center gap-2 text-red-400 font-bold font-mono">
                      <span>⚠️ PIPELINE FALLBACK TRIGGERED</span>
                    </div>
                    <p className="text-slate-300 text-[11px] leading-relaxed mt-1">
                      {(() => {
                        const ragTrace = selectedMessage.debugInfo.trace?.find(t => t.engine === "RAGRetrieval" || t.engine === "KnowledgeRetrieval");
                        if (ragTrace && ragTrace.reasonCode === "RAG_NO_RELEVANT_CHUNKS") {
                          const highest = ragTrace.metadata?.highest_similarity !== undefined 
                            ? (ragTrace.metadata.highest_similarity * 100).toFixed(0) + "%" 
                            : "N/A";
                          const thresh = ragTrace.metadata?.threshold !== undefined 
                            ? (ragTrace.metadata.threshold * 100).toFixed(0) + "%" 
                            : "N/A";
                          return `No retrieved document chunks exceeded the cosine similarity threshold (Highest similarity: ${highest}, Threshold: ${thresh}).`;
                        }
                        if (ragTrace && ragTrace.reasonCode === "RAG_SKIPPED_DB_UNAVAILABLE") {
                          return "The pgvector database was not connected or unavailable at execution time.";
                        }
                        return "No category intents matched via FastPath and no document segments exceeded the semantic search threshold.";
                      })()}
                    </p>
                  </div>
                )}

                {/* Intent & Confidence Card */}
                <div className="bg-slate-950/60 border border-slate-850 p-4.5 rounded-xl space-y-4 shadow-sm">
                  <div className="flex items-center justify-between text-[10px] text-slate-500 border-b border-slate-800 pb-2 mb-2 font-mono">
                    <span>EXECUTION OVERVIEW</span>
                    <span>ID: {selectedMessage.debugInfo.requestId}</span>
                  </div>

                  <div className="grid grid-cols-2 gap-4">
                    <div className="space-y-1">
                      <span className="text-[10px] text-slate-500 block">
                        Detected Intent
                      </span>
                      <span className="bg-slate-900 border border-slate-800 text-[10px] px-2 py-0.5 rounded font-mono text-slate-400 mt-1 block">
                        {selectedMessage.debugInfo.intent}
                      </span>
                    </div>

                    <div className="space-y-1">
                      <span className="text-[10px] text-slate-500 block">
                        Display Intent
                      </span>
                      {getIntentBadge(selectedMessage.debugInfo.intent, selectedMessage.debugInfo.displayIntent)}
                    </div>

                    <div className="space-y-1 col-span-2">
                      <span className="text-[10px] text-slate-500 block">
                        Confidence
                      </span>
                      <span className="text-lg font-bold text-teal-400 tracking-tight font-mono">
                        {(selectedMessage.debugInfo.confidence * 100).toFixed(0)}
                        %
                      </span>
                    </div>
                  </div>
                </div>

                {/* Decision Engine Routing Inspector */}
                {(() => {
                  const decisionTrace = selectedMessage.debugInfo.trace?.find(t => t.engine === "QueryDecision");
                  const decisionMeta = decisionTrace?.metadata || {};
                  return (
                    <div className="bg-slate-950/60 border border-slate-850 p-4.5 rounded-xl space-y-4 shadow-sm animate-fadeIn">
                      <div className="flex items-center justify-between text-[10px] text-slate-500 border-b border-slate-800 pb-2 font-mono uppercase tracking-wider">
                        <span>Decision Routing Inspector</span>
                        <span className="text-indigo-400 font-bold">QueryDecisionEngine</span>
                      </div>
                      
                      <div className="space-y-2 text-xs">
                        <div className="flex justify-between items-center bg-slate-900/60 border border-slate-850 px-2.5 py-2 rounded-lg">
                          <span className="text-slate-500 text-[10px]">Decision Action</span>
                          <span className="bg-indigo-950/40 text-indigo-300 border border-indigo-900/30 px-2 py-0.5 rounded text-[10px] font-mono font-bold">
                            {decisionMeta.decision || "N/A"}
                          </span>
                        </div>

                        {decisionMeta.why_chosen && (
                          <div className="bg-slate-900/40 p-2.5 rounded-lg border border-slate-850/60">
                            <span className="text-slate-500 text-[9px] uppercase font-mono block mb-1">Decision Logic Rationale</span>
                            <p className="text-slate-300 text-[10px] leading-relaxed font-sans">{decisionMeta.why_chosen}</p>
                          </div>
                        )}

                        {decisionMeta.routing_audit_log && decisionMeta.routing_audit_log.length > 0 && (
                          <div className="space-y-1.5">
                            <span className="text-slate-500 text-[9px] uppercase font-mono block">Routing Audit Logs</span>
                            <div className="max-h-36 overflow-y-auto space-y-1 pr-1 scrollbar-thin">
                              {decisionMeta.routing_audit_log.map((log, i) => (
                                <div key={i} className="text-[9px] font-mono text-slate-400 bg-slate-950 border border-slate-900 px-2.5 py-1.5 rounded flex items-start gap-1.5 leading-relaxed">
                                  <span className="text-indigo-400">⚡</span>
                                  <span>{log}</span>
                                </div>
                              ))}
                            </div>
                          </div>
                        )}
                      </div>
                    </div>
                  );
                })()}

                {/* RAG Diagnostics Section */}
                {selectedMessage.debugInfo.metadata && (selectedMessage.debugInfo.metadata.similarityScore !== undefined || selectedMessage.debugInfo.metadata.retrievedChunks) && (
                  <div className="bg-slate-950/60 border border-slate-850 p-4.5 rounded-xl space-y-3.5 shadow-sm animate-fadeIn">
                    <div className="text-[10px] text-slate-500 border-b border-slate-800 pb-2 mb-1.5 font-mono uppercase tracking-wider">
                      RAG Retrieval Diagnostics
                    </div>
                    <div className="grid grid-cols-2 gap-3.5 text-xs font-mono">
                      <div>
                        <span className="text-slate-500 text-[10px] block">Retrieved Chunk Count</span>
                        <span className="text-slate-200 font-semibold">{selectedMessage.debugInfo.metadata.chunkCount || 0} chunks</span>
                      </div>
                      <div>
                        <span className="text-slate-500 text-[10px] block">Similarity Threshold</span>
                        <span className="text-teal-400 font-semibold">{selectedMessage.debugInfo.metadata.threshold || "0.42"}</span>
                      </div>
                      <div>
                        <span className="text-slate-500 text-[10px] block">Max Similarity Score</span>
                        <span className="text-indigo-400 font-semibold">{(selectedMessage.debugInfo.metadata.similarityScore * 100).toFixed(1)}%</span>
                      </div>
                      <div>
                        <span className="text-slate-500 text-[10px] block">Documents Used</span>
                        <span className="text-slate-200 truncate block" title={selectedMessage.debugInfo.metadata.documentsUsed?.join(", ")}>
                          {selectedMessage.debugInfo.metadata.documentsUsed?.join(", ") || "None"}
                        </span>
                      </div>
                      <div>
                        <span className="text-slate-500 text-[10px] block">Embedding Latency</span>
                        <span className="text-slate-300">{selectedMessage.debugInfo.metadata.embeddingTimeMs || 0}ms</span>
                      </div>
                      <div>
                        <span className="text-slate-500 text-[10px] block">Vector Search Latency</span>
                        <span className="text-slate-300">{selectedMessage.debugInfo.metadata.searchTimeMs || 0}ms</span>
                      </div>
                      <div>
                        <span className="text-slate-500 text-[10px] block">Estimated Prompt Tokens</span>
                        <span className="text-slate-300">{selectedMessage.debugInfo.metadata.promptTokens || 0} tkn</span>
                      </div>
                      <div>
                        <span className="text-slate-500 text-[10px] block">Estimated Completion Tokens</span>
                        <span className="text-slate-300">{selectedMessage.debugInfo.metadata.completionTokens || 0} tkn</span>
                      </div>
                      {selectedMessage.debugInfo.metadata.evidence_score !== undefined && (
                        <div>
                          <span className="text-slate-500 text-[10px] block">Evidence Score</span>
                          <span className="text-purple-400 font-semibold">{(selectedMessage.debugInfo.metadata.evidence_score * 100).toFixed(1)}%</span>
                        </div>
                      )}
                      {selectedMessage.debugInfo.metadata.llmLatencyMs && (
                        <div>
                          <span className="text-slate-500 text-[10px] block">LLM Synthesis Latency</span>
                          <span className="text-slate-300">{selectedMessage.debugInfo.metadata.llmLatencyMs}ms</span>
                        </div>
                      )}
                      {selectedMessage.debugInfo.metadata.similarity_scores && selectedMessage.debugInfo.metadata.similarity_scores.length > 0 && (
                        <div className="col-span-2">
                          <span className="text-slate-500 text-[10px] block">Retrieved Similarity Scores</span>
                          <span className="text-slate-300 text-[10px] break-all">
                            {selectedMessage.debugInfo.metadata.similarity_scores.map(s => s.toFixed(4)).join(", ")}
                          </span>
                        </div>
                      )}
                    </div>

                    {/* Chunk Lists */}
                    {selectedMessage.debugInfo.metadata.retrievedChunks && selectedMessage.debugInfo.metadata.retrievedChunks.length > 0 && (
                      <div className="space-y-2 pt-2">
                        <span className="text-slate-500 text-[10px] block font-mono">RETRIEVED CHUNKS DETAIL</span>
                        <div className="max-h-48 overflow-y-auto space-y-2 pr-1 scrollbar-thin">
                          {selectedMessage.debugInfo.metadata.retrievedChunks.map((chunk, idx) => (
                            <div key={idx} className="bg-slate-900/60 p-2.5 rounded-lg border border-slate-850 text-[10px] font-mono space-y-1">
                              <div className="flex justify-between items-center text-slate-400">
                                <span className="text-indigo-400 font-bold truncate max-w-[140px]">{chunk.filename}</span>
                                <span>Page {chunk.pageNumber}</span>
                              </div>
                              <div className="text-slate-500 truncate text-[9px]">ID: {chunk.chunkId}</div>
                              {chunk.heading && <div className="text-slate-300 font-semibold truncate">Heading: {chunk.heading}</div>}
                            </div>
                          ))}
                        </div>
                      </div>
                    )}
                  </div>
                )}

                {/* Query Analysis Card */}
                <div className="bg-slate-950/60 border border-slate-850 p-4.5 rounded-xl space-y-3 shadow-sm">
                  <div className="text-[10px] text-slate-500 border-b border-slate-800 pb-2 mb-1.5 font-mono">
                    QUERY TRANSLATION
                  </div>

                  <div className="space-y-2 text-xs">
                    <div>
                      <span className="text-slate-500 text-[10px] block">
                        Normalized Text
                      </span>
                      <code className="bg-slate-900 px-2 py-1 rounded text-slate-300 font-mono mt-1 block border border-slate-850">
                        {selectedMessage.debugInfo.normalizedQuery || "None"}
                      </code>
                    </div>

                    <div>
                      <span className="text-slate-500 text-[10px] block">
                        Alias Resolved Text
                      </span>
                      <code className="bg-slate-900 px-2 py-1 rounded text-slate-300 font-mono mt-1 block border border-slate-850">
                        {selectedMessage.debugInfo.resolvedQuery || "None"}
                      </code>
                    </div>

                    <div>
                      <span className="text-slate-500 text-[10px] block">
                        Matched Keywords
                      </span>
                      <span className="text-slate-300 mt-1 block font-semibold">
                        {(selectedMessage.debugInfo.matchedKeywords || []).length > 0 ? (
                          <div className="flex flex-wrap gap-1.5">
                            {selectedMessage.debugInfo.matchedKeywords.map(
                              (kw, idx) => (
                                <span
                                  key={idx}
                                  className="bg-indigo-950/30 text-indigo-300 border border-indigo-900/30 px-2 py-0.5 rounded text-[10px] font-mono"
                                >
                                  {kw}
                                </span>
                              )
                            )}
                          </div>
                        ) : (
                          <span className="text-slate-500 italic">None</span>
                        )}
                      </span>
                    </div>
                  </div>
                </div>

                {/* Pipeline Flow Execution Trace */}
                <div className="space-y-3">
                  <div className="text-[10px] text-slate-500 border-b border-slate-800 pb-2 font-mono uppercase tracking-wider">
                    Pipeline Execution Timeline
                  </div>

                  <div className="relative border-l-2 border-slate-800 pl-4 py-1 space-y-4 ml-2.5">
                    {(selectedMessage.debugInfo.trace || []).map((step, idx) => {
                      const isExpanded = expandedTraceId[idx];
                      return (
                        <div key={idx} className="relative">
                          <span
                            className={`absolute -left-[23px] top-1 w-2.5 h-2.5 rounded-full border transition-all duration-200 ${
                              step.handled
                                ? "bg-green-500 border-green-400 ring-4 ring-green-950/40"
                                : "bg-slate-900 border-slate-700"
                            }`}
                          />

                          <div className="space-y-1">
                            <div className="flex items-center justify-between text-xs">
                              <span
                                className={`font-semibold transition-colors ${
                                  step.handled
                                    ? "text-green-400 font-bold"
                                    : "text-slate-300"
                                }`}
                              >
                                {step.engine}
                              </span>

                              <div className="flex items-center gap-2 text-[10px] text-slate-500">
                                <span
                                  className={
                                    step.handled ? "text-green-500" : ""
                                  }
                                >
                                  {step.handled ? "Handled" : "Pass"}
                                </span>
                                <span className="font-mono text-slate-600">
                                  {step.executionTimeMs}ms
                                </span>
                              </div>
                            </div>

                            <div className="flex justify-between items-center text-[10px] text-slate-500 bg-slate-950/40 border border-slate-850 px-2.5 py-1.5 rounded-lg">
                              <code className="font-mono font-bold text-slate-400">
                                {step.reasonCode}
                              </code>

                              {step.metadata &&
                                Object.keys(step.metadata).length > 0 && (
                                  <button
                                    onClick={() => toggleTraceNode(idx)}
                                    className="text-indigo-400 hover:text-indigo-300 font-semibold cursor-pointer"
                                  >
                                    {isExpanded ? "Hide" : "Inspect"}
                                  </button>
                                )}
                            </div>

                            {isExpanded &&
                              step.metadata &&
                              Object.keys(step.metadata).length > 0 && (
                                <div className="mt-1.5 p-2.5 bg-slate-950 border border-slate-850 rounded-lg text-[10px] font-mono text-slate-400 overflow-x-auto">
                                  <pre className="whitespace-pre-wrap max-w-full">
                                    {JSON.stringify(step.metadata, null, 2)}
                                  </pre>
                                </div>
                              )}
                          </div>
                        </div>
                      );
                    })}
                  </div>
                </div>
              </div>
            ) : (
              <div className="flex-1 flex flex-col items-center justify-center text-center text-slate-500 text-xs py-20">
                <svg
                  className="w-10 h-10 text-slate-600 mb-2 animate-pulse"
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={1.5}
                    d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
                  />
                </svg>
                <span>Select a bot response to inspect execution trace</span>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  </div>
  );
}

export default App;
