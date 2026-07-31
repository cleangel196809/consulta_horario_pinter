# Consulta de Horarios PINTER

Aplicación web del **Politécnico Internacional** para consultar horarios de
clase, docentes y estudiantes a partir de los archivos institucionales de
**PLANEACIÓN** e **INSCRITOS POR CICLO** (Excel). La cédula es la llave
primaria tanto de docentes como de estudiantes en la base de datos
PostgreSQL.

- **Backend:** Python (FastAPI) + SQLAlchemy
- **Base de datos:** PostgreSQL
- **Frontend:** HTML/CSS/JS simple (sin frameworks, servido como archivos
  estáticos), con diseño **responsive** para celular y el logo institucional
  en todas las pantallas.
- **Autenticación:** usuario/contraseña con roles `admin`, `consulta` y
  `coordinador`
- **Contenedores:** Docker Compose (API + PostgreSQL + Adminer)

## Roles

| Rol | Consultar horarios/docentes/estudiantes | Alcance de la consulta | Cargar archivos Excel | Gestionar usuarios |
|---|---|---|---|---|
| `admin` | Sí | Todo | Sí | Sí |
| `coordinador` | Sí | Limitado a su **facultad y/o sede** de alcance | No (403) | No (403) |
| `consulta` | Sí | Todo | No (403) | No (403) |

Solo el administrador puede cargar los archivos de **planeación** e
**inscritos** en cada ciclo, desde el Panel administrador de la aplicación
(o mediante la carga automática/cron descrita más abajo). El rol
`coordinador` es de solo lectura, igual que `consulta`, pero sus resultados
(horarios, dashboard, reportes) quedan filtrados automáticamente a la
facultad y/o sede que se le asigne al crear su usuario.

## Modelo de datos (PostgreSQL)

Ver el detalle completo en [`backend/scripts/init_db.sql`](backend/scripts/init_db.sql).

- `docentes` — llave primaria: `cedula` (documento del docente)
- `estudiantes` — llave primaria: `cedula` (documento del estudiante)
- `horarios` — una fila por franja de clase (día, hora, salón, sede, docente, grupo, asignatura, período)
- `inscripciones` — matrícula de un estudiante en un grupo/asignatura de un período (se cruza con `horarios` por `grupo` para armar el horario del estudiante)
- `usuarios` — cuentas de acceso a la aplicación (`admin` / `consulta` /
  `coordinador`, con `facultad_alcance` / `sede_alcance` opcionales para
  limitar el alcance de un coordinador)
- `cargas_archivo` — auditoría de cada archivo Excel cargado (quién, cuándo, cuántas filas)

## Formulario de consulta

La pantalla principal (`/consulta.html`) permite filtrar el horario por:
**día, sede, salón, materia y grupo de formación**, además de docente y
período. Una sección plegable de **"Búsqueda avanzada"** agrega
autocompletado (con `<datalist>`) por **facultad, programa y jornada**.

Cuando un horario trae código Moodle o enlace de Teams en el archivo de
planeación, la tabla de resultados muestra un botón **"Entrar a clase"** que
abre directamente ese enlace.

También hay búsqueda dedicada por **cédula o nombre** de docente
(`/docentes.html`) y de estudiante (`/estudiantes.html`), mostrando el
horario específico de esa persona, con botones para **descargar el horario
en PDF** o **agregarlo al calendario (.ics)** — compatible con Outlook y
Google Calendar, como evento semanal recurrente.

## Reportes (`/dashboard.html`)

Disponible para cualquier usuario autenticado (filtrado por alcance si es
`coordinador`):

- **Dashboard de indicadores**: grupos por origen (planeación/reflejos/
  cerrados), matriculados por programa, por sede y por jornada, y ocupación
  de salones por franja horaria (gráficas con Chart.js).
- **Carga horaria por docente**: horas y clases por semana, con alerta de
  **sobrecarga** (> 22 horas/semana, configurable en
  `backend/app/routers/reportes.py`).
- **Comparador entre ciclos** (ej. `2026-2T` vs `2026-3T`): grupos nuevos,
  eliminados y modificados (cambio de docente, salón, día u hora).
- **Reporte de inconsistencias**: grupos marcados como **CERRADOS** que
  igual conservan un horario activo en PLANEACIÓN/REFLEJOS, y filas de
  REFLEJOS sin un grupo vigente correspondiente en PLANEACIÓN.
