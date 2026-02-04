-- Migration: Add vehicle_type and plate_number columns and a check constraint
-- Up:
ALTER TABLE users ADD COLUMN IF NOT EXISTS vehicle_type VARCHAR(50);
ALTER TABLE users ADD COLUMN IF NOT EXISTS plate_number VARCHAR(20);
ALTER TABLE users ADD CONSTRAINT ck_courier_vehicle_required CHECK ((role != 'courier') OR (vehicle_type IS NOT NULL AND plate_number IS NOT NULL));

-- Down:
-- To revert apply the following commands:
-- ALTER TABLE users DROP CONSTRAINT IF EXISTS ck_courier_vehicle_required;
-- ALTER TABLE users DROP COLUMN IF EXISTS plate_number;
-- ALTER TABLE users DROP COLUMN IF EXISTS vehicle_type;
