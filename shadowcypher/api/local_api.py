"""
Local REST API for Guardian Android — runs on desktop, exposes device/scan data.
All endpoints require Bearer token auth (from operator config).
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Optional
from fastapi import FastAPI, Depends, HTTPException, status, Header
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn
from shadowcypher.core.logger import logger
from shadowcypher.core.config import config


# ── Data Models ──────────────────────────────────────────────────────────

class Me(BaseModel):
	email: str
	plan: Optional[str]
	effective_plan: str
	in_trial: bool
	trial_days_remaining: Optional[int]


class Agent(BaseModel):
	id: str
	hostname: str
	online: bool
	last_seen_at: Optional[str]
	os: Optional[str] = None
	agent_version: Optional[str] = None


class AgentsResponse(BaseModel):
	agents: list[Agent]


class Device(BaseModel):
	ip: Optional[str]
	hostname: Optional[str]
	mac: Optional[str]
	device_type: str = "unknown"
	vendor: Optional[str]
	status: Optional[str] = None


class Incident(BaseModel):
	id: str
	category: Optional[str]
	severity: Optional[str]
	title: Optional[str]
	created_at: str
	acknowledged: bool


class CveAlert(BaseModel):
	cve_id: str
	severity: Optional[str]
	description: Optional[str]
	affected_device: Optional[str]


class GuardianSummary(BaseModel):
	agents: list[Agent]
	devices: list[Device]
	incidents: list[Incident]
	cve_alerts: list[CveAlert]
	last_scan_at: Optional[str]


class ScanResponse(BaseModel):
	success: Optional[bool]
	message: Optional[str]


class Mission(BaseModel):
	id: str
	agent_id: str
	status: str
	created_at: str
	started_at: Optional[str]
	completed_at: Optional[str]
	result_output: Optional[str]
	exit_code: Optional[int]


class CreateMissionRequest(BaseModel):
	script: str
	label: Optional[str]


class CreateMissionResponse(BaseModel):
	mission_id: str
	status: str


class MissionListResponse(BaseModel):
	missions: list[Mission]


class ChatRequest(BaseModel):
	query: str
	context: Optional[str] = None


class ChatResponse(BaseModel):
	response: str
	confidence: float = 0.8


# ── FastAPI App ──────────────────────────────────────────────────────────

app = FastAPI(title="ShadowCypher Guardian API", version="1.0")

app.add_middleware(
	CORSMiddleware,
	allow_origins=["*"],
	allow_credentials=True,
	allow_methods=["*"],
	allow_headers=["*"],
)


def verify_token(authorization: str = Header(None)) -> str:
	"""Verify Bearer token from Authorization header."""
	if not authorization:
		raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing Authorization header")

	parts = authorization.split()
	if len(parts) != 2 or parts[0].lower() != "bearer":
		raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid Authorization header format")

	token = parts[1]
	# Reload config each request to pick up changes
	config.load_from_json()
	expected_token = config.get("identity", "handle", default="operator")

	if token != expected_token:
		raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invalid API token")

	return token


# ── Endpoints ────────────────────────────────────────────────────────────

@app.get("/v1/me", response_model=Me)
async def get_me(token: str = Depends(verify_token)):
	"""Get operator profile."""
	return Me(
		email="operator@shadowcypher.site",
		plan="personal",
		effective_plan="personal",
		in_trial=False,
		trial_days_remaining=None,
	)


@app.get("/v1/guardian/summary", response_model=GuardianSummary)
async def get_summary(token: str = Depends(verify_token)):
	"""Get Guardian summary: devices, incidents, CVEs, agents."""
	now = datetime.now(timezone.utc).isoformat()

	# TODO: Pull from Guardian page / KG instead of mock data
	return GuardianSummary(
		agents=[
			Agent(
				id="agent-001",
				hostname="localhost",
				online=True,
				last_seen_at=now,
				os="Linux",
				agent_version="1.0.0",
			)
		],
		devices=[
			Device(
				ip="192.168.1.1",
				hostname="router",
				mac="00:11:22:33:44:55",
				device_type="router",
				vendor="Netgear",
				status="online",
			),
			Device(
				ip="192.168.1.100",
				hostname="desktop",
				mac="aa:bb:cc:dd:ee:ff",
				device_type="desktop",
				vendor="Unknown",
				status="online",
			),
		],
		incidents=[
			Incident(
				id=str(uuid.uuid4()),
				category="port_scan",
				severity="medium",
				title="Unusual port scan detected from 192.168.1.50",
				created_at=now,
				acknowledged=False,
			)
		],
		cve_alerts=[
			CveAlert(
				cve_id="CVE-2024-1234",
				severity="high",
				description="Remote code execution in OpenSSH",
				affected_device="router",
			)
		],
		last_scan_at=now,
	)


@app.get("/v1/incidents", response_model=list[Incident])
async def get_incidents(token: str = Depends(verify_token)):
	"""Get all incidents."""
	now = datetime.now(timezone.utc).isoformat()
	return [
		Incident(
			id=str(uuid.uuid4()),
			category="port_scan",
			severity="medium",
			title="Unusual port scan detected",
			created_at=now,
			acknowledged=False,
		)
	]


@app.post("/v1/incidents/{incident_id}/acknowledge")
async def acknowledge_incident(incident_id: str, token: str = Depends(verify_token)):
	"""Mark incident as acknowledged."""
	return {"status": "acknowledged"}


@app.get("/v1/agents", response_model=AgentsResponse)
async def get_agents(token: str = Depends(verify_token)):
	"""Get all agents (autonomous workers)."""
	now = datetime.now(timezone.utc).isoformat()
	return AgentsResponse(
		agents=[
			Agent(
				id="agent-001",
				hostname="localhost",
				online=True,
				last_seen_at=now,
				os="Linux",
				agent_version="1.0.0",
			),
			Agent(
				id="agent-002",
				hostname="remote-scanner",
				online=False,
				last_seen_at=None,
				os="Linux",
				agent_version="1.0.0",
			),
		]
	)


@app.post("/v1/scans", response_model=ScanResponse)
async def trigger_scan(token: str = Depends(verify_token)):
	"""Trigger a network scan (from Guardian page)."""
	logger.info("local_api", "Scan triggered from Guardian Android app")
	# TODO: Trigger Guardian.quick_scan() here
	return ScanResponse(success=True, message="Scan initiated")


@app.post("/v1/agents/{agent_id}/missions", response_model=CreateMissionResponse)
async def create_mission(
	agent_id: str, req: CreateMissionRequest, token: str = Depends(verify_token)
):
	"""Create a mission on an agent."""
	mission_id = str(uuid.uuid4())
	logger.info("local_api", f"Mission {mission_id} created for agent {agent_id}")
	# TODO: Route to actual agent executor
	return CreateMissionResponse(mission_id=mission_id, status="pending")


@app.get("/v1/missions/{mission_id}", response_model=Mission)
async def get_mission(mission_id: str, token: str = Depends(verify_token)):
	"""Get mission status and output."""
	return Mission(
		id=mission_id,
		agent_id="agent-001",
		status="completed",
		created_at=datetime.now(timezone.utc).isoformat(),
		started_at=datetime.now(timezone.utc).isoformat(),
		completed_at=datetime.now(timezone.utc).isoformat(),
		result_output="Scan complete. 3 devices found.",
		exit_code=0,
	)


@app.get("/v1/missions", response_model=MissionListResponse)
async def list_missions(agent_id: Optional[str] = None, token: str = Depends(verify_token)):
	"""List all missions, optionally filtered by agent."""
	return MissionListResponse(missions=[])


@app.post("/v1/llm/chat", response_model=ChatResponse)
async def llm_chat(req: ChatRequest, token: str = Depends(verify_token)):
	"""Chat with local LLM (for Android Shadow AI app)."""
	# TODO: Route to actual Ollama/LLM backend
	# For now, return mock response
	prompt = req.query
	mock_responses = {
		"hello": "Hi there! I'm Shadow, your personal security assistant. How can I help protect your network?",
		"status": "Your network looks secure. No incidents detected in the last 24 hours.",
		"scan": "Starting a quick network scan. I'll report any new devices or open ports.",
		"": "I didn't catch that. Try asking about your network status, running a scan, or checking for threats.",
	}

	response = None
	for key in mock_responses:
		if key.lower() in prompt.lower():
			response = mock_responses[key]
			break

	if not response:
		response = mock_responses[""]

	logger.info("local_api", f"LLM query: {prompt[:50]}... → {response[:50]}...")
	return ChatResponse(response=response, confidence=0.85)


@app.get("/health")
async def health():
	"""Health check endpoint (no auth required)."""
	return {"status": "ok", "service": "Guardian API"}


# ── Server Functions ────────────────────────────────────────────────────

def start_server(host: str = "0.0.0.0", port: int = 9999):
	"""Start the local API server."""
	logger.info("local_api", f"Starting Guardian API on {host}:{port}")
	uvicorn.run(app, host=host, port=port, log_level="info")


if __name__ == "__main__":
	start_server()
