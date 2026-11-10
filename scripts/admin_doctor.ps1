# Read-only diagnostics for the GEANT admin panel. Changes nothing, deletes nothing.
# Run from the project root:   powershell -ExecutionPolicy Bypass -File .\scripts\admin_doctor.ps1

function Step($t) { Write-Host ""; Write-Host "== $t ==" -ForegroundColor Cyan }
function Ok($t)   { Write-Host "[OK]   $t" -ForegroundColor Green }
function Bad($t)  { Write-Host "[FAIL] $t" -ForegroundColor Red }

Step "1. Containers"
docker compose ps

Step "2. Does the RUNNING frontend contain the admin page?"
$hit = docker compose exec -T frontend sh -c "grep -l 'api/admin/products' /usr/share/nginx/html/assets/*.js"
if ($hit) { Ok "Frontend bundle contains the admin page" }
else { Bad "Frontend container is OLD (this is why /admin shows 'Page introuvable'). Rebuild: docker compose build --no-cache frontend ; docker compose up -d frontend" }

Step "3. Does the RUNNING API expose the admin routes?"
try {
  $spec = Invoke-RestMethod -Uri "http://localhost:8000/openapi.json" -TimeoutSec 10
  if ($spec.paths.PSObject.Properties.Name -contains "/api/admin/products") { Ok "API exposes /api/admin/products" }
  else { Bad "API container is OLD (no admin routes). Rebuild: docker compose build --no-cache api ; docker compose up -d api" }
} catch { Bad "API is not reachable on http://localhost:8000 - check: docker compose logs api --tail 50" }

Step "4. ADMIN_EMAIL inside the API container"
$mail = (docker compose exec -T api printenv ADMIN_EMAIL | Out-String).Trim()
if ($mail) { Ok "ADMIN_EMAIL = $mail" } else { Bad "ADMIN_EMAIL is empty in the API container. Add it to .env then: docker compose up -d api" }

Step "5. Database migrations (the users table must exist)"
docker compose exec -T api alembic current
docker compose exec -T db psql -U sales_ai -d sales_ai -c "select to_regclass('public.users') as users_table, to_regclass('public.user_sessions') as sessions_table;"

Step "6. Registered accounts (emails only)"
docker compose exec -T db psql -U sales_ai -d sales_ai -c "select id, email from users order by id;"
if ($mail) {
  $q = "select count(*) as admin_account_exists from users where lower(email) = lower('$mail');"
  docker compose exec -T db psql -U sales_ai -d sales_ai -c $q
  Write-Host "If admin_account_exists = 0, create the account once at http://localhost:5173/signup using exactly: $mail" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "Too many failed logins (8 within 5 minutes) lock login until the API restarts: docker compose restart api" -ForegroundColor Yellow
