#!/usr/bin/env python3
"""Functions for analyzing surfaces from field data
"""
import os
import sys
import time
from array import array
import numpy as np
from numpy import abs, pi, cos, sin, sqrt
import tecplot as tp
from tecplot.constant import *
from tecplot.exception import *
import pandas as pd
from stream_tools import (calculate_energetics, integrate_surface,
                              dump_to_pandas)


def volume_analysis(field_data, zone_name):
    """Function to calculate energy flux at magnetopause surface
    Inputs
        field_data- tecplot Dataset object with 3D field data and mp
        zone_name
    Outputs
        surface_power- power, or energy flux at the magnetopause surface
    """
    #calculate energetics field variables
    calculate_energetics(field_data, zone_name)
    #initialize objects for main frame
    main_frame = [fr for fr in tp.frames('main')][0]
    surface_name = zone_name.split('_')[0]
    zone_index = int(field_data.zone(zone_name).index)
    knet_index = int(field_data.variable('K_in *').index)
    kplus_index = int(field_data.variable('K_in+*').index)
    kminus_index = int(field_data.variable('K_in-*').index)
    print('\nbefore 1st integration:')
    for frame in tp.frames():
        print(frame.name)
    #integrate k flux
    kout_frame = integrate_surface(kplus_index, zone_index,
                                   surface_name+' K_out [kW]')
    print('\nbefore 2nd integration:')
    for frame in tp.frames():
        print(frame.name)

    knet_frame = integrate_surface(knet_index, zone_index,
                                   surface_name+' K_net [kW]')
    print('\nbefore 3rd integration:')
    for frame in tp.frames():
        print(frame.name)

    kin_frame = integrate_surface(kminus_index, zone_index,
                                  surface_name+' K_in [kW]')

    #Identify and delete dummy frame as workaround
    dummy_frame = [fr for fr in tp.frames('Frame*')][0]
    dummy_frame.move_to_bottom()
    print('\nactivated frame: {}'.format(tp.active_frame().name))

    #port data to pandas dataframes
    kout_df, _ = dump_to_pandas(kout_frame, [1], [4],
                                surface_name+'_outflux.csv')
    knet_df, _ = dump_to_pandas(knet_frame, [1], [4],
                                surface_name+'_netflux.csv')
    kin_df, _ = dump_to_pandas(kin_frame, [1], [4],
                               surface_name+'_influx.csv')
    #Combine into single dataframe
    surface_power = kout_df.combine(knet_df, np.minimum,
                                    fill_value=1e12).combine(
                                    kin_df, np.minimum,
                                    fill_value=1e12).drop(
                                    columns=['Unnamed: 1'])
    return surface_power


# Run this script with "-c" to connect to Tecplot 360 on port 7600
# To enable connections in Tecplot 360, click on:
#   "Scripting" -> "PyTecplot Connections..." -> "Accept connections"
# Run as main to test script functionality, will need valid .plt file that
# can handle the dummy circular zone

if __name__ == "__main__":
    if '-c' in sys.argv:
        tp.session.connect()
    os.environ["LD_LIBRARY_PATH"]='/usr/local/tecplot/360ex_2018r2/bin:/usr/local/tecplot/360ex_2018r2/bin/sys:/usr/local/tecplot/360ex_2018r2/bin/sys-util'
    tp.new_layout()
    tp.active_frame().name = 'main'
    #Give valid test dataset here!
    DATASET = tp.data.load_tecplot('3d__mhd_2_e20140219-123000-000.plt')
    #Create small test zone
    tp.macro.execute_command('''$!CreateCircularZone
                             IMax = 2
                             JMax = 20
                             KMax = 5
                             X = 0
                             Y = 0
                             Z1 = 0
                             Z2 = 5
                             Radius = 5''')
    POWER = surface_analysis(DATASET, 'Circular zone', [-5,0,5])
    print(POWER)