# Consulta de Horarios PINTER

Aplicación web para consultar horarios de clase, docentes y estudiantes a
partir de los archivos institucionales de **PLANEACIÓN** e **INSCRITOS POR
CICLO** (Excel). La cédula es la llave primaria tanto de docentes como de
estudiantes en la base de datos PostgreSQL.

- **Backend:** Python (FastAPI) + SQLAlchemy
- **Base de datos:** PostgreSQL
- **Frontend:** HTML/CSS/JS simple (sin frameworks, servido como archivos estáticos)
- **Autenticación:** usuario/contraseña con roles `admin` y `consulta`
- **Contenedores:** Docker Compose (API + PostgreSQL + Adminer)

## Roles

| Rol | Puede consultar horarios/docentes/estudiantes | Puede cargar archivos Excel | Puede gestionar usuarios |
|---|---|---|---|
| `admin` | Sí | Sí | Sí |
| `consulta` | Sí | No (403) | No (403) |

Solo el administrador puede cargar los archivos de **planeación** e
**inscritos** en cada ciclo, desde el Panel administrador de la aplicación.

## Modelo de datos (PostgreSQL)

Ver el detalle completo en [`backend/scripts/init_db.sql`](backend/scripts/init_db.sql).

- `docentes` — llave primaria: `cedula` (documento del docente)
- `estudiantes` — llave primaria: `cedula` (documento del estudiante)
- `horarios` — una fila por franja de clase (día, hora, salón, sede, docente, grupo, asignatura, período)
- `inscripciones` — matrícula de un estudiante en un grupo/asignatura de un período (se cruza con `horarios` por `grupo` para armar el horario del estudiante)
- `usuarios` — cuentas de acceso a la aplicación (`admin` / `consulta`)
- `cargas_archivo` — auditoría de cada archivo Excel cargado (quién, cuándo, cuántas filas)

## Formulario de consulta

La pantalla principal (`/consulta.html`) permite filtrar el horario por:
**día, sede, salón, materia y grupo de formación**, además de docente y período.

También hay búsqueda dedicada por **cédula o nombre** de docente
(`/docentes.html`) y de estudiante (`/estudiantes.html`), mostrando el
horario específico de esa persona.

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

Al iniciar por primera vez, la aplicación crea automáticamente el usuario
administrador definido en `.env` (`ADMIN_USERNAME` / `ADMIN_PASSWORD`).
**Cámbialo apenas ingreses** desde el panel de usuarios.

## Cargar los archivos de cada ciclo (solo administrador)

1. Inicia sesión con una cuenta de rol `admin`.
2. Ve a **Panel administrador**.
3. En "Cargar PLANEACIÓN" o "Cargar INSCRITOS", indica el período/ciclo
   (ej. `2026-3T`) y selecciona el archivo `.xlsx`.
4. El sistema procesa el archivo y muestra cuántas filas se cargaron
   correctamente y cuántas tuvieron error, además de dejar registro en el
   historial de cargas.

Los importadores (`backend/app/services/excel_import.py`) detectan las
columnas por nombre (no por posición fija), así que toleran variaciones
menores de formato entre ciclos. Fueron probados con los archivos reales
`PLANEACIÓN 2026-3T` (hojas PLANEACION, REFLEJOS, CERRADOS, DOCENTES) e
`INSCRITOS_POR_CICLO`.

## Endpoints principales de la API

- `POST /api/auth/login` — inicio de sesión
- `GET /api/horarios` — consulta con filtros `dia`, `sede`, `salon`, `materia`, `grupo`, `docente_nombre`, `periodo`
- `GET /api/horarios/filtros` — valores disponibles para poblar los combos
- `GET /api/horarios/choques` — detecta cruces de horario (mismo docente o mismo salón solapados)
- `GET /api/docentes`, `GET /api/docentes/{cedula}/horario`
- `GET /api/estudiantes`, `GET /api/estudiantes/{cedula}/horario`
- `POST /api/admin/cargar-planeacion`, `POST /api/admin/cargar-inscritos` — **solo admin**
- `GET /api/admin/cargas` — historial de cargas — **solo admin**
- `POST /api/usuarios`, `GET /api/usuarios` — gestión de usuarios — **solo admin**

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

