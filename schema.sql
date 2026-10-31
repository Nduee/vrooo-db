-- ========================================================================
-- SISTEM VROOO (Autonomous Adaptive Traffic Signal System)
-- DBMS: SQLite 3 (Dioptimalkan untuk Raspberry Pi 4 & Lingkungan Lokal)
-- ========================================================================

PRAGMA foreign_keys = ON;
PRAGMA journal_mode = WAL; -- Write-Ahead Logging untuk konkurensi CV & Web

-- 1. MASTER SIMPANG (INTERSECTIONS)
-- Menyimpan konfigurasi simpang jalan (Simpang 3, Simpang 4, Simpang 5)
CREATE TABLE IF NOT EXISTS intersections (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    code TEXT NOT NULL UNIQUE,                                             -- Contoh: 'SIMPANG-01'
    name TEXT NOT NULL,                                                    -- Contoh: 'Simpang Polibatam'
    type TEXT NOT NULL CHECK(type IN ('3_WAY', '4_WAY', '5_WAY')),         -- Bentuk simpang
    description TEXT,
    is_active INTEGER NOT NULL DEFAULT 1,                                  -- 1 = Aktif, 0 = Nonaktif
    created_at TEXT NOT NULL DEFAULT (datetime('now', 'localtime'))
);

-- 2. MASTER JALUR / ARAH MATA ANGIN (APPROACHES)
-- Setiap simpang memiliki beberapa jalur kedatangan (Utara, Timur, Selatan, Barat)
CREATE TABLE IF NOT EXISTS approaches (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    intersection_id INTEGER NOT NULL,
    direction TEXT NOT NULL CHECK(direction IN ('UTARA', 'TIMUR', 'SELATAN', 'BARAT', 'BARAT_LAUT', 'TIMUR_LAUT')),
    camera_source TEXT,                                                   -- Index webcam misal '0', '1' atau rtsp stream
    lane_count INTEGER NOT NULL DEFAULT 1,
    min_green_time INTEGER NOT NULL DEFAULT 10,                           -- Safety constraint (detik)
    max_green_time INTEGER NOT NULL DEFAULT 60,                           -- Batas waktu hijau adaptif (detik)
    created_at TEXT NOT NULL DEFAULT (datetime('now', 'localtime')),
    FOREIGN KEY (intersection_id) REFERENCES intersections(id) ON DELETE CASCADE,
    UNIQUE(intersection_id, direction)
);

