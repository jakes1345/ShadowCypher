# ShadowCypher

An elite, high-fidelity security platform and AI orchestration suite built on a Cairo GTK4 foundation.

## Branch Workflow
We use a standard branching strategy for release management:

1. **`main` (Stable/Production)**
   - The absolute, rock-solid core.
   - Only receives merges from `beta` when a feature has been 100% verified and stress-tested.
   - If someone runs this, it works flawlessly.

2. **`beta` (Staging/Candidate)**
   - Used for integrating features and testing UI/engine synchronization.
   - We merge features here from `alpha` once they are functionally complete, but might need final aesthetic polish or broad integration tests.
   - Often pushed to early testers.

3. **`alpha` (Experimental/Development)**
   - The bleeding edge.
   - New exploits, untested AI orchestration hooks, and radical UI overhauls live here.
   - Might break. Expected to break. This is where we build the new weapons.

## Usage
Switch to the branch you want to test before launching:
```bash
git checkout beta
python3 -m shadowcypher.app
```
