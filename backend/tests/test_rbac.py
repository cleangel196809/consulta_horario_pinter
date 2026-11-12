import unittest
from concurrent.futures import ThreadPoolExecutor
from types import SimpleNamespace

from fastapi import HTTPException

from app.deps import dentro_del_alcance, require_roles
from app.routers import auth


class RbacTests(unittest.TestCase):
    def usuario(self, rol, facultad=None, programa=None):
        return SimpleNamespace(
            rol=rol,
            facultad_alcance=facultad,
            sede_alcance=None,
            programa_alcance=programa,
        )

    def test_role_dependency_rejects_unprivileged_user(self):
        dependency = require_roles("administrador", "bienestar_universitario")
        with self.assertRaises(HTTPException) as error:
            dependency(current_user=self.usuario("consulta"))
        self.assertEqual(error.exception.status_code, 403)

    def test_role_dependency_accepts_wellbeing(self):
        dependency = require_roles("administrador", "bienestar_universitario")
        user = self.usuario("bienestar_universitario")
        self.assertIs(dependency(current_user=user), user)

    def test_coordinator_scope_requires_authorized_faculty_and_program(self):
        user = self.usuario("coordinador", "Ingeniería", "Software")
        self.assertTrue(dentro_del_alcance(user, " ingeniería ", "SOFTWARE"))
        self.assertFalse(dentro_del_alcance(user, "Facultad de Salud", "Enfermería"))

    def test_dean_scope_restricts_faculty(self):
        user = self.usuario("decano", "Salud")
        self.assertTrue(dentro_del_alcance(user, "SALUD", "Enfermería"))
        self.assertFalse(dentro_del_alcance(user, "Ingeniería", "Sistemas"))

    def test_missing_scope_never_grants_global_access(self):
        self.assertFalse(dentro_del_alcance(self.usuario("decano"), "Salud", "Enfermería"))
        self.assertFalse(dentro_del_alcance(self.usuario("coordinador"), "Salud", "Enfermería"))

    def test_failed_login_attempts_are_bounded_per_client(self):
        auth._failed_attempts.clear()
        allowed = []
        for _ in range(auth.LOGIN_MAX_ATTEMPTS + 5):
            allowed.append(auth._reserve_login_attempt("test-client")[0])
        self.assertEqual(
            len(auth._failed_attempts["test-client"]),
            auth.LOGIN_MAX_ATTEMPTS,
        )
        self.assertEqual(allowed.count(True), auth.LOGIN_MAX_ATTEMPTS)
        auth._failed_attempts.clear()

    def test_failed_login_reservation_is_atomic_and_globally_bounded(self):
        auth._failed_attempts.clear()
        with ThreadPoolExecutor(max_workers=20) as pool:
            results = list(pool.map(
                lambda _: auth._reserve_login_attempt("parallel-client")[0],
                range(50),
            ))
        self.assertEqual(results.count(True), auth.LOGIN_MAX_ATTEMPTS)

        original_limit = auth.LOGIN_MAX_CLIENTS
        try:
            auth.LOGIN_MAX_CLIENTS = 2
            auth._failed_attempts.clear()
            self.assertTrue(auth._reserve_login_attempt("one")[0])
            self.assertTrue(auth._reserve_login_attempt("two")[0])
            self.assertFalse(auth._reserve_login_attempt("three")[0])
        finally:
            auth.LOGIN_MAX_CLIENTS = original_limit
            auth._failed_attempts.clear()


if __name__ == "__main__":
    unittest.main()
