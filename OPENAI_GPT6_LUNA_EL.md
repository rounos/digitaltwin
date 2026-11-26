# EchoMind — GPT-6 Luna / OpenAI Responses API

Η εφαρμογή έχει προεπιλογή `LLM_PROVIDER=openai` και `OPENAI_MODEL=gpt-6-luna`.

1. Ανακαλέστε οποιοδήποτε API key κοινοποιήθηκε στο chat και δημιουργήστε νέο: https://platform.openai.com/api-keys
2. Στον κεντρικό φάκελο τρέξτε `Copy-Item .env.example .env` (εάν δεν υπάρχει ήδη `.env`).
3. Συμπληρώστε **τοπικά** `OPENAI_API_KEY=...` στο `.env` και διατηρήστε `LLM_PROVIDER=openai` / `OPENAI_MODEL=gpt-6-luna`.
4. Εκτελέστε `docker compose up -d --build --force-recreate`.
5. Ανοίξτε `http://localhost:8000/health`, ελέγξτε `llm_configured: true`, `provider: openai`, `model: gpt-6-luna`.
6. Δοκιμάστε μία ερώτηση στο Sandbox. Το `/health` δεν αποτελεί δοκιμή πραγματικής πρόσβασης ή διαθέσιμων credits.

Εάν λάβετε αβεβαιότητα ή failure, δείτε `docker compose logs --tail=60 backend` και την κατάσταση χρέωσης/διαθεσιμότητας του μοντέλου. Η εφαρμογή δεν αποστέλλει emails. Η λειτουργία «Έγκριση» αποθηκεύει την απόφαση τοπικά.

Το `OPENAI_REASONING_EFFORT=none` ευνοεί τη γρήγορη απόκριση στο demo. Μπορεί να αλλάξει στο `.env`, ανάλογα με την ποιότητα που θέλετε. Οι κλήσεις έχουν `store:false`. Το κλειδί δεν περιλαμβάνεται σε κανένα αρχείο του ZIP.

Οι δοκιμές είναι offline και δεν επαληθεύουν ότι το κλειδί σας είναι ενεργό ή έχει διαθέσιμα credits.
