# GeM Verify frontend

A plain HTML/CSS/JavaScript frontend for the supplied Flask backend. No frontend build step or framework is required. The interface intentionally uses no animations or transitions.

## Included screens
- Overview dashboard with review counts and recent records
- PDF upload and requirement form
- Verification result with matched, missing, and manual-review items
- Saved history with filename search and detail view

## Run it

1. Keep your backend files in the structure expected by your imports. Your `app(1).py` imports `backend.extraction`, `backend.compliance`, and `backend.database`, so a typical layout is:

   ```text
   project/
   ├── app.py
   ├── backend/
   │   ├── __init__.py
   │   ├── extraction.py
   │   ├── compliance.py
   │   └── database.py
   └── frontend/
       ├── index.html
       ├── style.css
       └── app.js
   ```

   Rename `app(1).py` to `app.py` and place the three backend modules inside `backend/` (or adjust the imports to match your actual folder structure). Add an empty `backend/__init__.py` if it is missing.

2. Install backend dependencies in your Python environment:

   ```bash
   pip install flask flask-cors pypdf
   ```

3. Start Flask from the project root:

   ```bash
   python app.py
   ```

   The API should be available at `http://127.0.0.1:5000`.

4. Open `frontend/index.html` in your browser. If browser restrictions block requests from a `file://` page, serve the frontend folder instead:

   ```bash
   python -m http.server 5500 --directory frontend
   ```

   Then open `http://127.0.0.1:5500`.

## API endpoints used

- `GET /` — checks API connectivity
- `POST /verify` — sends a PDF in `file` and comma-separated `requirements` fields
- `GET /history` — loads saved reviews
- `GET /history/<id>` — displays a saved review

If your Flask backend uses a different host or port, update `API_BASE` near the top of `app.js`.

## Important limitations in the supplied backend

- Compliance is phrase matching against extracted PDF text; it does not contact GST, PAN, Udyam, EPFO, Income Tax, or GeM systems.
- OCR for scanned PDFs is not included.
- The backend exposes no login, roles, or authorization routes. This frontend therefore does not claim to provide secure company/government authentication.
- History records store a summary and requirements, not the full itemized result. The live result screen shows itemized output immediately after verification; saved history detail can only show fields exposed by the current API.
