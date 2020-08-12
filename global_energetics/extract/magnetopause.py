#!/usr/bin/env python3
"""Extraction routine for magnetopause surface
"""
import logging as log
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
#interpackage modules
from global_energetics.extract import surface_construct
#from global_energetics.extract.view_set import display_magnetopause
from global_energetics.extract import surface_tools
from global_energetics.extract.surface_tools import (surface_analysis,
                                                     volume_analysis)
from global_energetics.extract import stream_tools
from global_energetics.extract.stream_tools import (calc_dayside_mp,
                                                    calc_tail_mp,
                                                    dump_to_pandas,
                                                    create_cylinder,
                                                    load_cylinder,
                                                    abs_to_timestamp,
                                                    write_to_timelog)

def get_magnetopause(field_data, datafile, *, pltpath='./', laypath='./',
                     pngpath='./', nstream_day=15, phi_max=122,
                     rday_max=30,rday_min=3.5, dayitr_max=100, daytol=0.1,
                     nstream_tail=15, rho_max=50,rho_step=0.5,tail_cap=-20,
                     nslice=40, nalpha=50, nfill=2):
    """Function that finds, plots and calculates energetics on the
        magnetopause surface.
    Inputs
        field_data- tecplot DataSet object with 3D field data
        datafile- field data filename, assumes .plt file
        pltpath, laypath, pngpath- path for output of .plt,.lay,.png files
        nstream_day- number of streamlines generated for dayside algorithm
        phi_max- azimuthal (sun=0) limit of dayside algorithm for streams
        rday_max, rday_min- radial limits (in XY) for dayside algorithm
        dayitr_max, daytol- settings for bisection search algorithm
        nstream_tail- number of streamlines generated for tail algorithm
        rho_max, rho_step- tail disc maximium radius and step (in YZ)
        tail_cap- X position of tail cap
        nslice, nalpha- cylindrical points used for surface reconstruction
    """
    #make unique outputname based on datafile string
    outputname = datafile.split('e')[1].split('-000.')[0]+'-mp'
    print(field_data)

    #set parameters
    phi = np.linspace(np.deg2rad(-1*phi_max),np.deg2rad(phi_max),
                      nstream_day)
    psi = np.linspace(-pi*(1-pi/nstream_tail), pi, nstream_tail)
    with tp.session.suspend():
        main_frame = tp.active_frame()
        main_frame.name = 'main'
        tp.data.operate.execute_equation(
                    '{r [R]} = sqrt({X [R]}**2 + {Y [R]}**2 + {Z [R]}**2)')

        #Create Dayside Magnetopause field lines
        calc_dayside_mp(field_data, phi, rday_max, rday_min, dayitr_max,
                        daytol)
        #Create Tail magnetopause field lines
        calc_tail_mp(field_data, psi, tail_cap, rho_max, rho_step)
        #Create Theta and Phi coordinates for all points in domain
        tp.data.operate.execute_equation(
                                   '{phi} = atan({Y [R]}/({X [R]}+1e-24))')
        tp.data.operate.execute_equation(
                                   '{theta} = acos({Z [R]}/{r [R]}) * '+
                                    '({X [R]}+1e-24) / abs({X [R]}+1e-24)')
        #port stream data to pandas DataFrame object
        stream_zone_list = np.linspace(2,field_data.num_zones,
                                       field_data.num_zones-2+1)
        stream_df, x_subsolar = dump_to_pandas(main_frame,
                                               stream_zone_list, [1,2,3],
                                               'stream_points.csv')
        #slice and construct XYZ data
        mp_mesh = surface_construct.yz_slicer(stream_df, tail_cap,
                                              x_subsolar, nslice, nalpha,
                                              False)
        #create and load cylidrical zone
        create_cylinder(field_data, nslice, nalpha, nfill, tail_cap,
                        x_subsolar, 'mp_zone')
        load_cylinder(field_data, mp_mesh, 'mp_zone', I=nfill, J=nslice,
                      K=nalpha)

        #interpolate field data to zone
        print('interpolating field data to magnetopause')
        tp.data.operate.interpolate_inverse_distance(
                destination_zone=field_data.zone('mp_zone'),
                source_zones=field_data.zone('global_field'))
        #magnetopause_power = surface_analysis(field_data, 'mp_zone')
        #print(magnetopause_power)
        mp_magnetic_energy = volume_analysis(field_data, 'mp_zone')
        print(mp_magnetic_energy)
        #write_to_timelog('mp_integral_log.csv',outputname,
        #                 magnetopause_power)

        #delete stream zones
        main_frame.activate()
        for zone in reversed(range(field_data.num_zones)):
            tp.active_frame().plot().fieldmap(zone).show=True
            if (field_data.zone(zone).name.find('cps_zone') == -1 and
                field_data.zone(zone).name.find('global_field') == -1 and
                field_data.zone(zone).name.find('mp_zone') == -1):
                field_data.delete_zones(field_data.zone(zone))


# Must list .plt that script is applied for proper execution
# Run this script with "-c" to connect to Tecplot 360 on port 7600
# To enable connections in Tecplot 360, click on:
#   "Scripting" -> "PyTecplot Connections..." -> "Accept connections"

if __name__ == "__main__":
    if '-c' in sys.argv:
        tp.session.connect()
    os.environ["LD_LIBRARY_PATH"]='/usr/local/tecplot/360ex_2018r2/bin:/usr/local/tecplot/360ex_2018r2/bin/sys:/usr/local/tecplot/360ex_2018r2/bin/sys-util'
    tp.new_layout()

    #Load .plt file, come back to this later for batching
    SWMF_DATA = tp.data.load_tecplot('3d__mhd_2_e20140219-123000-000.plt')

    #Set parameters
    #DaySide
    N_AZIMUTH_DAY = 15
    AZIMUTH_MAX = 122
    R_MAX = 30
    R_MIN = 3.5
    ITR_MAX = 100
    TOL = 0.1

    #Tail
    N_AZIMUTH_TAIL = 15
    RHO_MAX = 50
    RHO_STEP = 0.5
    X_TAIL_CAP = -20

    #YZ slices
    N_SLICE = 40
    N_ALPHA = 50

    #Visualization
    RCOLOR = 4

    get_magnetopause('./3d__mhd_2_e20140219_123000-000.plt')
