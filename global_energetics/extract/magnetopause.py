#!/usr/bin/env python3
"""Extraction routine for magnetopause surface
"""
import logging as log
import os
import sys
import time
from array import array
import numpy as np
from numpy import abs, pi, cos, sin, sqrt, rad2deg, deg2rad, linspace
import matplotlib.pyplot as plt
import datetime as dt
import tecplot as tp
from tecplot.constant import *
from tecplot.exception import *
import pandas as pd
from progress.bar import Bar
#interpackage modules
from global_energetics.makevideo import get_time
from global_energetics.extract import surface_construct
from global_energetics.extract import swmf_access
#from global_energetics.extract.view_set import display_magnetopause
from global_energetics.extract import surface_tools
from global_energetics.extract.surface_tools import surface_analysis
from global_energetics.extract import volume_tools
from global_energetics.extract.volume_tools import volume_analysis
from global_energetics.extract import stream_tools
from global_energetics.extract.stream_tools import (streamfind_bisection,
                                                    dump_to_pandas,
                                                    create_cylinder,
                                                    load_cylinder,
                                                    setup_isosurface,
                                                  calc_rho_innersurf_state,
                                                    abs_to_timestamp,
                                                    write_to_timelog)
from global_energetics.extract import shue
from global_energetics.extract.shue import (r_shue, r0_alpha_1997,
                                                    r0_alpha_1998)

def get_shue_mesh(field_data, year, nx, nphi, xtail,
                  x_subsolar, *, dx=10):
    """Function mesh of 3D volume points based on Shue 1997/8 model for
        magnetopause
    Inputs
        field_data
        year- 1997 or 1998 for which emperical model
        nx, nphi- 3D volume grid dimensions
        xtail- limit for how far to extend in negative x direction
        x_subsolar- if None will calculate with dayside fieldlines
    Outputs
        mesh- pandas DataFrame with X,Y,Z locations of outer surface
        x_subsolar
    """
    if x_subsolar == None:
        x_subsolar = 0
        #Call get streamfind with limited settings to get x_subsolar
        frontzoneindicies = streamfind_bisection(field_data, 'dayside', 10,
                                                 5, 30, 3.5, 100, 0.1)
        #Find the max value from set of zones
        for index in frontzoneindicies:
            x_subsolar = max(x_subsolar,
                                field_data.zone(index).values('X *').max())
        print('x_subsolar found at {}'.format(x_subsolar))
        #delete streamzones
        for zone_index in reversed(frontzoneindicies):
            field_data.delete_zones(field_data.zone(zone_index))
    #Probe field data at x_subsolar + dx to find Bz and Pdyn
    Bz = tp.data.query.probe_at_position(x_subsolar+dx,0,0)[0][9]
    rho = tp.data.query.probe_at_position(x_subsolar+dx,0,0)[0][3]
    ux = tp.data.query.probe_at_position(x_subsolar+dx,0,0)[0][4]
    uy = tp.data.query.probe_at_position(x_subsolar+dx,0,0)[0][5]
    uz = tp.data.query.probe_at_position(x_subsolar+dx,0,0)[0][6]
    Pdyn = 1/2*rho*(ux**2+uy**2+uz**2)*1.6605e-6
    #Get r0 and alpha based on IMF conditions
    if year == 1997:
        r0, alpha = r0_alpha_1997(Bz, Pdyn)
    else:
        r0, alpha = r0_alpha_1998(Bz, Pdyn)
    #Calculate the 2D r, theta curve
    thetalist = linspace(150, 0, 10000)
    h_curve = []
    x_curve = []
    for theta in thetalist:
        r = r_shue(r0, alpha, theta)
        h_curve.append(r*sin(deg2rad(theta)))
        x_curve.append(r*cos(deg2rad(theta)))
    #Set volume grid points
    xlist = linspace(xtail, x_curve[-1], nx)
    hlist = []
    for x in xlist:
        hlist.append(np.interp(x, x_curve, h_curve))
    philist = linspace(-180, 180, nphi)
    #Fill in volume based on revolved 2D curve of points
    xyz = ['X [R]', 'Y [R]', 'Z [R]']
    mesh = pd.DataFrame(columns=xyz)
    for point in enumerate(xlist):
        x = point[1]
        h = hlist[point[0]]
        for phi in philist:
            y = h*cos(deg2rad(phi))
            z = h*sin(deg2rad(phi))
            mesh = mesh.append(pd.DataFrame([[x,y,z]],columns=xyz))
    return mesh, x_subsolar

