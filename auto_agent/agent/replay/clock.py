"""
Deterministic Clock - Vaqt manbai
=================================

Bu klass vaqt manbasini boshqaradi, replay paytida vaqtni
freeze qilish yoki deterministic qilish imkonini beradi.

Features:
- freeze_time: Vaqtni replay davomida o'zgartirmaslik
- time_offset: Offset qo'shish orqali virtual vaqt yaratish
- tick_source: Har bir tickda chaqiriladigan callback
"""

import time
import threading
from typing import Optional, Callable, Union
from dataclasses import dataclass, field
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class ClockMode(str, Enum):
    """Clock ishlash rejimlari"""
    REAL = "real"           # Real vaqt (system clock)
    DETERMINISTIC = "deterministic"  # Deterministic (o'zingiz boshqarasiz)
    FROZEN = "frozen"       # Vaqt freeze qilingan
    SIMULATED = "simulated" # Simulatsiya vaqti


@dataclass
class TimeSnapshot:
    """Vaqt snapshot - replay uchun"""
    timestamp: float
    monotonic: float
    thread_time: float
    mode: ClockMode
    
    def to_dict(self) -> dict:
        return {
            'timestamp': self.timestamp,
            'monotonic': self.monotonic,
            'thread_time': self.thread_time,
            'mode': self.mode.value
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'TimeSnapshot':
        return cls(
            timestamp=data['timestamp'],
            monotonic=data['monotonic'],
            thread_time=data['thread_time'],
            mode=ClockMode(data['mode'])
        )


class DeterministicClock:
    """
    Deterministic Clock - Kernel uchun vaqt boshqaruvi
    
    Bu clock kernel'ga quyidagi imkoniyatlarni beradi:
    - Vaqtni replay davomida freeze qilish
    - Deterministic vaqt olish (har bir run bir xil)
    - Virtual vaqt yaratish (offset bilan)
    - Time travel (oldinga/ortga)
    
    Usage:
        clock = DeterministicClock(seed=42)
        
        # Real vaqt olish
        now = clock.now()
        
        # Freeze qilish (replay uchun)
        clock.freeze()
        frozen_time = clock.now()  # Doimiy qiymat
        
        # Deterministic vaqt olish
        det_clock = DeterministicClock(deterministic=True)
        t1 = det_clock.now()
        t2 = det_clock.now()
        # t2 > t1 har doim bir xil farq bilan
    """
    
    def __init__(
        self,
        seed: Optional[int] = None,
        deterministic: bool = False,
        frozen: bool = False,
        initial_time: Optional[float] = None,
        tick_callback: Optional[Callable[['DeterministicClock'], None]] = None,
        time_scale: float = 1.0
    ):
        """
        Args:
            seed: Random seed (deterministic rejim uchun)
            deterministic: Deterministic mode yoqish
            frozen: Vaqtni freeze qilish
            initial_time: Boshlang'ich vaqt (None = hozirgi system vaqti)
            tick_callback: Har bir now() chaqiruvida chaqiriladigan funksiya
            time_scale: Vaqt masshtabi (1.0 = normal, 2.0 = 2x tez)
        """
        self._seed = seed
        self._deterministic = deterministic
        self._frozen = frozen
        self._time_scale = time_scale
        
        # State
        self._current_time: float = initial_time if initial_time is not None else time.time()
        self._monotonic_offset: float = time.monotonic()
        self._thread_time_offset: float = time.thread_time() if hasattr(time, 'thread_time') else 0
        self._tick_count: int = 0
        
        # Internal state
        self._state_stack: list = []  # Vaqtni saqlash uchun
        self._mode: ClockMode = ClockMode.FROZEN if frozen else (ClockMode.DETERMINISTIC if deterministic else ClockMode.REAL)
        
        # RNG for deterministic mode
        if deterministic and seed is not None:
            import random
            self._rng = random.Random(seed)
        else:
            self._rng = None
        
        # Tick callback
        self._tick_callback = tick_callback
        
        # Thread safety
        self._lock = threading.RLock()
        
        logger.info(f"DeterministicClock initialized: mode={self._mode}, seed={seed}, frozen={frozen}")
    
    @property
    def mode(self) -> ClockMode:
        """Hozirgi clock rejimi"""
        return self._mode
    
    @property
    def is_frozen(self) -> bool:
        """Vaqt freeze qilinganmi?"""
        return self._frozen
    
    @property
    def is_deterministic(self) -> bool:
        """Deterministic rejimmi?"""
        return self._deterministic
    
    def now(self) -> float:
        """
        Hozirgi vaqtni olish
        
        Bu method har qachon chaqirilganda yangi vaqt qaytaradi,
        deterministic rejimda esa oldindan aniqlangan ketma-ketlik bilan.
        """
        with self._lock:
            if self._frozen:
                # Frozen rejimda - o'zgarmas vaqt
                return self._current_time
            
            if self._deterministic:
                # Deterministic rejimda - seed asosida progress
                self._tick_count += 1
                if self._rng:
                    # Random walk bilan deterministic vaqt
                    tick_increment = self._rng.uniform(0.001, 0.01) * self._time_scale
                    self._current_time += tick_increment
                else:
                    # Oddiy increment
                    self._current_time += 0.001 * self._time_scale
                
                # Callback chaqirish
                if self._tick_callback:
                    try:
                        self._tick_callback(self)
                    except Exception as e:
                        logger.warning(f"Tick callback error: {e}")
                
                return self._current_time
            
            # Real vaqt - system clock
            self._current_time = time.time()
            return self._current_time
    
    def now_monotonic(self) -> float:
        """Monotonic vaqt (system monotonic clock dan)"""
        with self._lock:
            if self._frozen:
                return self._monotonic_offset
            
            if self._deterministic:
                return self._monotonic_offset + (self._tick_count * 0.001)
            
            return time.monotonic()
    
    def now_thread_time(self) -> float:
        """Thread CPU vaqti"""
        with self._lock:
            if self._frozen:
                return self._thread_time_offset
            
            if self._deterministic:
                return self._thread_time_offset + (self._tick_count * 0.0001)
            
            return time.thread_time() if hasattr(time, 'thread_time') else 0.0
    
    def get_snapshot(self) -> TimeSnapshot:
        """Hozirgi vaqtni snapshot sifatida olish"""
        return TimeSnapshot(
            timestamp=self.now(),
            monotonic=self.now_monotonic(),
            thread_time=self.now_thread_time(),
            mode=self._mode
        )
    
    def restore_snapshot(self, snapshot: TimeSnapshot) -> None:
        """Snapshotdan vaqtni tiklash"""
        with self._lock:
            self._current_time = snapshot.timestamp
            self._monotonic_offset = snapshot.monotonic
            self._thread_time_offset = snapshot.thread_time
            self._mode = snapshot.mode
            self._frozen = snapshot.mode == ClockMode.FROZEN
            self._deterministic = snapshot.mode == ClockMode.DETERMINISTIC
            logger.info(f"Clock restored from snapshot: {snapshot.timestamp}")
    
    def freeze(self) -> float:
        """
        Vaqtni freeze qilish
        
        Returns:
            Hozirgi vaqt (freeze qilinishidan oldingi)
        """
        with self._lock:
            frozen_time = self._current_time
            self._frozen = True
            self._mode = ClockMode.FROZEN
            logger.info(f"Clock frozen at {frozen_time}")
            return frozen_time
    
    def unfreeze(self) -> None:
        """Vaqtni unfreeze qilish"""
        with self._lock:
            self._frozen = False
            self._mode = ClockMode.DETERMINISTIC if self._deterministic else ClockMode.REAL
            logger.info("Clock unfrozen")
    
    def set_time(self, timestamp: float) -> None:
        """Vaqtniqo'l bilan o'rnatish (deterministic/simulated rejimda)"""
        with self._lock:
            if self._mode == ClockMode.REAL and not self._deterministic:
                raise ValueError("Cannot set time in REAL mode")
            self._current_time = timestamp
            logger.info(f"Clock time set to {timestamp}")
    
    def advance(self, seconds: float) -> float:
        """
        Vaqtni oldinga surish
        
        Args:
            seconds: Qancha vaqt oldinga surish
            
        Returns:
            Yangi vaqt
        """
        with self._lock:
            if self._frozen:
                raise ValueError("Cannot advance frozen clock")
            self._current_time += seconds
            return self._current_time
    
    def rewind(self, seconds: float) -> float:
        """
        Vaqtni ortga qaytarish
        
        Args:
            seconds: Qancha vaqt ortga qaytarish
            
        Returns:
            Yangi vaqt
        """
        with self._lock:
            if self._frozen:
                raise ValueError("Cannot rewind frozen clock")
            self._current_time = max(0, self._current_time - seconds)
            return self._current_time
    
    def push_state(self) -> None:
        """Hozirgi vaqt holatini stack'ga saqlash"""
        with self._lock:
            self._state_stack.append({
                'current_time': self._current_time,
                'monotonic_offset': self._monotonic_offset,
                'thread_time_offset': self._thread_time_offset,
                'tick_count': self._tick_count,
                'frozen': self._frozen,
                'deterministic': self._deterministic,
                'mode': self._mode
            })
    
    def pop_state(self) -> None:
        """Stack'dan oxirgi holatni tiklash"""
        with self._lock:
            if not self._state_stack:
                raise ValueError("No state to pop")
            state = self._state_stack.pop()
            self._current_time = state['current_time']
            self._monotonic_offset = state['monotonic_offset']
            self._thread_time_offset = state['thread_time_offset']
            self._tick_count = state['tick_count']
            self._frozen = state['frozen']
            self._deterministic = state['deterministic']
            self._mode = state['mode']
    
    def reset(self, seed: Optional[int] = None) -> None:
        """
        Clock'ni reset qilish
        
        Args:
            seed: Yangi seed (None = avvalgisi)
        """
        with self._lock:
            if seed is not None:
                self._seed = seed
                if self._rng:
                    self._rng.seed(seed)
            
            self._current_time = time.time() if self._mode == ClockMode.REAL else 0
            self._tick_count = 0
            self._state_stack.clear()
            logger.info(f"Clock reset, seed={seed}")
    
    def __enter__(self) -> 'DeterministicClock':
        """Context manager - vaqtni freeze qilish"""
        self.freeze()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """Context manager - vaqtni unfreeze qilish"""
        self.unfreeze()
    
    def __repr__(self) -> str:
        return f"DeterministicClock(mode={self._mode}, time={self._current_time:.4f}, ticks={self._tick_count})"


class ClockManager:
    """
    Clock'ni boshqarish - kernel ichida singleton
    
    Bu klass kernel ichida clock'ni boshqaradi va barcha
    komponentlarga bir xil clock instance'ini beradi.
    """
    
    _instance: Optional['ClockManager'] = None
    _lock = threading.Lock()
    
    def __new__(cls) -> 'ClockManager':
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        self._clock: DeterministicClock = DeterministicClock()
        self._initialized = True
    
    @property
    def clock(self) -> DeterministicClock:
        return self._clock
    
    def create_clock(
        self,
        seed: Optional[int] = None,
        deterministic: bool = False,
        frozen: bool = False,
        **kwargs
    ) -> DeterministicClock:
        """Yangi clock yaratish"""
        return DeterministicClock(
            seed=seed,
            deterministic=deterministic,
            frozen=frozen,
            **kwargs
        )
    
    def set_global_clock(self, clock: DeterministicClock) -> None:
        """Global clock'ni o'rnatish"""
        self._clock = clock
    
    def get_time(self) -> float:
        """Global vaqt olish"""
        return self._clock.now()
    
    def freeze(self) -> float:
        """Global vaqtni freeze qilish"""
        return self._clock.freeze()
    
    def unfreeze(self) -> None:
        """Global vaqtni unfreeze qilish"""
        self._clock.unfreeze()


# Global instance
_global_clock_manager = None

def get_clock_manager() -> ClockManager:
    """Global clock manager olish"""
    global _global_clock_manager
    if _global_clock_manager is None:
        _global_clock_manager = ClockManager()
    return _global_clock_manager


def get_deterministic_clock(seed: Optional[int] = None) -> DeterministicClock:
    """
    Deterministic clock olish (qulaylik funksiyasi)
    
    Usage:
        clock = get_deterministic_clock(seed=42)
        t1 = clock.now()  # Har doim bir xil ketma-ketlik
    """
    return DeterministicClock(seed=seed, deterministic=True)


def get_frozen_clock(initial_time: Optional[float] = None) -> DeterministicClock:
    """
    Frozen clock olish (qulaylik funksiyasi)
    
    Usage:
        clock = get_frozen_clock()
        t1 = clock.now()  # Doim bir xil qiymat
    """
    return DeterministicClock(frozen=True, initial_time=initial_time)
