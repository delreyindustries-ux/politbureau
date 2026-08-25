"""Cadena de certificats per als servidors de l'Administracio espanyola.

Els dominis `*.gob.es` fan servir certificats de la FNMT, pero els servidors NO
envien el certificat intermedi ("AC Componentes Informaticos"). Sense ell,
Python no pot lligar el certificat del servidor amb l'arrel de la FNMT, que si
que te, i la connexio falla amb CERTIFICATE_VERIFY_FAILED.

La solucio correcta NO es desactivar la verificacio (`verify=False`), que ens
deixaria oberts a un atac de home-al-mig. El que fem es llegir l'extensio AIA
del certificat del servidor -- que diu on trobar l'intermedi que falta --,
baixar-lo i construir un magatzem propi = certifi + intermedis. La verificacio
segueix activa de cap a peus.
"""
from __future__ import annotations

import socket
import ssl
from pathlib import Path

import certifi
import requests
from cryptography import x509
from cryptography.hazmat.primitives.serialization import Encoding

ROOT = Path(__file__).resolve().parents[3]
BUNDLE = ROOT / "data" / "gob-es-ca-bundle.pem"


def _missing_intermediates(host: str, port: int = 443) -> list[bytes]:
    """Segueix la cadena AIA cap amunt i retorna els certificats en format PEM."""
    context = ssl.create_default_context()
    context.check_hostname = False
    context.verify_mode = ssl.CERT_NONE
    with socket.create_connection((host, port), timeout=30) as sock:
        with context.wrap_socket(sock, server_hostname=host) as tls:
            der = tls.getpeercert(binary_form=True)

    collected, seen = [], set()
    cert = x509.load_der_x509_certificate(der)
    for _ in range(4):                       # cap cadena real es mes llarga
        try:
            aia = cert.extensions.get_extension_for_class(
                x509.AuthorityInformationAccess).value
        except x509.ExtensionNotFound:
            break
        url = next((d.access_location.value for d in aia
                    if d.access_method._name == "caIssuers"), None)
        if not url or url in seen:
            break
        seen.add(url)
        resp = requests.get(url, timeout=60)
        resp.raise_for_status()
        body = resp.content
        issuer = (x509.load_pem_x509_certificate(body) if body.lstrip().startswith(b"-----")
                  else x509.load_der_x509_certificate(body))
        collected.append(issuer.public_bytes(Encoding.PEM))
        if issuer.subject == issuer.issuer:  # hem arribat a l'arrel
            break
        cert = issuer
    return collected


def bundle(host: str = "infoelectoral.interior.gob.es", refresh: bool = False) -> str:
    """Ruta a un magatzem de CA que si que pot verificar els servidors .gob.es."""
    if BUNDLE.exists() and not refresh:
        return str(BUNDLE)
    pem = Path(certifi.where()).read_bytes()
    extra = b"".join(_missing_intermediates(host))
    BUNDLE.parent.mkdir(parents=True, exist_ok=True)
    BUNDLE.write_bytes(pem + b"\n" + extra)
    return str(BUNDLE)


def session(host: str = "infoelectoral.interior.gob.es") -> requests.Session:
    sess = requests.Session()
    sess.verify = bundle(host)
    sess.headers["User-Agent"] = "politbureau/0.1 (projecte educatiu)"
    return sess
