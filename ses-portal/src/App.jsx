import React, { useState } from 'react';
import { 
  BookOpen, 
  Terminal, 
  Cpu, 
  Wallet, 
  Coins, 
  Play, 
  CheckCircle2, 
  AlertTriangle, 
  RefreshCw, 
  FileText, 
  ArrowRight,
  ShieldCheck,
  Search,
  Database
} from 'lucide-react';

export default function App() {
  const [activeTab, setActiveTab] = useState('docs');
  const [interactiveStep, setInteractiveStep] = useState('idle'); // idle, got_402, paid, completed
  const [mockLogs, setMockLogs] = useState([]);
  const [userQuery, setUserQuery] = useState('What does SES do?');

  const addLog = (message, type = 'info') => {
    setMockLogs(prev => [...prev, { time: new Date().toLocaleTimeString(), message, type }]);
  };

  const handleSimulateE2E = async () => {
    setInteractiveStep('got_402');
    setMockLogs([]);
    addLog(`Initiating agent query: "${userQuery}"`, 'info');
    addLog(`GET /v1/quote?operation=query&namespace=default - price: 0.001 USDC`, 'info');
    addLog(`POST /v1/query - Header: Authorization: Bearer <mock_key>`, 'info');
    addLog(`Server responded with HTTP 402 Payment Required`, 'warning');
    addLog(`Standardized x402 details received: Amount 0.001 USDC on Solana`, 'warning');
  };

  const handleSimulatePayment = () => {
    setInteractiveStep('paid');
    addLog(`Agent triggering Solana Pay wallet callback...`, 'info');
    addLog(`Simulating Solana transaction signature generation...`, 'info');
    addLog(`USDC Payment of 0.001 sent to merchant wallet. Tx: 5Hn...pQ2`, 'success');
    addLog(`Received receipt proof hash: sha256(...)`, 'success');
  };

  const handleSimulateRetry = () => {
    setInteractiveStep('completed');
    addLog(`Retrying query with X-Payment-Proof and Idempotency-Key...`, 'info');
    addLog(`POST /v1/query - Headers: X-Payment-Proof: 5Hn...pQ2, Idempotency-Key: id_8f3a`, 'info');
    addLog(`Server validated payment proof against ReceiptLedger.`, 'success');
    addLog(`HTTP 200 OK - Curated memory retrieved successfully!`, 'success');
  };

  const resetSimulation = () => {
    setInteractiveStep('idle');
    setMockLogs([]);
  };

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col font-sans">
      {/* Header */}
      <header className="border-b border-slate-800/60 glass sticky top-0 z-50">
        <div className="max-w-7xl mx-auto px-6 py-4 flex items-center justify-between">
          <div className="flex items-center gap-3 group cursor-pointer">
            <div className="h-10 w-10 rounded-xl bg-gradient-to-tr from-cyan-500 to-indigo-600 flex items-center justify-center shadow-lg shadow-cyan-500/30 group-hover:shadow-cyan-500/50 transition-all duration-300 group-hover:scale-105">
              <Cpu className="h-5 w-5 text-white" />
            </div>
            <div>
              <span className="font-extrabold text-xl tracking-tight bg-gradient-to-r from-cyan-400 to-indigo-400 bg-clip-text text-transparent">
                SES TOLLGATE
              </span>
              <span className="text-xs block text-slate-500 font-mono -mt-1">Memory Marketplace</span>
            </div>
          </div>

          <nav className="flex items-center gap-1">
            <button 
              onClick={() => setActiveTab('docs')}
              className={`px-4 py-2 rounded-lg text-sm font-medium transition-all ${activeTab === 'docs' ? 'bg-slate-800 text-cyan-400' : 'text-slate-400 hover:text-white'}`}
            >
              <BookOpen className="h-4 w-4 inline-block mr-2" />
              Documentation
            </button>
            <button 
              onClick={() => setActiveTab('sdk')}
              className={`px-4 py-2 rounded-lg text-sm font-medium transition-all ${activeTab === 'sdk' ? 'bg-slate-800 text-cyan-400' : 'text-slate-400 hover:text-white'}`}
            >
              <Terminal className="h-4 w-4 inline-block mr-2" />
              SDK Reference
            </button>
            <button 
              onClick={() => setActiveTab('playground')}
              className={`px-4 py-2 rounded-lg text-sm font-medium transition-all ${activeTab === 'playground' ? 'bg-slate-800 text-cyan-400' : 'text-slate-400 hover:text-white'}`}
            >
              <Play className="h-4 w-4 inline-block mr-2" />
              x402 Playground
            </button>
          </nav>
        </div>
      </header>

      {/* Hero Section */}
      <div className="relative overflow-hidden bg-[#020617] border-b border-slate-800/50 py-24 px-6 flex flex-col items-center justify-center min-h-[70vh]">
        <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_top,_var(--tw-gradient-stops))] from-indigo-900/30 via-slate-950 to-slate-950 pointer-events-none" />
        
        {/* Floating background elements */}
        <div className="absolute top-20 left-10 h-64 w-64 bg-cyan-600/10 rounded-full blur-3xl animate-float pointer-events-none"></div>
        <div className="absolute bottom-10 right-10 h-80 w-80 bg-indigo-600/10 rounded-full blur-3xl animate-float pointer-events-none" style={{ animationDelay: '2s' }}></div>

        <div className="max-w-5xl mx-auto text-center relative z-10">
          <div className="inline-flex items-center gap-2 px-4 py-1.5 rounded-full bg-cyan-500/10 border border-cyan-500/20 text-cyan-400 text-xs font-mono mb-8 hover:bg-cyan-500/20 transition-colors cursor-pointer">
            <ShieldCheck className="h-4 w-4" />
            v2.0.0 Stable Specs Released
          </div>
          <h1 className="text-5xl sm:text-7xl font-black tracking-tight text-white mb-8 leading-tight drop-shadow-2xl">
            Curated Paid Memory for <br />
            <span className="bg-gradient-to-r from-cyan-400 via-teal-300 to-indigo-400 bg-clip-text text-transparent text-glow">
              Autonomous Agents
            </span>
          </h1>
          <p className="text-slate-400 max-w-2xl mx-auto text-lg sm:text-xl mb-10 leading-relaxed font-light">
            Provide your agents with highly organized technical documentation, SDK guides, and knowledge namespaces without maintaining vector databases. Paid microtransactions over Solana Pay USDC.
          </p>
          <div className="flex justify-center gap-6">
            <button 
              onClick={() => setActiveTab('playground')}
              className="px-8 py-4 rounded-xl font-bold bg-gradient-to-r from-cyan-500 to-indigo-600 text-white shadow-xl shadow-indigo-500/25 hover:shadow-cyan-500/40 hover:scale-105 transition-all duration-300 text-sm flex items-center gap-2 group"
            >
              Launch Interactive Demo
              <ArrowRight className="h-4 w-4 group-hover:translate-x-1 transition-transform" />
            </button>
            <button 
              onClick={() => setActiveTab('docs')}
              className="px-8 py-4 rounded-xl font-bold bg-slate-800/80 backdrop-blur-sm border border-slate-700 text-slate-200 hover:bg-slate-700 hover:text-white hover:scale-105 transition-all duration-300 text-sm"
            >
              View Specifications
            </button>
          </div>
        </div>
      </div>

      {/* Main Content */}
      <main className="flex-1 max-w-7xl w-full mx-auto px-6 py-12">
        {activeTab === 'docs' && (
          <div className="grid grid-cols-1 lg:grid-cols-4 gap-8">
            {/* Sidebar Navigation */}
            <div className="lg:col-span-1 space-y-2">
              <h3 className="text-xs font-semibold text-slate-500 uppercase tracking-wider mb-4 px-2">Getting Started</h3>
              <a href="#overview" className="block px-3 py-2 rounded-md text-sm font-medium bg-slate-900 text-cyan-400 border-l-2 border-cyan-400">Overview</a>
              <a href="#architecture" className="block px-3 py-2 rounded-md text-sm font-medium text-slate-400 hover:text-white">Architecture</a>
              <a href="#contracts" className="block px-3 py-2 rounded-md text-sm font-medium text-slate-400 hover:text-white">Interface Contracts</a>
              <h3 className="text-xs font-semibold text-slate-500 uppercase tracking-wider mt-8 mb-4 px-2">Core API Specs</h3>
              <a href="#quote" className="block px-3 py-2 rounded-md text-sm font-medium text-slate-400 hover:text-white">GET /v1/quote</a>
              <a href="#query" className="block px-3 py-2 rounded-md text-sm font-medium text-slate-400 hover:text-white">POST /v1/query</a>
              <a href="#receipt" className="block px-3 py-2 rounded-md text-sm font-medium text-slate-400 hover:text-white">GET /v1/receipt</a>
            </div>

            {/* Main Docs Section */}
            <div className="lg:col-span-3 space-y-12">
              <section id="overview" className="scroll-mt-24 space-y-4">
                <h2 className="text-2xl font-bold text-white border-b border-slate-800 pb-3">Project Overview</h2>
                <p className="text-slate-400 leading-relaxed">
                  The **SES (Agent Memory Tollgate)** provides curated, paid technical memory namespaces for autonomous agents.
                  Instead of agents needing to download, chunk, embed, and maintain large reference libraries inside their local databases, they can query SES. 
                  SES charges micro-payments (typically 0.001 USDC) per query and returns validated answers, verified source citations, value proofs, and cryptographically sound receipts.
                </p>
                <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mt-6">
                  <div className="p-6 glass-card rounded-2xl group cursor-default">
                    <Coins className="h-8 w-8 text-cyan-400 mb-4 group-hover:scale-110 transition-transform" />
                    <h4 className="font-semibold text-white mb-2 text-lg">x402 Flow</h4>
                    <p className="text-sm text-slate-400">Standardized HTTP 402 protocol triggers automatic agent billing negotiation.</p>
                  </div>
                  <div className="p-6 glass-card rounded-2xl group cursor-default">
                    <Database className="h-8 w-8 text-indigo-400 mb-4 group-hover:scale-110 transition-transform" />
                    <h4 className="font-semibold text-white mb-2 text-lg">Curation Engine</h4>
                    <p className="text-sm text-slate-400">Strictly parsed markdown namespaces with stable chunking, freshness checks, and quality gates.</p>
                  </div>
                  <div className="p-6 glass-card rounded-2xl group cursor-default">
                    <ShieldCheck className="h-8 w-8 text-teal-400 mb-4 group-hover:scale-110 transition-transform" />
                    <h4 className="font-semibold text-white mb-2 text-lg">Audit Trail</h4>
                    <p className="text-sm text-slate-400">All queries record a transaction signature in a persistent SQL ledger for invoice auditability.</p>
                  </div>
                </div>
              </section>

              <section id="architecture" className="scroll-mt-24 space-y-4">
                <h2 className="text-2xl font-bold text-white border-b border-slate-800 pb-3">Architecture Components</h2>
                <ul className="space-y-3 text-slate-400">
                  <li className="flex gap-2">
                    <strong className="text-slate-200">FastAPI Gateway:</strong> Routes traffic, validates API keys, handles search/query requests, and implements the x402 payment validation middleware.
                  </li>
                  <li className="flex gap-2">
                    <strong className="text-slate-200">Payment Ledger:</strong> Persistent database caching responses, verifying Solana transactions, checking for idempotency key replays.
                  </li>
                  <li className="flex gap-2">
                    <strong className="text-slate-200">Curation CLI:</strong> Command-line toolkit to compile source documents, normalise files, build manifests, and run quality checks before ingestion.
                  </li>
                </ul>
              </section>

              <section id="contracts" className="scroll-mt-24 space-y-4">
                <h2 className="text-2xl font-bold text-white border-b border-slate-800 pb-3">Interface Contracts</h2>
                
                <h3 className="text-lg font-semibold text-slate-300">1. HTTP 402 Standard Error Schema</h3>
                <pre className="p-4 bg-slate-900 border border-slate-800 rounded-lg overflow-x-auto text-xs font-mono text-cyan-300">
{`{
  "error": "Payment required",
  "code": "payment_required",
  "next_action": "pay_and_retry",
  "payment_protocol": "x402",
  "amount": "0.001",
  "asset": "USDC",
  "network": "solana",
  "operation": "query",
  "retry": {
    "method": "POST",
    "path": "/v1/query",
    "required_headers": [
      "X-Payment-Proof",
      "Idempotency-Key"
    ]
  }
}`}
                </pre>

                <h3 className="text-lg font-semibold text-slate-300 mt-6">2. HTTP 200 Successful Response Schema</h3>
                <pre className="p-4 bg-slate-900 border border-slate-800 rounded-lg overflow-x-auto text-xs font-mono text-indigo-300">
{`{
  "answer": "SES acts as a paid semantic namespace registry...",
  "citations": [
    {
      "chunk_id": "overview:intro:1",
      "doc_id": "overview",
      "source_title": "SES Overview",
      "source_path": "docs/overview.md",
      "score": 0.98,
      "freshness_score": 1.0
    }
  ],
  "receipt": {
    "receipt_id": "rec_09f83a",
    "amount_paid": "0.001",
    "asset": "USDC",
    "network": "solana",
    "tx_signature": "5Hn...pQ2",
    "created_at": "2026-06-25T04:11:00Z"
  }
}`}
                </pre>
              </section>
            </div>
          </div>
        )}

        {activeTab === 'sdk' && (
          <div className="space-y-6">
            <h2 className="text-2xl font-bold text-white border-b border-slate-800 pb-3">Python Agent SDK Guide</h2>
            <p className="text-slate-400">
              The `ses-agent-sdk` library automates the entire payment negotiation sequence. Agents import the client, provide an on-chain wallet signing handler, and carry out standard method invocations. Under the hood, the SDK intercepts the HTTP 402 challenge, processes Solana Pay transaction instructions, signs them, submits to the blockchain, and retries the target query.
            </p>

            <div className="p-6 bg-slate-900 border border-slate-800 rounded-xl space-y-4">
              <h3 className="text-lg font-semibold text-white flex items-center gap-2">
                <Terminal className="h-5 w-5 text-cyan-400" />
                Python Client Example
              </h3>
              
              <pre className="p-4 bg-slate-950 border border-slate-800 rounded-lg overflow-x-auto text-xs font-mono text-emerald-400">
{`from ses_sdk import SESClient

# The agent provides a callback to sign Solana transaction proofs
def my_wallet_provider(amount_usdc: float, payment_data: dict) -> str:
    # 1. Inspect target merchant parameters and verify amount
    # 2. Trigger Solana private key signature
    # 3. Return transaction signature hash
    return "5HnGbc...qpQ2Jk"

# Instantiate client configured with memory gate address
client = SESClient(
    agent_id="autonomous-assistant-1", 
    api_url="https://api.ses-tollgate.net",
    payment_provider=my_wallet_provider
)

# Requesting context (negotiates 402 flow automatically)
response = client.query("What does SES do?")

print(f"Answer: {response['answer']}")
print(f"Verified Receipt ID: {response['receipt']['receipt_id']}")
for citation in response['citations']:
    print(f" - Citation: {citation['source_title']} [Score: {citation['score']}]")`}
              </pre>
            </div>
          </div>
        )}

        {activeTab === 'playground' && (
          <div className="space-y-8">
            <div className="border-b border-slate-800 pb-3">
              <h2 className="text-2xl font-bold text-white">x402 Protocol Playground</h2>
              <p className="text-slate-400 mt-1">Simulate how an agent negotiates semantic payment with the memory gateway.</p>
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
              {/* Simulation Controller */}
              <div className="glass-card p-6 rounded-2xl shadow-xl space-y-6">
                <div className="space-y-3">
                  <label className="text-sm font-semibold text-slate-300">Agent Query</label>
                  <div className="flex gap-2">
                    <input 
                      type="text" 
                      className="flex-1 bg-slate-950/80 border border-slate-700/50 rounded-xl px-4 py-3 text-sm text-white focus:outline-none focus:border-cyan-500 focus:ring-1 focus:ring-cyan-500 transition-all shadow-inner"
                      value={userQuery}
                      onChange={(e) => setUserQuery(e.target.value)}
                      disabled={interactiveStep !== 'idle'}
                    />
                    {interactiveStep === 'idle' ? (
                      <button 
                        onClick={handleSimulateE2E}
                        className="px-6 py-3 bg-gradient-to-r from-indigo-600 to-indigo-500 hover:from-indigo-500 hover:to-indigo-400 text-white rounded-xl text-sm font-semibold transition-all flex items-center gap-2 shadow-lg shadow-indigo-500/25"
                      >
                        <Play className="h-4 w-4 fill-current" /> Run Query
                      </button>
                    ) : (
                      <button 
                        onClick={resetSimulation}
                        className="px-6 py-3 bg-slate-800 hover:bg-slate-700 text-slate-300 rounded-xl text-sm font-semibold transition-all border border-slate-700"
                      >
                        Reset
                      </button>
                    )}
                  </div>
                </div>

                {/* Step Flowchart */}
                <div className="space-y-4">
                  <h4 className="text-xs font-semibold text-slate-400 uppercase tracking-wider">Protocol State Tracker</h4>
                  
                  {/* Step 1 */}
                  <div className={`p-4 rounded-xl border flex items-center justify-between ${interactiveStep !== 'idle' ? 'bg-slate-800/40 border-slate-750' : 'bg-slate-900/50 border-slate-800/50 opacity-55'}`}>
                    <div className="flex items-center gap-3">
                      <div className={`h-8 w-8 rounded-lg flex items-center justify-center font-bold text-xs ${interactiveStep !== 'idle' ? 'bg-amber-500/20 text-amber-400' : 'bg-slate-800 text-slate-500'}`}>1</div>
                      <div>
                        <h5 className="font-semibold text-sm text-slate-200">Query and Receive HTTP 402</h5>
                        <p className="text-xs text-slate-400">Agent triggers endpoint, receives standardized payload required metadata.</p>
                      </div>
                    </div>
                    {interactiveStep !== 'idle' && <CheckCircle2 className="h-5 w-5 text-amber-500" />}
                  </div>

                  {/* Step 2 */}
                  <div className={`p-4 rounded-xl border flex items-center justify-between transition-all duration-300 ${interactiveStep === 'got_402' ? 'bg-indigo-950/20 border-indigo-500/50 shadow-md shadow-indigo-500/5' : (interactiveStep === 'paid' || interactiveStep === 'completed') ? 'bg-slate-800/40 border-slate-750' : 'bg-slate-900/50 border-slate-800/50 opacity-35'}`}>
                    <div className="flex items-center gap-3">
                      <div className={`h-8 w-8 rounded-lg flex items-center justify-center font-bold text-xs ${(interactiveStep === 'paid' || interactiveStep === 'completed') ? 'bg-emerald-500/20 text-emerald-400' : interactiveStep === 'got_402' ? 'bg-indigo-500/20 text-indigo-400 animate-pulse' : 'bg-slate-800 text-slate-500'}`}>2</div>
                      <div>
                        <h5 className="font-semibold text-sm text-slate-200 font-sans">USDC Microtransaction Proof</h5>
                        <p className="text-xs text-slate-400">Wallet signs transactions and provides transaction signature hash.</p>
                      </div>
                    </div>
                    {interactiveStep === 'got_402' && (
                      <button 
                        onClick={handleSimulatePayment}
                        className="px-3 py-1.5 bg-indigo-600 hover:bg-indigo-500 text-white rounded-md text-xs font-bold transition-all shadow-md flex items-center gap-1"
                      >
                        <Wallet className="h-3 w-3" /> Pay 0.001 USDC
                      </button>
                    )}
                    {(interactiveStep === 'paid' || interactiveStep === 'completed') && <CheckCircle2 className="h-5 w-5 text-emerald-500" />}
                  </div>

                  {/* Step 3 */}
                  <div className={`p-4 rounded-xl border flex items-center justify-between transition-all duration-300 ${interactiveStep === 'paid' ? 'bg-cyan-950/20 border-cyan-500/50 shadow-md shadow-cyan-500/5' : interactiveStep === 'completed' ? 'bg-slate-800/40 border-slate-750' : 'bg-slate-900/50 border-slate-800/50 opacity-35'}`}>
                    <div className="flex items-center gap-3">
                      <div className={`h-8 w-8 rounded-lg flex items-center justify-center font-bold text-xs ${interactiveStep === 'completed' ? 'bg-cyan-500/20 text-cyan-400' : interactiveStep === 'paid' ? 'bg-cyan-500/20 text-cyan-400 animate-pulse' : 'bg-slate-800 text-slate-500'}`}>3</div>
                      <div>
                        <h5 className="font-semibold text-sm text-slate-200">Re-Query with Proof & Retrieve</h5>
                        <p className="text-xs text-slate-400">Agent retries initial query, including validated proofs in HTTP headers.</p>
                      </div>
                    </div>
                    {interactiveStep === 'paid' && (
                      <button 
                        onClick={handleSimulateRetry}
                        className="px-3 py-1.5 bg-cyan-600 hover:bg-cyan-500 text-white rounded-md text-xs font-bold transition-all shadow-md flex items-center gap-1"
                      >
                        <RefreshCw className="h-3 w-3" /> Fetch Memory
                      </button>
                    )}
                    {interactiveStep === 'completed' && <CheckCircle2 className="h-5 w-5 text-cyan-500" />}
                  </div>
                </div>
              </div>

              {/* Logs and Terminal Output */}
              <div className="glass-card border border-slate-700/50 rounded-2xl p-6 shadow-2xl flex flex-col min-h-[400px] bg-slate-950/80">
                <div className="flex items-center justify-between border-b border-slate-800/80 pb-4 mb-4">
                  <div className="flex items-center gap-2">
                    <div className="h-3 w-3 rounded-full bg-rose-500 shadow-[0_0_8px_rgba(244,63,94,0.6)]" />
                    <div className="h-3 w-3 rounded-full bg-amber-500 shadow-[0_0_8px_rgba(245,158,11,0.6)]" />
                    <div className="h-3 w-3 rounded-full bg-emerald-500 shadow-[0_0_8px_rgba(16,185,129,0.6)]" />
                    <span className="text-xs text-slate-400 font-mono ml-3">agent_negotiator.log</span>
                  </div>
                  <button 
                    onClick={() => setMockLogs([])}
                    className="text-xs text-slate-500 hover:text-slate-300 font-mono transition-colors"
                  >
                    Clear Logs
                  </button>
                </div>

                <div className="flex-1 overflow-y-auto space-y-2.5 font-mono text-xs max-h-[320px] scrollbar-thin">
                  {mockLogs.length === 0 ? (
                    <div className="h-full flex flex-col items-center justify-center text-slate-600 py-16">
                      <Terminal className="h-10 w-10 mb-3 opacity-40" />
                      <p>Run query simulation to inspect HTTP sequence logs...</p>
                    </div>
                  ) : (
                    mockLogs.map((log, index) => (
                      <div key={index} className="flex items-start gap-2 leading-relaxed">
                        <span className="text-slate-600 select-none">[{log.time}]</span>
                        <span className={
                          log.type === 'success' ? 'text-emerald-400' :
                          log.type === 'warning' ? 'text-amber-400' :
                          'text-slate-300'
                        }>
                          {log.message}
                        </span>
                      </div>
                    ))
                  )}

                  {interactiveStep === 'completed' && (
                    <div className="border border-emerald-500/20 bg-emerald-500/5 p-4 rounded-lg mt-4 space-y-2 text-slate-200">
                      <p className="font-semibold text-emerald-400 flex items-center gap-1.5">
                        <CheckCircle2 className="h-4 w-4" /> Received Semantic Namespace Context:
                      </p>
                      <blockquote className="border-l-2 border-slate-700 pl-3 py-1 italic text-slate-400">
                        "SES acts as a paid semantic namespace registry where agents request cached context on-chain..."
                      </blockquote>
                      <div className="pt-2 text-[10px] text-slate-500">
                        Receipt: rec_09f83a | Fee: 0.001 USDC | Solana Signature Check: OK
                      </div>
                    </div>
                  )}
                </div>
              </div>
            </div>
          </div>
        )}
      </main>

      {/* Footer */}
      <footer className="border-t border-slate-800 bg-slate-900/30 mt-auto py-8">
        <div className="max-w-7xl mx-auto px-6 text-center text-slate-500 text-xs font-mono">
          <p>© 2026 SES Agent Memory Tollgate. Standard Specification compliant.</p>
        </div>
      </footer>
    </div>
  );
}
