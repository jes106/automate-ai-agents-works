"""Restore initial data and empty the outbox without a running server: python reset.py"""
from store import STORE

STORE.reset()
print("data restored, outbox cleared")
