"""
LLM for code:
https://aistudio.google.com/app/prompts?state=%7B%22ids%22:%5B%221WoK0kFrRU1cRLGwGN52VJWF8arkBwt-a%22%5D,%22action%22:%22open%22,%22userId%22:%22107543393999580811311%22,%22resourceKeys%22:%7B%7D%7D&usp=sharing
https://aistudio.google.com/app/prompts?state=%7B%22ids%22:%5B%221pLG5UHFdzeiZA5W7crgnFXE0Xslpztce%22%5D,%22action%22:%22open%22,%22userId%22:%22107543393999580811311%22,%22resourceKeys%22:%7B%7D%7D&usp=sharing
"""

import subprocess
import os
from codecarbon import EmissionsTracker
import time
import pandas as pd

# ==============================================================================
# ---                           CONFIGURATION                              ---
# ==============================================================================
# --- Experiment Settings ---
number_of_runs = 10  # <--- SET HOW MANY TIMES TO REPEAT THE FULL SIMULATION

# --- Herwig Settings ---
herwig_run_directory = "/home/rosie/herwig-run" 
herwig_input_file = "LHC-Matchbox.in"
number_of_events_per_run = 2000
number_of_jobs = 1

# --- CodeCarbon Settings ---
output_directory_for_reports = os.getcwd()
# Filenames now reflect that they contain multiple runs
integration_report_file = f"20250804Int_report-{number_of_events_per_run}evt-{number_of_runs}runs.csv"
generation_report_file = f"20250804Gen_report-{number_of_events_per_run}evt-{number_of_runs}runs.csv"

# ==============================================================================
# ---                       INITIALIZE FOR EXPERIMENT                      ---
# ==============================================================================

run_file_name = herwig_input_file.replace('.in', '.run')
full_run_file_path = os.path.join(herwig_run_directory, run_file_name)

# --- Initialize two trackers, one for each phase we want to measure repeatedly ---
integration_tracker = EmissionsTracker(save_to_file=False, project_name="Herwig Integration Repeats")
generation_tracker = EmissionsTracker(save_to_file=False, project_name="Herwig Generation Repeats")

# --- Create empty lists to manually collect data from each run ---
all_integration_data = []
all_generation_data = []

# ==============================================================================
# ---                  MAIN EXPERIMENT LOOP (FULL RUNS)                    ---
# ==============================================================================
print("\n" + "="*60)
print(f"STARTING EXPERIMENT: {number_of_runs} full runs (Integration + Generation)")
print("="*60)

# Start the trackers. They will now listen for tasks.
integration_tracker.start()
generation_tracker.start()

for i in range(number_of_runs):
    run_number = i + 1
    print(f"\n--- Starting Full Run {run_number}/{number_of_runs} ---")

    # --- 1. CLEANUP: Ensure a fresh start by deleting the old .run file ---
    # This is the most critical step to force Herwig to re-integrate.
    if os.path.exists(full_run_file_path):
        os.remove(full_run_file_path)
        print("  -> Removed stale .run file for a clean integration.")

    # --- 2. MEASURE INTEGRATION PHASE ---
    integration_task_name = f"Integration Run {run_number}"
    integration_command = ["Herwig", "read", herwig_input_file]
    integration_task_data = None

    integration_tracker.start_task(integration_task_name)
    try:
        subprocess.run(integration_command, check=True, cwd=herwig_run_directory, capture_output=True, text=True)
    except subprocess.CalledProcessError as e:
        print(f"  -> !!! ERROR during Integration on run {run_number}: {e.stderr}")
    finally:
        integration_task_data = integration_tracker.stop_task()

    if integration_task_data:
        print(f"  -> Integration complete. Duration: {integration_task_data.duration:.2f}s.")
        # Convert the object to a dictionary before storing it
        integration_dict = {
            'task_name': integration_task_data,
            'duration': integration_task_data.duration,
            'emissions': integration_task_data.emissions,
            'cpu_energy': integration_task_data.cpu_energy,
            'ram_energy': integration_task_data.ram_energy,
            'energy_consumed': integration_task_data.energy_consumed
        }
        all_integration_data.append(integration_dict)

    # --- 3. MEASURE GENERATION PHASE ---
    generation_task_name = f"Generation Run {run_number}"
    generation_command = ["Herwig", "run", run_file_name, "-N", str(number_of_events_per_run), "-j", str(number_of_jobs)]
    generation_task_data = None
    
    generation_tracker.start_task(generation_task_name)
    try:
        subprocess.run(generation_command, check=True, cwd=herwig_run_directory, capture_output=True, text=True)
    except subprocess.CalledProcessError as e:
        print(f"  -> !!! ERROR during Generation on run {run_number}: {e.stderr}")
    finally:
        generation_task_data = generation_tracker.stop_task()

    if generation_task_data:
        print(f"  -> Generation complete. Duration: {generation_task_data.duration:.2f}s.")
        generation_dict = {
            'task_name': generation_task_name, 
            'duration': generation_task_data.duration,
            'emissions': generation_task_data.emissions,
            'cpu_energy': generation_task_data.cpu_energy,
            'ram_energy': generation_task_data.ram_energy,
            'energy_consumed': generation_task_data.energy_consumed
        }
        all_generation_data.append(generation_dict)

    time.sleep(2) # Pause between full runs

# Stop the main trackers after the loop is finished
integration_tracker.stop()
generation_tracker.stop()

# ==============================================================================
# ---                         FINALIZE AND SAVE REPORTS                    ---
# ==============================================================================
print("\n" + "="*60)
print("EXPERIMENT COMPLETE: WRITING FINAL REPORTS")

# --- Save Integration Report ---
if all_integration_data:
    integration_df = pd.DataFrame(all_integration_data)
    integration_df.to_csv(os.path.join(output_directory_for_reports, integration_report_file), index=False)
    print(f"  -> Integration report with {len(integration_df)} rows saved to: {integration_report_file}")
else:
    print("  -> No data was collected for the integration phase.")

# --- Save Generation Report ---
if all_generation_data:
    generation_df = pd.DataFrame(all_generation_data)
    generation_df.to_csv(os.path.join(output_directory_for_reports, generation_report_file), index=False)
    print(f"  -> Generation report with {len(generation_df)} rows saved to: {generation_report_file}")
else:
    print("  -> No data was collected for the generation phase.")

print("="*60)

