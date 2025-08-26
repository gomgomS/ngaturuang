from flask import Blueprint

bp = Blueprint("web", __name__)

from . import routes  # noqa: E402,F401


