# printer_bridge/server.py
import logging
from typing import Any, Dict

from fastapi import FastAPI, HTTPException, Header
from escpos.printer import Win32Raw, Usb

from config import load_config
from ticket_renderer import render_ticket

logger = logging.getLogger("printer_bridge")

app = FastAPI(title="AH2 Printer Bridge")


def get_active_printer():
    """Instancie la connexion imprimante reelle a chaque appel (pas de
    connexion persistante gardee ouverte entre deux tickets - plus simple,
    et une imprimante thermique USB/Win32Raw supporte tres bien une
    ouverture/fermeture par ticket sur le volume d'une secretariat)."""
    config = load_config()
    if config["connection_type"] == "win32raw":
        return Win32Raw(config["printer_name"])
    if config["connection_type"] == "usb":
        return Usb(config["vendor_id"], config["product_id"])
    raise ValueError(f"connection_type inconnu: {config['connection_type']}")


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/print")
def print_ticket(ticket_data: Dict[str, Any], x_print_token: str = Header(None)):
    config = load_config()
    if not x_print_token or x_print_token != config.get("token"):
        raise HTTPException(status_code=401, detail="Jeton invalide ou manquant")

    try:
        printer = get_active_printer()
    except Exception as e:
        logger.exception("Imprimante injoignable")
        raise HTTPException(status_code=503, detail=f"Imprimante indisponible: {e}")

    try:
        render_ticket(printer, ticket_data)
    except Exception as e:
        logger.exception("Echec du rendu/envoi du ticket")
        raise HTTPException(status_code=500, detail=f"Erreur d'impression: {e}")

    return {"status": "printed"}


if __name__ == "__main__":
    import uvicorn
    config = load_config()
    uvicorn.run(app, host="127.0.0.1", port=config.get("port", 9123))
