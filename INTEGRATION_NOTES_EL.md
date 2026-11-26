# EchoMind — σημειώσεις διασύνδεσης (25 Νοεμβρίου 2026)

Το frontend παραμένει React/Vite και το backend FastAPI. Η βασική αλλαγή είναι ότι **το backend επιστρέφει πλέον σταθερό JSON contract**, συμβατό με τα πεδία που χρησιμοποιεί το React. Το πλήρες `PersonaProfile` διατηρείται στο backend και μετατρέπεται μέσω `PersonaProfile.to_ui_dict()`.

## Διαδρομές API

| Method | Path | Περιγραφή |
|---|---|---|
| GET | `/health` | Κατάσταση API και διαθεσιμότητα LLM key |
| GET | `/api/persona` | Επιστρέφει `persona_id`, `name`, `role`, `writing_style`, `decision_heuristics`, `knowledge_facts` και επιπλέον `preferences`, `evidence`, `source_stats`, `persona_version` |
| PUT | `/api/persona` | Αποθηκεύει επεξεργασμένο persona, επιστρέφει τη νέα έκδοση. Τα αμετάβλητα entries διατηρούν τα αρχικά evidence IDs. |
| POST | `/api/ingest` | `multipart/form-data`, πολλαπλά `files`. Υποστηρίζονται UTF-8 TXT, MD, EML, JSON, JSONL και κειμενικά PDF (όχι OCR). Επιστρέφει `persona` και `persona_version`. |
| POST | `/api/twin/respond` | JSON `{ "incoming_message": "..." }`. Επιστρέφει `draft_id`, `status`, `twin_reply`, `confidence_score`, `is_uncertain`, `explanation`. |
| POST | `/api/twin/review/{draft_id}` | JSON `{ "action": "approved" | "rejected", "edited_reply": "..." }`. Καταγράφει την ανθρώπινη απόφαση. Δεν αποστέλλει email. |
| GET | `/api/audit` | Αποθηκευμένο ιστορικό αποφάσεων. |
| GET | `/api/evaluation/latest` | Τελευταία ολοκληρωμένη αξιολόγηση, αν υπάρχει. |
| POST | `/api/evaluation/run?limit=5` | Εκτελεί δοκιμές μόνο εφόσον υπάρχει ενεργό LLM key. |

## Τι διορθώθηκε

Το frontend πλέον δεν πραγματοποιεί benchmark αυτόματα με τη φόρτωση της σελίδας και δεν παρουσιάζει στατικά 94–97% ως πραγματικά αποτελέσματα. Η αποθήκευση persona και η έγκριση draft επιβεβαιώνονται από το API, ενώ τα σφάλματα εμφανίζονται στον χρήστη. Το audit log φορτώνεται ξανά από το backend.

Ο φάκελος `data/runtime/` κρατά τις συνθετικές/εγκεκριμένες μεταφορτώσεις, drafts, audit log και τελευταίο evaluation και αγνοείται από το Git. Για νέα μεταφόρτωση, η μνήμη προκύπτει μόνο από τα ανεβασμένα έγγραφα, χωρίς ανακάτεμα με την αρχική synthetic demo μνήμη. Η εξαγωγή κανόνων απαιτεί κλειδί LLM. Χωρίς κλειδί, η εφαρμογή εκκινεί και επιστρέφει ειλικρινές μήνυμα ότι δεν παρήχθη πραγματική AI απάντηση.

Η τρέχουσα ανάκτηση χρησιμοποιεί λεξική επικάλυψη (token overlap). Οι helpers για embeddings και vector store υπάρχουν στο repository αλλά **δεν έχουν ενσωματωθεί πλήρως** στο live retrieval. Επομένως δεν παρουσιάζουμε την τρέχουσα αναζήτηση ως ολοκληρωμένη vector/hybrid RAG. Δεν υπάρχει fine-tuning του μοντέλου.

## Εκκίνηση

Σε περιβάλλον με Docker και δικτυακή πρόσβαση για τα επίσημα πακέτα:

```bash
cp .env.example .env
# Το .env.example προεπιλέγει LLM_PROVIDER=openai και OPENAI_MODEL=gpt-6-luna.
# Συμπληρώστε ΝΕΟ OPENAI_API_KEY μόνο στο τοπικό .env. Μην το συμπεριλάβετε σε ZIP.
docker compose up --build
```

Frontend `http://localhost:5173`, backend `http://localhost:8000`, docs `http://localhost:8000/docs`.

Η υπηρεσία PostgreSQL είναι προαιρετική (`docker compose --profile postgres up --build`) καθώς η τρέχουσα υλοποίηση αποθηκεύει persona/memory σε αρχεία JSON. Δεν απαιτείται API key μόνο για να εκκινήσουν τα containers. Για πραγματικό digital twin generation και evaluation χρειάζεται έγκυρο API key. Δεν αποστέλλονται emails εξωτερικά.

## Όρια και ασφάλεια

Αυτό παραμένει hackathon prototype και **όχι** πλήρες προϊόν GDPR/DLP ή σύστημα με πολυχρηστική αυθεντικοποίηση. Χρησιμοποιήστε αποκλειστικά συνθετικά ή δικά σας εγκεκριμένα δεδομένα. Η απόκρυψη PII βασίζεται σε κανονικές εκφράσεις, όχι σε πλήρη ανωνυμοποίηση. Αποφύγετε πραγματικά δεδομένα τρίτων. Οι αξιολογήσεις είναι ενδεικτικές για το συγκεκριμένο test set και δεν σημαίνουν κλινικά/στατιστικά βαθμονομημένη πιθανότητα.

## Έλεγχοι αυτής της παράδοσης

Πραγματοποιήθηκαν τοπικοί έλεγχοι στα FastAPI endpoints και έλεγχος σύνταξης JSX. Δεν έγινε πλήρης Docker build επειδή το περιβάλλον παραγωγής των αρχείων δεν διαθέτει Docker. Ο πλήρης npm build δεν κατέστη δυνατός λόγω ελλιπούς npm cache / μη διαθέσιμης πρόσβασης στο registry σε αυτό το περιβάλλον. Να εκτελεστεί `docker compose up --build` στον υπολογιστή της ομάδας πριν την παρουσίαση.
