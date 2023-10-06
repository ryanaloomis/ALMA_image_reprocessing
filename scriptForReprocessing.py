############### USER EDITABLE VALUES FOR IMAGING; ONLY USED IF --image SELECTED ###############
###############  IF NOT CHANGED, IMAGING WILL BE IDENTICAL TO DELIVERED IMAGES  ###############
make_mfs_images = True                  # generate mfs (per spw) images
make_cont_images = True                 # generate aggregate continuum images
make_cube_images = True                 # generate cube images 
make_repBW_images = True                # generate images corresponding to the requested representative bandwidth
mitigate = True                         # run hif_checkproductsize() and mitigate created products if necessary. 
                                        # Set to false if you want all spws and all targets imaged at full resolution. 
                                        # WARNING: turning off mitigation may result in very large disk usage. Consider 
                                        # adjusting other mitigation parameter first, or manually selecting the target/spw 
                                        # combinations you want.

# for all values below, see Pipeline Users Guide and Reference Manual for detailed descriptions: 
# https://almascience.nrao.edu/processing/science-pipeline
#
# any parameters not selected here can be edited manually in relevant section of the script below
maxproductsize = 350.                   # for mitigation; in GB
maxcubesize = 40.                       # for mitigation; in GB
maxcubelimit = 60.                      # for mitigation; in GB

field = None                            # String specifying fields to be imaged; default is all (pending mitigation)
                                        #     Example: ’3C279, M82’
phasecenter = None                      # Direction measure or field id of the image center. The default phase center is 
                                        # set to the mean of the field directions of all fields that are to be image together.
                                        #     Examples: ’ICRS 13:05:27.2780 -049.28.04.458’, "TRACKFIELD" (for ephemeris)
spw = None                              # Spw(s) to image; default is all spws
                                        #     Example: '17, 23'
uvrange = None                          # Select a set of uv ranges to image; default is all
                                        #     Examples: ’0~1000klambda’, [’0~100klambda’,'300~1000klambda']
hm_imsize = None                        # Image x and y size in pixels or PB level; default is automatically determined
                                        #     Examples: ’0.3pb’, [120, 120]
hm_cell = None                          # Image cell size; default is automatically determined
                                        #     Examples: ’3ppb’, [’0.5arcsec’, ’0.5arcsec’]
nbins = None                            # Channel binning factor for each spw; default is none
                                        #     Format:’spw1:nb1,spw2:nb2,...’ with optional wildcards: ’*:nb’
                                        #     Examples: ’9:2,11:4,13:2,15:8’, ’*:2’ 
robust = None                           # Robust value to image with; default is automatically determined
                                        #     Example: 0.5
uvtaper = None                          # Uvtaper to apply to data; default is none
                                        #     Example: ['1arcsec']
################################################################################################


# imports
import argparse
import glob
import os
import shutil
import sys
import textwrap as _textwrap

class LineWrapRawTextHelpFormatter(argparse.RawDescriptionHelpFormatter):
    def _split_lines(self, text, width):
        text = self._whitespace_matcher.sub(' ', text).strip()
        return _textwrap.wrap(text, width)
os.environ['COLUMNS'] = "100"

# Parse all script options
parser = argparse.ArgumentParser(formatter_class=LineWrapRawTextHelpFormatter, description='ALMA pipeline reprocessing script', epilog='Example usage: \n  Continuum subtract to get uid*targets_line.ms and cleanup: \n    casa --pipeline -c scriptForReprocessing.py --cleanup \n\n  Continuum subtract with a modified cont.dat, reimage, and view the resultant weblog: \n    Modify cont.dat in caltables/\n    casa --pipeline -c scriptForReprocessing.py --contsub --image modified_images_folder --weblog \n\n  Make new mfs and agg cont images with different robust value and view the resultant weblog: \n    Modify robust parameter in scriptForReprocessing.py \n    casa --pipeline -c scriptForReprocessing.py --image new_robust_images_folder --weblog \n\n  Continuum subtract and generate all pipeline images with no mitigation \n    Modify mitigate parameter in scriptForReprocessing.py -> False \n    casa --pipeline -c scriptForReprocessing.py --contsub --image no_mitigation_folder\n\n  Make the old calibrated_final.ms and cleanup: \n    casa --pipeline -c scriptForReprocessing.py --calibrated_final --cleanup')

