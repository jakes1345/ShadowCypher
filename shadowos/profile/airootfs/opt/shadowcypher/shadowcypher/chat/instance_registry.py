"""Instance registry and heartbeat service for P2P Shadow instance discovery."""

import time

from sqlalchemy.orm import Session

from shadowcypher.chat.models import Instance

INSTANCE_TIMEOUT = 5 * 60  # Mark offline if no heartbeat for 5 minutes


def register_instance(session: Session, user_id: int, pubkey: bytes, endpoint: str = None) -> Instance:
    """Register a new Shadow instance for a user."""
    instance = Instance(user_id=user_id, pubkey=pubkey, endpoint=endpoint)
    session.add(instance)
    session.commit()
    session.refresh(instance)
    return instance


def heartbeat(session: Session, instance_id: str) -> bool:
    """Update last_heartbeat for an instance."""
    instance = session.query(Instance).filter(Instance.instance_id == instance_id).first()
    if not instance:
        return False
    instance.last_heartbeat = int(time.time())
    instance.is_online = True
    session.commit()
    return True


def get_instance(session: Session, instance_id: str) -> Instance | None:
    """Fetch instance by ID."""
    instance = session.query(Instance).filter(Instance.instance_id == instance_id).first()
    if instance:
        # Check if instance has timed out
        if int(time.time()) - instance.last_heartbeat > INSTANCE_TIMEOUT:
            instance.is_online = False
            session.commit()
    return instance


def list_online_instances(session: Session, user_id: int) -> list[Instance]:
    """List all online instances for a user."""
    instances = session.query(Instance).filter(Instance.user_id == user_id).all()
    online = []
    for inst in instances:
        if int(time.time()) - inst.last_heartbeat > INSTANCE_TIMEOUT:
            inst.is_online = False
            session.commit()
        if inst.is_online:
            online.append(inst)
    return online


def update_endpoint(session: Session, instance_id: str, endpoint: str) -> bool:
    """Update instance endpoint (e.g., after NAT traversal)."""
    instance = session.query(Instance).filter(Instance.instance_id == instance_id).first()
    if not instance:
        return False
    instance.endpoint = endpoint
    session.commit()
    return True
