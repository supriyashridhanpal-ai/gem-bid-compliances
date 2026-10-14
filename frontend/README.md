# GeM Verify — role-based frontend

This is a plain HTML/CSS/JavaScript frontend (no build step and no animations/transitions).

## Screens included
- Portal selection: Company or Government/Admin
- Company sign-in and company registration
- Company portal: published tenders, PDF bid upload, and own submission statuses
- Government admin sign-in
- Admin dashboard, tender publishing, and company upload results

## Run
1. Extract this ZIP into your project's `frontend` folder, replacing the old `index.html`, `style.css`, `app.js`.
2. Start your Flask backend from the project root.
3. Serve this folder, for example:
   `python -m http.server 5500 --directory frontend`
4. Open `http://127.0.0.1:5500`.

Change `API_BASE` at the top of `app.js` if your backend runs somewhere else.

## Important backend integration requirement
The backend files supplied with the original frontend only implement `GET /`, `POST /verify`, `GET /history`, and `GET /history/<id>`. They do **not** currently implement authentication, role permissions, tenders, company submissions, or admin results. This frontend intentionally calls the following expected API endpoints:
- `POST /auth/company/register`
- `POST /auth/company/login`
- `POST /auth/admin/login`
- `GET /tenders`
- `POST /company/submissions`
- `GET /company/submissions`
- `GET /admin/tenders`
- `POST /admin/tenders`
- `GET /admin/results`

Therefore login, registration, tender management, and protected data views will not work until the backend implements these routes and returns the expected JSON structures. This ZIP is the changed frontend only; it does not create secure authentication by itself.

## Confidentiality / security
Hiding admin pages in JavaScript is **not** security. The backend must verify a signed session/token on every protected route, enforce company-vs-admin roles, scope company submissions to the authenticated company, and only return detailed compliance results from admin-only endpoints. Do not expose the existing unprotected `/history` endpoint to company users. Admin accounts should be provisioned securely; do not hardcode a public admin password. Store password hashes, not plain-text passwords, and use HTTPS in deployment.

Expected tender shape can be an array of objects like `{ "id": 1, "title": "Tender title", "requirements": "GST, PAN", "status": "OPEN" }`. Admin result rows should include fields such as `id`, `company_name`, `tender_title`, `filename`, `status`, and `score`.


## Default admin login shown in the form
- Username: `Goverment`
- Password: `1234567890`

These values are prefilled in the frontend only. They do not create an admin account or secure the backend. The Flask backend must validate the credentials server-side and protect admin-only endpoints. Change the default password before deployment and do not use this demo credential in production.