parser.add_argument('--contsub', action='store_true', help="Fit and subtract continuum using the channel ranges from the local cont.dat file. Generates new uid*targets_line.ms in measurement_sets/")
parser.add_argument('--image', nargs='?', const="images", help="Run the imaging pipeline and place images in the specified directory (default='images'). NOTE: unless cont.dat or the imaging options in this script are modified, the images produced will be identical to those on the ALMA Science Archive")
parser.add_argument('--cleanup', action='store_true', help="Remove working_reprocess/ directory and log files after any other options are executed. WARNING: removes weblogs inside of working_reprocess/")
parser.add_argument('--weblog', nargs='?', const="latest", help="Launches a browser to view weblog after other tasks are run. By default ('latest'), displays the latest weblog generated locally. Other options are to use the specific pipeline folder name (e.g. 'pipeline-20221010T192458')")
# TODO: implement 'delivered'?         #, or 'delivered', to display the full calibration and imaging pipeline as delivered (available for 30 days)
parser.add_argument('--calibrated_final', action='store_true', help="Concatenate uid*targets.ms to produce calibrated_final.ms in measurement_sets/")
parser.add_argument('--calibrated_final_line', action='store_true', help="Concatenate uid*targets_line.ms (if they exist) to produce calibrated_final_line.ms in measurement_sets/")


args = parser.parse_args()

# Check arguments for not allowed combinations
if not any([args.calibrated_final, args.calibrated_final_line, args.contsub, args.image, args.cleanup, args.weblog]):
    print("ERROR: at least one argument must be selected")
    parser.print_help()
    sys.exit()

if (args.contsub) and glob.glob("measurement_sets/uid*targets_line.ms"):
    print("ERROR: uid*targets_line.ms already present in measurement_sets/  Will not contsub and overwrite. Please rename those files and try again.")
    sys.exit()

if args.weblog and args.calibrated_final and not args.contsub:
    print("ERROR: --calibrated_final does not produce a weblog, as no pipeline commands are used. Please use --weblog separately to view the calibration and imaging weblog")
    sys.exit()

if args.weblog and args.calibrated_final_line and not args.contsub:
    print("ERROR: --calibrated_final_line does not produce a weblog, as no pipeline commands are used. Please use --weblog separately to view the calibration and imaging weblog")
    sys.exit()

if args.weblog and args.cleanup:
    print("ERROR: weblog cannot be viewed if the working_reprocess/ directory is removed. Please retry without --cleanup")
    sys.exit()


# Check arguments for odd combinations:
if args.calibrated_final and (args.contsub):
    print("NOTE: Both calibrated_final.ms and uid*targets_line.ms will be created. calibrated_final.ms will not have any continuum subtracted data within it. Use --calibrated_final_line to concatenate the uid*targets_line.ms produced by --contsub.")

cleanup_only = False
if args.cleanup and not any([args.calibrated_final, args.calibrated_final_line, args.contsub, args.image]):
    cleanup_only = True



# Order of operations:
# create working_reprocess/
# move appropriate files to working_reprocess/
# intialize pipeline
# contsub
# image
# move images to images/ (or user specified directory)
# move measurement sets back to measurement_sets/
# calibrated_final / calibrated_final_line
# cleanup (remove working_reprocess/ and logs if asked for)
# weblog



# Create working_reprocess/ directory and move there
if not cleanup_only:
    working_reprocess_exists = bool(glob.glob("working_reprocess"))
    if working_reprocess_exists:
        print("working_reprocess/ exists, will not overwrite any files inside of it")
    else:
        os.mkdir("working_reprocess")

    os.chdir("working_reprocess")


# Move appropriate files to working_reprocess/
# keep track of whether measurement sets have been moved
ms_moved = False

# If contsub, we need cont.dat and the measurement sets
if args.contsub:
    os.system("cp -rf ../caltables/cont.dat .")
    os.system("mv ../measurement_sets/uid*targets.ms .")
    ms_moved = True


