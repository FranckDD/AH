import sys, os
from fastapi import FastAPI

# Permet d'importer les modules depuis la racine AH2
root_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.append(root_path)

# ⚠️ Ajustement ici selon les bons noms de fichiers
from .routes.auth import auth_endpoints
from .routes.patients import patients_endpoints

app = FastAPI(title="AH2 API")

# Inclusion des routers
app.include_router(auth_endpoints.router, prefix="", tags=["Auth"])
app.include_router(patients_endpoints.router, prefix="/patients", tags=["Patients"])
