#!/usr/bin/env python3
"""
test_system.py
Script simulasi pengujian alur database SQLite untuk sistem VROOO.
"""

import os
import sqlite3
import datetime
from db_helper import (
    init_database,
    log_vehicle_detection,
    log_traffic_density,
    log_signal_decision,
    record_playground_simulation,
    get_latest_traffic_status,
    DB_FILE
)
from cleanup_and_summary import run_weekly_aggregation_and_cleanup

def main():
    print("=== [1] Inisialisasi Database ===")
    if os.path.exists(DB_FILE):
        os.remove(DB_FILE)
    init_database()

    print("\n=== [2] Simulasi Input Data Deteksi Real-Time ===")
    # Pendekatan: 1=Utara, 2=Timur, 3=Selatan, 4=Barat
    log_vehicle_detection(approach_id=1, vehicle_type="MOBIL", confidence=0.92)
    log_vehicle_detection(approach_id=1, vehicle_type="MOTOR", confidence=0.88)
    log_vehicle_detection(approach_id=2, vehicle_type="BUS", confidence=0.95)

    # Catat kepadatan saat ini
    log_traffic_density(approach_id=1, motor=6, mobil=10, bus=1, truk=0, queue_meter=35.0, density_level="HIGH")
    log_traffic_density(approach_id=2, motor=2, mobil=4, bus=1, truk=1, queue_meter=15.0, density_level="MEDIUM")
    log_traffic_density(approach_id=3, motor=2, mobil=4, bus=1, truk=0, queue_meter=12.0, density_level="LOW")
    log_traffic_density(approach_id=4, motor=2, mobil=4, bus=1, truk=1, queue_meter=14.0, density_level="MEDIUM")

    # Catat keputusan kontrol lampu
    log_signal_decision(intersection_id=1, active_approach_id=1, signal_state="GREEN", green_duration=45, control_mode="ADAPTIVE")

    print("\n=== [3] Simulasi Web Playground (Sesuai Gambar SRS) ===")
    mock_playground_config = {
        "utara": {"mobil": 10, "motor": 6, "bus": 1, "truk": 0},
        "timur": {"mobil": 4, "motor": 2, "bus": 1, "truk": 1},
        "selatan": {"mobil": 4, "motor": 2, "bus": 1, "truk": 0},
        "barat": {"mobil": 4, "motor": 2, "bus": 1, "truk": 1}
    }
    sim_id = record_playground_simulation(
        intersection_id=1,
        scenario_name="Skenario Jam Sibuk Pagi",
        traffic_config=mock_playground_config,
        adaptive_waiting_time=3.7,
        conventional_waiting_time=5.8,
        efficiency_pct=36.2
    )
    print(f"[OK] Skenario simulasi tersimpan dengan ID: {sim_id}")

    print("\n=== [4] Query Status Terkini Dashboard Web ===")
    status = get_latest_traffic_status(intersection_id=1)
    for row in status:
        print(f"Jalur: {row['direction']:<8} | Total: {row['total_vehicles']} | Mobil: {row['mobil_count']} | Motor: {row['motor_count']} | Level: {row['density_level']}")

    print("\n=== [5] Simulasi Data 8 Hari Lalu (Untuk Test Cleanup Mingguan) ===")
    conn = sqlite3.connect(DB_FILE)
    old_date = (datetime.datetime.now() - datetime.timedelta(days=8)).strftime("%Y-%m-%d %H:%M:%S")
    conn.execute(
        "INSERT INTO traffic_density_logs (approach_id, total_vehicles, motor_count, mobil_count, bus_count, truk_count, recorded_at) VALUES (1, 50, 30, 20, 0, 0, ?)",
        (old_date,)
    )
    conn.commit()
    conn.close()

    print("\n=== [6] Jalankan Rutinitas Agregasi Mingguan & Pembersihan Log ===")
    run_weekly_aggregation_and_cleanup(retention_days=7)

    print("\n=== [7] Cek Isi Tabel weekly_traffic_summary ===")
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("SELECT approach_id, week_start_date, week_end_date, grand_total_vehicles, total_mobil, total_motor FROM weekly_traffic_summary")
    summaries = cursor.fetchall()
    for s in summaries:
        print(f"Summary Approach ID {s[0]} ({s[1]} s/d {s[2]}): Total={s[3]} (Mobil: {s[4]}, Motor: {s[5]})")
    conn.close()

if __name__ == "__main__":
    main()
