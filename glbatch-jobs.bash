#!/bin/bash
#'parallel' script for spawning lots of jobs

#define variables
INPUTDIR=./starlink2/IO2/
OUTPUTDIR=./star2_outputs_n1/
#INPUTDIR=./test_inputs/
#OUTPUTDIR=./test_outputs_n1/
#INPUTDIR=./may2019/IO2/
#OUTPUTDIR=./may2019_outputs_n1/
filecount=0
workercount=0

head=3d__var_1_e202202
#head=3d__var_1_e201905

satpath=star2satloc

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
    #exit

done
