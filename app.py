import subprocess
import os

# Auto-run the pipeline once before showing the dashboard
# Uncomment below to run pipeline on each deploy
# subprocess.run(["python", "src/extract.py"])
# subprocess.run(["python", "src/load_bronze.py"])
# subprocess.run(["python", "src/create_silver.py"])
# subprocess.run(["python", "src/build_gold.py"])

# Run the dashboard
exec(open("src/dashboard.py").read())
