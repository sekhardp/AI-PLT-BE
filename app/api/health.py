import logging
from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, Status
from pydantic import AwareDatetime, Field

from app.core.depen