- **Detección de choques** de horario (mismo docente o mismo salón, mismo
  día, con solape de horas).

## Puesta en marcha con Docker

1. Copia `.env.example` a `.env` y ajusta las contraseñas:
   ```bash
   cp .env.example .env
   ```
2. Levanta todo con:
   ```bash
   docker compose up --build
   ```
3. Abre:
   - Aplicación: http://localhost:8000
   - Documentación interactiva de la API: http://localhost:8000/docs
   - Adminer (administrar la base de datos): http://localhost:8080 (sistema: PostgreSQL, servidor: `db`)

Al iniciar por primera vez, la aplicación crea automáticamente tres usuarios
de prueba:

| Usuario | Contraseña | Rol | Notas |
|---|---|---|---|
| `admin` | `admin123` | `admin` | Definidos en `.env` (`ADMIN_USERNAME`/`ADMIN_PASSWORD`) |
| `consulta_prueba` | `prueba123` | `consulta` | Solo lectura, sin restricción de facultad/sede |
| `coord_prueba` | `coord123` | `coordinador` | Solo lectura, limitado a la facultad `SALUD` (configurable con `COORD_FACULTAD_ALCANCE`) |

**Cambia las tres contraseñas apenas ingreses**, desde el panel de usuarios
(los usuarios de prueba pueden desactivarse ahí mismo si no los necesitas).

## Cargar los archivos de cada ciclo (solo administrador)

**Opción 1 — manual, desde el Panel administrador:**

1. Inicia sesión con una cuenta de rol `admin`.
2. Ve a **Panel administrador**. La tarjeta **"🆕 Iniciar carga de un nuevo
   ciclo"** te permite escribir el período una sola vez (ej. `2026-3T`) y se
   completa automáticamente en los dos formularios de carga de abajo.
3. En "Cargar PLANEACIÓN" o "Cargar INSCRITOS", selecciona el archivo `.xlsx`.
4. El sistema procesa el archivo y muestra cuántas filas se cargaron
   correctamente y cuántas tuvieron error, además de dejar registro en el
   historial de cargas. Desde ahí también puedes pulsar **"Notificar"** para
   avisar por correo a los docentes/estudiantes afectados por esa carga
   (requiere SMTP configurado, ver más abajo).

**Opción 2 — automática (cron), sin subir el archivo a mano cada ciclo:**

`backend/scripts/auto_import.py` revisa una carpeta compartida
(`WATCH_DIR`, montada en Docker Compose como `./carga_automatica`) buscando
archivos `.xlsx` cuyo nombre contenga "PLANEACION" o "INSCRITOS". Si el
archivo es nuevo (por nombre + fecha de modificación, comparado contra el
historial de `cargas_archivo`), lo importa automáticamente y deja el
registro con el usuario `auto_import` (una cuenta inactiva creada solo para
trazabilidad, no puede iniciar sesión). Prográmalo con cron:

```bash
0 1 * * *  docker exec pinter_api python scripts/auto_import.py >> /var/log/pinter_auto_import.log 2>&1
```

En Windows, se puede programar la misma línea (`docker exec pinter_api
python scripts/auto_import.py`) con el Programador de tareas.

Los importadores (`backend/app/services/excel_import.py`) detectan las
columnas por nombre (no por posición fija), así que toleran variaciones
menores de formato entre ciclos. Fueron probados con los archivos reales
`PLANEACIÓN 2026-3T` (hojas PLANEACION, REFLEJOS, CERRADOS, DOCENTES) e
`INSCRITOS_POR_CICLO`.

## Endpoints principales de la API

