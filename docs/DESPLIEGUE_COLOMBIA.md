# Despliegue y pruebas — contexto colombiano

Esta guía es operativa y de seguridad; no sustituye concepto jurídico ni
afirma certificación o cumplimiento automático.

## 1. Preparación institucional

1. Identifique al **responsable del tratamiento** y documente finalidad, base
   de legitimación, categorías de titulares/datos y encargados.
2. Apruebe política de tratamiento, aviso de privacidad, canal para consultas
   y reclamos, tiempos de conservación y procedimiento de incidentes.
3. Evalúe si corresponde registrar bases en el RNBD según los criterios
   vigentes de la Superintendencia de Industria y Comercio (SIC).
4. Celebre contratos de transmisión de datos con proveedores de nube/correo y
   evalúe transferencias o transmisiones internacionales.
5. Defina roles nominales; no comparta cuentas. Recolecte solo datos necesarios.

Referencias para revisión jurídica: Constitución Política, artículo 15; Ley
1581 de 2012; Decreto 1074 de 2015 (régimen compilado de protección de datos);
Ley 1266 de 2008 cuando existan datos financieros/crediticios; Ley 1273 de 2009
para delitos informáticos; y guías/instrucciones vigentes de la SIC.

## 2. Preparar infraestructura

1. Use PostgreSQL administrado con cifrado, copias automáticas y acceso privado.
2. Publique la API solo detrás de HTTPS/TLS y un proxy/WAF con limitación
   compartida de intentos si hay varias réplicas.
3. Genere secretos fuera del repositorio:

   ```bash
   openssl rand -base64 48
   openssl rand -base64 32
   ```

4. Configure `POSTGRES_*`, `SECRET_KEY`, `ACCESS_TOKEN_EXPIRE_MINUTES`,
   `CORS_ORIGINS` y SMTP en el gestor de secretos. No use datos reales en
   ambientes de prueba.
5. Restrinja backups, logs, Adminer y consola de nube a personal autorizado.

## 3. Respaldo y despliegue

1. Abra una ventana de cambio y registre aprobador, versión y plan de reversa.
2. Cree y verifique un respaldo:

   ```bash
   pg_dump -Fc "$DATABASE_URL" > "pre_despliegue_$(date +%Y%m%d_%H%M).dump"
   pg_restore --list pre_despliegue_*.dump >/dev/null
   ```

3. En Docker, copie `.env.example` a `.env`, reemplace todos los valores y
   ejecute:

   ```bash
   docker compose config --quiet
   docker compose up -d --build
   docker compose ps
   docker compose logs --tail=100 api
   ```

4. En Render, conecte el repositorio, aplique `render.yaml`, configure
   `ADMIN_PASSWORD`, `CORS_ORIGINS` y SMTP como secretos, despliegue primero en
   staging y después en producción. No exponga Adminer.
5. Las migraciones se ejecutan al iniciar y quedan registradas en
   `schema_migrations`. Verifique:

   ```sql
   SELECT version, aplicado_en FROM schema_migrations ORDER BY version;
   ```

6. Si no usó `ADMIN_PASSWORD`, cree el administrador sin mostrar su clave:

   ```bash
   docker compose exec api python scripts/create_admin.py
   ```

## 4. Pruebas de aceptación y extremo a extremo

1. Ejecute pruebas unitarias y sintaxis:

   ```bash
   docker compose exec api python -m unittest discover -s tests -v
   docker compose exec api python -m compileall -q app scripts
   ```

2. Ejecute el E2E con datos exclusivamente sintéticos. Crea, verifica y elimina
   automáticamente usuarios `E2E_*`, estudiante, inscripción y ceremonia:

   ```bash
   docker compose exec api python scripts/e2e_smoke.py http://localhost:8000
   ```

3. Compruebe manualmente HTTPS, expiración de sesión, 401/403, alcance de
   decano/coordinador, cabeceras, navegación móvil, respaldo/restauración y que
   logs/auditoría no contengan claves, tokens ni datos personales innecesarios.
4. Valide con el responsable funcional los flujos de Horarios/SIIHAPI y
   Asistencia a Grados. SISCA no debe habilitar operaciones hasta recibir su
   contrato funcional y técnico.

## 5. Salida a producción

1. Cambie DNS o promoción de staging únicamente tras aprobación.
2. Ejecute `GET /api/salud` y el E2E en producción solo si la política autoriza
   datos sintéticos y su limpieza; en caso contrario use staging.
3. Revise métricas, errores, auditoría y consumo de base durante la ventana.
4. Registre evidencia: commit, fecha, aprobador, respaldo, resultados y riesgos.

## 6. Reversa e incidentes

1. Si falla la aplicación, vuelva a la imagen/commit anterior; las tablas
   aditivas pueden permanecer sin afectar el código anterior.
2. Si existe corrupción, restaure el respaldo en una base nueva, valide y
   cambie la conexión; no sobrescriba la única copia.
3. Ante un incidente de datos, contenga accesos, preserve evidencia, rote
   secretos, evalúe alcance y ejecute el procedimiento institucional de
   notificación a titulares/autoridades conforme al análisis jurídico vigente.
