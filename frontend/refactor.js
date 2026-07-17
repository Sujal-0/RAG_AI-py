
const fs = require('fs');

let content = fs.readFileSync('src/App.jsx', 'utf-8');

// Add imports
if (!content.includes('lucide-react')) {
    content = content.replace(
        'import ReactMarkdown from "react-markdown";',
        'import ReactMarkdown from "react-markdown";\nimport { MessageSquare, Folder, Settings, Wrench, RefreshCw, X, Minimize2, Maximize2, ChevronLeft, Building, Shield, Globe, Briefcase } from "lucide-react";'
    );
}

// Widget outside click
if (!content.includes('widgetRef')) {
    content = content.replace(
        'const [chatMode, setChatMode] = useState("widget"); // "widget" | "fullscreen"',
        'const [chatMode, setChatMode] = useState("widget"); // "widget" | "fullscreen"\n  const widgetRef = useRef(null);\n\n  useEffect(() => {\n    function handleClickOutside(event) {\n      if (widgetRef.current && !widgetRef.current.contains(event.target) && chatMode === "widget") {\n        setChatMode("collapsed");\n      }\n    }\n    document.addEventListener("mousedown", handleClickOutside);\n    return () => document.removeEventListener("mousedown", handleClickOutside);\n  }, [chatMode]);'
    );
    content = content.replace(
        'className={`absolute transition-all duration-300 flex flex-col overflow-hidden bg-slate-950 shadow-[0_8px_40px_rgb(0,0,0,0.4)]',
        'ref={widgetRef}\n             className={`absolute transition-all duration-300 flex flex-col overflow-hidden bg-slate-950 shadow-[0_8px_40px_rgb(0,0,0,0.4)]'
    );
}

// Logo fix & micro-interactions
content = content.replace(
    'className="w-8 h-8 object-contain brightness-0 invert relative z-10"',
    'className="w-6 h-6 object-contain relative z-10 group-hover:scale-110 transition-transform duration-300 group-hover:drop-shadow-[0_0_8px_rgba(255,255,255,0.8)]"'
);
content = content.replace(
    'className="w-full h-full rounded-full flex items-center justify-center relative overflow-hidden group border border-blue-400/30"',
    'className="w-full h-full rounded-full flex items-center justify-center relative overflow-hidden group border-2 border-white/20 bg-white shadow-inner hover:shadow-[0_0_20px_rgba(37,99,235,0.6)] transition-all duration-300"'
);

// Emojis in sidebars
content = content.replace(/<span>💬<\/span>/g, '<MessageSquare size={16} />');
content = content.replace(/<span>📂<\/span>/g, '<Folder size={16} />');
content = content.replace(/<span>⚙️<\/span>/g, '<Settings size={16} />');
content = content.replace(/<span>🛠️ DEV PANEL<\/span>/g, '<div className="flex items-center gap-2"><Wrench size={12} /><span>DEV PANEL</span></div>');
content = content.replace('◀', '<ChevronLeft size={14} />');

// Icons in collapsed sidebar
content = content.replace(/>\s*💬\s*<\/button>/g, '><MessageSquare size={20} className="mx-auto" /></button>');
content = content.replace(/>\s*📂\s*<\/button>/g, '><Folder size={20} className="mx-auto" /></button>');
content = content.replace(/>\s*⚙️\s*<\/button>/g, '><Settings size={20} className="mx-auto" /></button>');
content = content.replace(/>\s*🛠️\s*<\/button>/g, '><Wrench size={16} className="mx-auto" /></button>');

// Emojis in widget header
content = content.replace(/>\s*🔄\s*<\/button>/g, '><RefreshCw size={16} /></button>');
content = content.replace(/>\s*📂\s*<\/button>/g, '><Folder size={16} /></button>');
content = content.replace(/>\s*⚙️\s*<\/button>/g, '><Settings size={16} /></button>');
content = content.replace(/>\s*🛠️\s*<\/button>/g, '><Wrench size={16} /></button>');

content = content.replace('↙️ Exit Fullscreen', '<Minimize2 size={14} /> Exit Fullscreen');

// Icons for preset cards
content = content.replace('icon: "🏢"', 'icon: <Building size={20} className="text-indigo-400" />');
content = content.replace('icon: "🛡️"', 'icon: <Shield size={20} className="text-indigo-400" />');
content = content.replace('icon: "🌐"', 'icon: <Globe size={20} className="text-indigo-400" />');
content = content.replace('icon: "💼"', 'icon: <Briefcase size={20} className="text-indigo-400" />');

fs.writeFileSync('src/App.jsx', content, 'utf-8');
console.log("Refactoring complete");
