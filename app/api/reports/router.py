"""The dashboard counts and the verified export (api/openapi.yaml: /dashboard, /exports).

Routes arrive with US-00-008 and US-00-009. The router is mounted now so that the tasks that fill
it do not all edit `app/main.py`.
"""

from fastapi import APIRouter

router = APIRouter(tags=["reports"])