def inner_volume_df(df1, df2, upperbound, lowerbound, innerbound,
                    dim1, dim2, *, form='xcylinder',xkey='X [R]',
                                   quiet=True):
    """Function combines two dataframe sets of points representing volumes
        and keeping the interior points only based on form given
    Inputs
        df1, df2- pandas dataframe objects
        upperbound, lowerbound, innerbound- limits of search criteria
        dim1, dim2- dimensionality of search criteria of discrete vol elems
        form- default cylinder with axis on centerline
        xkey- string ID for x coordinate, y and z are assumed
        quiet- boolean for displaying points missing in 1 or more sets
    Returns
        df_combined
    """
    #get x, y, z variables
    ykey = xkey.split('X')[0]+'Y'+xkey.split('X')[-1]
    zkey = xkey.split('X')[0]+'Z'+xkey.split('X')[-1]
    xyz = [xkey, ykey, zkey]
    #establish volume elements for search according to form
    if form == 'xcylinder':
        #process dataframes according to upper,lower inner bounds
        df1 = df1[(df1[xkey]< upperbound) & (df1[xkey]>lowerbound) &
                  (df1[xkey]**2+df1[ykey]**2+df1[zkey]**2>innerbound**2)]
        df2 = df2[(df2[xkey]< upperbound) & (df2[xkey]>lowerbound) &
                  (df2[xkey]**2+df2[ykey]**2+df2[zkey]**2>innerbound**2)]
        #cylinder with axis on X axis, dim1=x slices, dim2=azimuth
        xmax = max(df1[xkey].max(), df2[xkey].max())
        xmin = min(df1[xkey].min(), df2[xkey].min())
        dim1list, dx1 = np.linspace(xmin, xmax, dim1, retstep=True)
        dim2list, dx2 = np.linspace(-pi, pi, dim2, retstep=True)
        #get height parameter
        def height(y,z): return np.sqrt(y**2+z**2)
        h1 = pd.DataFrame(height(df1[ykey],df1[zkey]), columns=['h'])
        h2 = pd.DataFrame(height(df2[ykey],df2[zkey]), columns=['h'])
        df1 = df1.combine(h1, np.minimum, fill_value=1000)
        df2 = df2.combine(h2, np.minimum, fill_value=1000)
        hkey = 'h'
        #remove points outside of hmax of the lower hmax
        hmax = min(h1['h'].max(), h2['h'].max())
        df1 = df1[(df1[hkey]< hmax)]
        df2 = df2[(df2[hkey]< hmax)]
        #set dim1key to x
        dim1key = xkey
        #get azimuth angle parameter
        def angle(y,z): return np.arctan2(z,y)
        a1 = pd.DataFrame(angle(df1[ykey],df1[zkey]), columns=['yz[rad]'])
        a2 = pd.DataFrame(angle(df2[ykey],df2[zkey]), columns=['yz[rad]'])
        df1 = df1.combine(a1, np.minimum, fill_value=1000)
        df2 = df2.combine(a2, np.minimum, fill_value=1000)
        dim2key = 'yz[rad]'
        #create placepoint function based on x1,x2,h general coordinates
        def placepoint(x1,x2,h):
            x = x1
            y = h*cos(x2)
            z = h*sin(x2)
            return x, y, z
    else:
        print('WARNING: form for combination of dataframes not recognized'+
              ' combining full set of points from each dataframe')
        df_combined = df1.append(df2)
        return df_combined.sort_values(by=[xkey])
    #loop through discretized volumes
    bar = Bar('combining dataframes:', max=len(dim1list)*len(dim2list))
    missing_points_list = []
    df_combined = pd.DataFrame(columns=xyz)
    df_flow = pd.DataFrame(columns=xyz)
    df_field = pd.DataFrame(columns=xyz)
    for x1 in dim1list:
        for x2 in dim2list:
            #get points within volume element
            tempdf1 = df1[(df1[dim1key]>x1-dx1/2)&(df1[dim1key]<x1+dx1/2) &
                          (df1[dim2key]>x2-dx2/2)&(df1[dim2key]<x2+dx2/2)]
            tempdf2 = df2[(df2[dim1key]>x1-dx1/2)&(df2[dim1key]<x1+dx1/2) &
                          (df2[dim2key]>x2-dx2/2)&(df2[dim2key]<x2+dx2/2)]
            #append a point at x1,x2 and h based on averages of df's
            if (not tempdf1.empty) | (not tempdf2.empty):
                hmax = min(tempdf1[hkey].max(), tempdf2[hkey].max())
                df_combined=df_combined.append(tempdf1[tempdf1[hkey]<hmax])
                df_combined=df_combined.append(tempdf2[tempdf2[hkey]<hmax])
            else:
                #assume location of point and record in missing list
                missing_points_list.append([x1,rad2deg(x2),
                                            tempdf1[hkey].mean(),
                                            tempdf2[hkey].mean()])
            bar.next()
    bar.finish()
    if not quiet and (len(missing_points_list)!=0):
        print('WARNING: Following points missing in both data sets')
        print('X    Theta(deg)      flow_h      field_h'+
            '\n--   ----------      ------      -------')
        for point in missing_points_list:
            print('{:.2f}  {:.0f}  {:.1f}  {:.1f}'.format(point[0],
                                                                  point[1],
                                                                  point[2],
                                                                  point[3]))
    return df_combined

