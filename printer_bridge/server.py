# printer_bridge/server.py
import logging
from typing import Any, Dict

from fastapi import APIRouter, FastAPI, HTTPException, Header, Request
from fastapi.middleware.cors import CORSMiddleware
from escpos.printer import Win32Raw, Usb, Network

from config import load_config
from ticket_renderer import render_ticket

logger = logging.getLogger("printer_bridge")

# Le frontend (autre origine, ex. http://localhost:4173 ou l'URL de prod)
# appelle ce pont via fetch() avec l'en-tete X-Print-Token : le navigateur
# envoie donc un preflight OPTIONS, rejete sans ces en-tetes CORS (retour
# terrain 2026-09-28). Origines explicites, jamais "*" - le jeton reste la
# vraie protection, CORS limite en plus qui peut meme tenter l'appel.
DEFAULT_ALLOWED_ORIGINS = ["http://localhost:4173", "http://localhost:5173"]


router = APIRouter()


def _allowed_origins():
    try:
        origins = load_config().get("allowed_origins", DEFAULT_ALLOWED_ORIGINS)
    except FileNotFoundError:
        return list(DEFAULT_ALLOWED_ORIGINS)  # tests/CI sans config.json
    # Jamais de joker : le jeton reste la vraie protection, CORS limite en
    # plus qui peut tenter l'appel. Une entree "*" est ignoree et journalisee.
    safe = [o for o in origins if o != "*"]
    if len(safe) != len(origins):
        logger.warning(
            "allowed_origins contient '*' : entree ignoree (origines explicites uniquement)"
        )
    return safe


def create_app() -> FastAPI:
    application = FastAPI(title="AH2 Printer Bridge")
    origins = _allowed_origins()

    application.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_methods=["GET", "POST"],
        allow_headers=["Content-Type", "X-Print-Token"],
    )

    # Private Network Access (Chrome/Edge) : une page HTTPS publique qui
    # appelle ce pont local envoie un preflight avec
    # Access-Control-Request-Private-Network: true ; il faut y repondre
    # Access-Control-Allow-Private-Network: true, et seulement pour une
    # origine autorisee. Ajoute apres CORSMiddleware donc execute apres lui
    # (on voit sa reponse : ACAO present seulement si l'origine est listee).
    @application.middleware("http")
    async def private_network_access(request: Request, call_next):
        response = await call_next(request)
        origin = request.headers.get("origin")
        if (
            request.method == "OPTIONS"
            and request.headers.get("access-control-request-private-network", "").lower() == "true"
            and origin in origins
            and response.headers.get("access-control-allow-origin") == origin
        ):
            response.headers["Access-Control-Allow-Private-Network"] = "true"
        return response

    application.include_router(router)
    return application


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


@router.get("/health")
def health():
    return {"status": "ok"}


@router.post("/print")
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


app = create_app()


if __name__ == "__main__":
    import uvicorn
    config = load_config()
    uvicorn.run(app, host="127.0.0.1", port=config.get("port", 9123))
