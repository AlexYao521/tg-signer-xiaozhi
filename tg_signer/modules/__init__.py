"""
Bot modules for channel automation
"""
from .herb_garden import HerbGardenModule
from .star_observatory import StarObservatoryModule
from .daily_routine import DailyRoutineModule
from .periodic_tasks import PeriodicTasksModule

__all__ = [
    "HerbGardenModule",
    "StarObservatoryModule",
    "DailyRoutineModule",
    "PeriodicTasksModule",
]
