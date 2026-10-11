"""Sentinel core infrastructure — persistence, caching, messaging and store clients.

Every module here is a thin wrapper over an external system, with a settings
object and a process-wide client instance. Domain packages depend on ``core``;
``core`` never depends on a domain, except for :mod:`src.core.models`, which is
the ORM schema shared by all of them.
"""
