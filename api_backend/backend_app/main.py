import sys, os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Permet d'importer les modules depuis la racine AH2
root_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.append(root_path)

# ⚠️ Ajustement ici selon les bons noms de fichiers
from .routes.auth import auth_endpoints
from .routes.patients import patients_endpoints
from .routes.medical_records import medical_records_endpoint
from .routes.prescription import prescriptions_endpoints
from .routes.appointment import appointment_endpoints
from .routes.cs import cs_endpoint
from .routes.caisse import caisse_endpoints
from .routes.retrait import retrait_endpoints
from .routes.toxico import toxico_endpoint

# --- AJOUT IMPORT LABO ---
from .routes.labo import lab_endpoints  # <--- AJOUT ICI

from .routes.pharmacy import pharmacy_endpoints
from .routes.admin import users_endpoint
from .routes import health_endpoint

from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi import Request
import json

app = FastAPI(title="AH2 API")

# 🟢 AJOUTER CE BLOC POUR LE DÉBOGAGE 422
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """
    Intercepte les erreurs 422 et les affiche proprement dans la console serveur.
    """
    error_details = exc.errors()
    
    print("\n" + "="*50)
    print(f"🛑 ERREUR DE VALIDATION (422) SUR : {request.method} {request.url}")
    print("="*50)
    
    for i, error in enumerate(error_details):
        loc = " -> ".join(str(l) for l in error['loc'])
        msg = error['msg']
        print(f"❌ Erreur #{i+1}:")
        print(f"   📍 Emplacement : {loc}")
        print(f"   ⚠️ Message     : {msg}")
        # Affiche la valeur reçue si disponible dans le contexte (dépend version Pydantic)
        if 'input' in error:
             print(f"   📥 Valeur reçue: {error['input']}")
    
    print("="*50 + "\n")

    return JSONResponse(
        status_code=422,
        content={"detail": error_details},
    )

origins = [
    # 1. Votre frontend Vue/Vite qui tourne sur ce port
    "http://localhost:5173", 
    # 2. Si vous utilisez un autre port, ajoutez-le ici
    "http://127.0.0.1:5173", 
    "http://localhost:3000",      # Autre port courant
    "*"
]

app.add_middleware(
    CORSMiddleware,
    # Autorise les origines ci-dessus (votre frontend)
    allow_origins=["*"],#allow_origins=origins, 
    # Autorise les identifiants/cookies (souvent requis pour l'authentification)
    allow_credentials=True, 
    # Autorise toutes les méthodes (GET, POST, PUT, DELETE, OPTIONS, etc.)
    allow_methods=["*"], 
    # Autorise tous les en-têtes (headers) dans la requête
    allow_headers=["*"],
)

# ----------------------------

# Inclusion des routers
app.include_router(auth_endpoints.router, prefix="", tags=["Auth"])
app.include_router(patients_endpoints.router)  # sans prefix et sans tags
app.include_router(medical_records_endpoint.router)
app.include_router(prescriptions_endpoints.router)
app.include_router(appointment_endpoints.router)
app.include_router(cs_endpoint.router)
app.include_router(caisse_endpoints.router)
app.include_router(retrait_endpoints.router)
app.include_router(toxico_endpoint.router)

# --- AJOUT ROUTER LABO ---
app.include_router(lab_endpoints.router) # <--- AJOUT ICI (Le préfixe "/labo" est déjà défini dans le fichier endpoint)

app.include_router(pharmacy_endpoints.router)
app.include_router(users_endpoint.router)
app.include_router(health_endpoint.router) 


#if __name__ == "__main__":
 #   import uvicorn, os
  #  port = int(os.getenv("PORT", 8000))
   # uvicorn.run("api_backend.backend_app.main:app", host="0.0.0.0", port=port)