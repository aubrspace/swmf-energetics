#!/bin/bash
#'parallel' script for spawning lots of jobs

#define variables
#INPUTDIR=./ideal_test/GM/IO2/
#OUTPUTDIR=./ideal_first_results/

#INPUTDIR=./starlink2/IO2/
#OUTPUTDIR=./star2_outputs_xslice/

#INPUTDIR=./ideal_conserve/GM/IO2/
#OUTPUTDIR=./ideal_conserve_sp10-3/

#INPUTDIR=./ideal_test/GM/IO2/
#OUTPUTDIR=./ideal_test_sp10-3/

#INPUTDIR=./ideal_IE1/GM/IO2/
#OUTPUTDIR=./ideal_IE1_sp10-3/

#INPUTDIR=./ideal_noRCM1/GM/IO2/
#OUTPUTDIR=./ideal_noRCM1_sp10-3/

#INPUTDIR=./ideal_refined/GM/IO2/
#OUTPUTDIR=./ideal_refined_sp10-3/

#DONE#INPUTDIR=./run_LOWnLOWu/GM/IO2/
     #OUTPUTDIR=./outputs_LOWnLOWu/

#DONE#INPUTDIR=./run_HIGHnHIGHu/GM/IO2/
     #OUTPUTDIR=./outputs_HIGHnHIGHu/

#DONE#INPUTDIR=./run_LOWnHIGHu/GM/IO2/
     #OUTPUTDIR=./outputs_LOWnHIGHu/

#DONE#INPUTDIR=./run_HIGHnLOWu/GM/IO2/
     #OUTPUTDIR=./outputs_HIGHnLOWu/

#INPUTDIR=./run_MEDnMEDu/GM/IO2/
#OUTPUTDIR=./outputs_MEDnMEDu/

#DONE#INPUTDIR=./run_MEDnHIGHu/GM/IO2/
     #OUTPUTDIR=./outputs_MEDnHIGHu/

INPUTDIR=./run_MEDnHIGHu/GM/IO2/
OUTPUTDIR=./outputs_mar24_MEDnHIGHu/

#INPUTDIR=./Original_sw_run_output/
#OUTPUTDIR=./outputs_MAST/Original_sw_run_energetics/

#INPUTDIR=./Box_run_output/
#OUTPUTDIR=./outputs_MAST/Box_run_energetics/

#INPUTDIR=./Box+ULF_run_output/
#OUTPUTDIR=./outputs_MAST/Box+ULF_run_energetics/

#INPUTDIR=./Lowpass_run_output/
#OUTPUTDIR=./outputs_MAST/Lowpass_run_energetics/

#INPUTDIR=./Only_ULF_run_output/
#OUTPUTDIR=./outputs_MAST/Only_ULF_run_energetics/

filecount=0
workercount=0

#head=3d__var_1_e20140410-080
#head=3d__var_1_e201404
#head=3d__var_1_e202202
head=3d__var_1_e202206
#head=3d__var_1_e201505
#head=it2206

#satpath=star2satloc

i=0
#execute script on tecplot output files
for file in $INPUTDIR$head*.plt
do
    #submit a job with the following flags:
    #   -i input directory
    #   -o output directory
    #   -f specific file to process
    #echo "-i $INPUTDIR -o $OUTPUTDIR -f ${file:${#INPUTDIR}} -s $satpath"
    sbatch batchjob_energetics.gl -i $INPUTDIR -o $OUTPUTDIR \
                                  -f ${file:${#INPUTDIR}}    \
    #                              -s $satpath

    #if you only want to process one file use this
    #i=$((i+1))
    #if [ $i == 4 ]
    #then
    #    exit
    #fi
done

