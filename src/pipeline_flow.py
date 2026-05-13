#!/usr/bin/env python3
"""
======== pipeline_flow.py ========
Step 8: Orchestration with Prefect
Schedules: extract → load_bronze → create_silver → build_gold
"""

from prefect import flow, task
import subprocess
import sys
import os

SRC_DIR = os.path.dirname(os.path.abspath(__file__))

@task
def extract_data():
    """Step 2: Extract data from CoinGecko API"""
    print("[PREFECT] Running extract.py...")
    result = subprocess.run(
        [sys.executable, os.path.join(SRC_DIR, "extract.py")],
        capture_output=True,
        text=True
    )
    print(result.stdout)
    if result.returncode != 0:
        print(result.stderr)
        raise Exception(f"extract.py failed: {result.stderr}")
    return "extract.py completed"

@task
def load_bronze():
    """Step 4: Load raw data into Bronze layer"""
    print("[PREFECT] Running load_bronze.py...")
    result = subprocess.run(
        [sys.executable, os.path.join(SRC_DIR, "load_bronze.py")],
        capture_output=True,
        text=True
    )
    print(result.stdout)
    if result.returncode != 0:
        print(result.stderr)
        raise Exception(f"load_bronze.py failed: {result.stderr}")
    return "load_bronze.py completed"

@task
def build_silver():
    """Step 5: Create Silver layer from Bronze"""
    print("[PREFECT] Running create_silver.py...")
    result = subprocess.run(
        [sys.executable, os.path.join(SRC_DIR, "create_silver.py")],
        capture_output=True,
        text=True
    )
    print(result.stdout)
    if result.returncode != 0:
        print(result.stderr)
        raise Exception(f"create_silver.py failed: {result.stderr}")
    return "create_silver.py completed"

@task
def build_gold():
    """Step 6: Build Gold aggregations from Silver"""
    print("[PREFECT] Running build_gold.py...")
    result = subprocess.run(
        [sys.executable, os.path.join(SRC_DIR, "build_gold.py")],
        capture_output=True,
        text=True
    )
    print(result.stdout)
    if result.returncode != 0:
        print(result.stderr)
        raise Exception(f"build_gold.py failed: {result.stderr}")
    return "build_gold.py completed"

@flow(name="coingecko_etl_pipeline")
def main_etl():
    """Full ETL: Extract → Bronze → Silver → Gold"""
    extract_data()
    load_bronze()
    build_silver()
    build_gold()
    print("[PREFECT] Pipeline completed successfully!")

if __name__ == "__main__":
    main_etl()