#!/usr/bin/env python3
"""
db_helper.py
Helper module Python untuk integrasi Computer Vision & Web VROOO ke SQLite.
"""

import sqlite3
import json
import os
from typing import Dict, Any, List, Optional

DB_FILE = os.path.join(os.path.dirname(__file__), "vrooo.db")
SCHEMA_FILE = os.path.join(os.path.dirname(__file__), "schema.sql")

def get_connection(db_path: str = DB_FILE) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA foreign_keys = ON;")
    conn.row_factory = sqlite3.Row
    return conn

def init_database(db_path: str = DB_FILE, schema_path: str = SCHEMA_FILE):
    """Menginisialisasi tabel-tabel SQLite dari schema.sql"""
    with open(schema_path, "r", encoding="utf-8") as f:
        sql_script = f.read()
    
    conn = get_connection(db_path)
    with conn:
        conn.executescript(sql_script)
    conn.close()
    print(f"[OK] Database initialized at: {db_path}")

def log_vehicle_detection(approach_id: int, vehicle_type: str, confidence: float = 1.0, db_path: str = DB_FILE):
    """Dipanggil oleh modul Computer Vision saat kendaraan terdeteksi"""
    conn = get_connection(db_path)
    with conn:
        conn.execute(
            "INSERT INTO vehicle_detections (approach_id, vehicle_type, confidence_score) VALUES (?, ?, ?)",
            (approach_id, vehicle_type.upper(), confidence)
        )
    conn.close()

def log_traffic_density(
    approach_id: int,
    motor: int,
    mobil: int,
    bus: int,
    truk: int,
    queue_meter: float = 0.0,
    density_level: str = "LOW",
    db_path: str = DB_FILE
):
    """Mencatat jumlah kendaraan dan tingkat kepadatan per siklus pengamatan"""
    total = motor + mobil + bus + truk
    conn = get_connection(db_path)
    with conn:
        conn.execute(
            """INSERT INTO traffic_density_logs 
               (approach_id, total_vehicles, motor_count, mobil_count, bus_count, truk_count, queue_length_meter, density_level)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (approach_id, total, motor, mobil, bus, truk, queue_meter, density_level.upper())
        )
    conn.close()

def log_signal_decision(
    intersection_id: int,
    active_approach_id: int,
    signal_state: str,
    green_duration: int,
    control_mode: str = "ADAPTIVE",
    db_path: str = DB_FILE
):
    """Mencatat keputusan durasi lampu hijau yang dikirim ke controller/LED"""
    conn = get_connection(db_path)
    with conn:
        conn.execute(
            """INSERT INTO traffic_signal_logs 
               (intersection_id, active_approach_id, signal_state, green_duration_seconds, control_mode)
               VALUES (?, ?, ?, ?, ?)""",
            (intersection_id, active_approach_id, signal_state.upper(), green_duration, control_mode.upper())
        )
    conn.close()

def record_playground_simulation(
    intersection_id: int,
    scenario_name: str,
    traffic_config: Dict[str, Any],
    adaptive_waiting_time: float,
    conventional_waiting_time: float,
    efficiency_pct: float,
    db_path: str = DB_FILE
) -> int:
    """Menyimpan hasil simulasi dari Web Playground (SRS Gambar 3 & 4)"""
    conn = get_connection(db_path)
    with conn:
        cursor = conn.execute(
            """INSERT INTO simulation_runs 
               (intersection_id, scenario_name, input_traffic_config, adaptive_avg_waiting_time, conventional_avg_waiting_time, efficiency_percentage)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (
                intersection_id,
                scenario_name,
                json.dumps(traffic_config),
                adaptive_waiting_time,
                conventional_waiting_time,
                efficiency_pct
            )
        )
        sim_id = cursor.lastrowid
    conn.close()
    return sim_id

def get_latest_traffic_status(intersection_id: int = 1, db_path: str = DB_FILE) -> List[Dict[str, Any]]:
    """Mengambil status real-time untuk ditampilkan di Web Dashboard/Monitoring"""
    conn = get_connection(db_path)
    query = """
        SELECT 
            a.id AS approach_id,
            a.direction,
            a.lane_count,
            COALESCE(tdl.total_vehicles, 0) AS total_vehicles,
            COALESCE(tdl.motor_count, 0) AS motor_count,
            COALESCE(tdl.mobil_count, 0) AS mobil_count,
            COALESCE(tdl.bus_count, 0) AS bus_count,
            COALESCE(tdl.truk_count, 0) AS truk_count,
            COALESCE(tdl.density_level, 'LOW') AS density_level,
            tdl.recorded_at
        FROM approaches a
        LEFT JOIN (
            SELECT * FROM traffic_density_logs 
            WHERE id IN (SELECT MAX(id) FROM traffic_density_logs GROUP BY approach_id)
        ) tdl ON a.id = tdl.approach_id
        WHERE a.intersection_id = ?
        ORDER BY a.id ASC
    """
    cursor = conn.execute(query, (intersection_id,))
    results = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return results
