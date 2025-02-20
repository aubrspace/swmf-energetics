#!/bin/bash
#'parallel' script for spawning lots of jobs

#define variables
#INPUTDIR=./theta_aurora1997/GM/IO2/
#OUTPUTDIR=./outputs_theta_aurora/

#INPUTDIR=./Starlink_Pleiades/
#OUTPUTDIR=./outputs_starlink_hires/

#INPUTDIR=./starlink2/IO2/
#OUTPUTDIR=./outputs_ccmcStarlink/

#INPUTDIR=./run_mothersday_ne/GM/IO2/
#OUTPUTDIR=./outputs_mothersday_ne/

#INPUTDIR=./run_MEDnMEDu/GM/IO2/
#OUTPUTDIR=./outputs_r3_x120_b07_dist_MEDnMEDu/

INPUTDIR=/home/aubr/pytecplot/swmf-energetics/gannon-storm/data/large/GM/IO2/IO2/
OUTPUTDIR=/home/aubr/pytecplot/swmf-energetics/gannon-storm/outputs/vis/
GMDIR=./run_mothersday_ne/GM/IO2/

filecount=0
workercount=0

#head=3d__var_3_e199701
#head=3d__var_1_e202206
#head=3d__var_1_e202202
#head=3d__var_1_e202405
head=3d__paraview_1_e202405

#satpath=star2satloc
#satpath=mothersday_sats/interp/

i=0
#execute script on tecplot output files
#for file in $INPUTDIR$head*.plt
for file in $GMDIR$head*.plt
do
    day=${file:${#GMDIR}+${#head}:2}
    hour=${file:${#GMDIR}+${#head}+3:2}
    minute=${file:${#GMDIR}+${#head}+5:2}
    
    # Filter by day/hour/minute
    #if [[ ${day#0} -eq 10 ]] && [[ ${hour#0} -lt 15 ]] \
    #                         && [[ ${minute#0} -gt 10 ]]
    #&& [[ ${hour#0} -gt 1 ]]
    if [[ 1 == 1 ]]
    then
        #echo "${file:${#GMDIR}} $day $hour"

        #submit a job with the following flags:
        #   -i input directory
        #   -o output directory
        #   -f specific file to process
        sbatch batchjob_energetics.gl -i $INPUTDIR -o $OUTPUTDIR \
                                      -f ${file:${#GMDIR}}    \
        #                              -n $i
        #                              -s $satpath
        #sbatch batchjob_park.gl -f ${file:${#INPUTDIR}}

        # If you only want to process n files from the list
        #i=$((i+1))
        #if [ $i == 8 ]
        #then
        #    exit
        #fi
        #exit

    fi
done