## Utilidades adicionales sugeridas para la aplicación

Ya incluidas en esta primera versión:
- Detección de **choques de horario** (mismo docente o mismo salón, mismo día, con solape de horas) vía `GET /api/horarios/choques`.
- **Auditoría de cargas**: quién subió qué archivo, cuándo, y con cuántas filas/errores.
- Gestión de usuarios con roles desde el propio panel admin.

Ideas para siguientes iteraciones:
1. **Exportar horario a PDF o a calendario (.ics)** individual por estudiante o por docente, para importarlo a Outlook/Google Calendar.
2. **Notificación por correo** al estudiante o docente cuando se carga o modifica su horario.
3. **Dashboard de indicadores**: grupos abiertos vs. cerrados, matriculados por programa/sede/jornada, ocupación de salones por franja horaria.
4. **Reporte de carga horaria por docente** (horas/semana) con alertas de sobrecarga o de choques.
5. **Comparador entre ciclos** (ej. 2026-2T vs 2026-3T) para ver qué grupos, docentes o salones cambiaron.
6. **Autocompletado y búsqueda avanzada** (por facultad, programa, jornada) en el formulario de consulta.
7. **Rol adicional "coordinador"**, con acceso de solo lectura filtrado a su propia facultad o sede.
8. **Integración con los enlaces de Moodle/Teams** que ya trae el archivo de planeación, como botón directo "Entrar a clase".
9. **Versionado histórico** de horarios por período para poder auditar cambios de un ciclo a otro.
10. **App/versión responsive para celular**, para que los estudiantes consulten su horario del día desde el móvil.
11. **Reporte de inconsistencias** entre PLANEACIÓN, REFLEJOS y CERRADOS (por ejemplo, un grupo que aparece cerrado pero sigue con horario activo).
12. **Carga programada (cron)** que lea automáticamente el archivo más reciente desde una carpeta compartida, sin necesidad de subirlo manualmente cada ciclo.

## Estructura del repositorio

```
consulta_horario_pinter/
├── backend/
│   ├── app/
│   │   ├── main.py            # arranque de FastAPI, monta el frontend estático
│   │   ├── models.py          # tablas SQLAlchemy (docentes, estudiantes, horarios, ...)
│   │   ├── schemas.py         # esquemas Pydantic de entrada/salida
│   │   ├── security.py        # hashing de contraseñas y JWT
│   │   ├── deps.py            # dependencias de autenticación y de rol admin
│   │   ├── routers/           # endpoints agrupados por recurso
│   │   └── services/
│   │       └── excel_import.py  # lógica de importación de los Excel institucionales
│   ├── scripts/init_db.sql    # esquema completo de PostgreSQL
│   ├── requirements.txt
│   └── Dockerfile
├── frontend/                  # login, consulta, docentes, estudiantes, panel admin
├── docker-compose.yml
├── .env.example
└── README.md
```

## Pruebas realizadas

Antes de publicar el repositorio se validó, con un PostgreSQL real:
- Creación del esquema completo (`init_db.sql`) sin errores.
- Importación completa del archivo `PLANEACIÓN 2026-3T` real (hojas
  PLANEACION + REFLEJOS + CERRADOS + DOCENTES): **1593 filas procesadas,
  0 errores**.
- Importación de una muestra del archivo `INSCRITOS_POR_CICLO` real:
  **1000 filas procesadas, 0 errores**.
- Autenticación, control de roles (403 para usuarios de consulta en rutas
  de administrador) y los filtros de consulta (día, sede, salón, materia,
  grupo) probados contra la API real con `TestClient`.
