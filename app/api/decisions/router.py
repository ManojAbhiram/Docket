"""Verifier decisions on flagged applications (api/openapi.yaml: /applications/{id}/decisions).

Routes arrive with US-00-007. The router is mounted now so that the tasks that fill it do not all
edit `app/main.py`.
"""

from fastapi import APIRouter

router = APIRouter(tags=["decisions"])
