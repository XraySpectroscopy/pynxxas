"""Data models
"""

from .xdi import XdiModel
from .nexus import NxXasModel

MODELS = {"xdi": XdiModel, "nexus": NxXasModel}
