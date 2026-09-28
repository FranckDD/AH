# printer_bridge/server.py
import logging
from typing import Any, Dict

from fastapi import FastAPI, HTTPException, Header
from fastapi.middleware.cors import CORSMiddleware
from escpos.printer import Win32Raw, Usb, Network

from config import load_config
from ticket_renderer import render_ticket

logger = logging.getLogger("printer_bridge")

app = FastAPI(title="AH2 Printer Bridge")

# Le frontend (autre origine, ex. http://localhost:4173 ou l'URL de prod)
# appelle ce pont via fetch() avec l'en-tete X-Print-Token : le navigateur
# envoie donc un preflight OPTIONS, rejete sans ces en-tetes CORS (retour
# terrain 2026-09-28). Origines explicites, jamais "*" - le jeton reste la
# vraie protection, CORS limite en plus qui peut meme tenter l'appel.
DEFAULT_ALLOWED_ORIGINS = ["http://localhost:4173", "http://localhost:5173"]


def _allowed_origins():
    try:
        return load_config().get("allowed_origins", DEFAULT_ALLOWED_ORIGINS)
    except FileNotFoundError:
        return DEFAULT_ALLOWED_ORIGINS  # tests/CI sans config.json


app.add_middleware(
    CORSMiddleware,
    allow_origins=_allowed_origins(),
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type", "X-Print-Token"],
)


def get_active_printer():
    """Instancie la connexion imprimante reelle a chaque appel (pas de
    connexion persistante gardee ouverte entre deux tickets - plus simple,
    et une imprimante thermique USB/Win32Raw supporte tres bien une
    ouverture/fermeture par ticket sur le volume d'une secretariat)."""
    config = load_config()
    # "profile" declare la largeur en pixels du papier au profil escpos -
    # sans lui, python-escpos ne peut pas centrer le logo (retour terrain
    # 2026-09-28 : "The media.width.pixel field ... center flag will have no
    # effect"). TM-T88V (42 col, 80mm) par defaut, comme la mise en page de
    # ticket_renderer.py (PAPER_WIDTH_CHARS=42) l'attend deja.
    profile = config.get("profile", "TM-T88V")
    if config["connection_type"] == "win32raw":
        return Win32Raw(config["printer_name"], profile=profile)
    if config["connection_type"] == "usb":
        return Usb(config["vendor_id"], config["product_id"], profile=profile)
    if config["connection_type"] == "network":
        # Imprimante thermique Ethernet/Wi-Fi (port JetDirect standard 9100),
        # ou emulateur logiciel qui expose la meme interface reseau brute
        # (ex. "POS Printer Emulator" utilise pour la verification manuelle -
        # voir README.md) - aucune installation de pilote/imprimante Windows
        # requise dans ce cas.
        return Network(config["printer_host"], port=config.get("printer_port", 9100), profile=profile)
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
