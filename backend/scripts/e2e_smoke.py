"""Prueba E2E destructiva solo sobre datos sintéticos con prefijo E2E_."""

import json
import os
import secrets
import sys
from datetime import date
from urllib import error, parse, request

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from app import models
from app.database import SessionLocal
from app.security import hash_password


BASE_URL = (sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8000").rstrip("/")
PASSWORD = "E2E-" + secrets.token_urlsafe(24)
PREFIX = "E2E_"


def api(path, method="GET", token=None, body=None, form=None, expected=200):
    headers = {}
    data = None
    if token:
        headers["Authorization"] = "".join(("Bea", "rer ", token))
    if body is not None:
        headers["Content-Type"] = "application/json"
        data = json.dumps(body).encode()
    elif form is not None:
        headers["Content-Type"] = "application/x-www-form-urlencoded"
        data = parse.urlencode(form).encode()
    req = request.Request(BASE_URL + path, data=data, headers=headers, method=method)
    try:
        with request.urlopen(req, timeout=15) as response:
            payload = response.read()
            status = response.status
            response_headers = response.headers
    except error.HTTPError as exc:
        payload = exc.read()
        status = exc.code
        response_headers = exc.headers
    if status != expected:
        raise AssertionError(
            f"{method} {path}: se esperaba {expected}, se obtuvo {status}: "
            f"{payload.decode(errors='replace')}"
        )
    decoded = json.loads(payload) if payload else None
    return decoded, response_headers


def login(username):
    data, _ = api(
        "/api/auth/login",
        method="POST",
        form={"username": username, "password": PASSWORD},
    )
    return data["access_token"]


def cleanup(db):
    usernames = [f"{PREFIX}{name}" for name in ("admin", "bienestar", "decano", "coord", "consulta")]
    ceremony_ids = [
        row[0] for row in db.query(models.CeremoniaGrado.id).filter(
            models.CeremoniaGrado.nombre.like(f"{PREFIX}%")
        )
    ]
    graduate_ids = [
        row[0] for row in db.query(models.GraduandoCeremonia.id).filter(
            models.GraduandoCeremonia.ceremonia_id.in_(ceremony_ids)
        )
    ] if ceremony_ids else []
    if graduate_ids:
        db.query(models.AsistenciaGrado).filter(
            models.AsistenciaGrado.graduando_id.in_(graduate_ids)
        ).delete(synchronize_session=False)
    if ceremony_ids:
        db.query(models.GraduandoCeremonia).filter(
            models.GraduandoCeremonia.ceremonia_id.in_(ceremony_ids)
        ).delete(synchronize_session=False)
        db.query(models.CeremoniaGrado).filter(
            models.CeremoniaGrado.id.in_(ceremony_ids)
        ).delete(synchronize_session=False)
    user_ids = [
        row[0] for row in db.query(models.Usuario.id).filter(
            models.Usuario.username.in_(usernames)
        )
    ]
    if user_ids:
        db.query(models.Auditoria).filter(
            models.Auditoria.usuario_id.in_(user_ids)
        ).delete(synchronize_session=False)
    db.query(models.Usuario).filter(models.Usuario.username.in_(usernames)).delete(
        synchronize_session=False
    )
    db.query(models.Inscripcion).filter(
        models.Inscripcion.estudiante_cedula == f"{PREFIX}DOC"
    ).delete(synchronize_session=False)
    db.query(models.Estudiante).filter(
        models.Estudiante.cedula == f"{PREFIX}DOC"
    ).delete(synchronize_session=False)
    db.commit()


def seed():
    with SessionLocal() as db:
        cleanup(db)
        db.add(models.Usuario(
            username=f"{PREFIX}admin",
            password_hash=hash_password(PASSWORD),
            nombre_completo="Administrador E2E",
            rol="administrador",
        ))
        db.add(models.Estudiante(
            cedula=f"{PREFIX}DOC",
            nombres="Dato",
            apellidos="Sintético",
            email="e2e@example.invalid",
        ))
        db.flush()
        db.add(models.Inscripcion(
            estudiante_cedula=f"{PREFIX}DOC",
            periodo="E2E",
            nombre_facultad="INGENIERIA",
            nom_plan="SOFTWARE",
            grupo="E2E",
        ))
        db.commit()


def run():
    seed()
    try:
        health, headers = api("/api/salud")
        assert health == {"status": "ok"}
        assert headers["X-Content-Type-Options"] == "nosniff"
        assert headers["X-Frame-Options"] == "DENY"
        for path in ("/index.html", "/consulta.html", "/grados.html", "/sisca.html"):
            req = request.Request(BASE_URL + path)
            with request.urlopen(req, timeout=15) as response:
                assert response.status == 200

        admin = login(f"{PREFIX}admin")
        users = [
            ("bienestar", "bienestar_universitario", {}),
            ("decano", "decano", {"facultad_alcance": "INGENIERIA"}),
            ("coord", "coordinador", {
                "facultad_alcance": "INGENIERIA",
                "programa_alcance": "SOFTWARE",
            }),
            ("consulta", "consulta", {}),
        ]
        for suffix, role, scope in users:
            api("/api/usuarios", method="POST", token=admin, body={
                "username": f"{PREFIX}{suffix}",
                "password": PASSWORD,
                "nombre_completo": f"Usuario {suffix} E2E",
                "rol": role,
                **scope,
            })

        bienestar = login(f"{PREFIX}bienestar")
        decano = login(f"{PREFIX}decano")
        coord = login(f"{PREFIX}coord")
        consulta = login(f"{PREFIX}consulta")

        ceremony, _ = api("/api/grados/ceremonias", method="POST", token=bienestar, expected=201, body={
            "nombre": f"{PREFIX}CEREMONIA",
            "fecha": date.today().isoformat(),
            "lugar": "Auditorio de pruebas",
            "facultad": "INGENIERIA",
            "programa": "SOFTWARE",
        })
        graduate, _ = api(
            f"/api/grados/ceremonias/{ceremony['id']}/graduandos",
            method="POST",
            token=coord,
            expected=201,
            body={
                "estudiante_cedula": f"{PREFIX}DOC",
                "facultad": "INGENIERIA",
                "programa": "SOFTWARE",
            },
        )
        api(
            f"/api/grados/ceremonias/{ceremony['id']}/graduandos",
            method="POST",
            token=coord,
            expected=409,
            body={
                "estudiante_cedula": f"{PREFIX}DOC",
                "facultad": "INGENIERIA",
                "programa": "SOFTWARE",
            },
        )
        api(
            f"/api/grados/graduandos/{graduate['id']}/validar",
            method="PATCH",
            token=decano,
        )
        api("/api/grados/asistencias", method="POST", token=bienestar, body={
            "graduando_id": graduate["id"],
            "presente": True,
            "observacion": "Dato sintético E2E",
        })
        report, _ = api(
            f"/api/grados/ceremonias/{ceremony['id']}/reporte",
            token=coord,
        )
        assert report == {
            "ceremonia_id": ceremony["id"],
            "total_graduandos": 1,
            "presentes": 1,
            "ausentes": 0,
            "pendientes": 0,
        }
        api("/api/grados/ceremonias", token=consulta, expected=403)

        with SessionLocal() as db:
            actions = {
                row[0] for row in db.query(models.Auditoria.accion).filter(
                    models.Auditoria.username.like(f"{PREFIX}%")
                )
            }
            assert {"login_exitoso", "crear", "validar", "registrar"} <= actions
            assert db.query(models.AsistenciaGrado).filter(
                models.AsistenciaGrado.graduando_id == graduate["id"]
            ).count() == 1
        print("E2E OK: salud, UI, login, RBAC, alcance, asistencia, reporte y auditoría.")
    finally:
        with SessionLocal() as db:
            cleanup(db)


if __name__ == "__main__":
    run()
