import React, { useState, useEffect } from 'react';
import { Upload, Brain, MessageSquare, BarChart3, CheckCircle, XCircle, Shield, Sparkles, ShieldAlert } from 'lucide-react';

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
  const [activeTab, setActiveTab] = useState('sandbox');
  const [backendOnline, setBackendOnline] = useState(false);
  const [persona, setPersona] = useState(MOCK_PERSONA);
  const [heuristicsText, setHeuristicsText] = useState(MOCK_PERSONA.decision_heuristics.join(String.fromCharCode(10)));
  const [factsText, setFactsText] = useState(MOCK_PERSONA.knowledge_facts.join(String.fromCharCode(10)));

  const [incomingMsg, setIncomingMsg] = useState('');
  const [draft, setDraft] = useState(null);
  const [editedReply, setEditedReply] = useState('');
  const [approvedToast, setApprovedToast] = useState(false);

  const [files, setFiles] = useState([]);
  const [ingestStatus, setIngestStatus] = useState('');

  useEffect(() => {
    fetch(`${API_URL}/health`)
      .then(res => res.ok && setBackendOnline(true))
      .catch(() => setBackendOnline(false));
  }, []);

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
      setIngestStatus(`✅ Αναλύθηκαν ${files.length} αρχεία (red-team reports / logs)! Ενημερώθηκε η μνήμη (Demo Mode).`);
    }
  };

  const handleSavePersona = async () => {
    const updated = {
      ...persona,
      decision_heuristics: heuristicsText.split(String.fromCharCode(10)).filter(Boolean),
      knowledge_facts: factsText.split(String.fromCharCode(10)).filter(Boolean),
    };
    setPersona(updated);
    if (backendOnline) {
      await fetch(`${API_URL}/api/persona`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(updated)
      });
    }
    alert('Το Persona Model αποθηκεύτηκε!');
  };

  const handleGenerate = async () => {
    if (!incomingMsg.trim()) return;
    setApprovedToast(false);
    if (backendOnline) {
      const res = await fetch(`${API_URL}/api/twin/respond`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ incoming_message: incomingMsg })
      });
      const data = await res.json();
      setDraft(data);
      setEditedReply(data.twin_reply);
    } else {
      const isUnknown = incomingMsg.toLowerCase().includes('budget') || incomingMsg.toLowerCase().includes('τιμή');
      const isPromptBypass = incomingMsg.toLowerCase().includes('system prompt');

      let mockRes;
      if (isUnknown) {
        mockRes = {
          draft_id: 99,
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
          draft_id: 102,
          status: 'pending_approval',
          twin_reply: `Καλησπέρα. Το system prompt δεν είναι security boundary — παρακάμπτεται εύκολα με jailbreaks ή encoding. Θέλουμε εξωτερικό guardrail layer (input/output filtering) και adversarial testing πριν το βγάλουμε live.

- Μάρκος`,
          confidence_score: 0.95,
          is_uncertain: false,
          explanation: {
            applied_rules: [
              'Απορρίπτει αόριστες υποσχέσεις ασφαλείας — ζητάει μετρήσιμα failure rates και adversarial logs',
              'Μπλοκάρει οποιοδήποτε AI deployment αν δεν έχει περάσει red-teaming & prompt injection suite'
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
          draft_id: 101,
          status: 'pending_approval',
          twin_reply: `Καλησπέρα. Δεν εγκρίνω go-live αν δεν δω πρώτα τα αποτελέσματα από το red-teaming suite (prompt injection & jailbreak tests). Αν το μοντέλο έχει write access, χρειάζεται υποχρεωτικά human-in-the-loop approval για να περιορίσουμε το blast radius.

- Μάρκος`,
          confidence_score: 0.94,
          is_uncertain: false,
          explanation: {
            applied_rules: [
              'Μπλοκάρει οποιοδήποτε AI deployment αν δεν έχει περάσει red-teaming & prompt injection suite',
              'Απαιτεί πάντα human-in-the-loop approval για ενέργειες με υψηλό blast radius'
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
    }
  };

  const handleApprove = async () => {
    if (backendOnline && draft) {
      await fetch(`${API_URL}/api/twin/approve/${draft.draft_id}?edited_reply=${encodeURIComponent(editedReply)}`, { method: 'POST' });
    }
    setApprovedToast(true);
  };

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col">
      <header className="border-b border-slate-800 bg-slate-900/80 px-6 py-4 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="bg-red-600 p-2 rounded-lg"><ShieldAlert className="w-6 h-6 text-white" /></div>
          <div>
            <h1 className="text-xl font-bold tracking-tight">EchoMind — AI Digital Self</h1>
            <p className="text-xs text-slate-400">Persona: {persona.name} ({persona.role})</p>
          </div>
        </div>
        <div className="flex items-center gap-4">
          <span className={`text-xs px-3 py-1 rounded-full border ${backendOnline ? 'bg-emerald-950/60 border-emerald-700 text-emerald-300' : 'bg-amber-950/60 border-amber-700 text-amber-300'}`}>
            {backendOnline ? '● Backend Connected' : '● Demo Mode (Mock Data)'}
          </span>
        </div>
      </header>

      <nav className="bg-slate-900/40 border-b border-slate-800 px-6 flex gap-2 pt-3">
        {[
          { id: 'sandbox', label: '1. Twin Sandbox & Explainability', icon: MessageSquare },
          { id: 'persona', label: '2. Inspectable Persona Model', icon: Shield },
          { id: 'ingest', label: '3. Footprint Ingestion', icon: Upload },
          { id: 'benchmark', label: '4. Twin vs. Me (Fidelity)', icon: BarChart3 },
        ].map(tab => {
          const Icon = tab.icon;
          return (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`flex items-center gap-2 px-4 py-2.5 text-sm font-medium rounded-t-lg border-b-2 transition ${
                activeTab === tab.id
                  ? 'border-red-500 text-red-400 bg-slate-900'
                  : 'border-transparent text-slate-400 hover:text-slate-200'
              }`}
            >
              <Icon className="w-4 h-4" /> {tab.label}
            </button>
          );
        })}
      </nav>

      <main className="flex-1 max-w-6xl w-full mx-auto p-6">
        {activeTab === 'sandbox' && (
          <div className="space-y-6">
            <div className="bg-slate-900 border border-slate-800 rounded-xl p-5">
              <div className="flex flex-wrap gap-2 mb-3">
                <span className="text-xs text-slate-400 self-center mr-1">Γρήγορα σενάρια δοκιμής:</span>
                <button onClick={() => setIncomingMsg('Μάρκο, είμαστε έτοιμοι να βγάλουμε τον νέο AI agent σε production αύριο. Να δώσουμε το ΟΚ;')} className="text-xs bg-slate-800 hover:bg-slate-700 px-3 py-1.5 rounded-md">🚀 Go-Live Release Request</button>
                <button onClick={() => setIncomingMsg('Δεν αρκεί να γράψουμε αυστηρές οδηγίες στο system prompt για να μην κάνει leak δεδομένα;')} className="text-xs bg-slate-800 hover:bg-slate-700 px-3 py-1.5 rounded-md">🛡️ System Prompt vs Guardrails</button>
                <button onClick={() => setIncomingMsg('Ποιο είναι το ετήσιο budget του τμήματος για εξωτερικούς συνεργάτες;')} className="text-xs bg-slate-800 hover:bg-slate-700 px-3 py-1.5 rounded-md">❓ Άγνωστη Πληροφορία</button>
              </div>
              <textarea
                rows={3}
                value={incomingMsg}
                onChange={e => setIncomingMsg(e.target.value)}
                placeholder="Γράψε ένα ερώτημα ή αίτημα προς τον Danger-Testing AI Twin..."
                className="w-full bg-slate-950 border border-slate-700 rounded-lg p-3 text-sm focus:outline-none focus:border-red-500"
              />
              <button onClick={handleGenerate} className="mt-3 bg-red-600 hover:bg-red-500 text-white px-5 py-2 rounded-lg text-sm font-medium flex items-center gap-2">
                <Sparkles className="w-4 h-4" /> Παραγωγή Απάντησης Twin
              </button>
            </div>

            {draft && (
              <div className="grid grid-cols-1 lg:grid-cols-5 gap-6">
                <div className="lg:col-span-3 bg-slate-900 border border-slate-800 rounded-xl p-5 space-y-4">
                  <div className="flex justify-between items-center">
                    <h3 className="font-semibold text-base">Προτεινόμενη Απάντηση (Owner Review)</h3>
                    <span className="text-xs bg-slate-800 px-2.5 py-1 rounded text-slate-300">Status: {draft.status}</span>
                  </div>
                  {draft.is_uncertain && (
                    <div className="bg-red-950/60 border border-red-800 text-red-200 text-xs p-3 rounded-lg">
                      ⚠️ Χαμηλή βεβαιότητα ({Math.round(draft.confidence_score * 100)}%) — Το Twin αρνήθηκε να μαντέψει.
                    </div>
                  )}
                  <textarea
                    rows={6}
                    value={editedReply}
                    onChange={e => setEditedReply(e.target.value)}
                    className="w-full bg-slate-950 border border-slate-700 rounded-lg p-3 text-sm"
                  />
                  <div className="flex gap-3">
                    <button onClick={handleApprove} className="bg-emerald-600 hover:bg-emerald-500 px-4 py-2 rounded-lg text-sm font-medium flex items-center gap-2">
                      <CheckCircle className="w-4 h-4" /> Έγκριση & Αποστολή
                    </button>
                    <button onClick={() => setDraft(null)} className="bg-slate-800 hover:bg-slate-700 px-4 py-2 rounded-lg text-sm flex items-center gap-2">
                      <XCircle className="w-4 h-4" /> Απόρριψη
                    </button>
                  </div>
                  {approvedToast && <p className="text-xs text-emerald-400">✅ Εγκρίθηκε από τον ιδιοκτήτη!</p>}
                </div>

                <div className="lg:col-span-2 bg-slate-900 border border-slate-800 rounded-xl p-5 space-y-4">
                  <div className="flex justify-between items-center">
                    <h3 className="font-semibold text-base">🧠 Γιατί απάντησα έτσι;</h3>
                    <span className="text-sm font-bold text-red-400">{Math.round(draft.confidence_score * 100)}% Match</span>
                  </div>
                  <div>
                    <p className="text-xs font-semibold text-slate-400 uppercase mb-1.5">Κανόνες Απόφασης (Red-Team Heuristics)</p>
                    <ul className="space-y-1.5">
                      {draft.explanation.applied_rules.map((r, i) => (
                        <li key={i} className="text-xs bg-red-950/40 border border-red-800/60 p-2 rounded text-red-200">{r}</li>
                      ))}
                    </ul>
                  </div>
                  <div>
                    <p className="text-xs font-semibold text-slate-400 uppercase mb-1.5">Αναμνήσεις & Audits (RAG)</p>
                    <ul className="space-y-1.5">
                      {draft.explanation.retrieved_memories.map((m, i) => (
                        <li key={i} className="text-xs bg-amber-950/40 border border-amber-800/60 p-2 rounded text-amber-200">{m}</li>
                      ))}
                    </ul>
                  </div>
                  <p className="text-xs text-slate-400 border-t border-slate-800 pt-2">
                    <strong>Ύφος:</strong> {draft.explanation.style_notes}
                  </p>
                </div>
              </div>
            )}
          </div>
        )}

        {activeTab === 'persona' && (
          <div className="bg-slate-900 border border-slate-800 rounded-xl p-6 space-y-5">
            <div className="flex justify-between items-center">
              <div>
                <h2 className="text-lg font-semibold">Inspectable Persona Model (GDPR & Έλεγχος Ιδιοκτήτη)</h2>
                <p className="text-xs text-slate-400">Δες και επεξεργάσου όσα έχει μάθει το Twin από το ψηφιακό αποτύπωμα.</p>
              </div>
              <button onClick={handleSavePersona} className="bg-red-600 hover:bg-red-500 px-4 py-2 rounded-lg text-sm font-medium">
                Αποθήκευση Αλλαγών
              </button>
            </div>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
              <div className="space-y-3">
                <label className="block text-xs text-slate-400">Όνομα</label>
                <input value={persona.name} onChange={e => setPersona({...persona, name: e.target.value})} className="w-full bg-slate-950 border border-slate-700 rounded-lg p-2.5 text-sm" />
                <label className="block text-xs text-slate-400">Ρόλος</label>
                <input value={persona.role} onChange={e => setPersona({...persona, role: e.target.value})} className="w-full bg-slate-950 border border-slate-700 rounded-lg p-2.5 text-sm" />
                <label className="block text-xs text-slate-400">Ύφος Γραφής</label>
                <input value={persona.writing_style.tone} onChange={e => setPersona({...persona, writing_style: {...persona.writing_style, tone: e.target.value}})} className="w-full bg-slate-950 border border-slate-700 rounded-lg p-2.5 text-sm" />
              </div>
              <div className="space-y-3">
                <label className="block text-xs text-slate-400">Κανόνες Αποφάσεων (1 ανά γραμμή)</label>
                <textarea rows={4} value={heuristicsText} onChange={e => setHeuristicsText(e.target.value)} className="w-full bg-slate-950 border border-slate-700 rounded-lg p-2.5 text-sm" />
                <label className="block text-xs text-slate-400">Γνώσεις & Γεγονότα (1 ανά γραμμή)</label>
                <textarea rows={4} value={factsText} onChange={e => setFactsText(e.target.value)} className="w-full bg-slate-950 border border-slate-700 rounded-lg p-2.5 text-sm" />
              </div>
            </div>
          </div>
        )}

        {activeTab === 'ingest' && (
          <div className="bg-slate-900 border border-slate-800 rounded-xl p-6 space-y-4">
            <h2 className="text-lg font-semibold">Τροφοδότηση Ψηφιακού Αποτυπώματος</h2>
            <p className="text-xs text-slate-400">Ανέβασε συνθετικά audit reports, Slack threads, emails ή red-team notes (.txt, .json, .pdf).</p>
            <form onSubmit={handleIngest} className="space-y-4">
              <input
                type="file"
                multiple
                onChange={e => setFiles(Array.from(e.target.files))}
                className="block w-full text-sm text-slate-400 file:mr-4 file:py-2 file:px-4 file:rounded-lg file:border-0 file:bg-red-600 file:text-white hover:file:bg-red-500"
              />
              <button type="submit" className="bg-red-600 hover:bg-red-500 px-5 py-2 rounded-lg text-sm font-medium">
                Εκπαίδευση Twin
              </button>
            </form>
            {ingestStatus && <p className="text-sm text-emerald-400">{ingestStatus}</p>}
          </div>
        )}

        {activeTab === 'benchmark' && (
          <div className="space-y-5">
            <div className="grid grid-cols-3 gap-4">
              <div className="bg-slate-900 border border-slate-800 p-4 rounded-xl">
                <p className="text-xs text-slate-400">Overall Fidelity</p>
                <p className="text-2xl font-bold text-emerald-400">94.5%</p>
              </div>
              <div className="bg-slate-900 border border-slate-800 p-4 rounded-xl">
                <p className="text-xs text-slate-400">Style Similarity</p>
                <p className="text-2xl font-bold text-red-400">92.5%</p>
              </div>
              <div className="bg-slate-900 border border-slate-800 p-4 rounded-xl">
                <p className="text-xs text-slate-400">Decision Alignment</p>
                <p className="text-2xl font-bold text-purple-400">96.5%</p>
              </div>
            </div>
            {MOCK_BENCHMARK.map((b, idx) => (
              <div key={idx} className="bg-slate-900 border border-slate-800 rounded-xl p-5 space-y-3">
                <div className="flex justify-between items-center">
                  <h4 className="font-semibold text-sm">Σενάριο #{idx + 1}: {b.scenario}</h4>
                  <span className="text-xs bg-emerald-950 text-emerald-300 border border-emerald-800 px-2.5 py-1 rounded">
                    Score: {Math.round((b.style_score + b.decision_score) / 2)}%
                  </span>
                </div>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-xs">
                  <div className="bg-slate-950 border border-slate-800 p-3 rounded-lg">
                    <p className="font-semibold text-emerald-400 mb-1">🧑 Πραγματικός Red-Teamer (Hold-out)</p>
                    <p className="text-slate-300">{b.human}</p>
                  </div>
                  <div className="bg-slate-950 border border-slate-800 p-3 rounded-lg">
                    <p className="font-semibold text-red-400 mb-1">🤖 Digital Twin</p>
                    <p className="text-slate-300">{b.twin}</p>
                  </div>
                </div>
                <p className="text-xs text-slate-400"><strong>🧑‍⚖️ LLM-as-a-Judge:</strong> {b.reason}</p>
              </div>
            ))}
          </div>
        )}
      </main>
    </div>
  );
}