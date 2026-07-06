"""
Shadow AI Voice Command Engine — Process voice commands for Guardian operations.
Converts natural language requests into Guardian API calls and responses.
"""

import re
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum

from shadowcypher.core.logger import logger


class VoiceCommandType(str, Enum):
    """Types of voice commands Shadow AI can handle."""
    STATUS = "status"  # "What's my network status?"
    INCIDENTS = "incidents"  # "Any incidents?"
    DEVICES = "devices"  # "What devices are online?"
    THREATS = "threats"  # "What threats detected?"
    SCAN = "scan"  # "Run a scan"
    BLOCK = "block"  # "Block this IP"
    ALERT = "alert"  # "Show recent alerts"
    HELP = "help"  # "What can you do?"


@dataclass
class VoiceCommand:
    """Parsed voice command."""
    type: VoiceCommandType
    confidence: float  # 0.0-1.0
    parameters: Dict[str, str]  # Additional params (IP, device, etc)
    original_text: str
    response: Optional[str] = None


class ShadowAIVoice:
    """Voice command processor for Guardian security operations."""

    def __init__(self):
        self.command_patterns = self._build_patterns()
        self.command_history: List[VoiceCommand] = []

    def process_voice_input(self, audio_text: str) -> VoiceCommand:
        """Process raw voice input and return parsed command."""
        try:
            # Normalize input
            text = audio_text.lower().strip()

            logger.info("shadow_ai", f"Processing voice input: {text}")

            # Try to match against known patterns
            for cmd_type, patterns in self.command_patterns.items():
                for pattern, param_handler in patterns:
                    match = re.search(pattern, text)
                    if match:
                        params = param_handler(match) if param_handler else {}
                        confidence = 0.95  # High confidence for regex match

                        command = VoiceCommand(
                            type=cmd_type,
                            confidence=confidence,
                            parameters=params,
                            original_text=text
                        )

                        logger.info("shadow_ai", f"Matched command: {cmd_type}")
                        self.command_history.append(command)
                        return command

            # No match found - return help command
            logger.debug("shadow_ai", "No command match found")
            return VoiceCommand(
                type=VoiceCommandType.HELP,
                confidence=0.0,
                parameters={},
                original_text=text
            )

        except Exception as e:
            logger.error("shadow_ai", f"Voice processing error: {e}")
            return VoiceCommand(
                type=VoiceCommandType.HELP,
                confidence=0.0,
                parameters={},
                original_text=audio_text
            )

    def execute_command(self, command: VoiceCommand, api_client) -> str:
        """Execute voice command via Guardian API and return response."""
        try:
            if command.type == VoiceCommandType.STATUS:
                return self._cmd_status(api_client)
            elif command.type == VoiceCommandType.INCIDENTS:
                return self._cmd_incidents(api_client)
            elif command.type == VoiceCommandType.DEVICES:
                return self._cmd_devices(api_client)
            elif command.type == VoiceCommandType.THREATS:
                return self._cmd_threats(api_client)
            elif command.type == VoiceCommandType.SCAN:
                return self._cmd_scan(api_client, command.parameters)
            elif command.type == VoiceCommandType.BLOCK:
                return self._cmd_block(api_client, command.parameters)
            elif command.type == VoiceCommandType.ALERT:
                return self._cmd_alerts(api_client)
            elif command.type == VoiceCommandType.HELP:
                return self._cmd_help()
            else:
                return "I didn't understand that command. Say 'help' for options."

        except Exception as e:
            logger.error("shadow_ai", f"Command execution error: {e}")
            return f"Error executing command: {e}"

    def _cmd_status(self, api_client) -> str:
        """Get overall security status."""
        try:
            summary = api_client.get_guardian_summary()
            devices = len(summary.get("devices", []))
            incidents = len(summary.get("incidents", []))

            return (
                f"Network status: {devices} devices detected. "
                f"{incidents} incident{'s' if incidents != 1 else ''} recorded. "
                f"System operational and monitoring."
            )
        except Exception as e:
            return f"Unable to get status: {e}"

    def _cmd_incidents(self, api_client) -> str:
        """Get recent incidents."""
        try:
            incidents = api_client.get_incidents(limit=3)

            if not incidents:
                return "No incidents detected. Network is secure."

            response = "Recent incidents: "
            for inc in incidents:
                severity = inc.get("severity", "unknown").upper()
                title = inc.get("title", "Unknown incident")
                response += f"{severity}: {title}. "

            return response

        except Exception as e:
            return f"Unable to get incidents: {e}"

    def _cmd_devices(self, api_client) -> str:
        """Get device status."""
        try:
            summary = api_client.get_guardian_summary()
            devices = summary.get("devices", [])

            if not devices:
                return "No devices detected on network."

            device_count = len(devices)
            online_count = sum(1 for d in devices if d.get("status") == "online")

            return (
                f"Total devices: {device_count}. "
                f"Online: {online_count}. "
                f"Scanning network for vulnerabilities."
            )

        except Exception as e:
            return f"Unable to get devices: {e}"

    def _cmd_threats(self, api_client) -> str:
        """Get threat summary."""
        try:
            threats = api_client.get_threat_summary()

            critical = threats.get("critical_incidents", 0)
            high_risk = threats.get("high_risk_devices", 0)
            unique = threats.get("unique_threat_types", 0)

            if critical == 0 and high_risk == 0:
                return "Threat level: Green. No significant threats detected."

            response = "Threat summary: "
            if critical > 0:
                response += f"{critical} critical incident{'s' if critical > 1 else ''}. "
            if high_risk > 0:
                response += f"{high_risk} high-risk device{'s' if high_risk > 1 else ''}. "
            if unique > 0:
                response += f"{unique} unique threat type{'s' if unique > 1 else ''} detected."

            return response

        except Exception as e:
            return f"Unable to get threats: {e}"

    def _cmd_scan(self, api_client, params: Dict) -> str:
        """Trigger a network scan."""
        try:
            target = params.get("target", "auto-detect")
            api_client.trigger_scan(subnet=target)

            return f"Network scan initiated. Targeting {target}. Scan results will be available in approximately 3 to 5 minutes."

        except Exception as e:
            return f"Unable to trigger scan: {e}"

    def _cmd_block(self, api_client, params: Dict) -> str:
        """Block a malicious IP."""
        try:
            ip = params.get("ip")
            if not ip:
                return "Please specify an IP address to block."

            api_client.block_ip(ip, reason="Voice command")

            return f"Firewall rule created to block {ip}. This host will no longer be able to access your network."

        except Exception as e:
            return f"Unable to block IP: {e}"

    def _cmd_alerts(self, api_client) -> str:
        """Get recent security alerts."""
        try:
            findings = api_client.get_module_findings(limit=5)

            if not findings:
                return "No recent security alerts."

            response = "Recent security alerts: "
            for finding in findings[:3]:  # Top 3
                module = finding.get("module", "Unknown")
                details = finding.get("details", "Unknown alert")
                response += f"{module}: {details}. "

            return response

        except Exception as e:
            return f"Unable to get alerts: {e}"

    def _cmd_help(self) -> str:
        """Show available commands."""
        return (
            "I'm Shadow AI, your voice-controlled security assistant. "
            "You can ask me: "
            "'What's my status?' "
            "'Any incidents?' "
            "'What devices are online?' "
            "'What threats detected?' "
            "'Run a scan' "
            "'Block this IP' "
            "'Recent alerts' "
            "Just speak naturally and I'll help secure your network."
        )

    def _build_patterns(self) -> Dict[VoiceCommandType, List[Tuple]]:
        """Build regex patterns for voice command matching."""
        return {
            VoiceCommandType.STATUS: [
                (r"(status|how am i|what.*status|network.*status)", None),
                (r"(secure|safe)", None),
            ],
            VoiceCommandType.INCIDENTS: [
                (r"(incident|alert|problem|issue)", None),
                (r"(any.*problem|anything wrong)", None),
            ],
            VoiceCommandType.DEVICES: [
                (r"(device|computer|host|machine)", None),
                (r"(what.*online|connected devices)", None),
            ],
            VoiceCommandType.THREATS: [
                (r"(threat|malware|virus|intrusion)", None),
                (r"(security|risk)", None),
            ],
            VoiceCommandType.SCAN: [
                (r"(scan|scan.*network)", self._extract_target),
                (r"(check.*network)", self._extract_target),
            ],
            VoiceCommandType.BLOCK: [
                (r"block\s+(\d+\.\d+\.\d+\.\d+)", self._extract_ip),
                (r"block\s+ip\s+(\d+\.\d+\.\d+\.\d+)", self._extract_ip),
            ],
            VoiceCommandType.ALERT: [
                (r"alert", None),
                (r"recent.*alert", None),
            ],
            VoiceCommandType.HELP: [
                (r"(help|what can you do|capabilities)", None),
            ],
        }

    @staticmethod
    def _extract_ip(match) -> Dict:
        """Extract IP from regex match."""
        return {"ip": match.group(1)}

    @staticmethod
    def _extract_target(match) -> Dict:
        """Extract scan target from regex match."""
        text = match.group(0)
        # Try to extract subnet from text
        subnet_match = re.search(r"(\d+\.\d+\.\d+\.\d+/\d+)", text)
        if subnet_match:
            return {"target": subnet_match.group(1)}
        return {}

    def get_history(self, limit: int = 20) -> List[Dict]:
        """Get voice command history."""
        return [
            {
                "type": cmd.type,
                "confidence": cmd.confidence,
                "input": cmd.original_text,
                "response": cmd.response
            }
            for cmd in self.command_history[-limit:]
        ]


# Singleton instance
_shadow_ai_voice = None


def get_shadow_ai_voice() -> ShadowAIVoice:
    """Get or create Shadow AI voice engine singleton."""
    global _shadow_ai_voice
    if _shadow_ai_voice is None:
        _shadow_ai_voice = ShadowAIVoice()
    return _shadow_ai_voice
