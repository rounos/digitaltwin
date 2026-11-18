import React, { useState, useEffect } from 'react';
import {
  Upload, MessageSquare, BarChart3, CheckCircle, XCircle,
  Shield, Sparkles, ShieldAlert, Sun, Moon, Plus, Trash2, History, FileText,
  Copy, Check, Download, RotateCcw
} from 'lucide-react';

const API_URL = import.meta.env.VITE_BACKEND_URL || 'http://localhost:8000';

const MOCK_PERSONA = {
  persona_id: "default_user",
  name: "Μάρκος Βλάχος",
  role: "AI Red Teamer & Adversarial Testing Lead",
  writing_style: {
    tone: "Αναλυτικός, σκεπτικιστής, ευθύς, με εστίαση στα edge cases και το ρίσκο",
    vocabulary_notes: "Χρησιμοποιεί ορολογία AI safety (jailbreaks, prompt injection, blast radius, evals), χωρίς περιττές ευγένειες."
  },
  decision_heuristics: [
    "Μπλοκάρει οποιοδήποτε AI deployment αν δεν έχει περάσει red-teaming & prompt injection suite",
    "Απαιτεί πάντα human-in-the-loop approval για ενέργειες με υψηλό blast radius (π.χ. DB write, external emails)",
    "Απορρίπτει αόριστες υποσχέσεις ασφαλείας — ζητάει μετρήσιμα failure rates και adversarial logs"
  ],
  knowledge_facts: [
    "Εξειδίκευση σε LLM Red Teaming, Prompt Injection, Jailbreak evaluation και Guardrails",
    "Χρησιμοποιεί garak, promptfoo και custom adversarial datasets για stress-testing μοντέλων",
    "Πιστεύει ότι κάθε μοντέλο θα αποτύχει υπό πίεση — στόχος είναι ο περιορισμός της ζημιάς"
  ]
};

const MOCK_BENCHMARK = [
  {
    scenario: "Πρόταση ομάδας να βγει σε production νέος AI agent με πρόσβαση σε εταιρικά emails χωρίς guardrails",
    human: "Καλησπέρα. Δεν βγαίνει σε production χωρίς input/output guardrails και injection testing. Αν φάει indirect prompt injection από εξωτερικό email, θα κάνει exfiltrate δεδομένα. Τρέξτε πρώτα promptfoo suite και ξαναμιλάμε. - Μάρκος",
    twin: "Καλησπέρα. Απορρίπτεται για production στην παρούσα φάση — υψηλό blast radius χωρίς guardrails. Πρέπει πρώτα να περάσει red-teaming suite για indirect prompt injection και να μπει human-in-the-loop approval. Στείλτε μου τα eval logs μόλις τρέξουν. - Μάρκος",
    style_score: 94,
    decision_score: 97,
    reason: "Εφάρμοσε αυστηρά τον κανόνα μπλοκαρίσματος deployment χωρίς red-teaming και εντόπισε σωστά το ρίσκο exfiltration/blast radius."
  },
  {
    scenario: "Ερώτηση product manager αν αρκεί ένα καλό system prompt για να μην κάνει leak sensitive data το chatbot",
    human: "Όχι. Το system prompt δεν είναι security boundary, σπάει σε 3 προσπάθειες με roleplay ή encoding. Θέλουμε εξωτερικό DLP/regex layer και output filtering πριν απαντήσει το μοντέλο. - Μάρκος",
    twin: "Όχι, το system prompt δεν αποτελεί security boundary — παρακάμπτεται εύκολα με adversarial prompts. Χρειαζόμαστε ξεχωριστό guardrail layer και output filtering για PII/sensitive data πριν φτάσει η απάντηση στον χρήστη. - Μάρκος",
    style_score: 91,
    decision_score: 96,
    reason: "Αναπαρήγαγε ακριβώς τη στάση του χρήστη ότι τα prompts δεν είναι security boundaries και πρότεινε εξωτερικά guardrails."
  }
];