# If image, we need the measurement sets:
if args.image:
    if not ms_moved:
        os.system("mv ../measurement_sets/uid*targets*.ms .")
        ms_moved = True


# Initialize pipeline
if args.contsub or args.image:
    # Do the pipeline initialization
    __rethrow_casa_exceptions = True
    pipelinemode='automatic'
    context = h_init()

    # List of all measurement sets to process
    visList = glob.glob("*targets.ms")

    # Load the uid*.ms files into the pipeline
    hifa_importdata(vis=visList, dbservice=False, pipelinemode=pipelinemode)


# Continuum subtraction if selected
if args.contsub:
    # Delete uid*_targets_line.ms and flagversions if they exist
    os.system('rm -rf uid*_targets_line.ms')
    os.system('rm -rf uid*_targets_line.ms.flagversions')

    # Fit and subtract the continuum using the cont.dat for all spws all fields
    hif_uvcontsub(pipelinemode=pipelinemode)


# Image as appropriate with selected imaging stages
if args.image:
    if not glob.glob("../"+args.image):
        # make directory to move images to
        os.mkdir("../"+args.image)
    else:
        print('ERROR: images directory "'+args.image+'" already exists. Will not overwrite. Please specify a new folder name to place images into using --images my_folder')
        os.system("mv *.ms ../measurement_sets")
        sys.exit()

    # move cont.dat to working_reprocess/ if it is not here already:
    if not glob.glob("cont.dat"):
        os.system("cp -rf ../caltables/cont.dat .")

    # calculate the synthesized beam and estimate the sensitivity 
    # for the aggregate bandwidth and representative bandwidth 
    # for multiple values of the robust parameter.   
    hifa_imageprecheck(pipelinemode="automatic")

    if mitigate:
        # check the imaging product size and adjust the relevent
        # imaging parameters (channel binning, cell size and image size)
        hif_checkproductsize(maxproductsize=maxproductsize, maxcubesize=maxcubesize, maxcubelimit=maxcubelimit)


    # make the images
    if make_mfs_images:
        if robust:
            hif_makeimlist(specmode='mfs', spw=spw, uvrange=uvrange, hm_imsize=hm_imsize, nbins=nbins, uvtaper=uvtaper, robust=robust, phasecenter=phasecenter, field=field)
        else:
            hif_makeimlist(specmode='mfs', spw=spw, uvrange=uvrange, hm_imsize=hm_imsize, nbins=nbins, uvtaper=uvtaper, phasecenter=phasecenter, field=field)            
        hif_makeimages(pipelinemode="automatic")

    if make_cont_images:
        if robust:
            hif_makeimlist(specmode='cont', spw=spw, uvrange=uvrange, hm_imsize=hm_imsize, nbins=nbins, uvtaper=uvtaper, robust=robust, phasecenter=phasecenter, field=field)
        else:
            hif_makeimlist(specmode='cont', spw=spw, uvrange=uvrange, hm_imsize=hm_imsize, nbins=nbins, uvtaper=uvtaper, phasecenter=phasecenter, field=field)            
        hif_makeimages(pipelinemode="automatic")


    # check to see if we have uid*targets_line.ms files to do cube imaging:
    if not glob.glob("uid*targets_line.ms") and (make_cube_images or make_repBW_images):
        print("WARNING: cannot image cubes without contsub being run first. Proceeding without cube and repBW cube imaging")
        pass
    else:
        if make_cube_images:
            if robust:
                hif_makeimlist(specmode='cube', spw=spw, uvrange=uvrange, hm_imsize=hm_imsize, nbins=nbins, uvtaper=uvtaper, robust=robust, phasecenter=phasecenter, field=field)
            else:
                hif_makeimlist(specmode='cube', spw=spw, uvrange=uvrange, hm_imsize=hm_imsize, nbins=nbins, uvtaper=uvtaper, phasecenter=phasecenter, field=field)            
            hif_makeimages(pipelinemode="automatic")

        if make_repBW_images:
            if robust:
                hif_makeimlist(specmode='repBW', spw=spw, uvrange=uvrange, hm_imsize=hm_imsize, nbins=nbins, uvtaper=uvtaper, robust=robust, phasecenter=phasecenter, field=field)
            else:
                hif_makeimlist(specmode='repBW', spw=spw, uvrange=uvrange, hm_imsize=hm_imsize, nbins=nbins, uvtaper=uvtaper, phasecenter=phasecenter, field=field)            
            hif_makeimages(pipelinemode="automatic")
    
    # move the images there:
    os.system("mv *.image ../"+args.image+" 2> /dev/null")
    os.system("mv *.image.pbcor ../"+args.image+" 2> /dev/null")
    os.system("mv *.mask ../"+args.image+" 2> /dev/null")
    os.system("mv *.mask.flattened ../"+args.image+" 2> /dev/null")
    os.system("mv *.model ../"+args.image+" 2> /dev/null")
    os.system("mv *.pb ../"+args.image+" 2> /dev/null")
    os.system("mv *.psf ../"+args.image+" 2> /dev/null")
    os.system("mv *.residual ../"+args.image+" 2> /dev/null")
    os.system("mv *.sumwt ../"+args.image+" 2> /dev/null")


