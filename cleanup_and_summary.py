#!/usr/bin/env python3
"""
cleanup_and_summary.py
Sistem VROOO (Autonomous Adaptive Traffic Signal System)

Fungsi:
1. Mengagregasi data log mentah (kendaraan, kepadatan, durasi lampu) selama 7 hari terakhir ke tabel weekly_traffic_summary.
2. Menghapus data log mentah berumur lebih dari 7 hari agar kapasitas penyimpanan Raspberry Pi 4 tetap hemat dan performa query tetap cepat.
3. Menjalankan VACUUM untuk mengoptimalkan ukuran file database SQLite.

Dapat dijalankan secara mandiri atau dijadwalkan via cron job di Raspberry Pi:
0 0 * * 0 /usr/bin/python3 /path/to/cleanup_and_summary.py
"""

import sqlite3
import datetime
import os
import argparse

DEFAULT_DB_PATH = os.path.join(os.path.dirname(__file__), "vrooo.db")

def run_weekly_aggregation_and_cleanup(db_path=DEFAULT_DB_PATH, retention_days=7):
    if not os.path.exists(db_path):
        print(f"[ERROR] Database file not found at: {db_path}")
        return False

    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA foreign_keys = ON;")
    cursor = conn.cursor()

    try:
        now = datetime.datetime.now()
        start_date = (now - datetime.timedelta(days=retention_days)).date().isoformat()
        end_date = now.date().isoformat()
        cutoff_timestamp = (now - datetime.timedelta(days=retention_days)).strftime("%Y-%m-%d %H:%M:%S")

        print(f"[*] Menjalankan rekapitulasi data periode: {start_date} s/d {end_date}")

        # 1. Agregasi data dari traffic_density_logs per approach_id
        aggregation_query = """
            SELECT 
                tdl.approach_id,
                COALESCE(SUM(tdl.motor_count), 0) AS total_motor,
                COALESCE(SUM(tdl.mobil_count), 0) AS total_mobil,
                COALESCE(SUM(tdl.bus_count), 0) AS total_bus,
                COALESCE(SUM(tdl.truk_count), 0) AS total_truk,
                COALESCE(SUM(tdl.total_vehicles), 0) AS grand_total_vehicles,
                COALESCE(AVG(tdl.queue_length_meter), 0.0) AS avg_queue_length,
                (
                    SELECT COALESCE(AVG(tsl.green_duration_seconds), 0.0)
                    FROM traffic_signal_logs tsl
                    WHERE tsl.active_approach_id = tdl.approach_id
                      AND tsl.started_at >= ?
                ) AS avg_green_duration
            FROM traffic_density_logs tdl
            WHERE tdl.recorded_at >= ?
            GROUP BY tdl.approach_id
        """

        cursor.execute(aggregation_query, (cutoff_timestamp, cutoff_timestamp))
        rows = cursor.fetchall()

        if rows:
            upsert_summary_query = """
                INSERT INTO weekly_traffic_summary (
                    approach_id,
                    week_start_date,
                    week_end_date,
                    total_motor,
                    total_mobil,
                    total_bus,
                    total_truk,
                    grand_total_vehicles,
                    avg_queue_length,
                    avg_green_duration,
                    created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, datetime('now', 'localtime'))
                ON CONFLICT(approach_id, week_start_date) DO UPDATE SET
                    week_end_date = excluded.week_end_date,
                    total_motor = excluded.total_motor,
                    total_mobil = excluded.total_mobil,
                    total_bus = excluded.total_bus,
                    total_truk = excluded.total_truk,
                    grand_total_vehicles = excluded.grand_total_vehicles,
                    avg_queue_length = excluded.avg_queue_length,
                    avg_green_duration = excluded.avg_green_duration;
            """

            for row in rows:
                approach_id, motor, mobil, bus, truk, total, avg_queue, avg_green = row
                cursor.execute(upsert_summary_query, (
                    approach_id,
                    start_date,
                    end_date,
                    motor,
                    mobil,
                    bus,
                    truk,
                    total,
                    round(avg_queue, 2),
                    round(avg_green, 2)
                ))
            print(f"[OK] Berhasil merekapitulasi {len(rows)} data jalur ke weekly_traffic_summary.")
        else:
            print("[INFO] Tidak ada data density baru untuk direkapitulasi pada periode ini.")

        # 2. Hapus log mentah yang lebih tua dari cutoff_timestamp
        print(f"[*] Membersihkan log mentah sebelum: {cutoff_timestamp}")
        
        cursor.execute("DELETE FROM vehicle_detections WHERE detected_at < ?", (cutoff_timestamp,))
        deleted_detections = cursor.rowcount

        cursor.execute("DELETE FROM traffic_density_logs WHERE recorded_at < ?", (cutoff_timestamp,))
        deleted_densities = cursor.rowcount

        cursor.execute("DELETE FROM traffic_signal_logs WHERE started_at < ?", (cutoff_timestamp,))
        deleted_signals = cursor.rowcount

        conn.commit()

        print(f"[OK] Log berhasil dibersihkan:")
        print(f"     - vehicle_detections dihapus : {deleted_detections} baris")
        print(f"     - traffic_density_logs dihapus: {deleted_densities} baris")
        print(f"     - traffic_signal_logs dihapus : {deleted_signals} baris")

        # 3. VACUUM untuk mengoptimalkan storage SQLite di Raspberry Pi
        print("[*] Menjalankan VACUUM database...")
        cursor.execute("VACUUM;")
        print("[OK] VACUUM selesai. Penyimpanan database teroptimalkan.")

        return True
    except Exception as e:
        conn.rollback()
        print(f"[ERROR] Terjadi kesalahan: {e}")
        return False
    finally:
        conn.close()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="VROOO Weekly Summary & Log Cleanup Routine")
    parser.add_argument("--db", default=DEFAULT_DB_PATH, help="Path ke file database sqlite (default: vrooo.db)")
    parser.add_argument("--days", type=int, default=7, help="Batas retensi log mentah dalam hari (default: 7)")
    args = parser.parse_args()

    run_weekly_aggregation_and_cleanup(db_path=args.db, retention_days=args.days)
