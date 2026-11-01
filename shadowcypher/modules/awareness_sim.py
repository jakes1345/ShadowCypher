"""
Awareness Sim — Security Awareness Simulation Engine
Generates phishing simulation templates, security quiz scenarios,
and social engineering awareness training content.
"""

from __future__ import annotations

import random
from typing import Any

from shadowcypher.core.module import BaseModule

# ── Phishing scenario templates ────────────────────────────────────────────────
_PHISHING_SCENARIOS: list[dict[str, Any]] = [
    {
        "id": "credential_harvest_it",
        "category": "CREDENTIAL_HARVEST",
        "difficulty": "LOW",
        "sender_spoof": "it-support@{domain}",
        "subject": "⚠️ Urgent: Password Expires in 24 Hours",
        "body_template": (
            "Dear {name},\n\nOur system indicates your password will expire in 24 hours. "
            "Please click the link below to reset it immediately to avoid losing access:\n\n"
            "  https://reset-password.{phish_domain}/secure?token={token}\n\n"
            "If you do not reset your password, your account will be locked.\n\n"
            "IT Support\n{org}"
        ),
        "red_flags": [
            "Urgency pressure ('24 hours', 'account locked')",
            "Link domain doesn't match org domain",
            "Unsolicited password reset request",
            "Generic greeting ('Dear {name}')",
        ],
        "training_tip": "Hover over links before clicking. Go directly to your IT portal, never via email links.",
    },
    {
        "id": "ceo_fraud_wire",
        "category": "BEC_WIRE_FRAUD",
        "difficulty": "MEDIUM",
        "sender_spoof": "ceo@{lookalike_domain}",
        "subject": "Confidential — Wire Transfer Required",
        "body_template": (
            "Hi {name},\n\nI need a wire transfer processed urgently. "
            "Please keep this between us — I'm in a meeting and can't talk.\n\n"
            "Amount: $47,500\nBeneficiary: {fake_vendor}\nAccount: {fake_account}\n\n"
            "Get this done before 3pm today.\n\nThanks,\n{ceo_name}"
        ),
        "red_flags": [
            "Request for secrecy",
            "Urgency without explanation",
            "Lookalike domain (check sender carefully)",
            "Large wire transfer via email",
            "No phone confirmation requested",
        ],
        "training_tip": "Always verify wire transfers via a known phone number — never reply-to the requesting email.",
    },
    {
        "id": "vishing_it_callback",
        "category": "VISHING",
        "difficulty": "MEDIUM",
        "medium": "voice_call",
        "script_template": (
            "Caller: 'Hi, this is {fake_name} from the {fake_team} team. "
            "We've detected suspicious activity on your account and need to verify your credentials. "
            "Can you confirm your username and current password?'"
        ),
        "red_flags": [
            "Unexpected call asking for password",
            "Caller creates urgency about 'suspicious activity'",
            "IT staff never ask for your password",
            "No callback number to verify identity",
        ],
        "training_tip": "Hang up. Call your IT helpdesk directly using the number in the internal directory.",
    },
    {
        "id": "usb_drop",
        "category": "PHYSICAL_USB",
        "difficulty": "LOW",
        "medium": "physical",
        "scenario": (
            "You find a USB drive in the parking lot labeled 'Q4 Payroll 2024.xlsx'. "
            "You plug it in to see if you can return it to the owner."
        ),
        "red_flags": [
            "Found media is a classic attack vector",
            "Enticing label triggers curiosity",
            "USB could execute malware on insertion (BadUSB)",
        ],
        "training_tip": "Never plug in found media. Turn it in to IT security.",
    },
]

# ── Security quiz questions ────────────────────────────────────────────────────
_QUIZ_QUESTIONS: list[dict[str, Any]] = [
    {
        "id": "q_phish_url",
        "question": "You receive an email with a link to 'http://paypa1.com/secure-login'. Is this safe?",
        "options": [
            "Yes — it says 'secure'",
            "No — 'paypa1' is a lookalike domain (1 not l)",
            "Maybe — depends on your browser",
            "Yes — http:// is fine for login",
        ],
        "correct": 1,
        "explanation": "Lookalike domains replace letters with similar-looking characters. Always inspect the full domain carefully.",
    },
    {
        "id": "q_password_strength",
        "question": "Which password is strongest?",
        "options": [
            "P@ssword1",
            "correct-horse-battery-staple",
            "Tr0ub4dor&3",
            "password123",
        ],
        "correct": 1,
        "explanation": "A long passphrase with multiple words beats short complex passwords — it has higher entropy and is easier to remember.",
    },
    {
        "id": "q_mfa",
        "question": "An attacker has your password. What stops them if you have MFA enabled?",
        "options": [
            "Nothing — MFA can be bypassed",
            "The second factor (token/app) they don't have",
            "Your firewall",
            "Account lockout after 3 attempts",
        ],
        "correct": 1,
        "explanation": "MFA requires a second factor the attacker doesn't possess. It stops most credential-stuffing attacks.",
    },
    {
        "id": "q_social_eng",
        "question": "A caller claims to be from IT and says your account will be deleted unless you provide your password now. You should:",
        "options": [
            "Provide the password — IT needs it",
            "Hang up and call IT via the official number",
            "Ask them to email you instead",
            "Change your password first, then tell them",
        ],
        "correct": 1,
        "explanation": "Legitimate IT staff never ask for your password. Always verify by calling back on a known number.",
    },
]


