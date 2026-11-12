-- Migración aditiva: no elimina ni sobrescribe datos existentes.
CREATE TABLE IF NOT EXISTS ceremonias_grado (
    id BIGSERIAL PRIMARY KEY,
    nombre VARCHAR(200) NOT NULL,
    fecha DATE NOT NULL,
    lugar VARCHAR(200) NOT NULL,
    facultad VARCHAR(150),
    programa VARCHAR(250),
    estado VARCHAR(30) NOT NULL DEFAULT 'planificada',
    creado_por_id BIGINT NOT NULL REFERENCES usuarios(id),
    creado_en TIMESTAMP DEFAULT NOW(),
    actualizado_en TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS graduandos_ceremonia (
    id BIGSERIAL PRIMARY KEY,
    ceremonia_id BIGINT NOT NULL REFERENCES ceremonias_grado(id) ON DELETE CASCADE,
    estudiante_cedula VARCHAR(30) NOT NULL REFERENCES estudiantes(cedula) ON DELETE RESTRICT,
    facultad VARCHAR(150) NOT NULL,
    programa VARCHAR(250) NOT NULL,
    validado BOOLEAN NOT NULL DEFAULT FALSE,
    creado_por_id BIGINT NOT NULL REFERENCES usuarios(id),
    creado_en TIMESTAMP DEFAULT NOW(),
    CONSTRAINT uq_graduando_ceremonia UNIQUE (ceremonia_id, estudiante_cedula)
);

CREATE TABLE IF NOT EXISTS asistencias_grado (
    id BIGSERIAL PRIMARY KEY,
    graduando_id BIGINT NOT NULL REFERENCES graduandos_ceremonia(id) ON DELETE CASCADE,
    presente BOOLEAN NOT NULL DEFAULT TRUE,
    observacion VARCHAR(500),
    registrado_por_id BIGINT NOT NULL REFERENCES usuarios(id),
    registrado_en TIMESTAMP DEFAULT NOW(),
    actualizado_en TIMESTAMP DEFAULT NOW(),
    CONSTRAINT uq_asistencia_graduando UNIQUE (graduando_id)
);

CREATE TABLE IF NOT EXISTS auditoria (
    id BIGSERIAL PRIMARY KEY,
    usuario_id BIGINT REFERENCES usuarios(id),
    username VARCHAR(80),
    accion VARCHAR(80) NOT NULL,
    recurso VARCHAR(80) NOT NULL,
    recurso_id VARCHAR(80),
    detalle TEXT,
    creado_en TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_graduandos_ceremonia ON graduandos_ceremonia(ceremonia_id);
CREATE INDEX IF NOT EXISTS idx_graduandos_alcance ON graduandos_ceremonia(facultad, programa);
CREATE INDEX IF NOT EXISTS idx_auditoria_fecha ON auditoria(creado_en);

DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'usuarios_rol_check') THEN
        ALTER TABLE usuarios DROP CONSTRAINT usuarios_rol_check;
    END IF;
    ALTER TABLE usuarios ADD CONSTRAINT usuarios_rol_check CHECK (
        rol IN ('admin','administrador','bienestar_universitario','decano','consulta',
                'coordinador','docente','consulta_estudiante')
    );
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;
