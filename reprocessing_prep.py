# run this script within the working/ directory to create a calibrated_final/ directory, mirroring the NA added value delivery structure.
# once calibrated_final/ is created, place scriptForReprocessing.py in calibrated_final/ and follow the scriptForReprocessing.py instructions

import glob
import os
import sys

# Check if calibrated_final/ already exists:
if glob.glob("calibrated_final"):
    print("ERROR: calibrated_final/ already exists; will not overwrite")
    sys.exit()
else:
    os.mkdir("calibrated_final")

# Fill the caltables
os.mkdir("calibrated_final/caltables")
os.system("cp -rf cont.dat calibrated_final/caltables")

# Fill the measurement_sets
os.mkdir("calibrated_final/measurement_sets")
# First try just uid*targets.ms
os.system("cp -rf uid*targets.ms calibrated_final/measurement_sets/")
# Then try uid*targets_line.ms
os.system("cp -rf uid*targets_line.ms calibrated_final/measurement_sets/")

print("Generated calibrated_final/ and filled caltables/ and measurement_sets/. Please place scriptForReprocessing.py in calibrated_final/ and follow README instructions.")

