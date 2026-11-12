-- ============================================================
-- Database Rescue — Chapter 4 CRUD Mini System
-- Team: Wonder Pets   |   Case: First Step Rural Bank (Banking)
-- Table: Borrower (from the Chapter 2 design)
-- Engine: SQLite 3 (runs on an empty database)
-- All names, numbers, and ID values below are FICTIONAL sample data.
-- ============================================================

PRAGMA foreign_keys = ON;

DROP TABLE IF EXISTS Borrower;

CREATE TABLE Borrower (
    BorrowerID      INTEGER      PRIMARY KEY AUTOINCREMENT,
    FirstName       VARCHAR(50)  NOT NULL,
    MiddleName      VARCHAR(50),
    LastName        VARCHAR(50)  NOT NULL,
    BirthDate       DATE         NOT NULL,
    ContactNo       VARCHAR(13)  NOT NULL,
    Address         VARCHAR(150) NOT NULL,
    GovIDType       VARCHAR(30)  NOT NULL,
    GovIDNo         VARCHAR(30)  NOT NULL,
    DateRegistered  DATE         NOT NULL DEFAULT CURRENT_DATE,
    -- One borrower = one government ID (fixes Symptom 1: duplicate borrowers)
    CONSTRAINT uq_borrower_govid   UNIQUE (GovIDType, GovIDNo),
    -- Same name + same birth date cannot be registered twice
    CONSTRAINT uq_borrower_identity UNIQUE (FirstName, LastName, BirthDate)
);

INSERT INTO Borrower (FirstName, MiddleName, LastName, BirthDate, ContactNo, Address, GovIDType, GovIDNo, DateRegistered) VALUES
('Maria',    'Luisa',   'Santos',     '1985-03-12', '09171230001', 'Purok 3, Brgy. San Vicente, Capas, Tarlac',     'PhilSys ID',       '4521-8830-1127-0001', '2026-01-12'),
('Juan',     'Pablo',   'Dela Cruz',  '1979-07-25', '09181230002', 'Brgy. Sta. Maria, Concepcion, Tarlac',          'Driver''s License','N03-26-004512',       '2026-01-15'),
('Rosario',  NULL,      'Dela Cruz',  '1990-11-02', '09191230003', 'Brgy. Poblacion, Gerona, Tarlac',               'Voter''s ID',      '7102-0045-8890',      '2026-01-20'),
('Eduardo',  'Manalo',  'Reyes',      '1972-04-18', '09201230004', 'Brgy. Lawy, Victoria, Tarlac',                  'SSS ID',           '33-4512890-1',        '2026-02-03'),
('Teresita', 'Garcia',  'Mendoza',    '1988-09-30', '09211230005', 'Brgy. Balite, Paniqui, Tarlac',                 'PhilSys ID',       '3318-7702-4415-0005', '2026-02-10'),
('Ricardo',  NULL,      'Bautista',   '1983-01-08', '09221230006', 'Brgy. Maliwalo, Tarlac City, Tarlac',           'UMID',             'CRN-0033-4512890-7',  '2026-02-18'),
('Elena',    'Ramos',   'Aquino',     '1995-06-21', '09231230007', 'Brgy. Anoling, Camiling, Tarlac',               'Postal ID',        'PRN-2201-77310',      '2026-03-02'),
('Antonio',  'Santos',  'Villanueva', '1968-12-05', '09241230008', 'Brgy. Sta. Rita, Capas, Tarlac',                'Driver''s License','N03-24-009821',       '2026-03-09'),
('Gloria',   'Mercado', 'Pascual',    '1992-02-14', '09251230009', 'Brgy. Poblacion A, Moncada, Tarlac',            'PhilSys ID',       '5509-1123-6684-0009', '2026-03-16'),
('Roberto',  NULL,      'Castillo',   '1981-08-27', '09261230010', 'Brgy. Salapungan, Concepcion, Tarlac',          'Voter''s ID',      '6620-1187-3345',      '2026-04-06'),
('Lourdes',  'Navarro', 'Francisco',  '1976-10-09', '09271230011', 'Brgy. Calumpang, Gerona, Tarlac',               'PRC ID',           '0098123',             '2026-04-20'),
('Miguel',   'Torres',  'Domingo',    '1999-05-16', '09281230012', 'Brgy. Mabini, Paniqui, Tarlac',                 'PhilSys ID',       '7740-2285-9913-0012', '2026-05-04');
