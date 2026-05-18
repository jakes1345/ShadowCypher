# ShadowCypher apt repository

## Install

```bash
# 1. Add the signing key (if repo is signed)
sudo install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://shadowcypher.site/apt/shadowcypher-apt.gpg \
  | sudo tee /etc/apt/keyrings/shadowcypher.gpg > /dev/null

# 2. Add the source
echo "deb [signed-by=/etc/apt/keyrings/shadowcypher.gpg arch=amd64] https://shadowcypher.site/apt stable main" \
  | sudo tee /etc/apt/sources.list.d/shadowcypher.list

# 3. Install
sudo apt update
sudo apt install shadowcypher

# Upgrade later
sudo apt update && sudo apt upgrade shadowcypher
```

## Unsigned fallback

If the signing key isn't available yet:

```bash
echo "deb [trusted=yes arch=amd64] https://shadowcypher.site/apt stable main" \
  | sudo tee /etc/apt/sources.list.d/shadowcypher.list
sudo apt update && sudo apt install shadowcypher
```
