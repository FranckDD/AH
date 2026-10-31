"""Filtre central des donnees de grossesse sur TOUTES les reponses JSON de l'API.

Regle (secretaire, assistant, toxico, psychologue, conseiller, stock, production, manager...) : aucune cle de
`PREGNANCY_FIELDS` ne sort jamais, quelle que soit la route, la mise en cache ou la jointure qui a porte un
patient ou un resultat de laboratoire. Seuls medecin, nurse, laborantin, admin et promoteur les voient.

Le role est pose sur `request.state.pregnancy_visible` par `get_current_user` / `role_required` /
`deny_roles` (voir auth_endpoints.py). Valeur absente (route publique, erreur d'authentification, dependance
remplacee) = non autorise : on retire. Middleware ASGI pur : seules les reponses `application/json` dont le
corps cite un nom de champ de grossesse sont decodees ; le reste passe sans copie.
"""
import json
import math

from utils.pregnancy_visibility import strip_pregnancy_fields_always

# Recherche d'indices dans le corps en minuscules (cles de grossesse sous toute epellation) ; `\\u` couvre
# les noms de cles ecrits en echappements unicode. Un faux positif ne coute qu'un decodage.
_NEEDLES = (b"pregnan", b"gestation", b"grossesse", b"enceinte", b"dpa", b"\\u")
_GENERIC_ERROR = b'{"detail":"Internal Server Error"}'


def _finite_or_none(text):
    value = float(text)
    return value if math.isfinite(value) else None


class PregnancyFilterMiddleware:
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        state = scope.setdefault("state", {})
        start_message = None
        chunks = []
        passthrough = False

        async def send_wrapper(message):
            nonlocal start_message, passthrough
            if passthrough:
                await send(message)
                return
            if message["type"] == "http.response.start":
                headers = {k.lower(): v for k, v in message.get("headers", [])}
                ctype = headers.get(b"content-type", b"").lower()
                if state.get("pregnancy_visible") is True or not ctype.startswith(b"application/json"):
                    passthrough = True
                    await send(message)
                    return
                start_message = message
                return
            if message["type"] == "http.response.body":
                chunks.append(message.get("body", b""))
                if message.get("more_body"):
                    return
                body = b"".join(chunks)
                lowered = body.lower()
                failed = False
                if any(n in lowered for n in _NEEDLES):
                    try:
                        # Lecture tolerante : NaN / Infinity / 1e999 deviennent null, jamais une erreur.
                        data = json.loads(
                            body, parse_constant=lambda _c: None, parse_float=_finite_or_none,
                        )
                        body = json.dumps(
                            strip_pregnancy_fields_always(data),
                            ensure_ascii=False, allow_nan=False, separators=(",", ":"),
                        ).encode("utf-8")
                    except Exception:
                        # Echec ferme : jamais le corps d'origine a un destinataire non autorise.
                        failed = True
                        body = _GENERIC_ERROR
                headers = [(k, v) for k, v in start_message.get("headers", []) if k.lower() != b"content-length"]
                headers.append((b"content-length", str(len(body)).encode("ascii")))
                begin = {**start_message, "headers": headers}
                if failed:
                    begin["status"] = 500
                await send(begin)
                await send({"type": "http.response.body", "body": body})
                return
            await send(message)

        await self.app(scope, receive, send_wrapper)