def get_magnetopause(field_data, datafile, *, outputpath='output/',
                     mode='iso_rho', source='swmf',
                     longitude_bounds=10, n_fieldlines=5,rmax=30,rmin=3,
                     dx_probe=-1,
                     shue_type=1998,
                     itr_max=100, tol=0.1,
                     tail_cap=-40, tail_analysis_cap=-20,
                     integrate_surface=True, integrate_volume=True,
                     xyzvar=[1,2,3], zone_rename=None):
    """Function that finds, plots and calculates energetics on the
        magnetopause surface.
    Inputs
        General
            field_data- tecplot DataSet object with 3D field data
            datafile- field data filename, assumes .plt file
            outputpath- path for output of .csv of points
            mode- iso_rho, shue97, or shue98
        Streamtracing
            longitude_bounds, nlines- bounds and density of search
            rmax, rmin, itr, tol- parameters for bisection algorithm
        Isosurface selection
            dx_probe- how far from x_subsolar to probe for iso creation
        Shue
            shue- 1997, 1998 uses Shue empirical
        Surface
            tail_cap- X position of tail cap
            tail_analysis_cap- X position where integration stops
            integrate_surface/volume- booleans for settings
            xyzvar- for X, Y, Z variables in field data variable list
            zone_rename- optional rename if calling multiple times
    """
    approved = ['iso_rho', 'shue97', 'shue98', 'shue']
    if not any([mode == match for match in approved]):
        print('Magnetopause mode "{}" not recognized!!'.format(mode))
        print('Please set mode to one of the following:')
        for choice in approved:
            print('\t{}'.format(choice))
        return
    display = ('Analyzing Magnetopause with the following settings:\n'+
               '\tdatafile: {}\n'.format(datafile)+
               '\toutputpath: {}\n'.format(outputpath)+
               '\tmode: {}\n'.format(mode)+
               '\tsource: {}\n'.format(source))
        #field line settings
    display = (display +
               '\tlongitude_bounds: {}\n'.format(longitude_bounds)+
               '\tn_fieldlines: {}\n'.format(n_fieldlines)+
               '\trmax: {}\n'.format(rmax)+
               '\trmin: {}\n'.format(rmin)+
               '\titr_max: {}\n'.format(itr_max)+
               '\ttol: {}\n'.format(tol))
    if mode == 'shue':
        #shue empirical settings
        display = (display+
               '\tshue: {}\n'.format(shue_type))
    #general surface settings
    display = (display+
               '\ttail_cap: {}\n'.format(tail_cap)+
               '\ttail_analysis_cap: {}\n'.format(tail_analysis_cap)+
               '\tintegrate_surface: {}\n'.format(integrate_surface)+
               '\tintegrate_volume: {}\n'.format(integrate_volume)+
               '\txyzvar: {}\n'.format(xyzvar)+
               '\tzone_rename: {}\n'.format(zone_rename))
    if os.path.exists('banner.txt') & (
                               not os.path.exists(outputpath+'/meshdata')):
        with open('banner.txt') as image:
            print(image.read())
    print('**************************************************************')
    print(display)
    print('**************************************************************')
    #get date and time info based on data source
    if source == 'swmf':
        eventtime = swmf_access.swmf_read_time()
        datestring = (str(eventtime.year)+'-'+str(eventtime.month)+'-'+
                      str(eventtime.day)+'-'+str(eventtime.hour)+'-'+
                      str(eventtime.minute))
    else:
        print("Unknown data source, cant find date/time and won't be able"+
              "to consider dipole orientation!!!")
        datestring = 'Date & Time Unknown'

    with tp.session.suspend():
        #get r, lon, lat if not already set
        if field_data.variable_names.count('r [R]') ==0:
            main_frame = tp.active_frame()
            aux = field_data.zone('global_field').aux_data
            main_frame.name = 'main'
            tp.data.operate.execute_equation(
                    '{r [R]} = sqrt({X [R]}**2 + {Y [R]}**2 + {Z [R]}**2)')
            tp.data.operate.execute_equation(
                    '{lat [deg]} = 180/pi*asin({Z [R]} / {r [R]})')
            tp.data.operate.execute_equation(
                    '{lon [deg]} = if({X [R]}>0,'+
                                     '180/pi*atan({Y [R]} / {X [R]}),'+
                                  'if({Y [R]}>0,'+
                                     '180/pi*atan({Y [R]}/{X [R]})+180,'+
                                     '180/pi*atan({Y [R]}/{X [R]})-180))')
            tp.data.operate.execute_equation(
                                      '{h} = sqrt({Y [R]}**2+{Z [R]}**2)')
        else:
            main_frame = [fr for fr in tp.frames('main')][0]
        #Get x_subsolar if not already there
        if any([key.find('x_subsolar')!=-1 for key in aux.keys()]):
            x_subsolar = aux['x_subsolar']
        else:
            frontzoneindicies = streamfind_bisection(field_data,'dayside',
                                            longitude_bounds, n_fieldlines,
                                            rmax, rmin, itr_max, tol)
            x_subsolar = 1
            for index in frontzoneindicies:
                x_subsolar = max(x_subsolar,
                                field_data.zone(index).values('X *').max())
            print('x_subsolar found at {}'.format(x_subsolar))
            aux['x_subsolar'] = x_subsolar
            #delete streamzones
            for zone_index in reversed(frontzoneindicies):
                field_data.delete_zones(field_data.zone(zone_index))
        #Get mesh points depending on mode setting
        ################################################################
        if mode == 'shue':
            mp_mesh, x_subsolar = get_shue_mesh(field_data, shue_type,
                                                nslice, nalpha, tail_cap,
                                                x_subsolar=x_subsolar)
            zonename = 'mp_shue'+str(shue_type)
        ################################################################
        if mode == 'iso_rho':
            zonename = 'mp_iso_innersurf'
            #probe data to find density value for isosurface
            density_index = field_data.variable('Rho *').index
            surface_density= tp.data.query.probe_at_position(
                                                     x_subsolar+dx_probe,
                                                     0,0)[0][density_index]
            #create density contour
            density_zone = setup_isosurface(surface_density, density_index,
                                            7, 7, 'iso_rho')
            #scrape at the cusps, to id the maximum r between the two,
            #limited to maximum of x_subsolar
            rvalues = density_zone.values('r *').as_numpy_array()
            latvalues = density_zone.values('lat *').as_numpy_array()
            cusplat = 90
            cusp_indices = np.where(abs(latvalues)>90)
            while (len(cusp_indices[0]) == 0) & (cusplat>0):
                cusp_indices = np.where(abs(latvalues)>cusplat)
                cusplat -= 0.5
            if cusplat == 0:
                print('No cusp indices found!! Setting to subsolar length')
                rinclude = x_subsolar
            else:
                print('cusplatitude found at {}'.format(cusplat))
                rinclude = min([max(rvalues[cusp_indices]),x_subsolar])
            field_data.delete_zones(density_zone)
            #calculate surface state variable
            rho_innersurf_index = calc_rho_innersurf_state(x_subsolar,
                                                           tail_cap, 50,
                                                           surface_density,
                                                           rinclude)
            #remake iso zone using new equation
            rho_innersurf_zone = setup_isosurface(1, rho_innersurf_index,
                                                  7, 7, zonename)
            zoneindex = rho_innersurf_zone.index
            if zone_rename != None:
                rho_innersurf_zone.name = zone_rename
                zonename = zone_rename
        ################################################################
        #save mesh to hdf file as key=mode, along with time in key='time'
        print(zoneindex)
        mp_mesh, _ = dump_to_pandas(main_frame, [zoneindex], xyzvar,
                                    'temp.csv')
        path_to_mesh = outputpath+'meshdata'
        if not os.path.exists(outputpath+'meshdata'):
            os.system('mkdir '+outputpath+'meshdata')
        meshfile = datestring+'_mesh.h5'
        mp_mesh.to_hdf(path_to_mesh+'/'+meshfile, key=zonename)
        pd.Series(eventtime).to_hdf(path_to_mesh+'/'+meshfile, 'time')

        #perform integration for surface and volume quantities
        mp_powers = pd.DataFrame()
        mp_magnetic_energy = pd.DataFrame()
        '''
        if integrate_surface:
            mp_powers = surface_analysis(field_data, zonename, nfill,
                                         nslice, cuttoff=tail_analysis_cap)
            print('\nMagnetopause Power Terms')
            print(mp_powers)
        if integrate_volume:
            mp_energies = volume_analysis(field_data, zonename,
                                          cuttoff=tail_analysis_cap)
            print('\nMagnetopause Energy Terms')
            print(mp_energies)
        if integrate_surface or integrate_surface:
            integralfile = outputpath+'mp_integral_log.h5'
            cols = mp_powers.keys().append(mp_energies.keys())
            mp_energetics = pd.DataFrame(columns=cols, data=[np.append(
                                     mp_powers.values,mp_energies.values)])
            #Add time column
            mp_energetics.loc[:,'Time [UTC]'] = eventtime
            with pd.HDFStore(integralfile) as store:
                if any([key.find(zonename)!=-1 for key in store.keys()]):
                    mp_energetics = store[zonename].append(mp_energetics,
                                                         ignore_index=True)
                store[zonename] = mp_energetics
        '''
    #Display result from this step
    result = ('Result\n'+
               '\tmeshdatafile: {}\n'.format(path_to_mesh+'/'+meshfile))
    '''
    if integrate_volume or integrate_surface:
        result = (result+
               '\tintegralfile: {}\n'.format(integralfile)+
               '\tzonename_added: {}\n'.format(zonename))
        with pd.HDFStore(integralfile) as store:
            result = result+'\tmp_energetics:\n'
            for key in store.keys():
                result = (result+
                '\t\tkey={}\n'.format(key)+
                '\t\t\tn_values: {}\n'.format(len(store[key])))
    '''
    print('**************************************************************')
    print(result)
    print('**************************************************************')



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
