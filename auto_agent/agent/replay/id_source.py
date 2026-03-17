"""
Deterministic ID Source - ID generator
======================================

Bu klass ID generatorni boshqaradi, replay paytida
ID'larni deterministic qilish imkonini beradi.

Features:
- Task ID generator
- Event ID generator
- Session ID generator
- Deterministic ketma-ketlik
"""

import uuid
import threading
from typing import Optional, Iterator, Callable
from dataclasses import dataclass, field
from enum import Enum
import hashlib
import logging

logger = logging.getLogger(__name__)


class IdType(str, Enum):
    """ID turlari"""
    TASK = "task"
    EVENT = "event"
    SESSION = "session"
    TRANSACTION = "transaction"
    CHECKPOINT = "checkpoint"
    RUNTIME = "runtime"


@dataclass
class IdConfig:
    """ID generator konfiguratsiyasi"""
    prefix: str = ""
    seed: Optional[int] = None
    timestamp_based: bool = True
    counter_based: bool = True
    hash_component: bool = True


class DeterministicIdSource:
    """
    Deterministic ID Source - Kernel uchun ID boshqaruvi
    
    Bu klass kernel'ga quyidagi imkoniyatlarni beradi:
    - Deterministic task ID olish
    - Deterministic event ID olish
    - Replay davomida bir xil ID ketma-ketligi
    - ID konfliktlarini oldini olish
    
    Usage:
        id_source = DeterministicIdSource(seed=42)
        
        # Task ID olish
        task_id = id_source.next_task_id()
        
        # Event ID olish
        event_id = id_source.next_event_id()
        
        # Replay uchun reset
        id_source.reset(seed=42)
    """
    
    def __init__(
        self,
        seed: Optional[int] = None,
        prefix: str = "",
        use_counter: bool = True,
        use_timestamp: bool = True,
        use_hash: bool = True
    ):
        """
        Args:
            seed: Random seed (deterministic rejim uchun)
            prefix: ID prefix (masalan, "task_", "evt_")
            use_counter: Counter asosida ID
            use_timestamp: Timestamp ishlatish
            use_hash: Hash component ishlatish
        """
        self._seed = seed
        self._prefix = prefix
        self._use_counter = use_counter
        self._use_timestamp = use_timestamp
        self._use_hash = use_hash
        
        # Counters
        self._task_counter: int = 0
        self._event_counter: int = 0
        self._session_counter: int = 0
        self._transaction_counter: int = 0
        self._checkpoint_counter: int = 0
        self._runtime_counter: int = 0
        self._global_counter: int = 0
        
        # State stack for save/restore
        self._state_stack: list = []
        
        # RNG for deterministic mode
        if seed is not None:
            import random
            self._rng = random.Random(seed)
        else:
            self._rng = None
        
        # Thread safety
        self._lock = threading.RLock()
        
        # Session ID (doimiy bir marta yaratiladi)
        self._session_id = str(uuid.uuid4())
        
        logger.info(f"DeterministicIdSource initialized: seed={seed}, prefix={prefix}")
    
    @property
    def session_id(self) -> str:
        """Session ID olish"""
        return self._session_id
    
    def next_id(
        self,
        id_type: IdType = IdType.TASK,
        custom_prefix: Optional[str] = None,
        include_context: Optional[str] = None
    ) -> str:
        """
        Generic ID olish
        
        Args:
            id_type: ID turi
            custom_prefix: Maxsus prefix
            include_context: Qo'shimcha context (hash uchun)
            
        Returns:
            Yangi ID string
        """
        with self._lock:
            self._global_counter += 1
            
            # Counter
            counter = self._get_counter(id_type)
            self._increment_counter(id_type)
            
            # Prefix
            prefix = custom_prefix or self._prefix or f"{id_type.value}_"
            
            # Timestamp
            if self._use_timestamp:
                import time
                ts = int(time.time() * 1000)
            else:
                ts = 0
            
            # Hash component
            hash_part = ""
            if self._use_hash and include_context:
                hash_obj = hashlib.sha256(
                    f"{include_context}{counter}{self._seed or 0}".encode()
                )
                hash_part = hash_obj.hexdigest()[:8]
            
            # RNG component (deterministic)
            rng_part = ""
            if self._rng:
                rng_part = f"{self._rng.randint(0, 999999):06d}"
            
            # Assemble ID
            parts = [prefix]
            if self._use_timestamp and ts:
                parts.append(f"{ts}")
            if rng_part:
                parts.append(rng_part)
            if hash_part:
                parts.append(hash_part)
            parts.append(f"{counter:08d}")
            
            return "-".join(parts)
    
    def _get_counter(self, id_type: IdType) -> int:
        """Counter olish"""
        return {
            IdType.TASK: self._task_counter,
            IdType.EVENT: self._event_counter,
            IdType.SESSION: self._session_counter,
            IdType.TRANSACTION: self._transaction_counter,
            IdType.CHECKPOINT: self._checkpoint_counter,
            IdType.RUNTIME: self._runtime_counter,
        }.get(id_type, self._global_counter)
    
    def _increment_counter(self, id_type: IdType) -> None:
        """Counter'ni oshirish"""
        if id_type == IdType.TASK:
            self._task_counter += 1
        elif id_type == IdType.EVENT:
            self._event_counter += 1
        elif id_type == IdType.SESSION:
            self._session_counter += 1
        elif id_type == IdType.TRANSACTION:
            self._transaction_counter += 1
        elif id_type == IdType.CHECKPOINT:
            self._checkpoint_counter += 1
        elif id_type == IdType.RUNTIME:
            self._runtime_counter += 1
        else:
            self._global_counter += 1
    
    def next_task_id(self, context: Optional[str] = None) -> str:
        """
        Task ID olish
        
        Args:
            context: Task haqida qo'shimcha context
            
        Returns:
            Task ID
        """
        return self.next_id(IdType.TASK, include_context=context)
    
    def next_event_id(self, context: Optional[str] = None) -> str:
        """
        Event ID olish
        
        Args:
            context: Event haqida qo'shimcha context
            
        Returns:
            Event ID
        """
        return self.next_id(IdType.EVENT, include_context=context)
    
    def next_transaction_id(self, context: Optional[str] = None) -> str:
        """
        Transaction ID olish
        """
        return self.next_id(IdType.TRANSACTION, include_context=context)
    
    def next_checkpoint_id(self, context: Optional[str] = None) -> str:
        """
        Checkpoint ID olish
        """
        return self.next_id(IdType.CHECKPOINT, include_context=context)
    
    def next_runtime_id(self, context: Optional[str] = None) -> str:
        """
        Runtime ID olish
        """
        return self.next_id(IdType.RUNTIME, include_context=context)
    
    def bulk_generate(self, count: int, id_type: IdType = IdType.TASK) -> list:
        """
        Ko'p ID bir vaqtda yaratish
        
        Args:
            count: Nechta ID
            id_type: ID turi
            
        Returns:
            ID'lar ro'yxati
        """
        return [self.next_id(id_type) for _ in range(count)]
    
    def get_snapshot(self) -> dict:
        """Hozirgi holatni snapshot sifatida olish"""
        with self._lock:
            return {
                'task_counter': self._task_counter,
                'event_counter': self._event_counter,
                'session_counter': self._session_counter,
                'transaction_counter': self._transaction_counter,
                'checkpoint_counter': self._checkpoint_counter,
                'runtime_counter': self._runtime_counter,
                'global_counter': self._global_counter,
                'session_id': self._session_id,
                'seed': self._seed
            }
    
    def restore_snapshot(self, snapshot: dict) -> None:
        """Snapshot'dan holatni tiklash"""
        with self._lock:
            self._task_counter = snapshot.get('task_counter', 0)
            self._event_counter = snapshot.get('event_counter', 0)
            self._session_counter = snapshot.get('session_counter', 0)
            self._transaction_counter = snapshot.get('transaction_counter', 0)
            self._checkpoint_counter = snapshot.get('checkpoint_counter', 0)
            self._runtime_counter = snapshot.get('runtime_counter', 0)
            self._global_counter = snapshot.get('global_counter', 0)
            self._session_id = snapshot.get('session_id', str(uuid.uuid4()))
            if 'seed' in snapshot and snapshot['seed'] is not None:
                self._seed = snapshot['seed']
                if self._rng:
                    self._rng.seed(self._seed)
            logger.info(f"IdSource restored from snapshot")
    
    def push_state(self) -> None:
        """Hozirgi holatni stack'ga saqlash"""
        with self._lock:
            self._state_stack.append(self.get_snapshot())
    
    def pop_state(self) -> None:
        """Stack'dan holatni tiklash"""
        with self._lock:
            if not self._state_stack:
                raise ValueError("No state to pop")
            snapshot = self._state_stack.pop()
            self.restore_snapshot(snapshot)
    
    def reset(self, seed: Optional[int] = None) -> None:
        """
        ID source'ni reset qilish
        
        Args:
            seed: Yangi seed (None = avvalgisi)
        """
        with self._lock:
            if seed is not None:
                self._seed = seed
                if self._rng:
                    self._rng.seed(seed)
            
            self._task_counter = 0
            self._event_counter = 0
            self._session_counter = 0
            self._transaction_counter = 0
            self._checkpoint_counter = 0
            self._runtime_counter = 0
            self._global_counter = 0
            
            logger.info(f"IdSource reset, seed={seed}")
    
    def __repr__(self) -> str:
        return f"DeterministicIdSource(seed={self._seed}, task={self._task_counter}, event={self._event_counter})"


