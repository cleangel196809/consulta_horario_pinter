-- Mantiene separado el alcance por programa del alcance por sede usado en horarios.
ALTER TABLE usuarios ADD COLUMN IF NOT EXISTS programa_alcance VARCHAR(250);
