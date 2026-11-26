# EchoMind — Γρήγορη εκκίνηση για την παρουσίαση

Πρόκειται για το ενοποιημένο project React + FastAPI. Οι αλλαγές και τα API fields περιγράφονται στο `INTEGRATION_NOTES_EL.md`.

Στα Windows, μέσα από PowerShell στον κεντρικό φάκελο του project, αν δεν υπάρχει το αρχείο `.env`:

```powershell
Copy-Item .env.example .env
```

Το προεπιλεγμένο μοντέλο είναι **GPT-6 Luna** (`gpt-6-luna`) μέσω OpenAI Responses API. Ανοίξτε το `.env` και συμπληρώστε **μόνο ένα ΝΕΟ OpenAI API key** στη γραμμή `OPENAI_API_KEY=`. Το `LLM_PROVIDER=openai` και το `OPENAI_MODEL=gpt-6-luna` είναι ήδη έτοιμα. Αν κάποιο κλειδί κοινοποιήθηκε σε chat, ανακαλέστε το και δημιουργήστε νέο στο https://platform.openai.com/api-keys. Μη βάλετε κλειδιά σε αρχεία κώδικα, ZIP ή GitHub.

Στη συνέχεια:

```powershell
docker compose up --build
```

Αν αλλάξετε το `.env`, κάντε επανεκκίνηση των containers:

```powershell
docker compose up -d --build --force-recreate
```

Ελέγξτε `http://localhost:8000/health`: πρέπει να εμφανίζει `"provider":"openai"`, `"model":"gpt-6-luna"` και `"llm_configured":true`. Αυτό δείχνει ότι το key έχει φορτωθεί, όχι ότι έχει γίνει επιτυχής κλήση. Δοκιμάστε πραγματική ερώτηση στο Sandbox. Για αποτυχία: `docker compose logs --tail=60 backend`.

Μετά την εκκίνηση ανοίξτε `http://localhost:5173` για το frontend και `http://localhost:8000/docs` για τα endpoints.

Προτεινόμενη ροή demo: ανοίξτε το Persona tab για να δείξετε τα χαρακτηριστικά και τα evidence IDs, επιστρέψτε στο Sandbox και ζητήστε να αξιολογήσει ένα υποθετικό AI release χωρίς security review, δείξτε το draft και τα σχετικά evidence, τροποποιήστε την απάντηση και εγκρίνετε το draft (δεν αποστέλλεται email), έπειτα δείξτε το Audit Log. Για νέα εισαγωγή χρησιμοποιήστε μόνο συνθετικά TXT/MD/EML/JSON/PDF και ελέγξτε ότι το Persona ανανεώθηκε. Εάν έχετε ενεργό API key, εκτελέστε τις αξιολογήσεις αποκλειστικά χειροκίνητα στην καρτέλα Fidelity.

Χωρίς κλειδί η εφαρμογή εξακολουθεί να εκκινεί, αλλά **δεν** ισχυρίζεται ότι παράγει πραγματικές LLM απαντήσεις ή έγκυρες μετρήσεις fidelity.

Για βασικά tests backend σε περιβάλλον ανάπτυξης με Python, `pytest`, `httpx` και τα requirements εγκατεστημένα:

```powershell
$env:PYTHONPATH='backend'
python -m pytest -q backend/tests/test_integration.py
```

Ο έλεγχος Docker build πρέπει να πραγματοποιηθεί στον υπολογιστή της ομάδας, γιατί δεν ήταν διαθέσιμο Docker στο περιβάλλον που δημιουργήθηκε αυτό το ZIP. Ο έλεγχος του Vite/npm build απαιτεί πρόσβαση στο npm registry.
