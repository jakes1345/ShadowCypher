"""
Local REST API for Guardian Android — runs on desktop, exposes device/scan data.
All endpoints require Bearer token auth (from operator config).
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Optional
from fastapi import FastAPI, Depends, HTTPException, status, Header, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn
from shadowcypher.core.logger import logger
from shadowcypher.core.config import config
from shadowcypher.api.websocket_server import subscribe_to_mission


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
	device_type: Optional[str] = "unknown"
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


class ScheduledMissionRequest(BaseModel):
	mission_type: str
	frequency: str  # hourly, daily, weekly, monthly
	target: Optional[str] = None
	description: Optional[str] = None


class ScheduledMissionResponse(BaseModel):
	id: str
	mission_type: str
	frequency: str
	enabled: bool
	target: Optional[str]
	last_run_at: Optional[str]
	next_run_at: Optional[str]
	run_count: int
	created_at: str
	description: Optional[str]


class ScheduleListResponse(BaseModel):
	schedules: list[ScheduledMissionResponse]


class IncidentRuleRequest(BaseModel):
	name: str
	condition: str
	severity_threshold: str
	actions: list[str]
	description: Optional[str] = None


class IncidentRuleResponse(BaseModel):
	id: str
	name: str
	condition: str
	severity_threshold: str
	actions: list[str]
	enabled: bool
	created_at: str
	description: Optional[str]


class RuleListResponse(BaseModel):
	rules: list[IncidentRuleResponse]


class ProcessIncidentRequest(BaseModel):
	incident_type: str
	severity: str
	details: dict


class ModuleResultResponse(BaseModel):
	module_type: str
	timestamp: str
	target: str
	status: str
	findings: list[dict]
	execution_time: float
	error: Optional[str] = None


class ModuleScanRequest(BaseModel):
	modules: Optional[list[str]] = None  # specific modules, or None for all
	host: Optional[str] = "localhost"
	target_path: Optional[str] = "/tmp"


class ModuleSummaryResponse(BaseModel):
	total_scans: int
	total_findings: int
	by_severity: dict
	by_module: dict


class ActionHistoryResponse(BaseModel):
	action: str
	target: str
	success: bool
	message: str
	timestamp: str


class ActionStatisticsResponse(BaseModel):
	total_actions: int
	success_rate: float
	by_action: dict
	by_result: dict
	blocked_ips: list[str]
	quarantined_files: list[str]


# ── FastAPI App ──────────────────────────────────────────────────────────

app = FastAPI(title="ShadowCypher Guardian API", version="1.0")

app.add_middleware(
	CORSMiddleware,
	allow_origins=["*"],
	allow_credentials=True,
	allow_methods=["*"],
	allow_headers=["*"],
)


@app.on_event("startup")
async def startup_event():
	"""Initialize scheduler and audit agent on API startup."""
	try:
		from shadowcypher.core.mission_executor import setup_scheduler_integration
		setup_scheduler_integration()
	except Exception as e:
		logger.error("local_api", f"Failed to initialize scheduler: {e}")

	try:
		from shadowcypher.core.module_audit_agent import get_module_audit_agent
		agent = get_module_audit_agent()
		agent.start()
	except Exception as e:
		logger.error("local_api", f"Failed to initialize audit agent: {e}")


def verify_token(authorization: str = Header(None)) -> str:
	"""Verify Bearer token from Authorization header."""
	if not authorization:
		raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing Authorization header")

	parts = authorization.split()
	if len(parts) != 2 or parts[0].lower() != "bearer":
		raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid Authorization header format")

	token = parts[1]
	# Get the operator handle from config
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
	from shadowcypher.core.guardian_service import get_guardian_service

	guardian = get_guardian_service()

	# Get real data from Guardian scans and knowledge graph
	device_data = guardian.get_recent_devices()
	devices = [
		Device(
			ip=d.get("ip"),
			hostname=d.get("hostname"),
			mac=d.get("mac"),
			device_type=d.get("device_type") or "unknown",
			vendor=d.get("vendor"),
			status=d.get("status"),
		)
		for d in device_data
	]

	incident_data = guardian.get_incidents(limit=10)
	incidents = [
		Incident(
			id=inc.get("id", str(uuid.uuid4())),
			category=inc.get("category"),
			severity=inc.get("severity"),
			title=inc.get("title"),
			created_at=inc.get("created_at", datetime.now(timezone.utc).isoformat()),
			acknowledged=inc.get("acknowledged", False),
		)
		for inc in incident_data
	]

	cve_data = guardian.get_cve_alerts(limit=5)
	cve_alerts = [
		CveAlert(
			cve_id=alert.get("cve_id"),
			severity=alert.get("severity"),
			description=alert.get("description"),
			affected_device=alert.get("affected_device"),
		)
		for alert in cve_data
	]

	agent_data = guardian.get_agents()
	agents = [
		Agent(
			id=agent.get("id"),
			hostname=agent.get("hostname"),
			online=agent.get("online", True),
			last_seen_at=agent.get("last_seen_at"),
			os=agent.get("os"),
			agent_version=agent.get("agent_version"),
		)
		for agent in agent_data
	]

	return GuardianSummary(
		agents=agents,
		devices=devices,
		incidents=incidents,
		cve_alerts=cve_alerts,
		last_scan_at=guardian.get_last_scan_time(),
	)


@app.get("/v1/incidents", response_model=list[Incident])
async def get_incidents(token: str = Depends(verify_token)):
	"""Get all incidents."""
	from shadowcypher.core.guardian_service import get_guardian_service

	guardian = get_guardian_service()
	incident_data = guardian.get_incidents(limit=50)

	return [
		Incident(
			id=inc.get("id", str(uuid.uuid4())),
			category=inc.get("category"),
			severity=inc.get("severity"),
			title=inc.get("title"),
			created_at=inc.get("created_at", datetime.now(timezone.utc).isoformat()),
			acknowledged=inc.get("acknowledged", False),
		)
		for inc in incident_data
	]


@app.post("/v1/incidents/{incident_id}/acknowledge")
async def acknowledge_incident(incident_id: str, token: str = Depends(verify_token)):
	"""Mark incident as acknowledged."""
	return {"status": "acknowledged"}


@app.get("/v1/agents", response_model=AgentsResponse)
async def get_agents(token: str = Depends(verify_token)):
	"""Get all agents (autonomous workers)."""
	from shadowcypher.core.guardian_service import get_guardian_service

	guardian = get_guardian_service()
	agent_data = guardian.get_agents()

	return AgentsResponse(
		agents=[
			Agent(
				id=agent.get("id"),
				hostname=agent.get("hostname"),
				online=agent.get("online", True),
				last_seen_at=agent.get("last_seen_at"),
				os=agent.get("os"),
				agent_version=agent.get("agent_version"),
			)
			for agent in agent_data
		]
	)


@app.post("/v1/scans", response_model=ScanResponse)
async def trigger_scan(subnet: Optional[str] = None, token: str = Depends(verify_token)):
	"""Trigger a network scan (from Guardian page or Android app)."""
	from shadowcypher.core.mission_executor import get_mission_executor

	try:
		executor = get_mission_executor()
		mission_id = executor.execute_network_scan(subnet=subnet)
		logger.info("local_api", f"Scan triggered from Android app (mission {mission_id})")
		return ScanResponse(success=True, message=f"Scan initiated (mission {mission_id})")
	except Exception as e:
		logger.error("local_api", f"Failed to trigger scan: {e}")
		return ScanResponse(success=False, message=f"Scan failed: {e}")


@app.post("/v1/agents/{agent_id}/missions", response_model=CreateMissionResponse)
async def create_mission(
	agent_id: str, req: CreateMissionRequest, token: str = Depends(verify_token)
):
	"""Create a mission on an agent."""
	mission_id = str(uuid.uuid4())
	logger.info("local_api", f"Mission {mission_id} created for agent {agent_id}")
	# TODO: Route to actual agent executor
	return CreateMissionResponse(mission_id=mission_id, status="pending")


@app.get("/v1/missions/{mission_id}", response_model=dict)
async def get_mission(mission_id: str, token: str = Depends(verify_token)):
	"""Get mission status and output."""
	from shadowcypher.core.mission_executor import get_mission_executor

	executor = get_mission_executor()
	mission = executor.get_mission(mission_id)

	if not mission:
		raise HTTPException(status_code=404, detail=f"Mission {mission_id} not found")

	return {
		"id": mission.id,
		"type": mission.type,
		"target": mission.target,
		"status": mission.status,
		"created_at": mission.created_at,
		"started_at": mission.started_at,
		"completed_at": mission.completed_at,
		"result_output": mission.result_output,
		"devices_found": mission.devices_found,
		"incidents_found": mission.incidents_found,
		"exit_code": mission.exit_code,
	}


@app.get("/v1/missions", response_model=dict)
async def list_missions(status: Optional[str] = None, limit: int = 50, token: str = Depends(verify_token)):
	"""List all missions, optionally filtered by status."""
	from shadowcypher.core.mission_executor import get_mission_executor

	executor = get_mission_executor()
	missions = executor.list_missions(status=status, limit=limit)

	return {
		"missions": [
			{
				"id": m.id,
				"type": m.type,
				"target": m.target,
				"status": m.status,
				"created_at": m.created_at,
				"started_at": m.started_at,
				"completed_at": m.completed_at,
				"devices_found": m.devices_found,
				"incidents_found": m.incidents_found,
			}
			for m in missions
		],
		"total": len(missions),
	}


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


@app.get("/v1/scan-history", response_model=list[dict])
async def get_scan_history(scan_type: Optional[str] = None, limit: int = 10, token: str = Depends(verify_token)):
	"""Get historical scans from the database."""
	from shadowcypher.core.scan_history import get_scan_history

	history = get_scan_history()
	scans = history.get_recent_scans(scan_type=scan_type, limit=limit)
	return scans


@app.get("/v1/scan-history/{scan_id}", response_model=dict)
async def get_scan_detail(scan_id: str, token: str = Depends(verify_token)):
	"""Get detailed results of a specific scan."""
	from shadowcypher.core.scan_history import get_scan_history

	history = get_scan_history()
	detail = history.get_scan_details(scan_id)
	if not detail:
		raise HTTPException(status_code=404, detail=f"Scan {scan_id} not found")
	return detail


@app.get("/v1/statistics", response_model=dict)
async def get_statistics(token: str = Depends(verify_token)):
	"""Get aggregate statistics about all scans."""
	from shadowcypher.core.scan_history import get_scan_history

	history = get_scan_history()
	stats = history.get_statistics()
	return stats


@app.get("/v1/analytics/timeline", response_model=dict)
async def get_timeline(days: int = 30, token: str = Depends(verify_token)):
	"""Get device discovery timeline over past N days."""
	from shadowcypher.core.scan_analytics import get_scan_analytics

	analytics = get_scan_analytics()
	return analytics.get_device_discovery_timeline(days=days)


@app.get("/v1/analytics/risk-distribution", response_model=dict)
async def get_risk_dist(token: str = Depends(verify_token)):
	"""Get distribution of devices by risk level."""
	from shadowcypher.core.scan_analytics import get_scan_analytics

	analytics = get_scan_analytics()
	return analytics.get_risk_distribution()


@app.get("/v1/analytics/threats", response_model=dict)
async def get_threats(token: str = Depends(verify_token)):
	"""Get aggregate threat summary."""
	from shadowcypher.core.scan_analytics import get_scan_analytics

	analytics = get_scan_analytics()
	return analytics.get_threat_summary()


@app.get("/v1/analytics/top-devices", response_model=dict)
async def get_top_devices(limit: int = 10, token: str = Depends(verify_token)):
	"""Get devices with most incidents."""
	from shadowcypher.core.scan_analytics import get_scan_analytics

	analytics = get_scan_analytics()
	return {"top_devices": analytics.get_top_devices_by_incident_count(limit=limit)}


@app.get("/v1/analytics/effectiveness", response_model=dict)
async def get_effectiveness(token: str = Depends(verify_token)):
	"""Get scan effectiveness metrics."""
	from shadowcypher.core.scan_analytics import get_scan_analytics

	analytics = get_scan_analytics()
	return analytics.get_scan_effectiveness()


@app.post("/v1/schedules", response_model=ScheduledMissionResponse)
async def create_schedule(req: ScheduledMissionRequest, token: str = Depends(verify_token)):
	"""Create a new recurring mission schedule."""
	from shadowcypher.core.mission_scheduler import get_mission_scheduler

	scheduler = get_mission_scheduler()
	schedule_id = scheduler.create_schedule(
		mission_type=req.mission_type,
		frequency=req.frequency,
		target=req.target,
		description=req.description,
	)

	schedule = scheduler.get_schedule(schedule_id)
	from dataclasses import asdict
	return asdict(schedule)


@app.get("/v1/schedules", response_model=ScheduleListResponse)
async def list_schedules(token: str = Depends(verify_token)):
	"""List all mission schedules."""
	from shadowcypher.core.mission_scheduler import get_mission_scheduler

	scheduler = get_mission_scheduler()
	schedules = scheduler.list_schedules()

	from dataclasses import asdict
	return ScheduleListResponse(
		schedules=[asdict(s) for s in schedules]
	)


@app.get("/v1/schedules/{schedule_id}", response_model=ScheduledMissionResponse)
async def get_schedule(schedule_id: str, token: str = Depends(verify_token)):
	"""Get a schedule by ID."""
	from shadowcypher.core.mission_scheduler import get_mission_scheduler

	scheduler = get_mission_scheduler()
	schedule = scheduler.get_schedule(schedule_id)

	if not schedule:
		raise HTTPException(status_code=404, detail=f"Schedule {schedule_id} not found")

	from dataclasses import asdict
	return asdict(schedule)


@app.put("/v1/schedules/{schedule_id}", response_model=ScheduledMissionResponse)
async def update_schedule(
	schedule_id: str, updates: dict, token: str = Depends(verify_token)
):
	"""Update a schedule."""
	from shadowcypher.core.mission_scheduler import get_mission_scheduler

	scheduler = get_mission_scheduler()
	if not scheduler.update_schedule(schedule_id, **updates):
		raise HTTPException(status_code=404, detail=f"Schedule {schedule_id} not found")

	schedule = scheduler.get_schedule(schedule_id)
	from dataclasses import asdict
	return asdict(schedule)


@app.delete("/v1/schedules/{schedule_id}")
async def delete_schedule(schedule_id: str, token: str = Depends(verify_token)):
	"""Delete a schedule."""
	from shadowcypher.core.mission_scheduler import get_mission_scheduler

	scheduler = get_mission_scheduler()
	if not scheduler.delete_schedule(schedule_id):
		raise HTTPException(status_code=404, detail=f"Schedule {schedule_id} not found")

	return {"status": "deleted", "schedule_id": schedule_id}


@app.post("/v1/schedules/start")
async def start_scheduler(token: str = Depends(verify_token)):
	"""Start the mission scheduler."""
	from shadowcypher.core.mission_scheduler import get_mission_scheduler

	scheduler = get_mission_scheduler()
	scheduler.start()
	return {"status": "started"}


@app.post("/v1/incident-rules", response_model=IncidentRuleResponse)
async def create_incident_rule(req: IncidentRuleRequest, token: str = Depends(verify_token)):
	"""Create a new incident response rule."""
	from shadowcypher.core.incident_response import get_incident_response_engine

	engine = get_incident_response_engine()
	rule_id = engine.create_rule(
		name=req.name,
		condition=req.condition,
		severity_threshold=req.severity_threshold,
		actions=req.actions,
		description=req.description,
	)

	rule = engine.get_rule(rule_id)
	from dataclasses import asdict
	return asdict(rule)


@app.get("/v1/incident-rules", response_model=RuleListResponse)
async def list_incident_rules(token: str = Depends(verify_token)):
	"""List all incident response rules."""
	from shadowcypher.core.incident_response import get_incident_response_engine

	engine = get_incident_response_engine()
	rules = engine.list_rules()

	from dataclasses import asdict
	return RuleListResponse(rules=[asdict(r) for r in rules])


@app.get("/v1/incident-rules/{rule_id}", response_model=IncidentRuleResponse)
async def get_incident_rule(rule_id: str, token: str = Depends(verify_token)):
	"""Get an incident response rule by ID."""
	from shadowcypher.core.incident_response import get_incident_response_engine

	engine = get_incident_response_engine()
	rule = engine.get_rule(rule_id)

	if not rule:
		raise HTTPException(status_code=404, detail=f"Rule {rule_id} not found")

	from dataclasses import asdict
	return asdict(rule)


@app.put("/v1/incident-rules/{rule_id}", response_model=IncidentRuleResponse)
async def update_incident_rule(
	rule_id: str, updates: dict, token: str = Depends(verify_token)
):
	"""Update an incident response rule."""
	from shadowcypher.core.incident_response import get_incident_response_engine

	engine = get_incident_response_engine()
	if not engine.update_rule(rule_id, **updates):
		raise HTTPException(status_code=404, detail=f"Rule {rule_id} not found")

	rule = engine.get_rule(rule_id)
	from dataclasses import asdict
	return asdict(rule)


@app.delete("/v1/incident-rules/{rule_id}")
async def delete_incident_rule(rule_id: str, token: str = Depends(verify_token)):
	"""Delete an incident response rule."""
	from shadowcypher.core.incident_response import get_incident_response_engine

	engine = get_incident_response_engine()
	if not engine.delete_rule(rule_id):
		raise HTTPException(status_code=404, detail=f"Rule {rule_id} not found")

	return {"status": "deleted", "rule_id": rule_id}


@app.post("/v1/modules/scan", response_model=list[ModuleResultResponse])
async def scan_modules(req: ModuleScanRequest, token: str = Depends(verify_token)):
	"""Run Guardian security modules (fail2ban, host_audit, tls_audit, yara_scan)."""
	from shadowcypher.core.guardian_modules import get_guardian_modules
	from dataclasses import asdict

	modules = get_guardian_modules()

	if req.modules and len(req.modules) > 0:
		# Run specific modules
		results = []
		for module_name in req.modules:
			if module_name == "fail2ban":
				results.append(modules.run_fail2ban_scan(req.host))
			elif module_name == "host_audit":
				results.append(modules.run_host_audit(req.host))
			elif module_name == "tls_audit":
				results.append(modules.run_tls_audit(req.host))
			elif module_name == "yara_scan":
				results.append(modules.run_yara_scan(req.target_path))
	else:
		# Run all modules
		results = modules.run_all_modules(req.host)

	return [asdict(r) for r in results]


@app.get("/v1/modules/findings", response_model=list[dict])
async def get_module_findings(module_type: Optional[str] = None, limit: int = 50, token: str = Depends(verify_token)):
	"""Get recent findings from Guardian module scans."""
	from shadowcypher.core.guardian_modules import get_guardian_modules

	modules = get_guardian_modules()
	findings = modules.get_recent_findings(module_type=module_type, limit=limit)

	return findings


@app.get("/v1/modules/summary", response_model=ModuleSummaryResponse)
async def get_modules_summary(token: str = Depends(verify_token)):
	"""Get summary of all Guardian module scans."""
	from shadowcypher.core.guardian_modules import get_guardian_modules

	modules = get_guardian_modules()
	summary = modules.get_module_summary()

	return summary


@app.post("/v1/audit/start")
async def start_audit_agent(token: str = Depends(verify_token)):
	"""Start the automated module audit agent."""
	from shadowcypher.core.module_audit_agent import get_module_audit_agent

	agent = get_module_audit_agent()
	agent.start()

	return {"status": "started"}


@app.post("/v1/audit/stop")
async def stop_audit_agent(token: str = Depends(verify_token)):
	"""Stop the automated module audit agent."""
	from shadowcypher.core.module_audit_agent import get_module_audit_agent

	agent = get_module_audit_agent()
	agent.stop()

	return {"status": "stopped"}


@app.get("/v1/audit/status")
async def get_audit_status(token: str = Depends(verify_token)):
	"""Get automated audit agent status."""
	from shadowcypher.core.module_audit_agent import get_module_audit_agent

	agent = get_module_audit_agent()
	return agent.get_status()


@app.get("/v1/actions/history", response_model=list[ActionHistoryResponse])
async def get_action_history(limit: int = 100, token: str = Depends(verify_token)):
	"""Get history of executed security actions."""
	from shadowcypher.core.action_executor import get_action_executor

	executor = get_action_executor()
	return executor.get_action_history(limit=limit)


@app.get("/v1/actions/statistics", response_model=ActionStatisticsResponse)
async def get_action_statistics(token: str = Depends(verify_token)):
	"""Get security action execution statistics."""
	from shadowcypher.core.action_executor import get_action_executor

	executor = get_action_executor()
	return executor.get_statistics()


@app.post("/v1/actions/block-ip")
async def block_ip(ip: str, reason: Optional[str] = None, token: str = Depends(verify_token)):
	"""Block an IP address."""
	from shadowcypher.core.action_executor import get_action_executor

	executor = get_action_executor()
	result = executor.block_ip(ip, reason=reason or "Manual block")

	return {
		"action": result.action,
		"target": result.target,
		"success": result.success,
		"message": result.message,
		"timestamp": result.timestamp
	}


@app.post("/v1/actions/quarantine-file")
async def quarantine_file(file_path: str, reason: Optional[str] = None, token: str = Depends(verify_token)):
	"""Quarantine a suspicious file."""
	from shadowcypher.core.action_executor import get_action_executor

	executor = get_action_executor()
	result = executor.quarantine_file(file_path, reason=reason or "Manual quarantine")

	return {
		"action": result.action,
		"target": result.target,
		"success": result.success,
		"message": result.message,
		"timestamp": result.timestamp
	}


@app.post("/v1/actions/isolate-device")
async def isolate_device(device_ip: str, reason: Optional[str] = None, token: str = Depends(verify_token)):
	"""Isolate a device from the network."""
	from shadowcypher.core.action_executor import get_action_executor

	executor = get_action_executor()
	result = executor.isolate_device(device_ip, reason=reason or "Manual isolation")

	return {
		"action": result.action,
		"target": result.target,
		"success": result.success,
		"message": result.message,
		"timestamp": result.timestamp
	}


@app.post("/v1/incidents/process")
async def process_incident(req: ProcessIncidentRequest, token: str = Depends(verify_token)):
	"""Process an incident and trigger automated responses."""
	from shadowcypher.core.incident_response import get_incident_response_engine
	import uuid

	engine = get_incident_response_engine()
	incident_id = f"incident-{uuid.uuid4().hex[:8]}"

	response_id = engine.process_incident(
		incident_id=incident_id,
		incident_type=req.incident_type,
		severity=req.severity,
		details=req.details,
	)

	return {
		"incident_id": incident_id,
		"response_id": response_id,
		"status": "processed" if response_id else "no_match",
	}


@app.websocket("/ws/missions/{mission_id}")
async def websocket_mission_updates(mission_id: str, websocket: WebSocket):
	"""WebSocket endpoint for real-time mission updates.

	Clients connect and receive updates as mission status changes.
	Message types:
	  - initial_state: Current mission status on connect
	  - mission_update: Status change (mission status changed)
	  - mission_status: Response to get_status query
	"""
	await subscribe_to_mission(mission_id, websocket)


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
