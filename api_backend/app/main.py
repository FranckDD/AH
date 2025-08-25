import sys, os
from fastapi import FastAPI

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
from .routes.pharmacy import pharmacy_endpoints
from .routes.admin import users_endpoint

app = FastAPI(title="AH2 API")

# Inclusion des routers
app.include_router(auth_endpoints.router, prefix="", tags=["Auth"])
app.include_router(patients_endpoints.router)  # sans prefix et sans tags
app.include_router(medical_records_endpoint.router)
app.include_router(prescriptions_endpoints.router)
app.include_router(appointment_endpoints.router)
app.include_router(cs_endpoint.router)
app.include_router(caisse_endpoints.router)
app.include_router(pharmacy_endpoints.router)
app.include_router(users_endpoint.router)

