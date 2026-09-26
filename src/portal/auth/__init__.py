"""Portal auth slice — signup, login, ``/auth/me``, and workspace creation.

Session tokens are minted by :mod:`src.portal.security`; the resolved caller and
the merchant keys they may see come from :class:`src.portal.deps.AccessScope`.
"""