class IdSourceManager:
    """
    ID source'ni boshqarish - kernel ichida singleton
    """
    
    _instance: Optional['DeterministicIdSource'] = None
    _lock = threading.Lock()
    
    def __new__(cls) -> 'IdSourceManager':
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        self._id_source: DeterministicIdSource = DeterministicIdSource()
        self._initialized = True
    
    @property
    def id_source(self) -> DeterministicIdSource:
        return self._id_source
    
    def create_id_source(
        self,
        seed: Optional[int] = None,
        prefix: str = "",
        **kwargs
    ) -> DeterministicIdSource:
        """Yangi ID source yaratish"""
        return DeterministicIdSource(seed=seed, prefix=prefix, **kwargs)
    
    def set_global_id_source(self, id_source: DeterministicIdSource) -> None:
        """Global ID source'ni o'rnatish"""
        self._id_source = id_source
    
    def next_task_id(self, context: Optional[str] = None) -> str:
        """Global task ID olish"""
        return self._id_source.next_task_id(context)
    
    def next_event_id(self, context: Optional[str] = None) -> str:
        """Global event ID olish"""
        return self._id_source.next_event_id(context)


# Global instance
_global_id_source_manager = None

def get_id_source_manager() -> IdSourceManager:
    """Global ID source manager olish"""
    global _global_id_source_manager
    if _global_id_source_manager is None:
        _global_id_source_manager = IdSourceManager()
    return _global_id_source_manager


def get_deterministic_id_source(seed: Optional[int] = None, prefix: str = "") -> DeterministicIdSource:
    """
    Deterministic ID source olish (qulaylik funksiyasi)
    
    Usage:
        id_source = get_deterministic_id_source(seed=42)
        task_id = id_source.next_task_id()  # Har doim bir xil ketma-ketlik
    """
    return DeterministicIdSource(seed=seed, prefix=prefix)
