# ShadowCypher Encrypted Group Channels

## Overview

Phase 3 introduces **encrypted group channels** — a secure, zero-knowledge messaging platform for team collaboration.

### Key Features

- 🔒 **AES-256-GCM Encryption** — Military-grade encryption with authenticated encryption
- 👥 **Group Management** — Create groups, add/remove members, role-based access
- 🔄 **Key Rotation** — Automatic key updates when members leave (maintains history)
- 📱 **Multi-Platform** — Desktop app, mobile (APK), web interface
- ⚡ **Zero-Knowledge** — Server never holds plaintext keys or messages
- 💬 **Real-Time** — Live message delivery and member presence

## Accessing Group Chat

### Desktop App
1. Open ShadowCypher → **Chat** tab
2. Click **+ Create Group** (🔒 Encrypted Groups section)
3. Enter group name
4. Add members by ID
5. Start messaging

### Mobile (Guardian)
1. Open ShadowCypher Guardian → **Groups**
2. Tap **+ New Group**
3. Name and add members
4. Chat appears in real-time

### Web
Visit `shadowcypher.site/chat` (requires login)

## How It Works

### Encryption Model

**Setup (Group Creation):**
1. Admin creates group
2. Backend generates 32-byte AES-256 key
3. Key delivered to creator encrypted with device key
4. Creator distributes to members via P2P DM (not via server)

**Messaging:**
- Each message encrypted with current group key
- Key version tag on each message
- Nonce (96-bit) per message prevents replay

**Key Rotation (Member Removal):**
1. Admin removes member
2. Backend generates new key (v2, v3, etc.)
3. New key sent to admin only (via removal response)
4. Admin sends new key to remaining members via DM
5. New messages use new key; old messages stay readable

### Why This Is Secure

- **No plaintext keys on server** — only version numbers
- **No message access** — server stores encrypted blobs only
- **Member removal enforced** — old key version can't decrypt new messages
- **Device key wrapping** — keys never leave encrypted container
- **Device unlock required** — all keys behind biometric/PIN

## API Endpoints

Base: `https://api.shadowcypher.site`

### Groups

| Method | Endpoint | Auth | Purpose |
|--------|----------|------|---------|
| POST | `/chat/groups` | Bearer | Create group, get initial key |
| GET | `/chat/groups` | Bearer | List user's groups |
| GET | `/chat/groups/{id}` | Bearer | Get group metadata (name, key version) |
| DELETE | `/chat/groups/{id}` | Bearer | Delete group (admin only) |

### Members

| Method | Endpoint | Auth | Purpose |
|--------|----------|------|---------|
| POST | `/chat/groups/{id}/members` | Bearer | Add member to group |
| GET | `/chat/groups/{id}/members` | Bearer | List group members |
| DELETE | `/chat/groups/{id}/members/{member_id}` | Bearer | Remove member, get new key |

### Messages

| Method | Endpoint | Auth | Purpose |
|--------|----------|------|---------|
| POST | `/chat/groups/{id}/messages` | Bearer | Send encrypted message |
| GET | `/chat/groups/{id}/messages` | Bearer | Fetch group message history |

## Example Usage

### Create Group (Desktop App)
```
1. Click "🔒 Encrypted Groups"
2. "+ Create Group"
3. Name: "Red Team Alpha"
4. Add members: user_id_1, user_id_2, user_id_3
✓ Group created, key stored locally
```

### Send Message
```
User types: "Intel on target network ready"
Client encrypts with current group key + random nonce
Sends to server (unreadable without key)
Server stores encrypted blob
All members receive and decrypt with their copy of key
✓ Message appears in real-time
```

### Remove Member
```
Admin removes user_id_2 (left the team)
Server generates new key (v2)
Admin gets new key in removal response
Admin sends new key to user_id_1 and user_id_3 via DM
New messages use v2; old messages still readable with v1
User_id_2 can't decrypt v2 messages
✓ Removal enforced, group history preserved
```

## Security Considerations

### What You Get
✓ Encryption: All messages encrypted end-to-end
✓ Authentication: Message integrity verified
✓ Forward Secrecy: Old keys can't decrypt new messages
✓ Zero-Knowledge: Server never has plaintext keys
✓ Audit Trail: Every key rotation logged

### What You Need
- Keep device key safe (biometric/PIN lock)
- Share new group keys securely (P2P DM)
- Don't screenshot plaintext messages
- Use trusted networks for initial group setup

### Limitations
- Messages encrypted but metadata (timestamps, member list) visible to server
- Group name encrypted with device key (not visible to server)
- Rotating keys requires admin action (not automatic)
- No forward secrecy if device compromised (key in memory)

## Roadmap

**Current (Phase 3):**
- ✅ Multi-member encrypted groups
- ✅ Key rotation on member removal
- ✅ Desktop + mobile apps
- ✅ Web interface
- ✅ E2E testing

**Coming Soon (Phase 4):**
- [ ] Automatic key rotation (background)
- [ ] Message search (client-side decryption)
- [ ] Group roles (admin/member/read-only)
- [ ] Invite links (encrypted, time-limited)
- [ ] Message reactions (emoji)
- [ ] Threaded replies
- [ ] File sharing (encrypted)

## Troubleshooting

### "Messages show as encrypted blob"
- App crashed before decrypting
- Restart app and re-open group
- Check that group key is loaded in localStorage

### "New member can't read old messages"
- By design! Older messages were encrypted with old key
- New member gets current key only
- Request message export from admin (if needed)

### "Member removal failed"
- Network error — retry deletion
- Permission denied — only group creator can remove
- Member already removed — refresh group list

## Contact & Support

- **Issues**: github.com/jakes1345/ShadowCypher/issues
- **Docs**: shadowcypher.site/docs/chat
- **Status**: status.shadowcypher.site
