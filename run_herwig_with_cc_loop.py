import subprocess
import os
from codecarbon import EmissionsTracker
import time

# ==============================================================================
# ---                           CONFIGURATION                              ---
# ==============================================================================
# --- Experiment Settings ---
number_of_runs = 10  # <--- SET HOW MANY TIMES YOU WANT TO RUN THE FULL SEQUENCE

# --- Herwig Settings ---
herwig_run_directory = "/home/rosie/herwig-run" 
herwig_input_file = "LHC-Matchbox.in"
number_of_events_per_run = 9000  # Events for each of the 10 runs
number_of_jobs = 4               # Parallel jobs for Herwig

# --- CodeCarbon Settings ---
output_directory_for_reports = os.getcwd() # Saves reports in the same folder as this script
integration_report_file = "Int_emissions-9000-4.csv"
generation_report_file = "Gen_emissions-9000-4.csv"

# ==============================================================================
# ---                            EXECUTION                                 ---
# ==============================================================================

# Derive the .run filename from the .in filename
run_file_name = herwig_input_file.replace('.in', '.run')

# --- Initialize ONE tracker for each PHASE, outside the loop ---
print("Initializing CodeCarbon trackers...")
integration_tracker = EmissionsTracker(
    output_dir=output_directory_for_reports, 
    output_file=integration_report_file,
    project_name="Herwig Integration Phase"
)
generation_tracker = EmissionsTracker(
    output_dir=output_directory_for_reports, 
    output_file=generation_report_file,
    project_name="Herwig Generation Phase"
)

# Start both main trackers. They will now measure the total time and energy for all runs.
integration_tracker.start()
generation_tracker.start()

# --- Main Experiment Loop ---
print("\n" + "="*60)
print(f"STARTING EXPERIMENT: {number_of_runs} full runs (Integration + Generation)")
print("="*60)

for i in range(number_of_runs):
    run_number = i + 1
    print(f"\n--- Starting Full Run {run_number}/{number_of_runs} ---")
    
    # --- Phase 1: Integration (Herwig read) ---
    integration_task_name = f"Integration Run {run_number}"
    integration_tracker.start_task(integration_task_name)
    integration_command = ["Herwig", "read", herwig_input_file]
    
    try:
        print(f"  -> Running Integration...")
        subprocess.run(
            integration_command, 
            check=True,                 
            cwd=herwig_run_directory,
            capture_output=True, # Hide output to keep the log clean
            text=True
        )
    except subprocess.CalledProcessError as e:
        print(f"  -> ERROR during Integration on run {run_number}: {e.stderr}")
    finally:
        integration_tracker.stop_task()
        print(f"  -> Integration for run {run_number} complete.")

    # --- Phase 2: Event Generation (Herwig run) ---
    generation_task_name = f"Generation Run {run_number}"
    generation_tracker.start_task(generation_task_name)
    generation_command = [
        "Herwig", "run", run_file_name, 
        "-N", str(number_of_events_per_run), 
        "-j", str(number_of_jobs)
    ]
    
    try:
        print(f"  -> Running Generation...")
        subprocess.run(
            generation_command, 
            check=True, 
            cwd=herwig_run_directory,
            capture_output=True, # Hide output
            text=True
        )
    except subprocess.CalledProcessError as e:
        print(f"  -> ERROR during Generation on run {run_number}: {e.stderr}")
    finally:
        generation_tracker.stop_task()
        print(f"  -> Generation for run {run_number} complete.")

    print(f"--- Finished Full Run {run_number}/{number_of_runs} ---")
    time.sleep(2) # Small pause between full runs

# --- Finalize and Save Reports ---
# Stop the main trackers after all runs are complete to write the final CSVs.
total_integration_emissions = integration_tracker.stop()
total_generation_emissions = generation_tracker.stop()

print("\n" + "="*60)
print("EXPERIMENT COMPLETE")
print(f"Total Integration emissions over {number_of_runs} runs: {total_integration_emissions} kg CO₂eq.")
print(f"Total Generation emissions over {number_of_runs} runs: {total_generation_emissions} kg CO₂eq.")
print(f"Detailed reports saved to:")
print(f"  - {integration_report_file}")
print(f"  - {generation_report_file}")
print("="*60)