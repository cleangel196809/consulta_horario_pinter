import unittest
from types import SimpleNamespace

from fastapi import HTTPException

from app.deps import dentro_del_alcance, require_roles


class RbacTests(unittest.TestCase):
    def usuario(self, rol, facultad=None, programa=None):
        return SimpleNamespace(
            rol=rol,
            facultad_alcance=facultad,
            sede_alcance=programa,
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
        self.assertTrue(dentro_del_alcance(user, "Facultad de Ingeniería", "Tecnología de Software"))
        self.assertFalse(dentro_del_alcance(user, "Facultad de Salud", "Enfermería"))

    def test_dean_scope_restricts_faculty(self):
        user = self.usuario("decano", "Salud")
        self.assertTrue(dentro_del_alcance(user, "Facultad de Salud", "Enfermería"))
        self.assertFalse(dentro_del_alcance(user, "Ingeniería", "Sistemas"))

    def test_missing_scope_never_grants_global_access(self):
        self.assertFalse(dentro_del_alcance(self.usuario("decano"), "Salud", "Enfermería"))
        self.assertFalse(dentro_del_alcance(self.usuario("coordinador"), "Salud", "Enfermería"))


if __name__ == "__main__":
    unittest.main()