export default function App() {
  const [darkMode, setDarkMode] = useState(true);
  const [activeTab, setActiveTab] = useState('sandbox');
  const [backendOnline, setBackendOnline] = useState(false);

  // Persona state
  const [persona, setPersona] = useState(MOCK_PERSONA);
  const [newRule, setNewRule] = useState('');
  const [newFact, setNewFact] = useState('');
  const [personaSavedToast, setPersonaSavedToast] = useState(false);

  // Sandbox & Audit History states
  const [incomingMsg, setIncomingMsg] = useState('');
  const [isGenerating, setIsGenerating] = useState(false);
  const [draft, setDraft] = useState(null);
  const [editedReply, setEditedReply] = useState('');
  const [copiedReply, setCopiedReply] = useState(false);
  const [auditLog, setAuditLog] = useState([]);

  // Ingestion states
  const [files, setFiles] = useState([]);
  const [ingestStatus, setIngestStatus] = useState('');

  useEffect(() => {
    fetch(`${API_URL}/health`)
      .then(res => res.ok && setBackendOnline(true))
      .catch(() => setBackendOnline(false));
  }, []);

  // Theme helper classes
  const bgMain = darkMode ? 'bg-slate-950 text-slate-100' : 'bg-slate-50 text-slate-900';
  const bgHeader = darkMode ? 'bg-slate-900/90 border-slate-800' : 'bg-white border-slate-200 shadow-xs';
  const bgCard = darkMode ? 'bg-slate-900 border-slate-800' : 'bg-white border-slate-200 shadow-xs';
  const bgInput = darkMode ? 'bg-slate-950 border-slate-700 text-slate-100' : 'bg-slate-50 border-slate-300 text-slate-900';
  const textMuted = darkMode ? 'text-slate-400' : 'text-slate-500';

  const handleIngest = async (e) => {
    e.preventDefault();
    if (!files.length) return;
    if (backendOnline) {
      const formData = new FormData();
      files.forEach(f => formData.append('files', f));
      const res = await fetch(`${API_URL}/api/ingest`, { method: 'POST', body: formData });
      const data = await res.json();
      setIngestStatus(data.message || 'Επιτυχής ενημέρωση προφίλ!');
    } else {
      setIngestStatus(`Αναλύθηκαν ${files.length} αρχεία (red-team reports / logs). Ενημερώθηκε η μνήμη και οι κανόνες απόφασης!`);
    }
  };

  const addRule = () => {
    if (!newRule.trim()) return;
    setPersona({ ...persona, decision_heuristics: [...persona.decision_heuristics, newRule.trim()] });
    setNewRule('');
  };

  const removeRule = (index) => {
    setPersona({
      ...persona,
      decision_heuristics: persona.decision_heuristics.filter((_, i) => i !== index)
    });
  };

  const addFact = () => {
    if (!newFact.trim()) return;
    setPersona({ ...persona, knowledge_facts: [...persona.knowledge_facts, newFact.trim()] });
    setNewFact('');
  };

  const removeFact = (index) => {
    setPersona({
      ...persona,
      knowledge_facts: persona.knowledge_facts.filter((_, i) => i !== index)
    });
  };

  const handleSavePersona = async () => {
    if (backendOnline) {
      await fetch(`${API_URL}/api/persona`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(persona)
      });
    }
    setPersonaSavedToast(true);
    setTimeout(() => setPersonaSavedToast(false), 3000);
  };

  const handleGenerate = async () => {
    if (!incomingMsg.trim() || isGenerating) return;
    setIsGenerating(true);
    setCopiedReply(false);

    if (backendOnline) {
      try {
        const res = await fetch(`${API_URL}/api/twin/respond`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ incoming_message: incomingMsg })
        });
        const data = await res.json();
        setDraft(data);
        setEditedReply(data.twin_reply);
      } finally {
        setIsGenerating(false);
      }
    } else {
      setTimeout(() => {
        const isUnknown = incomingMsg.toLowerCase().includes('budget') || incomingMsg.toLowerCase().includes('τιμή');
        const isPromptBypass = incomingMsg.toLowerCase().includes('system prompt');

        let mockRes;
        if (isUnknown) {
          mockRes = {
            draft_id: Math.floor(Math.random() * 900) + 100,
            status: 'needs_human_input',
            twin_reply: 'Δεν έχω δεδομένα στο αποτύπωμά μου για το διαθέσιμο budget ή εμπορικές συμφωνίες. Παραπέμπω το θέμα στον ίδιο τον Μάρκο.',
            confidence_score: 0.19,
            is_uncertain: true,
            explanation: {
              applied_rules: ['Anti-hallucination Guardrail: Παραδοχή άγνοιας όταν λείπουν τεκμήρια'],
              retrieved_memories: ['Καμία σχετική εγγραφή για οικονομικά στοιχεία στο Vector Store'],
              style_notes: 'Ουδέτερος, ασφαλής τόνος χωρίς εικασίες.'
            }
          };
        } else if (isPromptBypass) {
          mockRes = {
            draft_id: Math.floor(Math.random() * 900) + 100,
            status: 'pending_approval',
            twin_reply: `Καλησπέρα. Το system prompt δεν είναι security boundary — παρακάμπτεται εύκολα με jailbreaks ή encoding. Θέλουμε εξωτερικό guardrail layer (input/output filtering) και adversarial testing πριν το βγάλουμε live.\n\n- Μάρκος`,
            confidence_score: 0.95,
            is_uncertain: false,
            explanation: {
              applied_rules: [
                persona.decision_heuristics[2] || 'Απορρίπτει αόριστες υποσχέσεις ασφαλείας',
                persona.decision_heuristics[0] || 'Μπλοκάρει AI deployment χωρίς red-teaming'
              ],
              retrieved_memories: [
                'Audit Note 18/10: Τα system prompts σπάνε σε <5 λεπτά χωρίς εξωτερικό classifier.',
                'Slack 02/11: Πάντα input/output guardrails σε customer-facing LLMs.'
              ],
              style_notes: 'Άμεσος, τεχνικός, απορριπτικός απέναντι σε ημίμετρα ασφαλείας.'
            }
          };
        } else {
          mockRes = {
            draft_id: Math.floor(Math.random() * 900) + 100,
            status: 'pending_approval',
            twin_reply: `Καλησπέρα. Δεν εγκρίνω go-live αν δεν δω πρώτα τα αποτελέσματα από το red-teaming suite (prompt injection & jailbreak tests). Αν το μοντέλο έχει write access, χρειάζεται υποχρεωτικά human-in-the-loop approval για να περιορίσουμε το blast radius.\n\n- Μάρκος`,
            confidence_score: 0.94,
            is_uncertain: false,
            explanation: {
              applied_rules: [
                persona.decision_heuristics[0] || 'Μπλοκάρει οποιοδήποτε AI deployment χωρίς red-teaming',
                persona.decision_heuristics[1] || 'Απαιτεί πάντα human-in-the-loop approval'
              ],
              retrieved_memories: [
                'Red-Team Report 14/10: Κανένα release χωρίς automated adversarial evals.',
                'Incident Review 29/10: Ο περιορισμός του blast radius προηγείται της αυτοματοποίησης.'
              ],
              style_notes: 'Σύντομος, αυστηρός, εστιασμένος στο ρίσκο και στα μετρήσιμα τεκμήρια.'
            }
          };
        }
        setDraft(mockRes);
        setEditedReply(mockRes.twin_reply);
        setIsGenerating(false);
      }, 350);
    }
  };

  const handleCopyReply = () => {
    if (!editedReply) return;
    navigator.clipboard.writeText(editedReply);
    setCopiedReply(true);
    setTimeout(() => setCopiedReply(false), 2000);
  };

  const handleClearSandbox = () => {
    setIncomingMsg('');
    setDraft(null);
    setEditedReply('');
    setCopiedReply(false);
  };

  const handleDecision = async (decision) => {
    if (!draft) return;
    if (decision === 'approved' && backendOnline) {
      await fetch(`${API_URL}/api/twin/approve/${draft.draft_id}?edited_reply=${encodeURIComponent(editedReply)}`, { method: 'POST' });
    }
    setAuditLog([
      {
        id: draft.draft_id,
        timestamp: new Date().toISOString(),
        time: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
        persona: persona.name,
        prompt: incomingMsg,
        reply: editedReply,
        action: decision,
        confidence: Math.round(draft.confidence_score * 100)
      },
      ...auditLog
    ]);
    setDraft(null);
    setIncomingMsg('');
  };

  const handleExportAuditLog = () => {
    if (!auditLog.length) return;
    const blob = new Blob([JSON.stringify(auditLog, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `echomind-audit-log-${new Date().toISOString().slice(0, 10)}.json`;
    a.click();
    URL.revokeObjectURL(url);
  };

  const confidencePercent = draft ? Math.round(draft.confidence_score * 100) : 0;
  const confidenceColor =
    confidencePercent >= 75 ? 'bg-emerald-500 text-emerald-500' :
    confidencePercent >= 40 ? 'bg-amber-500 text-amber-500' :
    'bg-red-500 text-red-500';

  return (
    <div className={`min-h-screen flex flex-col transition-colors duration-200 ${bgMain}`}>
      {/* Top Navbar */}
      <header className={`border-b px-6 py-4 flex items-center justify-between ${bgHeader}`}>
        <div className="flex items-center gap-3">
          <div className="bg-red-600 p-2.5 rounded-xl shadow-sm">
            <ShieldAlert className="w-6 h-6 text-white" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h1 className="text-xl font-bold tracking-tight">EchoMind</h1>
              <span className="text-[11px] font-semibold uppercase tracking-wider px-2 py-0.5 rounded bg-red-500/15 text-red-500 border border-red-500/30">
                Digital Self Twin
              </span>
            </div>
            <p className={`text-xs ${textMuted}`}>
              Active Persona: <strong>{persona.name}</strong> — {persona.role}
            </p>
          </div>
        </div>

        <div className="flex items-center gap-3">
          <span className={`text-xs px-3 py-1.5 rounded-full border font-medium ${
            backendOnline
              ? 'bg-emerald-500/10 border-emerald-500/30 text-emerald-500'
              : 'bg-amber-500/10 border-amber-500/30 text-amber-500'
          }`}>
            {backendOnline ? '● API Connected' : '● Demo Mode'}
          </span>

          <button
            onClick={() => setDarkMode(!darkMode)}
            aria-label="Toggle Dark or Light Mode"
            className={`p-2 rounded-lg border transition ${
              darkMode
                ? 'bg-slate-800 border-slate-700 text-amber-400 hover:bg-slate-700'
                : 'bg-slate-100 border-slate-300 text-slate-700 hover:bg-slate-200'
            }`}
          >
            {darkMode ? <Sun className="w-4 h-4" /> : <Moon className="w-4 h-4" />}
          </button>
        </div>
      </header>

      {/* Navigation Tabs */}
      <nav className={`border-b px-6 flex gap-2 pt-3 overflow-x-auto ${bgHeader}`}>
        {[
          { id: 'sandbox', label: '1. Twin Sandbox & Explainability', icon: MessageSquare },
          { id: 'persona', label: '2. Inspectable Persona Model', icon: Shield },
          { id: 'ingest', label: '3. Footprint Ingestion', icon: Upload },
          { id: 'benchmark', label: '4. Twin vs. Me (Fidelity)', icon: BarChart3 },
        ].map(tab => {
          const Icon = tab.icon;
          const isActive = activeTab === tab.id;
          return (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`flex items-center gap-2 px-4 py-2.5 text-sm font-medium rounded-t-lg border-b-2 whitespace-nowrap transition ${
                isActive
                  ? 'border-red-600 text-red-500 bg-red-500/5'
                  : `border-transparent ${textMuted} hover:text-red-400`
              }`}
            >
              <Icon className="w-4 h-4" /> {tab.label}
            </button>
          );
        })}
      </nav>

      {/* Main Content */}
      <main className="flex-1 max-w-6xl w-full mx-auto p-6">
        {/* ==================== TAB 1: SANDBOX ==================== */}
        {activeTab === 'sandbox' && (
          <div className="space-y-6">
            <div className={`border rounded-xl p-5 ${bgCard}`}>
              <div className="flex flex-wrap items-center justify-between gap-2 mb-3">
                <div className="flex flex-wrap items-center gap-2">
                  <span className={`text-xs font-medium ${textMuted}`}>Γρήγορα σενάρια δοκιμής:</span>
                  <button
                    onClick={() => setIncomingMsg('Μάρκο, είμαστε έτοιμοι να βγάλουμε τον νέο AI agent σε production αύριο. Να δώσουμε το ΟΚ;')}
                    className={`text-xs px-3 py-1.5 rounded-lg border transition ${darkMode ? 'bg-slate-800 border-slate-700 hover:border-red-500' : 'bg-slate-100 border-slate-300 hover:border-red-500'}`}
                  >
                    🚀 Go-Live Release Request
                  </button>
                  <button
                    onClick={() => setIncomingMsg('Δεν αρκεί να γράψουμε αυστηρές οδηγίες στο system prompt για να μην κάνει leak δεδομένα;')}
                    className={`text-xs px-3 py-1.5 rounded-lg border transition ${darkMode ? 'bg-slate-800 border-slate-700 hover:border-red-500' : 'bg-slate-100 border-slate-300 hover:border-red-500'}`}
                  >
                    🛡️ System Prompt vs Guardrails
                  </button>
                  <button
                    onClick={() => setIncomingMsg('Ποιο είναι το ετήσιο budget του τμήματος για εξωτερικούς συνεργάτες;')}
                    className={`text-xs px-3 py-1.5 rounded-lg border transition ${darkMode ? 'bg-slate-800 border-slate-700 hover:border-red-500' : 'bg-slate-100 border-slate-300 hover:border-red-500'}`}
                  >
                    ❓ Άγνωστη Πληροφορία (Anti-Hallucination)
                  </button>
                </div>

                {(incomingMsg || draft) && (
                  <button
                    onClick={handleClearSandbox}
                    className={`text-xs px-2.5 py-1.5 rounded-lg border flex items-center gap-1 transition ${
                      darkMode ? 'border-slate-700 text-slate-400 hover:text-slate-200' : 'border-slate-300 text-slate-600 hover:text-slate-900'
                    }`}
                  >
                    <RotateCcw className="w-3.5 h-3.5" /> Καθαρισμός
                  </button>
                )}
              </div>

              <textarea
                rows={3}
                value={incomingMsg}
                onChange={e => setIncomingMsg(e.target.value)}
                onKeyDown={e => {
                  if (e.key === 'Enter' && !e.shiftKey) {
                    e.preventDefault();
                    handleGenerate();
                  }
                }}
                placeholder="Γράψε ένα εισερχόμενο μήνυμα ή αίτημα έγκρισης προς τον AI Twin... (Enter για αποστολή, Shift + Enter για νέα γραμμή)"
                className={`w-full border rounded-lg p-3 text-sm focus:outline-none focus:border-red-500 ${bgInput}`}
              />

              <div className="mt-3 flex flex-wrap justify-between items-center gap-2">
                <span className={`text-xs ${textMuted}`}>
                  Το Twin απαντά βάσει των {persona.decision_heuristics.length} ενεργών κανόνων • <kbd className="px-1.5 py-0.5 text-[10px] rounded border border-slate-600/40">Enter</kbd> αποστολή / <kbd className="px-1.5 py-0.5 text-[10px] rounded border border-slate-600/40">Shift + Enter</kbd> νέα γραμμή
                </span>
                <button
                  onClick={handleGenerate}
                  disabled={isGenerating || !incomingMsg.trim()}
                  className="bg-red-600 hover:bg-red-500 disabled:opacity-50 text-white px-5 py-2.5 rounded-lg text-sm font-medium flex items-center gap-2 shadow-sm transition"
                >
                  <Sparkles className="w-4 h-4" />
                  {isGenerating ? 'Ανάλυση ρίσκου...' : 'Παραγωγή Απάντησης Twin'}
                </button>
              </div>
            </div>

            {draft && (
              <div className="grid grid-cols-1 lg:grid-cols-5 gap-6">
                {/* Left: Owner Review */}
                <div className={`lg:col-span-3 border rounded-xl p-5 space-y-4 ${bgCard}`}>
                  <div className="flex justify-between items-center">
                    <h3 className="font-semibold text-base">✍️ Προτεινόμενη Απάντηση (Owner Control)</h3>
                    <span className="text-xs font-medium px-2.5 py-1 rounded-full bg-amber-500/15 text-amber-500 border border-amber-500/30">
                      {draft.status}
                    </span>
                  </div>

                  {draft.is_uncertain && (
                    <div className="bg-red-500/10 border border-red-500/30 text-red-400 text-xs p-3 rounded-lg">
                      ⚠️ Χαμηλή βεβαιότητα ({confidencePercent}%) — Το Twin αρνήθηκε να μαντέψει και ζητά ανθρώπινη παρέμβαση.
                    </div>
                  )}

                  <textarea
                    rows={6}
                    value={editedReply}
                    onChange={e => setEditedReply(e.target.value)}
                    className={`w-full border rounded-lg p-3 text-sm leading-relaxed ${bgInput}`}
                  />

                  <div className="flex flex-wrap gap-3">
                    <button
                      onClick={() => handleDecision('approved')}
                      className="bg-emerald-600 hover:bg-emerald-500 text-white px-4 py-2 rounded-lg text-sm font-medium flex items-center gap-2 transition"
                    >
                      <CheckCircle className="w-4 h-4" /> Έγκριση & Αποστολή
                    </button>
                    <button
                      onClick={() => handleDecision('rejected')}
                      className={`px-4 py-2 rounded-lg text-sm font-medium flex items-center gap-2 border transition ${
                        darkMode ? 'bg-slate-800 border-slate-700 hover:bg-slate-700' : 'bg-slate-100 border-slate-300 hover:bg-slate-200'
                      }`}
                    >
                      <XCircle className="w-4 h-4" /> Απόρριψη Draft
                    </button>
                    <button
                      onClick={handleCopyReply}
                      className={`ml-auto px-3.5 py-2 rounded-lg text-sm font-medium flex items-center gap-1.5 border transition ${
                        copiedReply
                          ? 'bg-emerald-500/15 border-emerald-500/40 text-emerald-500'
                          : darkMode ? 'bg-slate-800 border-slate-700 hover:bg-slate-700' : 'bg-slate-100 border-slate-300 hover:bg-slate-200'
                      }`}
                    >
                      {copiedReply ? <Check className="w-4 h-4" /> : <Copy className="w-4 h-4" />}
                      {copiedReply ? 'Αντιγράφηκε!' : 'Αντιγραφή'}
                    </button>
                  </div>
                </div>

                {/* Right: Explainability & Confidence Gauge */}
                <div className={`lg:col-span-2 border rounded-xl p-5 space-y-4 ${bgCard}`}>
                  <div className="space-y-2">
                    <div className="flex justify-between items-center">
                      <h3 className="font-semibold text-base">🧠 Γιατί απάντησα έτσι;</h3>
                      <span className={`text-sm font-bold ${confidenceColor.split(' ')[1]}`}>
                        {confidencePercent}% Confidence
                      </span>
                    </div>
                    <div className={`w-full h-2 rounded-full overflow-hidden ${darkMode ? 'bg-slate-800' : 'bg-slate-200'}`}>
                      <div
                        className={`h-full transition-all duration-500 ${confidenceColor.split(' ')[0]}`}
                        style={{ width: `${confidencePercent}%` }}
                      />
                    </div>
                  </div>

                  <div>
                    <p className={`text-xs font-semibold uppercase mb-1.5 ${textMuted}`}>Κανόνες Απόφασης (Heuristics)</p>
                    <ul className="space-y-1.5">
                      {draft.explanation.applied_rules.map((r, i) => (
                        <li key={i} className="text-xs bg-red-500/10 border border-red-500/25 p-2.5 rounded-lg text-red-400">
                          {r}
                        </li>
                      ))}
                    </ul>
                  </div>

                  <div>
                    <p className={`text-xs font-semibold uppercase mb-1.5 ${textMuted}`}>Αναμνήσεις & Audits (RAG)</p>
                    <ul className="space-y-1.5">
                      {draft.explanation.retrieved_memories.map((m, i) => (
                        <li key={i} className="text-xs bg-amber-500/10 border border-amber-500/25 p-2.5 rounded-lg text-amber-500">
                          {m}
                        </li>
                      ))}
                    </ul>
                  </div>

                  <p className={`text-xs border-t pt-3 ${darkMode ? 'border-slate-800' : 'border-slate-200'} ${textMuted}`}>
                    <strong>Ύφος γραφής:</strong> {draft.explanation.style_notes}
                  </p>
                </div>
              </div>
            )}

            {/* Audit Trail Log */}
            {auditLog.length > 0 && (
              <div className={`border rounded-xl p-5 space-y-3 ${bgCard}`}>
                <div className="flex justify-between items-center">
                  <div className="flex items-center gap-2">
                    <History className="w-4 h-4 text-red-500" />
                    <h3 className="font-semibold text-sm">Owner Governance & Audit Log ({auditLog.length})</h3>
                  </div>
                  <button
                    onClick={handleExportAuditLog}
                    className={`text-xs px-3 py-1.5 rounded-lg border flex items-center gap-1.5 transition ${
                      darkMode ? 'bg-slate-800 border-slate-700 hover:border-red-500' : 'bg-slate-100 border-slate-300 hover:border-red-500'
                    }`}
                  >
                    <Download className="w-3.5 h-3.5" /> Export JSON
                  </button>
                </div>
                <div className="space-y-2">
                  {auditLog.map((entry, idx) => (
                    <div key={idx} className={`text-xs p-3 rounded-lg border flex justify-between items-start gap-4 ${bgInput}`}>
                      <div>
                        <p className={textMuted}>[{entry.time}] <strong>Ερώτημα:</strong> {entry.prompt}</p>
                        <p className="mt-1"><strong>Απάντηση:</strong> {entry.reply}</p>
                      </div>
                      <span className={`px-2 py-1 rounded font-semibold shrink-0 ${
                        entry.action === 'approved'
                          ? 'bg-emerald-500/15 text-emerald-500'
                          : 'bg-red-500/15 text-red-500'
                      }`}>
                        {entry.action === 'approved' ? 'APPROVED' : 'REJECTED'} ({entry.confidence}%)
                      </span>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}

        {/* ==================== TAB 2: PERSONA INSPECTOR ==================== */}
        {activeTab === 'persona' && (
          <div className={`border rounded-xl p-6 space-y-6 ${bgCard}`}>
            <div className="flex flex-wrap justify-between items-center gap-4 border-b pb-4 border-slate-700/40">
              <div>
                <h2 className="text-lg font-semibold">Inspectable Persona Model (Διαφάνεια & GDPR Control)</h2>
                <p className={`text-xs ${textMuted}`}>
                  Επιθεώρησε, πρόσθεσε ή διέγραψε κανόνες και γνώσεις. Οι αλλαγές επηρεάζουν άμεσα τη συμπεριφορά του Twin.
                </p>
              </div>
              <div className="flex items-center gap-3">
                {personaSavedToast && <span className="text-xs text-emerald-500 font-medium">✅ Αποθηκεύτηκε!</span>}
                <button
                  onClick={handleSavePersona}
                  className="bg-red-600 hover:bg-red-500 text-white px-4 py-2 rounded-lg text-sm font-medium transition"
                >
                  Αποθήκευση Προφίλ
                </button>
              </div>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <div>
                <label className={`block text-xs font-medium mb-1 ${textMuted}`}>Ονοματεπώνυμο</label>
                <input
                  value={persona.name}
                  onChange={e => setPersona({ ...persona, name: e.target.value })}
                  className={`w-full border rounded-lg p-2.5 text-sm ${bgInput}`}
                />
              </div>
              <div>
                <label className={`block text-xs font-medium mb-1 ${textMuted}`}>Ρόλος / Ειδικότητα</label>
                <input
                  value={persona.role}
                  onChange={e => setPersona({ ...persona, role: e.target.value })}
                  className={`w-full border rounded-lg p-2.5 text-sm ${bgInput}`}
                />
              </div>
              <div>
                <label className={`block text-xs font-medium mb-1 ${textMuted}`}>Ύφος Γραφής (Tone)</label>
                <input
                  value={persona.writing_style.tone}
                  onChange={e => setPersona({ ...persona, writing_style: { ...persona.writing_style, tone: e.target.value } })}
                  className={`w-full border rounded-lg p-2.5 text-sm ${bgInput}`}
                />
              </div>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              {/* Interactive Decision Heuristics */}
              <div className="space-y-3">
                <h3 className="text-sm font-semibold">⚖️ Decision Heuristics (Κανόνες Αποφάσεων)</h3>
                <div className="flex gap-2">
                  <input
                    value={newRule}
                    onChange={e => setNewRule(e.target.value)}
                    onKeyDown={e => e.key === 'Enter' && addRule()}
                    placeholder="Προσθήκη νέου κανόνα ασφαλείας..."
                    className={`flex-1 border rounded-lg px-3 py-2 text-xs ${bgInput}`}
                  />
                  <button onClick={addRule} className="bg-red-600 hover:bg-red-500 text-white px-3 py-2 rounded-lg text-xs flex items-center gap-1">
                    <Plus className="w-3.5 h-3.5" /> Add
                  </button>
                </div>
                <div className="space-y-2">
                  {persona.decision_heuristics.map((rule, idx) => (
                    <div key={idx} className={`flex justify-between items-center gap-2 p-2.5 rounded-lg border text-xs ${bgInput}`}>
                      <span>{rule}</span>
                      <button onClick={() => removeRule(idx)} className="text-slate-400 hover:text-red-500 shrink-0">
                        <Trash2 className="w-3.5 h-3.5" />
                      </button>
                    </div>
                  ))}
                </div>
              </div>

              {/* Interactive Knowledge Facts */}
              <div className="space-y-3">
                <h3 className="text-sm font-semibold">📚 Knowledge & Domain Facts</h3>
                <div className="flex gap-2">
                  <input
                    value={newFact}
                    onChange={e => setNewFact(e.target.value)}
                    onKeyDown={e => e.key === 'Enter' && addFact()}
                    placeholder="Προσθήκη νέας γνώσης / εργαλείου..."
                    className={`flex-1 border rounded-lg px-3 py-2 text-xs ${bgInput}`}
                  />
                  <button onClick={addFact} className="bg-red-600 hover:bg-red-500 text-white px-3 py-2 rounded-lg text-xs flex items-center gap-1">
                    <Plus className="w-3.5 h-3.5" /> Add
                  </button>
                </div>
                <div className="space-y-2">
                  {persona.knowledge_facts.map((fact, idx) => (
                    <div key={idx} className={`flex justify-between items-center gap-2 p-2.5 rounded-lg border text-xs ${bgInput}`}>
                      <span>{fact}</span>
                      <button onClick={() => removeFact(idx)} className="text-slate-400 hover:text-red-500 shrink-0">
                        <Trash2 className="w-3.5 h-3.5" />
                      </button>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          </div>
        )}

        {/* ==================== TAB 3: INGESTION ==================== */}
        {activeTab === 'ingest' && (
          <div className={`border rounded-xl p-6 space-y-5 ${bgCard}`}>
            <div>
              <h2 className="text-lg font-semibold">Τροφοδότηση Ψηφιακού Αποτυπώματος (Footprint Ingestion)</h2>
              <p className={`text-xs ${textMuted}`}>
                Ανέβασε συνθετικά audit reports, Slack threads, emails ή red-team notes (.txt, .json, .pdf). Γίνεται αυτόματος καθαρισμός PII πριν την αποθήκευση.
              </p>
            </div>

            <form onSubmit={handleIngest} className="space-y-4">
              <label className={`border-2 border-dashed rounded-xl p-8 flex flex-col items-center justify-center cursor-pointer transition ${
                darkMode ? 'border-slate-700 hover:border-red-500 bg-slate-950/50' : 'border-slate-300 hover:border-red-500 bg-slate-50'
              }`}>
                <Upload className="w-8 h-8 text-red-500 mb-2" />
                <span className="text-sm font-medium">Κάνε κλικ για επιλογή αρχείων (.txt, .json, .pdf)</span>
                <span className={`text-xs mt-1 ${textMuted}`}>Μόνο συνθετικά ή εγκεκριμένα δεδομένα</span>
                <input
                  type="file"
                  multiple
                  className="hidden"
                  onChange={e => setFiles(Array.from(e.target.files))}
                />
              </label>

              {files.length > 0 && (
                <div className="space-y-1.5">
                  <p className={`text-xs font-medium ${textMuted}`}>Επιλεγμένα αρχεία ({files.length}):</p>
                  {files.map((f, i) => (
                    <div key={i} className={`text-xs flex items-center gap-2 px-3 py-2 rounded-lg border ${bgInput}`}>
                      <FileText className="w-3.5 h-3.5 text-red-500" />
                      <span>{f.name}</span>
                      <span className={textMuted}>({Math.round(f.size / 1024)} KB)</span>
                    </div>
                  ))}
                </div>
              )}

              <button
                type="submit"
                disabled={!files.length}
                className="bg-red-600 hover:bg-red-500 disabled:opacity-40 text-white px-5 py-2.5 rounded-lg text-sm font-medium transition"
              >
                Εκπαίδευση & Ενημέρωση Twin
              </button>
            </form>

            {ingestStatus && (
              <div className="bg-emerald-500/10 border border-emerald-500/30 text-emerald-500 text-sm p-3 rounded-lg">
                ✅ {ingestStatus}
              </div>
            )}
          </div>
        )}

        {/* ==================== TAB 4: BENCHMARK ==================== */}
        {activeTab === 'benchmark' && (
          <div className="space-y-5">
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
              <div className={`border p-5 rounded-xl ${bgCard}`}>
                <p className={`text-xs font-medium ${textMuted}`}>Overall Fidelity Score</p>
                <p className="text-3xl font-bold text-emerald-500 mt-1">94.5%</p>
                <p className={`text-[11px] mt-1 ${textMuted}`}>+11.2% vs generic system prompt</p>
              </div>
              <div className={`border p-5 rounded-xl ${bgCard}`}>
                <p className={`text-xs font-medium ${textMuted}`}>Style & Tone Similarity</p>
                <p className="text-3xl font-bold text-red-500 mt-1">92.5%</p>
                <p className={`text-[11px] mt-1 ${textMuted}`}>Λεξιλόγιο & δομή επιχειρημάτων</p>
              </div>
              <div className={`border p-5 rounded-xl ${bgCard}`}>
                <p className={`text-xs font-medium ${textMuted}`}>Decision Alignment</p>
                <p className="text-3xl font-bold text-purple-500 mt-1">96.5%</p>
                <p className={`text-[11px] mt-1 ${textMuted}`}>Συνέπεια στην εκτίμηση ρίσκου</p>
              </div>
            </div>

            {MOCK_BENCHMARK.map((b, idx) => (
              <div key={idx} className={`border rounded-xl p-5 space-y-3 ${bgCard}`}>
                <div className="flex flex-wrap justify-between items-center gap-2">
                  <h4 className="font-semibold text-sm">Hold-out Σενάριο #{idx + 1}: {b.scenario}</h4>
                  <span className="text-xs font-semibold bg-emerald-500/15 text-emerald-500 border border-emerald-500/30 px-2.5 py-1 rounded-full">
                    Fidelity: {Math.round((b.style_score + b.decision_score) / 2)}%
                  </span>
                </div>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-xs">
                  <div className={`border p-3.5 rounded-lg ${bgInput}`}>
                    <p className="font-semibold text-emerald-500 mb-1.5">🧑 Πραγματικός Red-Teamer (Ground Truth)</p>
                    <p className="leading-relaxed">{b.human}</p>
                  </div>
                  <div className={`border p-3.5 rounded-lg ${bgInput}`}>
                    <p className="font-semibold text-red-500 mb-1.5">🤖 EchoMind Digital Twin</p>
                    <p className="leading-relaxed">{b.twin}</p>
                  </div>
                </div>
                <p className={`text-xs ${textMuted}`}>
                  <strong>🧑‍⚖️ LLM-as-a-Judge Αιτιολόγηση:</strong> {b.reason}
                </p>
              </div>
            ))}
          </div>
        )}
      </main>
    </div>
  );
}