class AwarenessSim(BaseModule):
    """Security awareness simulation and training engine."""

    def __init__(self):
        super().__init__(module_name="awareness_sim")

    # ── Phishing simulation ────────────────────────────────────────────────────

    def list_scenarios(self, category: str | None = None) -> list[dict[str, Any]]:
        """List available phishing/social engineering scenarios."""
        if category:
            return [s for s in _PHISHING_SCENARIOS if s["category"] == category.upper()]
        return _PHISHING_SCENARIOS

    def render_scenario(
        self,
        scenario_id: str,
        org: str = "Acme Corp",
        name: str = "Employee",
        domain: str = "acme.com",
    ) -> dict[str, Any]:
        """Render a phishing scenario with org-specific substitutions."""
        scenario = next((s for s in _PHISHING_SCENARIOS if s["id"] == scenario_id), None)
        if scenario is None:
            return {"error": f"Unknown scenario: {scenario_id}"}

        ctx = {
            "name": name,
            "org": org,
            "domain": domain,
            "phish_domain": f"{domain.split('.')[0]}-secure.net",
            "lookalike_domain": domain.replace("o", "0").replace("l", "1"),
            "token": f"{random.randint(100000, 999999):x}",
            "ceo_name": "Alex Johnson",
            "fake_vendor": "Global Solutions LLC",
            "fake_account": "****4821",
            "fake_name": "Mike from IT",
            "fake_team": "Security Operations",
        }

        rendered: dict[str, Any] = {**scenario}
        for key in ("body_template", "subject", "sender_spoof", "script_template", "scenario"):
            if key in rendered and isinstance(rendered[key], str):
                try:
                    rendered[key] = rendered[key].format(**ctx)
                except KeyError:
                    pass

        self.log(f"SCENARIO_RENDERED: {scenario_id} for {org}")
        return rendered

    # ── Quiz ──────────────────────────────────────────────────────────────────

    def get_quiz(self, count: int = 4) -> list[dict[str, Any]]:
        """Return a randomized quiz set (without correct answer revealed)."""
        questions = random.sample(_QUIZ_QUESTIONS, min(count, len(_QUIZ_QUESTIONS)))
        return [
            {
                "id": q["id"],
                "question": q["question"],
                "options": q["options"],
            }
            for q in questions
        ]

    def check_answer(self, question_id: str, answer_index: int) -> dict[str, Any]:
        """Check a quiz answer and return result with explanation."""
        q = next((x for x in _QUIZ_QUESTIONS if x["id"] == question_id), None)
        if q is None:
            return {"error": f"Unknown question: {question_id}"}
        correct = q["correct"] == answer_index
        return {
            "question_id": question_id,
            "correct": correct,
            "correct_index": q["correct"],
            "explanation": q["explanation"],
        }

    # ── Reporting ─────────────────────────────────────────────────────────────

    def campaign_report(
        self,
        campaign_name: str,
        targets_sent: int,
        clicked: int,
        submitted_creds: int,
        reported: int,
    ) -> dict[str, Any]:
        """Generate a phishing campaign awareness report."""
        click_rate = (clicked / targets_sent * 100) if targets_sent else 0
        cred_rate = (submitted_creds / targets_sent * 100) if targets_sent else 0
        report_rate = (reported / targets_sent * 100) if targets_sent else 0

        risk = "HIGH" if cred_rate > 10 else "MEDIUM" if cred_rate > 3 else "LOW"
        self.log(f"CAMPAIGN_REPORT: {campaign_name} risk={risk}")
        return {
            "campaign": campaign_name,
            "targets_sent": targets_sent,
            "metrics": {
                "click_rate_pct": round(click_rate, 1),
                "cred_submission_rate_pct": round(cred_rate, 1),
                "report_rate_pct": round(report_rate, 1),
            },
            "risk_level": risk,
            "recommendations": self._recommendations(cred_rate, report_rate),
        }

    @staticmethod
    def _recommendations(cred_rate: float, report_rate: float) -> list[str]:
        recs = []
        if cred_rate > 10:
            recs.append("Mandatory phishing awareness training for all staff immediately")
        if cred_rate > 3:
            recs.append("Deploy browser-based phishing warnings and URL reputation filtering")
        if report_rate < 5:
            recs.append("Increase visibility of the 'Report Phishing' button in email client")
        recs.append("Enforce MFA on all accounts to limit credential theft impact")
        return recs
