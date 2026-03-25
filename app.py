from threading import Lock

from fastapi import FastAPI, HTTPException

from config.config_loader import load_local_config
from services.sync_service import run_full_sync


app = FastAPI(title="1C-Kaiten Integration Service")
_sync_lock = Lock()


@app.get("/health")
def health():
    try:
        config = load_local_config()
        return {
            "status": "ok",
            "configured": True,
            "host": config.py_service_host,
            "port": config.py_service_port,
        }
    except Exception as exc:
        return {
            "status": "degraded",
            "configured": False,
            "error": str(exc),
        }


@app.post("/sync/run")
def sync_run():
    if not _sync_lock.acquire(blocking=False):
        raise HTTPException(status_code=409, detail="Синхронизация уже выполняется")

    try:
        run_full_sync()
        return {"success": True, "message": "Синхронизация завершена"}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))
    finally:
        _sync_lock.release()
