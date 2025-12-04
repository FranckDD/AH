# managers/sync_manager.py
import redis
import json
import logging
from typing import Dict, List, Any, Optional
from datetime import datetime
from enum import Enum

logger = logging.getLogger(__name__)

class OperationType(Enum):
    CREATE = "create"
    UPDATE = "update"
    DELETE = "delete"
    READ = "read"  # Optionnel pour cache sync

class SyncManager:
    def __init__(self, cache_manager: 'CacheManager', user_id: str, redis_client=None):
        self.user_id = user_id
        self.cache = cache_manager  # Pour data persistance
        self.redis = redis_client or cache_manager.client  # Réutilise Redis du cache
        self.queue_key = f"sync_queue:{user_id}"  # Queue ops pending (list Redis)

    def queue_operation(self, op_type: OperationType, entity: str, data: Dict[str, Any], timestamp: Optional[float] = None):
        """Queue une op offline (ex. : create_patient)."""
        if timestamp is None:
            timestamp = datetime.now().timestamp()
        
        op = {
            "type": op_type.value,
            "entity": entity,  # ex. "patient", "appointment"
            "data": data,  # Payload (id, fields...)
            "timestamp": timestamp,
            "status": "pending"
        }
        
        # Push à droite (FIFO pour ordre)
        self.redis.rpush(self.queue_key, json.dumps(op))
        logger.info(f"[SYNC] Op queued: {op_type.value} {entity} pour user {self.user_id}")

    def get_pending_ops(self) -> List[Dict[str, Any]]:
        """Récupère ops pending."""
        ops = []
        while True:
            op_json = self.redis.lpop(self.queue_key)  # Pop gauche (FIFO)
            if not op_json:
                break
            op = json.loads(op_json)
            if op["status"] == "pending":
                ops.append(op)
        return ops

    def flush_to_online(self, auth_ctrl: Any, gateway: Any) -> Dict[str, Any]:
        """Flush queue vers online (API ou direct DB via auth_ctrl). Retourne stats sync."""
        pending = self.get_pending_ops()
        if not pending:
            return {"synced": 0, "errors": 0}

        stats = {"synced": 0, "errors": 0, "details": []}
        for op in pending:
            try:
                # Map op to controller method (ex. : create_patient via patient_controller)
                entity_ctrl = self._get_entity_controller(auth_ctrl, op["entity"])
                if entity_ctrl:
                    result = self._execute_online_op(entity_ctrl, op)
                    if result:
                        op["status"] = "synced"
                        self.cache.cache_list(op["entity"], self.user_id, [result])  # Update cache
                        stats["synced"] += 1
                        logger.info(f"[SYNC] Synced: {op['type']} {op['entity']} (ts={op['timestamp']})")
                    else:
                        # Re-queue si échec (retry later)
                        self.redis.rpush(self.queue_key, json.dumps(op))
                        stats["errors"] += 1
                        stats["details"].append(f"Retry {op['type']} {op['entity']}")
                else:
                    stats["errors"] += 1
                    stats["details"].append(f"No controller for {op['entity']}")
            except Exception as e:
                logger.exception(f"[SYNC] Erreur sync op: {e}")
                # Re-queue
                self.redis.rpush(self.queue_key, json.dumps(op))
                stats["errors"] += 1
                stats["details"].append(str(e))

        return stats

    def _get_entity_controller(self, auth_ctrl: Any, entity: str) -> Optional[Any]:
        """Map entity to controller (via auth_ctrl pass-through)."""
        if entity == "patient":
            return auth_ctrl.patient_controller
        elif entity == "appointment":
            return auth_ctrl.appointment_controller
        elif entity == "medical_record":
            return auth_ctrl.medical_record_controller
        elif entity == "prescription":
            return auth_ctrl.prescription_controller
        # Ajoute d'autres (lab, etc.)
        return None

    def _execute_online_op(self, controller: Any, op: Dict[str, Any]) -> Optional[Any]:
        """Exécute op sur online controller (avec conflit check)."""
        op_type = op["type"]
        data = op["data"]
        ts = op["timestamp"]
        
        # Simple conflit : Check timestamp ou version (adapte si besoin)
        if op_type == OperationType.CREATE.value:
            return controller.create_patient(**data) if "patient" in str(controller) else controller.create_appointment(**data)  # Exemple
        elif op_type == OperationType.UPDATE.value:
            # Check last modified > ts avant update
            existing = controller.get_patient(data["id"]) if "patient" in str(controller) else None
            if existing and getattr(existing, "last_modified", 0) > ts:
                logger.warning(f"[SYNC] Conflit ignoré (old ts): {op_type} {data['id']}")
                return None
            return controller.update_patient(data["id"], **data)  # Exemple
        elif op_type == OperationType.DELETE.value:
            return controller.delete_patient(data["id"])  # Exemple
        return None

    def clear_queue(self):
        """Clear sur logout complet."""
        self.redis.delete(self.queue_key)
        logger.info(f"[SYNC] Queue cleared pour user {self.user_id}")