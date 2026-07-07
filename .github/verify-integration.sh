#!/bin/bash
# verify-integration.sh
# End-to-end verification of Phase 3 integration
# Checks: API endpoints, vault password, download page, desktop app

set -e

echo "🔍 ShadowCypher Phase 3 Integration Verification"
echo "=================================================="
echo ""

# Color codes
GREEN='\033[0;32m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m'

PASS=0
FAIL=0

check() {
    local name="$1"
    local result="$2"
    if [ "$result" -eq 0 ]; then
        echo -e "${GREEN}✓${NC} $name"
        ((PASS++))
    else
        echo -e "${RED}✗${NC} $name"
        ((FAIL++))
    fi
}

echo -e "${BLUE}1. API Endpoints${NC}"
python3 -c "
from shadowcypher.main import app
from fastapi.testclient import TestClient
client = TestClient(app)

# Test /api/latest
resp = client.get('/api/latest')
assert resp.status_code == 200, f'Expected 200, got {resp.status_code}'
data = resp.json()
assert 'version' in data, 'Missing version'
assert 'assets' in data, 'Missing assets'
print('OK')
" > /dev/null 2>&1
check "/api/latest endpoint" $?

echo ""
echo -e "${BLUE}2. Backend Tests${NC}"
python -m pytest tests/chat/test_group_routes.py -q > /dev/null 2>&1
check "Group routes (11 tests)" $?

python -m pytest tests/chat/test_group_crypto.py tests/chat/test_group_message_routes.py tests/chat/test_group_models.py -q > /dev/null 2>&1
check "Group crypto & messages (8 tests)" $?

python -m pytest tests/integration/test_group_e2e_flow.py -q > /dev/null 2>&1
check "E2E flow (1 test)" $?

echo ""
echo -e "${BLUE}3. Code Structure${NC}"

# Check vault unlock endpoint exists
grep -q "def unlock_vault" shadowcypher/chat/routes.py
check "Vault unlock endpoint defined" $?

# Check VaultUnlock component exists
[ -f shadowcypher/ui/components/Chat/VaultUnlock.tsx ]
check "VaultUnlock React component" $?

# Check download page exists
[ -f shadowcypher/ui/download_page.html ]
check "Download page HTML" $?

# Check chat documentation
[ -f shadowcypher/knowledge/app/chat.md ]
check "Chat feature documentation" $?

echo ""
echo -e "${BLUE}4. File Structure${NC}"

# Check GitHub Actions scripts
[ -f .github/setup-releases-server.sh ]
check "Releases server setup script" $?

[ -f .github/deploy-download-page.sh ]
check "Download page deploy script" $?

[ -f .github/upload-releases.yml ]
check "CI/CD workflow configured" $?

# Check guides
[ -f .github/QUICK_START.md ]
check "Quick start guide" $?

[ -f .github/RELEASES_SETUP.md ]
check "Releases setup guide" $?

echo ""
echo -e "${BLUE}5. Feature Verification${NC}"

# Check vault endpoint imports
python3 -c "
from shadowcypher.chat.schemas import VaultUnlockRequest, VaultUnlockResponse
from shadowcypher.chat.routes import unlock_vault
print('OK')
" > /dev/null 2>&1
check "Vault endpoint schemas" $?

# Check group chat imports
python3 -c "
from shadowcypher.ui.components.Chat.VaultUnlock import VaultUnlock
print('OK')
" > /dev/null 2>&1 || echo "  (Frontend imports require npm build)"

echo ""
echo "=================================================="
echo -e "${BLUE}Summary${NC}"
echo "  ${GREEN}Passed: $PASS${NC}"
echo "  ${RED}Failed: $FAIL${NC}"

if [ $FAIL -eq 0 ]; then
    echo ""
    echo -e "${GREEN}✓ All checks passed! Ready for deployment.${NC}"
    exit 0
else
    echo ""
    echo -e "${RED}✗ Some checks failed. Review above.${NC}"
    exit 1
fi