- `POST /api/auth/login` — inicio de sesión
- `GET /api/horarios` — consulta con filtros `dia`, `sede`, `salon`, `materia`, `grupo`, `docente_nombre`, `periodo`, `facultad`, `programa`, `jornada`
- `GET /api/horarios/filtros` — valores disponibles para poblar los combos (incluye facultades/programas/jornadas)
- `GET /api/horarios/choques` — detecta cruces de horario (mismo docente o mismo salón solapados)
- `GET /api/docentes`, `GET /api/docentes/{cedula}/horario`
- `GET /api/docentes/{cedula}/horario.pdf`, `GET /api/docentes/{cedula}/horario.ics` — exportar horario del docente
- `GET /api/estudiantes`, `GET /api/estudiantes/{cedula}/horario`
- `GET /api/estudiantes/{cedula}/horario.pdf`, `GET /api/estudiantes/{cedula}/horario.ics` — exportar horario del estudiante
- `GET /api/reportes/dashboard` — indicadores generales (grupos, matriculados, ocupación de salones)
- `GET /api/reportes/carga-horaria-docentes` — horas/semana por docente y alerta de sobrecarga
- `GET /api/reportes/comparar-periodos?periodo_a=...&periodo_b=...` — diferencias entre dos ciclos
- `GET /api/reportes/inconsistencias` — cruces PLANEACIÓN / REFLEJOS / CERRADOS
- `POST /api/admin/cargar-planeacion`, `POST /api/admin/cargar-inscritos` — **solo admin**
- `GET /api/admin/cargas` — historial de cargas — **solo admin**
- `POST /api/admin/cargas/{id}/notificar` — notifica por correo a los afectados por una carga — **solo admin**
- `POST /api/usuarios`, `GET /api/usuarios` — gestión de usuarios (incluye rol `coordinador` con `facultad_alcance`/`sede_alcance`) — **solo admin**

Todos los endpoints de solo lectura respetan el alcance del rol
`coordinador`: si el usuario tiene `facultad_alcance` y/o `sede_alcance`
asignados, los resultados se filtran automáticamente a esos valores
(`backend/app/deps.py::aplicar_alcance_coordinador`).

## Notificaciones por correo (opcional)

Al cargar un archivo, el administrador puede pulsar **"Notificar"** en el
historial de cargas para avisar por correo a los docentes (carga de
planeación) o estudiantes (carga de inscritos) afectados. Esto requiere
configurar las variables `SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`,
`SMTP_PASSWORD`, `SMTP_FROM` y `SMTP_USE_TLS` en el `.env`. Si no están
configuradas, el endpoint responde claramente `"habilitado": false` con un
mensaje explicativo, en vez de fallar.

## Limitaciones conocidas / notas de los datos reales

- La **sede** no siempre viene en una columna separada en PLANEACIÓN: se
  extrae del texto de `NOMBRE_SALON` (ej. "SALÓN 403-SEDE SUR") o, si no,
  de la columna `MODALIDAD` cuando coincide con una sede conocida. Si tu
  institución empieza a diligenciar una columna `SEDE` explícita, es fácil
  ajustar `_extraer_sede()` para priorizarla.
- La hoja **REFLEJOS** usa nombres de columna distintos para la asignatura
  y el grupo "vigente" (a la que se refleja la materia no ofertada); el
  importador ya los reconoce como alias.
- Docentes con documento `0` en el archivo (marcador de "sin asignar") se
  guardan como horario sin docente, no como docente inválido.

## Utilidades adicionales de la aplicación

Ya incluidas:
- Detección de **choques de horario** (mismo docente o mismo salón, mismo día, con solape de horas) vía `GET /api/horarios/choques`.
- **Auditoría de cargas**: quién subió qué archivo, cuándo, y con cuántas filas/errores.
- Gestión de usuarios con roles (`admin` / `consulta` / `coordinador`) desde el propio panel admin.
- **Exportar horario a PDF o a calendario (.ics)** individual por estudiante o por docente, para importarlo a Outlook/Google Calendar (evento semanal recurrente).
- **Notificación por correo** (opcional, requiere SMTP) al estudiante o docente cuando se carga su horario.
- **Dashboard de indicadores**: grupos por origen, matriculados por programa/sede/jornada, ocupación de salones por franja horaria.
- **Reporte de carga horaria por docente** (horas/semana) con alerta de sobrecarga.
- **Comparador entre ciclos** (ej. 2026-2T vs 2026-3T) para ver qué grupos, docentes o salones cambiaron.
- **Autocompletado y búsqueda avanzada** (por facultad, programa, jornada) en el formulario de consulta.
- **Rol "coordinador"**, con acceso de solo lectura filtrado a su propia facultad y/o sede.
- **Botón "Entrar a clase"** que usa los enlaces de Moodle/Teams que ya trae el archivo de planeación.
- **App responsive para celular** (menús, tablas y formularios adaptados a pantallas pequeñas).
- **Reporte de inconsistencias** entre PLANEACIÓN, REFLEJOS y CERRADOS (ej. un grupo marcado cerrado que sigue con horario activo).
- **Carga programada (cron)** que lee automáticamente los archivos nuevos desde una carpeta compartida, sin necesidad de subirlos manualmente cada ciclo (`backend/scripts/auto_import.py`).
- **Identidad visual institucional**: el logo del Politécnico Internacional en el login y en todas las pantallas, y en los PDF de horario exportados.

