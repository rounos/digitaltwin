import React, { useState, useEffect } from 'react';
import { Upload, Brain, MessageSquare, BarChart3, CheckCircle, XCircle, Shield, Sparkles, ShieldAlert } from 'lucide-react';

const API_URL = import.meta.env.VITE_BACKEND_URL || 'http://localhost:8000';

const MOCK_PERSONA = {
  persona_id: "default_user",
  name: "Δημήτριος Καρούνος",
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
  const [heuristicsText, setHeuristicsText] = useState(MOCK_PERSONA.decision_heuristics.join('\n'));
  const [factsText, setFactsText] = useState(MOCK_PERSONA.knowledge_facts.join('\n'));

  // Sandbox states
  const [incomingMsg, setIncomingMsg] = useState('');
  const [draft, setDraft] = useState(null);
  const [editedReply, setEditedReply] = useState('');
  const [approvedToast, setApprovedToast] = useState(false);

  // Ingestion states
  const [files, setFiles] = useState([]);
  const [ingestStatus, setIngestStatus] = useState('');

  useEffect(() => {
    fetch(`${API_URL}/health`) .then(res => res.ok && setBackendOnline(true)) .catch(() => setBackendOnline(false)); }, []);  const handleIngest = async (e) => { e.preventDefault(); if (!files.length) return; if (backendOnline) { const formData = new FormData(); files.forEach(f => formData.append('files', f)); const res = await fetch(`${API_URL}/api/ingest`, { method: 'POST', body: formData });
      const data = await res.json();
      setIngestStatus(data.message || 'Επιτυχής ενημέρωση προφίλ!');
    } else {
      setIngestStatus(`✅ Αναλύθηκαν ${files.length} αρχεία (red-team reports / logs)! Ενημερώθηκε η μνήμη (Demo Mode).`); } };  const handleSavePersona = async () => { const updated = { ...persona, decision_heuristics: heuristicsText.split('\n').filter(Boolean), knowledge_facts: factsText.split('\n').filter(Boolean), }; setPersona(updated); if (backendOnline) { await fetch(`${API_URL}/api/persona`, {
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
      const res = await fetch(`${API_URL}/api/twin/respond`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ incoming_message: incomingMsg }) }); const data = await res.json(); setDraft(data); setEditedReply(data.twin_reply); } else { const isUnknown = incomingMsg.toLowerCase().includes('budget') \vert{}\vert{} incomingMsg.toLowerCase().includes('τιμή'); const isPromptBypass = incomingMsg.toLowerCase().includes('system prompt');  let mockRes; if (isUnknown) { mockRes = { draft_id: 99, status: 'needs_human_input', twin_reply: 'Δεν έχω δεδομένα στο αποτύπωμά μου για το διαθέσιμο budget ή εμπορικές συμφωνίες. Παραπέμπω το θέμα στον ίδιο τον Μάρκο.', confidence_score: 0.19, is_uncertain: true, explanation: { applied_rules: ['Anti-hallucination Guardrail: Παραδοχή άγνοιας όταν λείπουν τεκμήρια'], retrieved_memories: ['Καμία σχετική εγγραφή για οικονομικά στοιχεία στο Vector Store'], style_notes: 'Ουδέτερος, ασφαλής τόνος χωρίς εικασίες.' } }; } else if (isPromptBypass) { mockRes = { draft_id: 102, status: 'pending_approval', twin_reply: 'Καλησπέρα. Το system prompt δεν είναι security boundary — παρακάμπτεται εύκολα με jailbreaks ή encoding. Θέλουμε εξωτερικό guardrail layer (input/output filtering) και adversarial testing πριν το βγάλουμε live.\n\n- Μάρκος', confidence_score: 0.95, is_uncertain: false, explanation: { applied_rules: [ 'Απορρίπτει αόριστες υποσχέσεις ασφαλείας — ζητάει μετρήσιμα failure rates και adversarial logs', 'Μπλοκάρει οποιοδήποτε AI deployment αν δεν έχει περάσει red-teaming & prompt injection suite' ], retrieved_memories: [ 'Audit Note 18/10: Τα system prompts σπάνε σε <5 λεπτά χωρίς εξωτερικό classifier.', 'Slack 02/11: Πάντα input/output guardrails σε customer-facing LLMs.' ], style_notes: 'Άμεσος, τεχνικός, απορριπτικός απέναντι σε ημίμετρα ασφαλείας.' } }; } else { mockRes = { draft_id: 101, status: 'pending_approval', twin_reply: 'Καλησπέρα. Δεν εγκρίνω go-live αν δεν δω πρώτα τα αποτελέσματα από το red-teaming suite (prompt injection & jailbreak tests). Αν το μοντέλο έχει write access, χρειάζεται υποχρεωτικά human-in-the-loop approval για να περιορίσουμε το blast radius.\n\n- Μάρκος', confidence_score: 0.94, is_uncertain: false, explanation: { applied_rules: [ 'Μπλοκάρει οποιοδήποτε AI deployment αν δεν έχει περάσει red-teaming & prompt injection suite', 'Απαιτεί πάντα human-in-the-loop approval για ενέργειες με υψηλό blast radius' ], retrieved_memories: [ 'Red-Team Report 14/10: Κανένα release χωρίς automated adversarial evals.', 'Incident Review 29/10: Ο περιορισμός του blast radius προηγείται της αυτοματοποίησης.' ], style_notes: 'Σύντομος, αυστηρός, εστιασμένος στο ρίσκο και στα μετρήσιμα τεκμήρια.' } }; } setDraft(mockRes); setEditedReply(mockRes.twin_reply); } };  const handleApprove = async () => { if (backendOnline && draft) { await fetch(`${API_URL}/api/twin/approve/${draft.draft_id}?edited_reply=${encodeURIComponent(editedReply)}`, { method: 'POST' });
    }
    setApprovedToast(true);
  };

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col">
      {/* Top Navbar */}
      <header className="border-b border-slate-800 bg-slate-900/80 px-6 py-4 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="bg-red-600 p-2 rounded-lg"><ShieldAlert className="w-6 h-6 text-white" /></div>
          <div>
            <h1 className="text-xl font-bold tracking-tight">EchoMind — AI Digital Self</h1>
            <p className="text-xs text-slate-400">Persona: {persona.name} ({persona.role})</p>
          </div>
        </div>
        <div className="flex items-center gap-4">
          <span className={`text-xs px-3 py-1 rounded-full border