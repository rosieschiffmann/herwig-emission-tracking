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
number_of_warmup_runs = 2 # Number of runs to perform and discard to warm up caches
number_of_measured_runs = 8 # Number of runs to actually measure and save

# --- Herwig Settings ---
herwig_run_directory = "/home/rosie/herwig-run" 
herwig_input_file = "LHC-Matchbox.in"
number_of_events_per_run = 2000
number_of_jobs = 1

# --- CodeCarbon Settings ---
output_directory_for_reports = os.getcwd()
integration_report_file = f"Int_report-{number_of_events_per_run}evt-{number_of_measured_runs}runs.csv"
generation_report_file = f"Gen_report-{number_of_events_per_run}evt-{number_of_measured_runs}runs.csv"

# ==============================================================================
# ---                       INITIALIZE FOR EXPERIMENT                      ---
# ==============================================================================
run_file_name = herwig_input_file.replace('.in', '.run')
full_run_file_path = os.path.join(herwig_run_directory, run_file_name)
integration_tracker = EmissionsTracker(save_to_file=False, project_name="Herwig Integration Repeats")
generation_tracker = EmissionsTracker(save_to_file=False, project_name="Herwig Generation Repeats")
all_integration_data = []
all_generation_data = []

total_runs = number_of_warmup_runs + number_of_measured_runs

# ==============================================================================
# ---                  MAIN EXPERIMENT LOOP (INCLUDES WARM-UP)             ---
# ==============================================================================
print("\n" + "="*60)
print(f"STARTING EXPERIMENT: {number_of_warmup_runs} warm-up runs, {number_of_measured_runs} measured runs")
print("="*60)

integration_tracker.start()
generation_tracker.start()

for i in range(total_runs):
    run_number = i + 1
    is_warmup = (i < number_of_warmup_runs)
    
    if is_warmup:
        print(f"\n--- Starting WARM-UP Run {run_number}/{number_of_warmup_runs} (Data will be discarded) ---")
    else:
        # Adjust run number for printing to be 1-based for measured runs
        measured_run_num = run_number - number_of_warmup_runs
        print(f"\n--- Starting MEASURED Run {measured_run_num}/{number_of_measured_runs} ---")

    if os.path.exists(full_run_file_path):
        os.remove(full_run_file_path)

    # --- Run Integration & Generation regardless of warm-up status ---
    integration_task_name = f"Integration Run {run_number}"
    generation_task_name = f"Generation Run {run_number}"
    
    # Run integration
    integration_tracker.start_task(integration_task_name)
    try:
        subprocess.run(["Herwig", "read", herwig_input_file], check=True, cwd=herwig_run_directory, capture_output=True, text=True)
    except subprocess.CalledProcessError as e:
        print(f"  -> ERROR during Integration: {e.stderr}")
    finally:
        integration_task_data = integration_tracker.stop_task()
    
    # Run generation
    generation_tracker.start_task(generation_task_name)
    try:
        subprocess.run(["Herwig", "run", run_file_name, "-N", str(number_of_events_per_run), "-j", str(number_of_jobs)], check=True, cwd=herwig_run_directory, capture_output=True, text=True)
    except subprocess.CalledProcessError as e:
        print(f"  -> ERROR during Generation: {e.stderr}")
    finally:
        generation_task_data = generation_tracker.stop_task()

    # --- Store data ONLY if it's NOT a warm-up run ---
    if not is_warmup:
        if integration_task_data:
            # ## CORRECTED: Get all data using __dict__ and add the task_name
            integration_dict = integration_task_data.__dict__
            integration_dict['task_name'] = integration_task_name
            all_integration_data.append(integration_dict)
            print(f"  -> Measured Integration complete. Duration: {integration_task_data.duration:.2f}s.")

        if generation_task_data:
            # ## CORRECTED: Get all data using __dict__ and add the task_name
            generation_dict = generation_task_data.__dict__
            generation_dict['task_name'] = generation_task_name
            all_generation_data.append(generation_dict)
            print(f"  -> Measured Generation complete. Duration: {generation_task_data.duration:.2f}s.")
    else:
        print("  -> Warm-up run complete.")

    time.sleep(2)

integration_tracker.stop()
generation_tracker.stop()

# ==============================================================================
# ---                         FINALIZE AND SAVE REPORTS                    ---
# ==============================================================================
print("\n" + "="*60)
print("EXPERIMENT COMPLETE: WRITING FINAL REPORTS")

if all_integration_data:
    integration_df = pd.DataFrame(all_integration_data)
    integration_df.to_csv(os.path.join(output_directory_for_reports, integration_report_file), index=False)
    print(f"  -> Integration report with {len(integration_df)} rows saved to: {integration_report_file}")
else:
    print("  -> No measured data was collected for the integration phase.")

if all_generation_data:
    generation_df = pd.DataFrame(all_generation_data)
    generation_df.to_csv(os.path.join(output_directory_for_reports, generation_report_file), index=False)
    print(f"  -> Generation report with {len(generation_df)} rows saved to: {generation_report_file}")
else:
    print("  -> No measured data was collected for the generation phase.")

print("="*60)