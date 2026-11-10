# GEANT Admin — installation and use

This change adds a product-management page at `/admin` to the existing React + FastAPI application. It uses the existing PostgreSQL `products` table and the existing cookie-based authentication/session + CSRF protection. No database migration is required.

## Included

- Admin-only product list with search and category filter.
- Create, edit and delete products.
- Product fields: name, category, brand, description, price, currency, stock quantity, product URL, and demo-data flag.
- Pagination and delete protection when a product is already referenced by an order/cart.

Image uploads, CSV import/export, and a dedicated product-specification editor are intentionally not included in this first version.

## Setup on your existing project

1. Back up the project folder. Do not delete Docker volumes.
2. Copy the changed files from this package into the matching paths in your current project, allowing overwrite:
   - `app/core/config.py`
   - `app/main.py`
   - `app/api/routes/admin.py` (new)
   - `frontend/src/App.jsx`
   - `frontend/src/main.jsx`
   - `frontend/src/pages/AdminProductsPage.jsx` (new)
   - `frontend/src/services/api.js`
   - `frontend/src/styles/admin.css` (new)
3. Open the existing `.env` file (not `.env.example`) and add:

   ```env
   ADMIN_EMAIL=the-email-you-will-use-for-admin
   ```

   Use the exact email address of the account you will sign into. Do not publish `.env` or commit it to Git.
4. If that account does not exist yet, create it once through the existing `/signup` page using that email. Then sign in with it. The admin allowlist is controlled by `ADMIN_EMAIL`; normal registered users do not receive admin access.
5. Rebuild/restart the API and frontend from the project root:

   ```powershell
   docker compose up -d --build api frontend
   ```
6. Open `http://localhost:5173/admin` and sign in using the account whose email is configured in `ADMIN_EMAIL`.

## Verify

- API docs: `http://localhost:8000/docs` — look for the `admin` group.
- `GET /api/admin/me` must return `{"is_admin": true}` when signed in as the configured admin.
- Product changes are written directly to the current `products` table.

## Important behavior

- Existing storefront user authentication remains unchanged.
- The admin backend checks the configured admin email on every admin endpoint. The frontend route alone is not the security boundary.
- Writes require the existing CSRF token.
- Deleting a product referenced by a cart/order is rejected with HTTP 409 to preserve referential integrity.
- This is a single-admin allowlist, not a role-management system.
- This ZIP was built from the uploaded `sales_ai-develop.zip` snapshot. If your local project has changed since that snapshot, compare/merge these files instead of blindly overwriting newer work.

## Troubleshooting

Run the read-only diagnostic from the project root:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\admin_doctor.ps1
```

| Symptom | Cause | Fix |
|---|---|---|
| `/admin` shows "Page introuvable" | The running frontend image is old (built before the admin page existed) | `docker compose build --no-cache frontend` then `docker compose up -d frontend`, then hard-refresh (Ctrl+Shift+R) |
| "Admin access only" page | Signed-in email differs from `ADMIN_EMAIL` | Fix `ADMIN_EMAIL` in `.env`, then `docker compose up -d api` |
| "Too many login attempts" | 8 failed logins in 5 minutes | `docker compose restart api` |
| "Invalid email or password" | No account with that email | Create it once at `/signup` |
| "Server error (HTTP 500)" | Usually missing migration (`users` table) | `docker compose exec api alembic upgrade head`, check `docker compose logs api --tail 50` |
