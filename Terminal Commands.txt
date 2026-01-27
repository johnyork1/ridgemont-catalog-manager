# ====================================
# 1. RIDGEMONT CATALOG MANAGER (Main)
# ====================================
cd ~/Ridgemont\ Studio/Claude\ Cowork/Ridgemont\ Catalog\ Manager
git add data/catalog.json scripts/app.py .gitignore
git commit -m "Add Albums page and Dark Pattern album for Stone Meridian"
git push --set-upstream origin main

# ====================================
# 2. FROZEN CLOUD PORTAL
# ====================================
# Copy latest catalog
cp ~/Ridgemont\ Studio/Claude\ Cowork/Ridgemont\ Catalog\ Manager/data/catalog.json ~/Ridgemont\ Studio/Claude\ Cowork/frozen-cloud-portal/data/
cd ~/Ridgemont\ Studio/Claude\ Cowork/frozen-cloud-portal
git add -A
git commit -m "Sync catalog data"
git push --set-upstream origin main

# ====================================
# 3. PARK BELLEVUE PORTAL
# ====================================
# Copy latest catalog
cp ~/Ridgemont\ Studio/Claude\ Cowork/Ridgemont\ Catalog\ Manager/data/catalog.json ~/Ridgemont\ Studio/Claude\ Cowork/park-bellevue-portal/data/
cd ~/Ridgemont\ Studio/Claude\ Cowork/park-bellevue-portal
git init
git add -A
git commit -m "Initial Park Bellevue portal setup with synced catalog"
gh repo create johnyork1/park-bellevue-portal --public --source=. --push