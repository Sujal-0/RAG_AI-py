export default function LandingPage() {
  return (
    <div className="w-full h-full relative overflow-hidden bg-[#020813] text-white flex flex-col font-sans">
      {/* Dynamic Background */}
      <div className="absolute inset-0 pointer-events-none z-0 overflow-hidden">
        <div className="absolute top-[-20%] right-[-10%] w-[70vw] h-[70vw] rounded-full bg-blue-900/20 blur-[120px]"></div>
        <div className="absolute bottom-[-20%] left-[-10%] w-[50vw] h-[50vw] rounded-full bg-indigo-900/20 blur-[100px]"></div>
        <div className="absolute top-[20%] right-[10%] w-[40vw] h-[40vw] rounded-full border border-blue-500/10 shadow-[0_0_80px_rgba(30,58,138,0.3)]"></div>
        <div className="absolute top-[25%] right-[15%] w-[30vw] h-[30vw] rounded-full border border-blue-400/20 shadow-[0_0_60px_rgba(30,58,138,0.4)]"></div>
        <div className="absolute top-[30%] right-[20%] w-[20vw] h-[20vw] rounded-full border border-blue-300/30 shadow-[0_0_40px_rgba(59,130,246,0.5)]"></div>
      </div>

      {/* Navigation */}
      <nav className="relative z-10 w-full px-12 py-6 flex items-center justify-between border-b border-white/5 bg-[#020813]/80 backdrop-blur-md">
        <div className="flex items-center gap-3">
          <img src="/logos/mobiloitte-ai-logo.png" alt="Mobiloitte Logo" className="w-8 h-8 object-contain" />
          <span className="text-xl font-bold tracking-tight">Mobiloitte</span>
        </div>
        <div className="hidden lg:flex items-center gap-10 text-sm font-medium text-slate-300">
          <a href="#" className="hover:text-white transition-colors flex items-center gap-1">What we do <span className="text-[10px]">▼</span></a>
          <a href="#" className="hover:text-white transition-colors flex items-center gap-1">What we think <span className="text-[10px]">▼</span></a>
          <a href="#" className="hover:text-white transition-colors flex items-center gap-1">Who we are <span className="text-[10px]">▼</span></a>
          <a href="#" className="hover:text-white transition-colors">Careers</a>
        </div>
        <button className="px-5 py-2 rounded-full border border-white/20 text-sm font-semibold hover:bg-white hover:text-black transition-colors">
          Contact Us
        </button>
      </nav>

      {/* Main Content */}
      <main className="relative z-10 flex-1 flex flex-col justify-center px-12 max-w-4xl">
        <h1 className="text-5xl md:text-7xl font-bold leading-tight mb-8">
          AI Governance,<br />
          Security & Compliance for<br />
          Regulated Enterprises
        </h1>
        <p className="text-base text-slate-300 mb-10 max-w-2xl leading-relaxed">
          Mobiloitte builds secure AI systems, custom AI software, generative AI solutions, RAG architectures, AI agents, blockchain platforms, cloud infrastructure, cybersecurity solutions, web applications, AI-powered mobile apps, and automation workflows for enterprise digital transformation. From AI consulting and workflow design to development, integration, deployment, governance, and scale, Mobiloitte helps businesses launch production-ready AI solutions, enterprise software platforms, cloud-native applications, blockchain systems, and intelligent automation workflows.
        </p>
        <div className="flex items-center gap-4">
          <button className="px-6 py-3 bg-blue-600 hover:bg-blue-500 text-white rounded-lg font-semibold flex items-center gap-2 transition-colors">
            Book an AI Strategy Session <span>→</span>
          </button>
          <button className="px-6 py-3 border border-white/20 hover:bg-white/5 text-white rounded-lg font-semibold transition-colors">
            See What We Build
          </button>
        </div>
      </main>

      {/* Footer Text */}
      <footer className="relative z-10 p-12 max-w-6xl">
        <p className="text-xs text-slate-400">
          From AI strategy to generative AI development, RAG chatbot development, LLM integration, AI agent development, enterprise software engineering, mobile app development, cloud, DevOps, cybersecurity, and blockchain deployment.
        </p>
      </footer>
    </div>
  );
}
