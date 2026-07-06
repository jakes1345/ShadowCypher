# ShadowOS AppArmor Security Profiles

## Confined Applications

ShadowOS includes AppArmor profiles for critical applications:

- **Guardian** - Security monitoring service
- **SSH Server** - Remote access daemon

## Managing Profiles

```bash
# View profile status
sudo aa-status

# Reload profile
sudo apparmor_parser -r /etc/apparmor.d/profile-name

# Set to complain mode (learning)
sudo aa-complain /etc/apparmor.d/profile-name

# Set to enforce mode
sudo aa-enforce /etc/apparmor.d/profile-name
```

## Creating Custom Profiles

```bash
# Start in complain mode
sudo aa-complain /usr/bin/myapp

# Generate rules by running app
sudo systemctl restart myapp

# Check generated rules
sudo aa-logprof

# Move to enforce mode
sudo aa-enforce /etc/apparmor.d/usr.bin.myapp
```
