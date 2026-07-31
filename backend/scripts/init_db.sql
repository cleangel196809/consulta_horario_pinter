-- =====================================================================
-- Esquema de base de datos: Consulta de Horarios PINTER
-- Motor: PostgreSQL 14+
-- La cédula (documento de identidad) es la llave primaria natural tanto
-- de docentes como de estudiantes, tal como lo maneja la institución.
-- =====================================================================

CREATE TABLE IF NOT EXISTS docentes (
    cedula              BIGINT PRIMARY KEY,
    nombre_completo      VARCHAR(200) NOT NULL,
    correo_institucional VARCHAR(150),
    facultad             VARCHAR(150),
    sede                 VARCHAR(100),
    activo               BOOLEAN DEFAULT TRUE,
    creado_en            TIMESTAMP DEFAULT NOW(),
    actualizado_en       TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS estudiantes (
    cedula                 VARCHAR(30) PRIMARY KEY,
    tipo                   VARCHAR(30),
    nombres                VARCHAR(150),
    apellidos              VARCHAR(150),
    correo_aula_virtual    VARCHAR(150),
    email                  VARCHAR(150),
    celular                VARCHAR(30),
    telefono               VARCHAR(30),
    ciclo_ingreso          VARCHAR(20),
    creado_en              TIMESTAMP DEFAULT NOW(),
    actualizado_en         TIMESTAMP DEFAULT NOW()
);

-- Un registro de horario = una franja de clase de un grupo/asignatura
CREATE TABLE IF NOT EXISTS horarios (
    id                     BIGSERIAL PRIMARY KEY,
    llave                  VARCHAR(60),
    periodo                VARCHAR(20) NOT NULL,          -- ej: 2026-3T (ciclo de carga)
    codigo_asignatura      VARCHAR(20),
    facultad               VARCHAR(150),
    programa               VARCHAR(250),
    plan                   VARCHAR(30),
    asignatura             VARCHAR(250),
    ciclo                  VARCHAR(10),
    creditos               VARCHAR(10),
    grupo                  VARCHAR(60) NOT NULL,
    codigo_moodle          VARCHAR(100),
    codigo_teams           VARCHAR(100),
    enlace_teams           TEXT,
    estado                 VARCHAR(60),
    modalidad              VARCHAR(100),
    jornada                VARCHAR(60),
    capacidad              INTEGER,
    dia                    VARCHAR(30),
    hora_inicio            TIME,
    hora_fin               TIME,
    nombre_salon           VARCHAR(250),
    sede                   VARCHAR(100),
    docente_cedula         BIGINT REFERENCES docentes(cedula) ON DELETE SET NULL,
    nombre_docente         VARCHAR(200),
    correo_docente         VARCHAR(150),
    observaciones          TEXT,
    origen_hoja            VARCHAR(30) DEFAULT 'PLANEACION',  -- PLANEACION | REFLEJOS | CERRADOS
    carga_id               BIGINT,
    creado_en              TIMESTAMP DEFAULT NOW(),
    actualizado_en         TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_horarios_dia ON horarios(dia);
CREATE INDEX IF NOT EXISTS idx_horarios_sede ON horarios(sede);
CREATE INDEX IF NOT EXISTS idx_horarios_salon ON horarios(nombre_salon);
CREATE INDEX IF NOT EXISTS idx_horarios_asignatura ON horarios(asignatura);
CREATE INDEX IF NOT EXISTS idx_horarios_grupo ON horarios(grupo);
CREATE INDEX IF NOT EXISTS idx_horarios_docente ON horarios(docente_cedula);
CREATE INDEX IF NOT EXISTS idx_horarios_periodo ON horarios(periodo);

-- Matrícula del estudiante en una asignatura/grupo de un ciclo
CREATE TABLE IF NOT EXISTS inscripciones (
    id                     BIGSERIAL PRIMARY KEY,
    estudiante_cedula      VARCHAR(30) NOT NULL REFERENCES estudiantes(cedula) ON DELETE CASCADE,
    periodo                VARCHAR(20) NOT NULL,
    ciclo_ingreso          VARCHAR(20),
    cod_plan               VARCHAR(30),
    nom_plan               VARCHAR(250),
    cod_asignatura         VARCHAR(20),
    asignatura             VARCHAR(250),
    ciclo                  VARCHAR(10),
    creditos               VARCHAR(10),
    grupo                  VARCHAR(60),
    jornada                VARCHAR(60),
    estado                 VARCHAR(60),
    sede                   VARCHAR(100),
    identificador          VARCHAR(120),
    flg_virtual            VARCHAR(5),
    semilla                VARCHAR(60),
    nombre_facultad        VARCHAR(150),
    carga_id               BIGINT,
    creado_en              TIMESTAMP DEFAULT NOW(),
    UNIQUE (estudiante_cedula, periodo, cod_asignatura, grupo)
);

CREATE INDEX IF NOT EXISTS idx_inscripciones_estudiante ON inscripciones(estudiante_cedula);
CREATE INDEX IF NOT EXISTS idx_inscripciones_grupo ON inscripciones(grupo);
CREATE INDEX IF NOT EXISTS idx_inscripciones_periodo ON inscripciones(periodo);

-- Usuarios de la aplicación (login).
-- rol = 'admin' (control total) | 'consulta' (solo lectura) |
--       'coordinador' (solo lectura, limitado a su facultad y/o sede)
CREATE TABLE IF NOT EXISTS usuarios (
    id                     BIGSERIAL PRIMARY KEY,
    username               VARCHAR(80) UNIQUE NOT NULL,
    password_hash          VARCHAR(255) NOT NULL,
    nombre_completo        VARCHAR(200),
    rol                    VARCHAR(20) NOT NULL DEFAULT 'consulta' CHECK (rol IN ('admin','consulta','coordinador')),
    cedula_relacionada      VARCHAR(30),  -- opcional: vincula el usuario a un docente/estudiante
    facultad_alcance        VARCHAR(150), -- solo aplica si rol = 'coordinador'
    sede_alcance            VARCHAR(100), -- solo aplica si rol = 'coordinador'
    activo                 BOOLEAN DEFAULT TRUE,
    creado_en              TIMESTAMP DEFAULT NOW()
);

-- Auditoría de cargas de archivos Excel (solo administrador puede insertar)
CREATE TABLE IF NOT EXISTS cargas_archivo (
    id                     BIGSERIAL PRIMARY KEY,
    tipo                   VARCHAR(30) NOT NULL CHECK (tipo IN ('planeacion','inscritos')),
    nombre_archivo         VARCHAR(255),
    periodo                VARCHAR(20),
    usuario_id             BIGINT REFERENCES usuarios(id),
    filas_procesadas       INTEGER DEFAULT 0,
    filas_error            INTEGER DEFAULT 0,
    estado                 VARCHAR(30) DEFAULT 'completado',
    detalle_error          TEXT,
    creado_en              TIMESTAMP DEFAULT NOW()
);
