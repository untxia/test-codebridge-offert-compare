"""API : POST /api/compare (multipart : original, revised, overrides?) -> rapport JSON.
Sans état : rien n'est conservé côté serveur (fichiers temporaires supprimés après traitement)."""
import json
import os
import re
import sys
import tempfile
from typing import Optional

from fastapi import FastAPI, File, Form, HTTPException, UploadFile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from offercompare import agent  # noqa: E402
from offercompare.diff import compare_files  # noqa: E402
from offercompare.readers import UnsupportedFormat  # noqa: E402

MAX_BYTES = 2 * 1024 * 1024      # 2 Mo par fichier (limite de corps de requête des fonctions serverless : 4,5 Mo)
app = FastAPI(title="offer-compare", docs_url=None, redoc_url=None)


def _overrides(raw: Optional[str]) -> dict:
    if not raw:
        return {}
    try:
        o = json.loads(raw)
        out = {"pairs": [], "removed": [], "added": []}
        for k in ("removed", "added"):
            out[k] = [int(x) for x in o.get(k, [])]
        out["pairs"] = [[int(a), int(b)] for a, b in o.get("pairs", [])]
        return out
    except Exception:
        raise HTTPException(400, "overrides invalides")


async def _save(up: UploadFile, td: str, tag: str) -> str:
    data = await up.read()
    if len(data) > MAX_BYTES:
        raise HTTPException(413, f"{tag} : fichier trop volumineux (max {MAX_BYTES // 1024 // 1024} Mo)")
    if not data:
        raise HTTPException(400, f"{tag} : fichier vide")
    ext = os.path.splitext(up.filename or "")[1].lower()
    ext = ext if re.fullmatch(r"\.[a-z0-9]{1,5}", ext) else ""
    path = os.path.join(td, f"{tag}{ext}")
    with open(path, "wb") as fh:
        fh.write(data)
    return path


@app.get("/api/health")
def health():
    return {"ok": True}


@app.post("/api/compare")
async def compare(original: UploadFile = File(...), revised: UploadFile = File(...), overrides: Optional[str] = Form(None)):
    ov = _overrides(overrides)
    with tempfile.TemporaryDirectory() as td:
        po, pr = await _save(original, td, "original"), await _save(revised, td, "revised")
        try:
            return compare_files(po, pr, ov, names={"original": original.filename or "original",
                                                    "revised": revised.filename or "revised"})
        except HTTPException:
            raise
        except UnsupportedFormat as e:
            raise HTTPException(415, str(e))
        except Exception as e:   # PDF corrompu, chiffré...
            raise HTTPException(422, f"Lecture impossible ({type(e).__name__}) : fichier corrompu, protégé ou format inattendu.")


@app.get("/api/agent")
def agent_status():
    return {"enabled": agent.enabled()}


@app.post("/api/ask")
async def ask(payload: dict):
    """Assistant IA : explique le rapport déjà calculé (aucun fichier n'est reçu, rien n'est conservé)."""
    try:
        return agent.ask(payload.get("report"), payload.get("question", ""), payload.get("history"), payload.get("lang", "fr"))
    except agent.AgentDisabled:
        raise HTTPException(503, "agent_disabled")
    except agent.AgentError as e:
        raise HTTPException(502, str(e))
