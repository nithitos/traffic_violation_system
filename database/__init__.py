"""
Database package for Traffic Violation & Accident Alert System
"""
from .db_manager import DatabaseManager
from .seed_data import seed_database

__all__ = ["DatabaseManager", "seed_database"]
