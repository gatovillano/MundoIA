-- Migration to add 'alianzas' and 'tratados' columns to the 'agentes' table

-- Add 'alianzas' column if it doesn't exist
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 
        FROM information_schema.columns 
        WHERE table_name = 'agentes' 
        AND column_name = 'alianzas'
    ) THEN
        ALTER TABLE agentes ADD COLUMN alianzas JSONB DEFAULT '[]';
        RAISE NOTICE 'Column "alianzas" added to table "agentes".';
    ELSE
        RAISE NOTICE 'Column "alianzas" already exists in table "agentes".';
    END IF;
END $$;

-- Add 'tratados' column if it doesn't exist
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 
        FROM information_schema.columns 
        WHERE table_name = 'agentes' 
        AND column_name = 'tratados'
    ) THEN
        ALTER TABLE agentes ADD COLUMN tratados JSONB DEFAULT '[]';
        RAISE NOTICE 'Column "tratados" added to table "agentes".';
    ELSE
        RAISE NOTICE 'Column "tratados" already exists in table "agentes".';
    END IF;
END $$;