# Move measurement sets back to measurement_sets/
if ms_moved:
    os.system("mv *.ms ../measurement_sets")


# Create calibrated_final.ms and/or calibrated_final_line.ms if requested
if args.calibrated_final:
    list_of_ms = glob.glob("../measurement_sets/*targets.ms")
    if not glob.glob("../measurement_sets/calibrated_final.ms"):
        concat(vis=list_of_ms, concatvis="../measurement_sets/calibrated_final.ms")
    else:
        print("WARNING: calibrated_final.ms already exists; will not overwrite.")   
        pass

if args.calibrated_final_line:
    list_of_ms_line = glob.glob("../measurement_sets/*targets_line.ms")
    if not list_of_ms_line:
        print("ERROR: No uid*targets_line.ms files present to concatenate and create calibrated_final_line.ms. --contsub must be run first.")
        sys.exit()
    else:
        if not glob.glob("../measurement_sets/calibrated_final_line.ms"):
            concat(vis=list_of_ms_line, concatvis="../measurement_sets/calibrated_final_line.ms")
        else:
            print("WARNING: calibrated_final.ms already exists; will not overwrite.")   
            pass

# Move out of working_reprocess
if not cleanup_only:
    os.chdir("..")


# Cleanup if requested
if args.cleanup:
    print("Cleaning up... removing working_reprocess/ and casa*.log")
    if glob.glob("working_reprocess/*.ms"):
        print("WARNING: measurement sets still present in working_reprocess/. Will not remove directory until these are moved")
    else:
        os.system("rm -rf working_reprocess")
    os.system("rm -rf casa*.log")
    os.system("rm -rf casacalls*")


# Open relevant weblog
if args.weblog:
    if args.weblog=='latest':
        if glob.glob("working_reprocess"):
            os.chdir("working_reprocess")
        else:
            print("ERROR: folder working_reprocess/ does not exist, cannot find weblog")
            sys.exit()

        # get the most recent weblog
        pipeline_runs = glob.glob("pipeline*[!timetracker.json]")
        latest_run = max(pipeline_runs, key=os.path.getctime)

        # open weblog:
        print("Viewing latest weblog: " + latest_run)
        os.chdir(latest_run)
        h_weblog()
        print("Press Enter to exit weblog...")
        sys.stdout = open(os.devnull, "w")
        sys.stderr = open(os.devnull, "w")
        input()

    else:
        if glob.glob("working_reprocess"):
            os.chdir("working_reprocess")
        else:
            print("ERROR: folder working_reprocess/ does not exist, cannot find weblog")
            sys.exit()

        # get the specified weblog
        desired_run = args.weblog

        # open weblog:
        print("Viewing specified weblog: " + desired_run)
        os.chdir(desired_run)
        h_weblog()
        print("Press Enter to exit weblog...")
        sys.stdout = open(os.devnull, "w")
        sys.stderr = open(os.devnull, "w")
        input()
