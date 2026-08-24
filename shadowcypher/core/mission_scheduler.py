"""
Mission Scheduler — Schedules recurring scans and automated tasks.
Supports cron-like scheduling with mission persistence.
"""

import json
import os
import threading
import time
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from enum import Enum
from typing import Dict, List, Optional

from shadowcypher.core.logger import logger


class ScheduleFrequency(str, Enum):
    """Supported schedule frequencies."""
    HOURLY = "hourly"
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    ONCE = "once"


@dataclass
class ScheduledMission:
    """Scheduled mission configuration."""
    id: str
    mission_type: str  # "network_scan", "host_audit", "router_scan"
    frequency: str  # "hourly", "daily", "weekly", "monthly"
    enabled: bool = True
    target: Optional[str] = None  # subnet for network scans, host for audits
    last_run_at: Optional[str] = None
    next_run_at: Optional[str] = None
    run_count: int = 0
    created_at: str = None
    description: Optional[str] = None

    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now(timezone.utc).isoformat()


class MissionScheduler:
    """Schedules and runs recurring scanning missions."""

    def __init__(self):
        self.schedules: Dict[str, ScheduledMission] = {}
        self.lock = threading.Lock()
        self.running = False
        self.scheduler_thread: Optional[threading.Thread] = None
        self.on_mission_ready: List[callable] = []
        self._load_schedules()

    def create_schedule(
        self,
        mission_type: str,
        frequency: str,
        target: Optional[str] = None,
        description: Optional[str] = None,
    ) -> str:
        """Create a new recurring mission schedule."""
        import uuid
        schedule_id = f"schedule-{uuid.uuid4().hex[:8]}"

        schedule = ScheduledMission(
            id=schedule_id,
            mission_type=mission_type,
            frequency=frequency,
            target=target,
            description=description,
        )

        with self.lock:
            self.schedules[schedule_id] = schedule

        self._save_schedules()
        logger.info("mission_scheduler", f"Schedule {schedule_id} created: {mission_type} every {frequency}")

        return schedule_id

    def get_schedule(self, schedule_id: str) -> Optional[ScheduledMission]:
        """Get a schedule by ID."""
        with self.lock:
            return self.schedules.get(schedule_id)

    def list_schedules(self, enabled_only: bool = False) -> List[ScheduledMission]:
        """List all schedules."""
        with self.lock:
            schedules = list(self.schedules.values())

        if enabled_only:
            schedules = [s for s in schedules if s.enabled]

        return sorted(schedules, key=lambda s: s.created_at, reverse=True)

    def update_schedule(self, schedule_id: str, **updates) -> bool:
        """Update a schedule (enabled, target, frequency, etc)."""
        with self.lock:
            if schedule_id not in self.schedules:
                return False

            schedule = self.schedules[schedule_id]
            for key, value in updates.items():
                if hasattr(schedule, key):
                    setattr(schedule, key, value)

        self._save_schedules()
        logger.info("mission_scheduler", f"Schedule {schedule_id} updated")
        return True

    def delete_schedule(self, schedule_id: str) -> bool:
        """Delete a schedule."""
        with self.lock:
            if schedule_id not in self.schedules:
                return False
            del self.schedules[schedule_id]

        self._save_schedules()
        logger.info("mission_scheduler", f"Schedule {schedule_id} deleted")
        return True

    def start(self):
        """Start the scheduler background thread."""
        if self.running:
            return

        self.running = True
        self.scheduler_thread = threading.Thread(
            target=self._scheduler_loop,
            daemon=True,
            name="MissionScheduler",
        )
        self.scheduler_thread.start()
        logger.info("mission_scheduler", "Scheduler started")

    def stop(self):
        """Stop the scheduler."""
        self.running = False
        if self.scheduler_thread:
            self.scheduler_thread.join(timeout=5)
        logger.info("mission_scheduler", "Scheduler stopped")

    def register_callback(self, callback: callable):
        """Register callback for when a mission should run."""
        self.on_mission_ready.append(callback)

    def _scheduler_loop(self):
        """Background loop that checks for missions to run."""
        while self.running:
            try:
                current_time = datetime.now(timezone.utc)

                due = []
                with self.lock:
                    for schedule in self.schedules.values():
                        if not schedule.enabled:
                            continue
                        if schedule.next_run_at is None:
                            schedule.next_run_at = current_time.isoformat()
                        next_run = datetime.fromisoformat(schedule.next_run_at)
                        if current_time >= next_run:
                            due.append(schedule)

                for schedule in due:
                    self._trigger_mission(schedule)

                self._save_schedules()
            except Exception as e:
                logger.error("mission_scheduler", f"Scheduler error: {e}")

            time.sleep(60)  # Check every minute

    def _trigger_mission(self, schedule: ScheduledMission):
        """Trigger a mission from a schedule."""
        try:
            logger.info(
                "mission_scheduler",
                f"Triggering {schedule.mission_type} from schedule {schedule.id}",
            )

            # Notify subscribers
            for callback in self.on_mission_ready:
                try:
                    callback(schedule)
                except Exception as e:
                    logger.error("mission_scheduler", f"Callback failed: {e}")

            # Update schedule timing
            schedule.last_run_at = datetime.now(timezone.utc).isoformat()
            schedule.run_count += 1
            schedule.next_run_at = self._calculate_next_run(schedule).isoformat()

        except Exception as e:
            logger.error("mission_scheduler", f"Failed to trigger mission: {e}")

    def _calculate_next_run(self, schedule: ScheduledMission) -> datetime:
        """Calculate when the next run should be."""
        from datetime import timedelta

        now = datetime.now(timezone.utc)

        if schedule.frequency == ScheduleFrequency.HOURLY:
            return now + timedelta(hours=1)
        elif schedule.frequency == ScheduleFrequency.DAILY:
            return now + timedelta(days=1)
        elif schedule.frequency == ScheduleFrequency.WEEKLY:
            return now + timedelta(weeks=1)
        elif schedule.frequency == ScheduleFrequency.MONTHLY:
            # Add roughly 30 days
            return now + timedelta(days=30)
        else:
            return now + timedelta(hours=1)

    def _load_schedules(self):
        """Load schedules from disk."""
        try:
            config_dir = os.path.expanduser("~/.shadowcypher")
            schedules_file = os.path.join(config_dir, "schedules.json")

            if os.path.exists(schedules_file):
                with open(schedules_file) as f:
                    data = json.load(f)
                    for schedule_id, schedule_data in data.items():
                        schedule = ScheduledMission(**schedule_data)
                        self.schedules[schedule_id] = schedule

                logger.info("mission_scheduler", f"Loaded {len(self.schedules)} schedules")
        except Exception as e:
            logger.debug("mission_scheduler", f"Failed to load schedules: {e}")

    def _save_schedules(self):
        """Save schedules to disk."""
        try:
            config_dir = os.path.expanduser("~/.shadowcypher")
            os.makedirs(config_dir, exist_ok=True)

            schedules_file = os.path.join(config_dir, "schedules.json")
            with open(schedules_file, "w") as f:
                data = {sid: asdict(s) for sid, s in self.schedules.items()}
                json.dump(data, f, indent=2)
        except Exception as e:
            logger.error("mission_scheduler", f"Failed to save schedules: {e}")


# Singleton instance
_mission_scheduler = None


def get_mission_scheduler() -> MissionScheduler:
    """Get or create MissionScheduler singleton."""
    global _mission_scheduler
    if _mission_scheduler is None:
        _mission_scheduler = MissionScheduler()
    return _mission_scheduler