Ideas para siguientes iteraciones:
1. **Versionado histórico** de horarios por período, para comparar más de dos ciclos a la vez o ver la línea de tiempo completa de un grupo.
2. Envío real de notificaciones push/WhatsApp además del correo.
3. Exportación masiva (ZIP) de los PDF de horario de todo un programa o facultad.

## Estructura del repositorio

```
consulta_horario_pinter/
├── backend/
│   ├── app/
│   │   ├── main.py            # arranque de FastAPI, monta el frontend estático
│   │   ├── models.py          # tablas SQLAlchemy (docentes, estudiantes, horarios, ...)
│   │   ├── schemas.py         # esquemas Pydantic de entrada/salida
│   │   ├── security.py        # hashing de contraseñas y JWT
│   │   ├── deps.py            # autenticación, rol admin y alcance de coordinador
│   │   ├── assets/logo-pinter.png  # logo institucional (usado en los PDF exportados)
│   │   ├── routers/           # endpoints agrupados por recurso (horarios, exportar, reportes, ...)
│   │   └── services/
│   │       ├── excel_import.py    # importación de los Excel institucionales
│   │       ├── exportar.py        # generación de horario en PDF (reportlab) e ICS
│   │       └── notificaciones.py  # envío de correo (opcional, requiere SMTP)
│   ├── scripts/
│   │   ├── init_db.sql        # esquema completo de PostgreSQL
│   │   └── auto_import.py     # carga automática (cron) desde carpeta compartida
│   ├── requirements.txt
│   └── Dockerfile
├── frontend/                  # login, consulta, docentes, estudiantes, dashboard, panel admin
│   └── img/logo-pinter.png    # logo institucional (topbar y login)
├── carga_automatica/          # carpeta observada por auto_import.py (montada en Docker)
├── docker-compose.yml
├── .env.example
└── README.md
```

## Pruebas realizadas

Antes de publicar el repositorio se validó todo, con un PostgreSQL real
(embebido con `pgserver`, sin necesidad de Docker) y peticiones HTTP reales
contra la API (`TestClient`):

**Base y carga de datos**
- Creación del esquema completo (`init_db.sql`, incluido el rol
  `coordinador` y sus columnas de alcance) sin errores.
- Importación completa del archivo `PLANEACIÓN 2026-3T` real (hojas
  PLANEACION + REFLEJOS + CERRADOS + DOCENTES): **1593 filas procesadas,
  0 errores**.
- Importación del archivo `INSCRITOS_POR_CICLO` real (probado con muestras
  de 1000 y 5000 filas, y con el archivo completo en la fase inicial):
  **0 errores** en todos los casos.

**Funcionalidades nuevas (47 verificaciones automáticas, todas exitosas)**
- Autenticación y control de roles: `admin`, `consulta` y `coordinador`,
  incluyendo los 403 esperados en cada ruta restringida.
- Exportación de horario a PDF e ICS, para estudiante y para docente
  (contenido no vacío, `Content-Type` correcto, `RRULE` presente en el ICS).
- Dashboard de indicadores, carga horaria docente (con conteo de docentes en
  sobrecarga), comparador entre dos períodos y reporte de inconsistencias.
- Detección de choques de horario.
- Creación de un usuario `coordinador` con alcance de facultad, verificando
  que sus consultas quedan efectivamente filtradas a esa facultad.
- Endpoint de notificación por correo respondiendo correctamente
  `"habilitado": false` cuando SMTP no está configurado.
- Historial de cargas y listado de usuarios.
- Script `auto_import.py`: detecta un archivo nuevo en la carpeta
  observada, lo procesa, deduplica si se ejecuta de nuevo sin cambios, y
  reprocesa si el archivo se reemplaza (fecha de modificación distinta).
- Sintaxis validada (`node --check`) de todos los archivos JavaScript del
  frontend, incluidos los scripts embebidos en cada página.