-- 3. LOG DETEKSI KENDARAAN REAL-TIME (RAW CV DETECTIONS)
-- Dicatat setiap kali model Computer Vision (YOLO/OpenCV) mendeteksi objek
CREATE TABLE IF NOT EXISTS vehicle_detections (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    approach_id INTEGER NOT NULL,
    vehicle_type TEXT NOT NULL CHECK(vehicle_type IN ('MOTOR', 'MOBIL', 'BUS', 'TRUK')),
    confidence_score REAL,
    detected_at TEXT NOT NULL DEFAULT (datetime('now', 'localtime')),
    FOREIGN KEY (approach_id) REFERENCES approaches(id) ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS idx_detections_approach_date ON vehicle_detections(approach_id, detected_at);

-- 4. LOG KEPADATAN LALU LINTAS PER INTERVAL (TRAFFIC DENSITY LOGS)
-- Hasil agregasi perhitungan CV per siklus/interval waktu pengamatan
CREATE TABLE IF NOT EXISTS traffic_density_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    approach_id INTEGER NOT NULL,
    total_vehicles INTEGER NOT NULL DEFAULT 0,
    motor_count INTEGER NOT NULL DEFAULT 0,
    mobil_count INTEGER NOT NULL DEFAULT 0,
    bus_count INTEGER NOT NULL DEFAULT 0,
    truk_count INTEGER NOT NULL DEFAULT 0,
    queue_length_meter REAL NOT NULL DEFAULT 0.0,
    density_level TEXT NOT NULL CHECK(density_level IN ('LOW', 'MEDIUM', 'HIGH', 'CONGESTED')) DEFAULT 'LOW',
    recorded_at TEXT NOT NULL DEFAULT (datetime('now', 'localtime')),
    FOREIGN KEY (approach_id) REFERENCES approaches(id) ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS idx_density_approach_date ON traffic_density_logs(approach_id, recorded_at);

-- 5. LOG KEPUTUSAN SINYAL LAMPU LALU LINTAS (SIGNAL CONTROL LOGS)
-- Perintah fase dan durasi hijau/merah yang dikirim ke controller/modul LED
CREATE TABLE IF NOT EXISTS traffic_signal_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    intersection_id INTEGER NOT NULL,
    active_approach_id INTEGER NOT NULL,
    signal_state TEXT NOT NULL CHECK(signal_state IN ('GREEN', 'YELLOW', 'RED')) DEFAULT 'GREEN',
    green_duration_seconds INTEGER NOT NULL,
    control_mode TEXT NOT NULL CHECK(control_mode IN ('ADAPTIVE', 'CONVENTIONAL')) DEFAULT 'ADAPTIVE',
    started_at TEXT NOT NULL DEFAULT (datetime('now', 'localtime')),
    ended_at TEXT,
    FOREIGN KEY (intersection_id) REFERENCES intersections(id) ON DELETE CASCADE,
    FOREIGN KEY (active_approach_id) REFERENCES approaches(id) ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS idx_signal_intersection_date ON traffic_signal_logs(intersection_id, started_at);

-- 6. SIMULASI PLAYGROUND (MODUL SRS GAMBAR 2, 3, 4)
-- Untuk menyimpan eksperimen perbandingan simulasi adaptif vs konvensional
CREATE TABLE IF NOT EXISTS simulation_runs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    intersection_id INTEGER,
    scenario_name TEXT NOT NULL,
    input_traffic_config TEXT NOT NULL,                                   -- Format JSON: jumlah mobil, motor, bus, truk per arah
    adaptive_avg_waiting_time REAL NOT NULL,                              -- Waktu tunggu adaptif (detik)
    conventional_avg_waiting_time REAL NOT NULL,                          -- Waktu tunggu konvensional (detik)
    efficiency_percentage REAL NOT NULL,                                  -- Persentase efisiensi (misal 35.5%)
    executed_at TEXT NOT NULL DEFAULT (datetime('now', 'localtime')),
    FOREIGN KEY (intersection_id) REFERENCES intersections(id) ON DELETE SET NULL
);

-- 7. SUMMARY MINGGUAN (PERMANENT AGGREGATION / OLAP BI)
-- Menyimpan rekapitulasi data mingguan sebelum raw log dihapus
CREATE TABLE IF NOT EXISTS weekly_traffic_summary (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    approach_id INTEGER NOT NULL,
    week_start_date TEXT NOT NULL,                                        -- Format 'YYYY-MM-DD'
    week_end_date TEXT NOT NULL,                                          -- Format 'YYYY-MM-DD'
    total_motor INTEGER NOT NULL DEFAULT 0,
    total_mobil INTEGER NOT NULL DEFAULT 0,
    total_bus INTEGER NOT NULL DEFAULT 0,
    total_truk INTEGER NOT NULL DEFAULT 0,
    grand_total_vehicles INTEGER NOT NULL DEFAULT 0,
    avg_queue_length REAL NOT NULL DEFAULT 0.0,
    avg_green_duration REAL NOT NULL DEFAULT 0.0,
    created_at TEXT NOT NULL DEFAULT (datetime('now', 'localtime')),
    FOREIGN KEY (approach_id) REFERENCES approaches(id) ON DELETE CASCADE,
    UNIQUE(approach_id, week_start_date)
);
CREATE INDEX IF NOT EXISTS idx_summary_approach_date ON weekly_traffic_summary(approach_id, week_start_date);

-- ========================================================================
-- SEED DATA DEFAULT (Simpang Prototype & Arah Mata Angin)
-- ========================================================================
INSERT OR IGNORE INTO intersections (id, code, name, type, description) 
VALUES (1, 'SIMPANG-01', 'Simpang 4 Prototype PBL', '4_WAY', 'Persimpangan 4 arah prototype Raspberry Pi 4');

INSERT OR IGNORE INTO approaches (id, intersection_id, direction, camera_source, lane_count, min_green_time, max_green_time)
VALUES 
(1, 1, 'UTARA', '0', 2, 10, 60),
(2, 1, 'TIMUR', '1', 2, 10, 60),
(3, 1, 'SELATAN', '2', 2, 10, 60),
(4, 1, 'BARAT', '3', 2, 10, 60);
