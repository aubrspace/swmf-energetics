#!/bin/bash
#Batch file for running extract_mpsurface.py on all .plt files

#create output folders
PLTDIR=localdbug/plt/
SCRIPTDIR=./
mkdir output
mkdir output/plt
mkdir output/lay
mkdir output/png
OUT=output
PLTOUT=output/plt/
LAYOUT=output/lay/
PNGOUT=output/png/
echo "Created output directory"

#ensure batch mode is ready for tecpot LINUX SPECIFIC
TECPATH=$(which tec360)
eval `$TECPATH-env`
echo LD_LIBRARY_PATH: $LD_LIBRARY_PATH

#create log file for integral quantities
touch $OUT/mp_integral_log_hybrid.csv
echo $'year, month, day, hour, minute, second, K_out [kW], K_net [kW], K_in [kW], Area [m^2], uB [J], KEpar [J], KEperp [J], Etherm [J], Volume [R^3]'>>$OUT/mp_integral_log_hybrid.csv
cp $OUT/mp_integral_log_hybrid.csv $OUT/mp_integral_log_flowline.csv
cp $OUT/mp_integral_log_hybrid.csv $OUT/mp_integral_log_shue.csv
#touch output/cps_integral_log.csv
#echo $'year, month, day, hour, minute, second, Etherm[J], KEpar[J], KEperp[J], k_in[kW], k_net[kW], k_out[kW], uB[J]'>>output/cps_integral_log.csv

#execute script on .plt files
for file in $PLTDIR*.plt
do
    python main.py $file $OUT/ $PNGOUT $PLTOUT
done

#create video from png file
python global_energetics/makevideo.py $PNGOUT
