# Permissions Declaration Statements
## Use these if Google asks you to justify permissions during review

---

## Guardian — site.shadowcypher.app

**RECEIVE_BOOT_COMPLETED**
Guardian monitors the user's home network continuously. This permission restarts the background sync worker after a device reboot so the user continues to receive alerts about their own network without having to manually reopen the app. Without this permission, monitoring would stop every time the phone restarts.

**POST_NOTIFICATIONS**
Guardian alerts the user when new unrecognized devices join their home network and when security incidents are detected. These are security alerts about the user's own infrastructure — the core value of the app. Notifications are only sent when the Guardian agent on the user's own server detects an event.

**ACCESS_NETWORK_STATE**
Used only to check whether the phone has an active internet connection before making API requests. This prevents showing error states when the phone is offline. No network scanning is performed from the phone — all network scanning is done by the agent on the user's own Linux server.

---

## Shadow AI — site.shadowcypher.assistant

**RECORD_AUDIO**
Shadow AI is a voice assistant. The microphone is the primary input method. Voice is processed entirely on-device using the Vosk offline speech recognition library — no audio data is ever transmitted to any server, recorded, or stored. The microphone is only active when the user has opened the assistant and is actively speaking. There is no background listening except for the optional on-device wake word detector, which also runs locally.

**RECEIVE_BOOT_COMPLETED**
Used to restore the user's wake word preference setting after a phone restart. Without this, users who enabled the optional "Hey Shadow" wake word would need to re-enable it every time their phone reboots.

**POST_NOTIFICATIONS**
Used for timer and alarm notifications set by voice command (e.g., "set a timer for 10 minutes"). Notifications are generated locally on-device only — no server is involved.

---

## Network scanning clarification (for both apps)

Neither app performs any network scanning from the Android device itself.

Guardian displays results from the Guardian agent — a separate open-source program the user installs on their own Linux computer. That agent scans the user's own home network. The Android app only displays those results via the user's own API key.

Shadow AI does not perform any network scanning at all. It only queries the Guardian API (with the user's API key) to display pre-existing scan results if the user asks for them.

Both apps can only access data from networks the user has personally set up and owns.
