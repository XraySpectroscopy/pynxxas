"""Data models"""

from .nexus import NxXasModel
from .xdi import XdiModel

MODELS = {"xdi": XdiModel, "nexus": NxXasModel}
