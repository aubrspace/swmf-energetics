#!/usr/bin/env python3
"""Functions for identifying surfaces from field data
"""
import logging as log
import os
import sys
import time
from array import array
import numpy as np
from numpy import abs, pi, cos, sin, sqrt, rad2deg, matmul, deg2rad
import datetime as dt
from progress.bar import Bar
from progress.spinner import Spinner
import spacepy
from spacepy import coordinates as coord
from spacepy import time as spacetime
import tecplot as tp
from tecplot.constant import *
from tecplot.exception import *
import pandas as pd
#Interpackage modules
from global_energetics.extract import shue
from global_energetics.extract.shue import (r_shue, r0_alpha_1997,
                                                    r0_alpha_1998)

def create_stream_zone(field_data, x1start, x2start, x3start,
                       zone_name, *, line_type=None, cart_given=False,
                       save=False):
    """Function to create a streamline, created in 2 directions from
       starting point
    Inputs
        field_data- Dataset class from tecplot with 3D field data
        x1start- starting position for streamline, default radius [R]
        x2start- starting position for streamline, default latitude [deg]
        x3start- starting position for streamline, default longitude [deg]
        zone_name
        line_type- day, north or south for determining stream direction
        cart_given- optional input for giving cartesian coord [x,y,z]
    Outputs
        streamzone
    """
    if cart_given==False:
        # Get starting position in cartesian coordinates
        [x_start, y_start, z_start] = sph_to_cart(x1start, x2start,
                                                  x3start)
    else:
        x_start = x1start
        y_start = x2start
        z_start = x3start
    # Create streamline
    tp.active_frame().plot().show_streamtraces = True
    field_line = tp.active_frame().plot().streamtraces
    if line_type == 'south':
        field_line.add(seed_point=[x_start, y_start, z_start],
                       stream_type=Streamtrace.VolumeLine,
                       direction=StreamDir.Reverse)
    elif line_type == 'north':
        field_line.add(seed_point=[x_start, y_start, z_start],
                       stream_type=Streamtrace.VolumeLine,
                       direction=StreamDir.Forward)
    else:
        field_line.add(seed_point=[x_start, y_start, z_start],
                       stream_type=Streamtrace.VolumeLine,
                       direction=StreamDir.Both)
    # Create zone
    field_line.extract()
    field_data.zone(-1).name = zone_name
    # Delete streamlines
    field_line.delete_all()


def check_streamline_closed(field_data, zone_name, r_seed, line_type):
    """Function to check if a streamline is open or closed
    Inputs
        field_data- tecplot Dataset class with 3D field data
        zone_name
        r_seed [R]- position used to seed field line
        line_type- dayside, north or south from tail
    Outputs
        isclosed- boolean, True for closed
    """
    # Get starting and endpoints of streamzone
    r_values = field_data.zone(zone_name+'*').values('r *').as_numpy_array()
    if line_type == 'north':
        r_end_n = r_values[-1]
        r_end_s = 0
        r_seed = 2
    elif line_type == 'south':
        r_end_n = 0
        r_end_s = r_values[0]
        r_seed = 2
    elif line_type == 'inner_mag':
        xmax, xmin = field_data.zone(zone_name+'*').values('X *').minmax()
        ymax, ymin = field_data.zone(zone_name+'*').values('Y *').minmax()
        zmax, zmin = field_data.zone(zone_name+'*').values('Z *').minmax()
        extrema = [[xmax, ymax, zmax],
                   [xmin, ymin, zmin]]
        bounds = [[-220,-126,-126],
                  [31.5, 126, 126]]
        isclosed = True
        for minmax in enumerate(extrema):
            for value in enumerate(minmax[1]):
                if abs(value[1])>0.9*abs(bounds[minmax[0]][value[0]]):
                    isclosed = False
                    return isclosed
        return isclosed
    elif line_type == 'flowline':
        rmin = field_data.zone(zone_name+'*').values('r *').min()
        if rmin < r_seed:
            isclosed = True
            return isclosed
        else:
            isclosed = False
            return isclosed
    else:
        r_end_n, r_end_s = r_values[0], r_values[-1]
    #check if closed
    if (r_end_n > r_seed) or (r_end_s > r_seed):
        isclosed = False
    else:
        isclosed = True
    return isclosed

def sph_to_cart(radius, lat, lon):
    """Function converts spherical coordinates to cartesian coordinates
    Inputs
        radius- radial position
        lat- latitude [deg]
        lon- longitude [deg]
    Outputs
        [x_pos, y_pos, z_pos]- list of x y z_pos coordinates
    """
    x_pos = (radius * cos(deg2rad(lat)) * cos(deg2rad(lon)))
    y_pos = (radius * cos(deg2rad(lat)) * sin(deg2rad(lon)))
    z_pos = (radius * sin(deg2rad(lat)))
    return [x_pos, y_pos, z_pos]
def mag2gsm(x1, x2, x3, time, *, inputtype='sph'):
    """Function converts magnetic spherical coordinates to cartesian
        coordinates in GSM
    Inputs
        if inputtype='sph':
            x1,x2,x3- radius, latitue and longitude
        if inputtype='car':
            x1,x2,x3- x,y,z
        time- spacepy Ticktock object with time information
    Output
        xgsm, ygsm, zgsm- in form of 3 element np array
    """
    coordinates = coord.Coords([radius, latitude, longitude], 'SM',
                               inputtype)
    coordinates.ticks = time
    return coordinates.convert('GSM', 'car').data[0][0:3]

'''
def sm2gsm_temp(radius, latitude, longitude, time):
    """Function converts solar magnetic spherical coordinates to cartesian
        coordinates in GSM
    Inputs
        radius
        latitude- relative to magnetic dipole axis
        longitude- relative to magnetic dipole axis
        time- spacepy Ticktock object with time information
    Output
        xgsm, ygsm, zgsm- in form of 3 element np array
    """
    xsm = radius * cos(deg2rad(latitude))*cos(deg2rad(longitude))
    ysm = radius * cos(deg2rad(latitude))*sin(deg2rad(longitude))
    zsm = radius * sin(deg2rad(latitude))
    #Read from file generated using spacepy, temp fix only
    dpdf = pd.read_csv('dipole_loc.csv')
    xdp = dpdf[dpdf['time'] == str(time.data[0])][' xgsm'].values[0]
    ydp = dpdf[dpdf['time'] == str(time.data[0])][' ygsm'].values[0]
    zdp = dpdf[dpdf['time'] == str(time.data[0])][' zgsm'].values[0]
    mu = np.arctan2(-xdp, np.sqrt(zdp**2+ydp**2))
    Tmat = rotation(-mu, 'y')
    #getTmat function give similar results but not identical
    #Tmat = getTmat(time)
    xgsm, ygsm, zgsm = np.matmul(Tmat, [[xsm], [ysm], [zsm]])
    return xgsm[0], ygsm[0], zgsm[0]
'''

def getTmat(time):
    """Function takes spacepy ticktock object and returns trans matrix
    Inputs
        time
    Output
        T4_t - transformation matrix for sm2gsm
    """
    '''
    y2k = dt.datetime(2000,1,1,12)
    y2ktick = spacetime.Ticktock(y2k, 'UTC')
    T0 = time.getUNX()[0] - y2ktick.getUNX()[0]
    '''
    MJD = time.getMJD()[0]
    T0 = (MJD-51544.5)/36525
    theta = deg2rad(100.461+36000.770*T0+15.04107)
    eps = deg2rad(23.439-0.013*T0)
    M = 357.528+35999.05*T0+0.04107
    lam = 280.460+36000.772*T0+0.04107
    lam_sun = deg2rad(lam+(1.915-0.0048*T0)*sin(M)+0.02*sin(2*M))
    T1 = rotation(theta, 'z')
    T2 = np.matmul(rotation(lam_sun, 'z'), rotation(eps, 'x'))
    xg = cos(deg2rad(287.45))*cos(deg2rad(80.25))
    yg = cos(deg2rad(287.45))*sin(deg2rad(80.25))
    zg = sin(deg2rad(287.45))
    T = np.matmul(T2, np.transpose(T1))
    xe, ye, ze = np.matmul(T, [[xg], [yg], [zg]])
    mu = np.arctan2(-xe,np.sqrt(ye**2+ze**2))
    T4_t = np.transpose(rotation(-mu[0], 'y'))
    return T4_t

def rotation(angle, axis):
    """Function returns rotation matrix given axis and angle
    Inputs
        angle
        axis
    Outputs
        matrix
    """
    if axis == 'x' or axis == 'X':
        matrix = [[1,           0,          0],
                  [0,  cos(angle), sin(angle)],
                  [0, -sin(angle), cos(angle)]]
    elif axis == 'y' or axis == 'Y':
        matrix = [[ cos(angle), 0, sin(angle)],
                  [0,           1,          0],
                  [-sin(angle), 0, cos(angle)]]
    elif axis == 'z' or axis == 'Z':
        matrix = [[ cos(angle), sin(angle), 0],
                  [-sin(angle), cos(angle), 0],
                  [0,           0,          1]]
    return matrix

def get_lateral_arc(zone, last_angle, last_r, method, *, dx=1):
    '''Function to calculate lateral angle, used to ensure coverage in the
        tail when seeding streams on the dayside
    Inputs
        zone- streamzone to probe values from
        last_angle
        last_r
        method- flow, day, tail, cps determines how to define r
    Outputs
        l_arc defined by dangle*mean_r
        rnew same as mean_r
        angle
    '''
    xzonevals = zone.values('X *').as_numpy_array()
    yzonevals = zone.values('Y *').as_numpy_array()
    zzonevals = zone.values('Z *').as_numpy_array()
    if method == 'dayside':
        dayindices = np.where((zzonevals>-dx/2)&
                              (zzonevals<dx/2))
        yave_day = yzonevals[dayindices].mean()
        xave_day = zzonevals[dayindices].mean()
        angle = np.rad2deg(np.arctan2(yave_day,xave_day))
        r = np.sqrt(yave_day**2+xave_day**2)
    if (method == 'flow') or (method == 'tail'):
        xzonevals = zone.values('X *').as_numpy_array()
        yzonevals = zone.values('Y *').as_numpy_array()
        zzonevals = zone.values('Z *').as_numpy_array()
        tail_indices = np.where((xzonevals>-10-dx/2)&
                                (xzonevals<-10+dx/2))
        yave_tail = yzonevals[tail_indices].mean()
        zave_tail = zzonevals[tail_indices].mean()
        angle = np.rad2deg(np.arctan2(zave_tail,yave_tail))
        r = np.sqrt(yave_tail**2+zave_tail**2)
    dangle = deg2rad(abs(angle-last_angle))
    mean_r = abs(r-last_r)/2
    return dangle * mean_r, mean_r, angle

def streamfind_bisection(field_data, method,
                         dimmax, nstream, rmax, rmin, itr_max, tolerance,
                         *, rcheck=7, time=None,
                         field_key_x='B_x*', global_key='global_field',
                         disp_search=False):
    """Generalized function for generating streamlines for a 'last closed'          condition based on a bisection algorithm
    Inputs
        General
            field_data- Tecplot Dataset with flowfield information
            method- 'dayside', 'tail', 'flow', or 'plasmasheet'
        Parameters
            dimmmax- X location for tail/flow, maxextent for
                     dayside/plasmasheet
            nstream- number of streamlines to generate
            rmax, rmin- outer/inner bounds of search in whichever direction
            itr_max, tolerance- bisection alg settings
        Special
            rcheck- consideration for "closed" for 'flow' method only
            time- spacepy Ticktock of current time for 'plasmasheet' only
        Other
            field_key_x- string ID for x var to be traced, y&z assumed
            global_key- string ID for zone containing field data
    Outputs
       zonelist- list of indices of created zones
    """
    #validate method form
    approved_methods = ['dayside', 'tail', 'flow', 'plasmasheet']
    reverse_if_flow = 0
    if all([test.find(method)==-1 for test in approved_methods]):
        print('WARNING: method for streamfind_bisection not recognized!!'+
              '\nno streamzones created')
        return None

    #set streamline seed positions in the fixed dimension
    if method == 'dayside':
        #set of points in z=0 plane from + to - dimmax angle from +x ax
        positions = np.linspace(-1*dimmax, dimmax, nstream)
        disp_message = 'Finding Magnetopause Dayside Field Lines'
        lin_type = 'dayside'
    elif (method == 'tail') or (method == 'flow'):
        #set of points 360deg around disc in the tail at x=dimmax
        positions = np.linspace(-180*(1-1/nstream), 180, nstream)
        if method == 'tail':
            disp_message = 'Finding Magnetopause Tail Field Lines'
        elif method == 'flow':
            disp_message = 'Finding Magnetopause Flow Lines'
            lin_type = 'flowline'
            reverse_if_flow = 1
    elif method == 'plasmasheet':
        #set of points on r=1Re at different longitudes N and S poles
        positions = np.append(np.linspace(-dimmax, -180,int(nstream/4)),
                              np.linspace(180, dimmax, int(nstream/4)))
        disp_message = 'Finding Plasmasheet Field Lines'
        lin_type = 'inner_mag'

    #set vector field
    field_key_y = field_key_x.split('x')[0]+'y'+field_key_x.split('x')[-1]
    field_key_z = field_key_x.split('x')[0]+'z'+field_key_x.split('x')[-1]
    plot = tp.active_frame().plot()
    plot.vector.u_variable = field_data.variable(field_key_x)
    plot.vector.v_variable = field_data.variable(field_key_y)
    plot.vector.w_variable = field_data.variable(field_key_z)

    bar = Bar(disp_message, max=len(positions))
    seedlist = []
    streamtrace = tp.active_frame().plot().streamtraces
    for a in positions:
        notfound = True
        #Set getseed function based only on search variable r
        #all getseeds return val: dim1, dim2, dim3,rcheck,lin_type
        if method == 'dayside':
            def getseed(r):return r, 0, a, r, lin_type
            cartesian = False
        elif method == 'tail':
            def getseed(r):
                x, y, z = dimmax, r*cos(deg2rad(a)), r*sin(deg2rad(a))
                if tp.data.query.probe_at_position(x, y, z)[0][7] < 0:
                    lin_type = 'south'
                else:
                    lin_type = 'north'
                return [dimmax, r*cos(deg2rad(a)), r*sin(deg2rad(a)),
                        rcheck, lin_type]
            cartesian = True
        elif method == 'flow':
            def getseed(r):
                return [dimmax, r*cos(deg2rad(a)), r*sin(deg2rad(a)),
                        rcheck, lin_type]
            cartesian = True
        elif method == 'plasmasheet':
            def getseed(r):return (sm2gsm_temp(1, r, a, time), None,
                                    lin_type)
            cartesian = True
        #Create initial max/min to lines
        x1, x2, x3, rchk, lin_type = getseed(rmax)
        create_stream_zone(field_data, x1, x2, x3,
                            'max line',
                            cart_given=cartesian)
        x1, x2, x3, rchk, lin_type = getseed(rmin)
        create_stream_zone(field_data, x1, x2, x3,
                            'min line',
                            cart_given=cartesian)
        #Check that last closed is bounded, delete min/max
        max_closed = check_streamline_closed(field_data, 'max*', rchk,
                                            line_type=lin_type)
        min_closed = check_streamline_closed(field_data, 'min*', rchk,
                                            line_type=lin_type)
        field_data.delete_zones(field_data.zone('min*'),
                                field_data.zone('max*'))
        if max_closed and min_closed:
            notfound = False
            print('Warning: line closed at {}'.format(rmax))
        elif not max_closed and not min_closed:
            notfound = False
            print('Warning: line open at {}'.format(rmin))
        else:
            rmid = (rmax+rmin)/2
            itr = 0
            rout = rmax
            rin = rmin
            #Enter bisection search algorithm
            while(notfound and itr < itr_max):
                #create mid
                x1, x2, x3, rchk, lin_type = getseed(rmid)
                create_stream_zone(field_data, x1, x2, x3,
                                    'mid line',
                                    cart_given=cartesian)
                #check midclosed
                mid_closed = check_streamline_closed(field_data,
                                                        'mid*', rchk,
                                                    line_type=lin_type)
                if mid_closed:
                    rin = rmid
                else:
                    rout = rmid
                if abs(rout-rin) < tolerance and (bool(
                                    int(mid_closed)-reverse_if_flow)):
                    #keep closed on boundary unless in 'flowline' method
                    notfound = False
                    field_data.delete_zones(field_data.zone(-1))
                else:
                    rmid = (rin+rout)/2
                    field_data.delete_zones(field_data.zone(-1))
                itr += 1
        seedlist.append([x1,x2,x3])
        bar.next()
    #Regenerate all best find streamlines and extracting together
    for seed in seedlist:
        if cartesian == False:
            seed = sph_to_cart(seed[0],seed[1],seed[2])
        print(seed)
        streamtrace.add(seed_point=seed,
                       stream_type=Streamtrace.VolumeLine,
                       direction=StreamDir.Both)
    streamtrace.extract(concatenate=True)
    field_data.zone(-1).name = lin_type+'stream'
    zoneindex = field_data.zone(-1).index
    streamtrace.delete_all()
    return zoneindex

def dump_to_pandas(frame, zonelist, varlist, filename):
    """Function to hand zone data to pandas to do processing
    Inputs-
        frame- tecplot frame object to export
        zonelist- array like object of which zones to export
        varlist- which variables
        filename
    Outputs-
        loc_data- DataFrame of stream zone data
        x_max
    """
    frame.activate()
    os.system('touch '+filename)
    #Export 3D point data to csv file
    tp.macro.execute_extended_command(command_processor_id='excsv',
            command='VarNames:'+
                    'FrOp=1:'+
                    'ZnCount={:d}:'.format(len(zonelist))+
                    'ZnList=[{:d}-{:d}]:'.format(int(zonelist[0]+1),
                                                 int(zonelist[-1])+1)+
                    'VarCount={:d}:'.format(len(varlist))+
                    'VarList=[{:d}-{:d}]:'.format(int(varlist[0]),
                                                  int(varlist[-1]))+
                    'ValSep=",":'+
                    'FNAME="'+os.getcwd()+'/'+filename+'"')
    loc_data = pd.read_csv(filename)
    if any(col == 'X [R]' for col in loc_data.columns):
        loc_data = loc_data.drop(columns=['Unnamed: 3'])
        loc_data = loc_data.sort_values(by=['X [R]'])
        loc_data = loc_data.reset_index(drop=True)
        x_max = loc_data['X [R]'].max()
    else: x_max = []
    #Delete csv file
    os.system('rm '+os.getcwd()+'/'+filename)
    return loc_data, x_max


def get_surface_variables(field_data, zone_name):
    """Function calculated variables for a specific 3D surface
    Inputs
        field_data, zone_name
    """
    zone_index = field_data.zone(zone_name).index
    #Get grid dependent variables
    tp.macro.execute_extended_command('CFDAnalyzer3',
                                      'CALCULATE FUNCTION = '+
                                      'GRIDKUNITNORMAL VALUELOCATION = '+
                                      'CELLCENTERED')
    tp.macro.execute_extended_command('CFDAnalyzer3',
                                      'CALCULATE FUNCTION = '+
                                      'CELLVOLUME VALUELOCATION = '+
                                      'CELLCENTERED')
    eq = tp.data.operate.execute_equation
    eq('{x_cc}={X [R]}', value_location=ValueLocation.CellCentered)
    xvalues = field_data.zone(zone_name).values('x_cc').as_numpy_array()
    xnormals = field_data.zone(zone_name).values(
                                  'X GRID K Unit Normal').as_numpy_array()
    df = pd.DataFrame({'x':xvalues,'normal':xnormals})
    #Check that surface normals are pointing outward from surface
    if (len(df[(df['x']==df['x'].min())&(df['normal']>0)]) >
        len(df[(df['x']==df['x'].min())&(df['normal']<0)])):
        eq('{surface_normal_x} = -1*{X Grid K Unit Normal}')
        eq('{surface_normal_y} = -1*{Y Grid K Unit Normal}')
        eq('{surface_normal_z} = -1*{Z Grid K Unit Normal}')
    else:
        eq('{surface_normal_x} = {X Grid K Unit Normal}')
        eq('{surface_normal_y} = {Y Grid K Unit Normal}')
        eq('{surface_normal_z} = {Z Grid K Unit Normal}')
    ######################################################################
    #Normal Total Energy Flux
    eq('{ExB_net [W/Re^2]} = ({ExB_x [W/Re^2]}*{surface_normal_x}'+
                            '+{ExB_y [W/Re^2]}*{surface_normal_y}'+
                            '+{ExB_z [W/Re^2]}*{surface_normal_z})',
        value_location=ValueLocation.CellCentered,
        zones=[zone_index])

    #Split into + and - flux
    eq('{ExB_escape} = max({ExB_net [W/Re^2]},0)',
        value_location=ValueLocation.CellCentered,
        zones=[zone_index])
    eq('{ExB_injection} = min({ExB_net [W/Re^2]},0)',
        value_location=ValueLocation.CellCentered,
        zones=[zone_index])
    ######################################################################
    #Normal Total Pressure Flux
    eq('{P0_net [W/Re^2]} = ({P0_x [W/Re^2]}*{surface_normal_x}'+
                            '+{P0_y [W/Re^2]}*{surface_normal_y}'+
                            '+{P0_z [W/Re^2]}*{surface_normal_z})',
        value_location=ValueLocation.CellCentered,
        zones=[zone_index])

    #Split into + and - flux
    eq('{P0_escape} = max({P0_net [W/Re^2]},0)',
        value_location=ValueLocation.CellCentered,
        zones=[zone_index])
    eq('{P0_injection} = min({P0_net [W/Re^2]},0)',
        value_location=ValueLocation.CellCentered,
        zones=[zone_index])
    ######################################################################
    #Normal Total Energy Flux
    eq('{K_net [W/Re^2]} = ({K_x [W/Re^2]}*{surface_normal_x}'+
                            '+{K_y [W/Re^2]}*{surface_normal_y}'+
                            '+{K_z [W/Re^2]}*{surface_normal_z})',
        value_location=ValueLocation.CellCentered,
        zones=[zone_index])

    #Split into + and - flux
    eq('{K_escape} = max({K_net [W/Re^2]},0)',
        value_location=ValueLocation.CellCentered,
        zones=[zone_index])
    eq('{K_injection} = min({K_net [W/Re^2]},0)',
        value_location=ValueLocation.CellCentered,
        zones=[zone_index])


def get_global_variables(field_data):
    """Function calculates values for energetics tracing
    Inputs
        field_data- tecplot Dataset class containing 3D field data
    """
    eq = tp.data.operate.execute_equation
    #Useful spatial variables
    eq('{r [R]} = sqrt({X [R]}**2 + {Y [R]}**2 + {Z [R]}**2)')
    eq('{h} = sqrt({Y [R]}**2+{Z [R]}**2)')
    eq('{theta} = IF({X [R]}>0,atan({h}/{X [R]}), pi-atan({h}/{X [R]}))')
    eq('{lat [deg]} = 180/pi*asin({Z [R]} / {r [R]})')
    eq('{lon [deg]} = if({X [R]}>0, 180/pi*atan({Y [R]} / {X [R]}),'+
                     'if({Y [R]}>0, 180/pi*atan({Y [R]}/{X [R]})+180,'+
                                   '180/pi*atan({Y [R]}/{X [R]})-180))')
    #Dynamic Pressure
    eq('{Dp [nPa]} = {Rho [amu/cm^3]}*1e6*1.6605e-27*'+
              '({U_x [km/s]}**2+{U_y [km/s]}**2+{U_z [km/s]}**2)*1e6*1e9',
        value_location=ValueLocation.CellCentered)
    #Plasma Beta
    eq('{beta}=({P [nPa]})/({B_x [nT]}**2+{B_y [nT]}**2+{B_z [nT]}**2)'+
                '*(2*4*pi*1e-7)*1e9')
    #Plasma Beta* using total pressure
    eq('{beta_star}=({P [nPa]}+{Dp [nPa]})/'+
                          '({B_x [nT]}**2+{B_y [nT]}**2+{B_z [nT]}**2)'+
                '*(2*4*pi*1e-7)*1e9')

    #Magnetic field unit vectors
    eq('{bx} ={B_x [nT]}/sqrt({B_x [nT]}**2+{B_y [nT]}**2+{B_z [nT]}**2)')
    eq('{by} ={B_y [nT]}/sqrt({B_x [nT]}**2+{B_y [nT]}**2+{B_z [nT]}**2)')
    eq('{bz} ={B_z [nT]}/sqrt({B_x [nT]}**2+{B_y [nT]}**2+{B_z [nT]}**2)')
    eq('{Bmag [nT]} =sqrt({B_x [nT]}**2+{B_y [nT]}**2+{B_z [nT]}**2)',
        value_location=ValueLocation.CellCentered)
    '''
    eq('{divB [nT/Re]} =IF({r [R]}>4,'+
                     'ddx({B_x [nT]})+ddy({B_y [nT]})+ddz({B_z [nT]}),0)',
        value_location=ValueLocation.CellCentered)
    eq('{bdotu}= ({B_x [nT]}*{U_x [km/s]}+'+
                 '{B_y [nT]}*{U_y [km/s]}+'+
                 '{B_z [nT]}*{U_z [km/s]}*(4*pi*1e2))',
        value_location=ValueLocation.CellCentered)
        variable_data_type=FieldDataType.Double)
    eq('{S [W]} = {divB [nT/Re]}*{bdotu}*6371**2',
        value_location=ValueLocation.CellCentered)
    #eq('{F2 [W/Re^3]} = ({B_x [nT]}*ddx({bdotu})+'+
                        '{B_y [nT]}*ddy({bdotu})+'+
                        '{B_z [nT]}*ddz({bdotu}))*6371**2')
    '''

    #Magnetic Energy per volume
    eq('{uB [J/Re^3]} = ({B_x [nT]}**2+{B_y [nT]}**2+{B_z [nT]}**2)'+
                        '/(2*4*pi*1e-7)*(1e-9)**2*1e9*6371**3',
        value_location=ValueLocation.CellCentered)

    #Ram pressure energy per volume
    eq('{KEpar [J/Re^3]} = {Rho [amu/cm^3]}/2 *'+
                                    '(({U_x [km/s]}*{bx})**2+'+
                                    '({U_y [km/s]}*{by})**2+'+
                                    '({U_z [km/s]}*{bz})**2) *'+
                                    '1e6*1.6605e-27*1e6*1e9*6371**3',
        value_location=ValueLocation.CellCentered)
    eq('{KEperp [J/Re^3]} = {Rho [amu/cm^3]}/2 *'+
                          '(({U_y [km/s]}*{bz} - {U_z [km/s]}*{by})**2+'+
                           '({U_z [km/s]}*{bx} - {U_x [km/s]}*{bz})**2+'+
                           '({U_x [km/s]}*{by} - {U_y [km/s]}*{bx})**2)'+
                                       '*1e6*1.6605e-27*1e6*1e9*6371**3',
        value_location=ValueLocation.CellCentered)

    #Electric Field
    eq('{E_x [mV/km]} = ({U_z [km/s]}*{B_y [nT]}'+
                          '-{U_y [km/s]}*{B_z [nT]})',
        value_location=ValueLocation.CellCentered)
    eq('{E_y [mV/km]} = ({U_x [km/s]}*{B_z [nT]}'+
                         '-{U_z [km/s]}*{B_x [nT]})',
        value_location=ValueLocation.CellCentered)
    eq('{E_z [mV/km]} = ({U_y [km/s]}*{B_x [nT]}'+
                         '-{U_x [km/s]}*{B_y [nT]})',
        value_location=ValueLocation.CellCentered)

    #Electric Energy per volume
    eq('{uE [J/Re^3]} = ({E_x [mV/km]}**2+{E_y [mV/km]}**2+'+
                        '{E_z [mV/km]}**2)*'+
                        '1e-6/(2*4*pi*1e-7*(3e8)**2)*1e9*6371**3',
        value_location=ValueLocation.CellCentered)

    #Poynting Flux
    # E (m⋅kg⋅s−3⋅A−1)*1e-6 * B ( 1 kg⋅s−2⋅A−1)*1e-9 * 1/mu0 (A2/N)*4pie7
    # (kg2 m)/(s5 N)
    # (kg m/s2) (kg)/ (s3 N)
    # (kg) / (s3)
    # (kg m/s2) / (s m)
    # (W / m)
    # km/s  nT  nT  1/mu0   Re^2
    # 1e6   1e-9 1e-9 1e7/4pi 6371^2 1e6
    # 19-18
    eq('{ExB_x [W/Re^2]} = -1e-2/(4*pi)*6371**2*'+
                            '({E_z [mV/km]}*{B_y [nT]}'+
                            '-{E_y [mV/km]}*{B_z [nT]})',
        value_location=ValueLocation.CellCentered)
    eq('{ExB_y [W/Re^2]} = -1e-2/(4*pi)*6371**2*'+
                            '({E_x [mV/km]}*{B_z [nT]}'+
                            '-{E_z [mV/km]}*{B_x [nT]})',
        value_location=ValueLocation.CellCentered)
    eq('{ExB_z [W/Re^2]} = -1e-2/(4*pi)*6371**2*'+
                            '({E_y [mV/km]}*{B_x [nT]}'+
                            '-{E_x [mV/km]}*{B_y [nT]})',
        value_location=ValueLocation.CellCentered)
    '''
    eq('{ExB_z [W/Re^2]} = -3.22901e4*({E_y [mV/km]}*{B_x [nT]}'+
                                       '-{E_x [mV/km]}*{B_y [nT]})')
    '''

    #Total pressure Flux
    eq('{P0_x [W/Re^2]} = ({P [nPa]}*(2.5)+{Dp [nPa]})*6371**2'+
                          '*{U_x [km/s]}',
        value_location=ValueLocation.CellCentered)
    eq('{P0_y [W/Re^2]} = ({P [nPa]}*(2.5)+{Dp [nPa]})*6371**2'+
                          '*{U_y [km/s]}',
        value_location=ValueLocation.CellCentered)
    eq('{P0_z [W/Re^2]} = ({P [nPa]}*(2.5)+{Dp [nPa]})*6371**2'+
                          '*{U_z [km/s]}',
        value_location=ValueLocation.CellCentered)
    '''
    eq('{P0_z [W/Re^2]} = ({P [nPa]}*(1.666667/0.666667)*2.585e11'+
                                        '+4.2941e5*{Rho [amu/cm^3]}/2*'+
                                                    '({U_x [km/s]}**2'+
                                                    '+{U_y [km/s]}**2'+
                                                    '+{U_z [km/s]}**2))'+
                          '*1.5696123057605e-4*{U_z [km/s]}')
    '''
    #Total Energy Flux
    eq('{K_x [W/Re^2]} = {P0_x [W/Re^2]}+{ExB_x [W/Re^2]}',
        value_location=ValueLocation.CellCentered)
    eq('{K_y [W/Re^2]} = {P0_y [W/Re^2]}+{ExB_y [W/Re^2]}',
        value_location=ValueLocation.CellCentered)
    eq('{K_z [W/Re^2]} = {P0_z [W/Re^2]}+{ExB_z [W/Re^2]}',
        value_location=ValueLocation.CellCentered)

def integrate_surface(var_index, zone_index, *, VariableOption='Scalar'):
    """Function to calculate integral of variable on a 3D exterior surface
    Inputs
        var_index- variable to be integrated
        zone_index- index of the zone to perform integration
        VariableOption- default scalar, can choose others
    Output
        integrated_total from result dataframe
    """
    #setup integration command
    integrate_command=("Integrate [{:d}] ".format(zone_index+1)+
                         "VariableOption="+VariableOption+" ")
    if VariableOption == 'Scalar':
        integrate_command = (integrate_command+
                         "ScalarVar={:d} ".format(var_index+1))
    integrate_command = (integrate_command+
                         "XVariable=1 "+
                         "YVariable=2 "+
                         "ZVariable=3 "+
                         "ExcludeBlanked='T' "+
                         " PlotResults='F' ")
    #integrate
    tp.macro.execute_extended_command(command_processor_id='CFDAnalyzer4',
                                      command=integrate_command)
    #access data via file write out then delete file
    filename = os.getcwd()+'/Out.txt'
    tp.macro.execute_extended_command(command_processor_id='CFDAnalyzer4',
        command='SaveIntegrationResults FileName="'+filename+'"')
    result = pd.read_table('./Out.txt', sep=':',index_col=0)
    os.system('rm {}'.format(filename))
    return result.iloc[-1].values[0]

def integrate_volume(var_index, zone_index, *, VariableOption='Scalar'):
    """Function to calculate integral of variable within a 3D volume
    Inputs
        var_index- variable to be integrated
        zone_index- index of the zone to perform integration
        VariableOption- default scalar, can choose others
    Output
        integral
    """
    #Setup macrofunction command
    integrate_command=("Integrate [{:d}] ".format(zone_index+1)+
                       "VariableOption={} ".format(VariableOption))
    if VariableOption == 'Scalar':
        integrate_command = (integrate_command+
                       "ScalarVar={:d} ".format(var_index+1))
    integrate_command = (integrate_command+
                       "XVariable=1 "+
                       "YVariable=2 "+
                       "ZVariable=3 "+
                       "ExcludeBlanked='T' "+
                       "IntegrateOver='Cells' "+
                       "IntegrateBy='Zones' "+
                       "PlotResults='F' ")
    #Perform integration and extract resultant value
    tp.macro.execute_extended_command(command_processor_id='CFDAnalyzer4',
                                      command=integrate_command)
    filename = os.getcwd()+'/Out.txt'
    tp.macro.execute_extended_command(command_processor_id='CFDAnalyzer4',
        command='SaveIntegrationResults FileName="'+filename+'"')
    result = pd.read_table('./Out.txt', sep=':',index_col=0)
    integral = result.iloc[-1].values[0]

    #Delete created file and turn off blanking
    os.system('rm Out.txt')
    return integral

def setup_isosurface(iso_value, varindex, contindex, isoindex, zonename):
    """Function creates an isosurface and then extracts and names the zone
    Inputs
        iso_value
        varindex, contindex, isoindex- storage locations on tecplot side
        zonename
    Outputs
        newzone
    """
    frame = tp.active_frame()
    frame.plot().show_isosurfaces = True
    iso = frame.plot().isosurface(isoindex)
    iso.show = True
    iso.definition_contour_group_index = contindex
    frame.plot().contour(contindex).variable_index = varindex
    iso.isosurface_values[0] = iso_value
    print('creating isosurface of {}={:.2f}'.format(
                                    frame.dataset.variable(varindex).name,
                                    iso_value))
    orig_nzones = frame.dataset.num_zones
    tp.macro.execute_command('$!ExtractIsoSurfaces Group = {:d} '.format(
                                                              isoindex+1)+
                             'ExtractMode = OneZonePerConnectedRegion')
    iso.show = False
    #only keep zone with the highest number of elements
    nelements = 0
    for i in range(orig_nzones, frame.dataset.num_zones):
        if len(frame.dataset.zone(i).values('X *')) > nelements:
            nelements = len(frame.dataset.zone(i).values('X *'))
            keep_index = i
    for i in reversed(range(orig_nzones, frame.dataset.num_zones)):
        if i != keep_index:
            frame.dataset.delete_zones(i)
        else:
            newzone_key = frame.dataset.zone(i).name
    newzone = frame.dataset.zone(newzone_key)
    newzone.name = zonename
    return newzone

def calc_transition_rho_state(xmax, xmin, hmax, rhomax, rhomin, uBmin):
    """Function creates equation in tecplot representing surface
    Inputs
        xmax, xmin, hmax, hmin, rmin- spatial bounds
        rhomax- density bound
    Outputs
        created variable index
    """
    drho = rhomax-rhomin
    eq = tp.data.operate.execute_equation
    eq('{mp_rho_transition} = '+
        'IF({X [R]} >'+str(xmin)+' &&'+
        '{X [R]} <'+str(xmax)+' && {h} < '+str(hmax)+','+
           'IF({Rho [amu/cm^3]}<(atan({X [R]}+5)+pi/2)/pi*'+str(drho)+'+'+
            str(rhomin)+'||({uB [J/Re^3]}>'+str(uBmin)+'), 1, 0), 0)')
    return tp.active_frame().dataset.variable('mp_rho_transition').index

def calc_betastar_state(zonename, xmax, xmin, hmax, betamax, core,
                        coreradius, closed_zone):
    """Function creates equation in tecplot representing surface
    Inputs
        zonename
        xmax, xmin, hmax, hmin, rmin- spatial bounds
        rhomax- density bound
        core- boolean for including the inner boundary in domain, used to
                isolate effects on outer boundary only
        closed_zone- zone object, None to omit closed zone in equation
    Outputs
        created variable index
    """
    eq = tp.data.operate.execute_equation
    eqstr = ('{'+zonename+'} = '+
        'IF({X [R]} >'+str(xmin-2)+'&&'+
        '{X [R]} <'+str(xmax)+'&& {h} < '+str(hmax))
    if core == False:
        eqstr =(eqstr+'&& {r [R]} > '+str(coreradius))
    eqstr = (eqstr+',IF({beta_star}<'+str(betamax)+',1,')
    if type(closed_zone) != type(None):
        print(closed_zone)
        eqstr =(eqstr+'IF({'+closed_zone.name+'} == 1,1,0))')
    else:
        eqstr =(eqstr+'0)')
    eqstr =(eqstr+',0)')
    eq(eqstr)
    return tp.active_frame().dataset.variable(zonename).index

def calc_iso_rho_state(xmax, xmin, hmax, rhomax, rmin_north, rmin_south):
    """Function creates equation in tecplot representing surface
    Inputs
        xmax, xmin, hmax, hmin, rmin- spatial bounds
        rhomax- density bound
    Outputs
        created variable index
    """
    eq = tp.data.operate.execute_equation
    eq('{mp_rho_innerradius} = '+
        'IF({X [R]} >'+str(xmin-2)+'&&'+
        '{X [R]} <'+str(xmax)+'&& {h} < '+str(hmax)+','+
            'IF({Rho [amu/cm^3]}<'+str(rhomax)+', 1,'+
                'IF(({r [R]} <'+str(rmin_north)+'&&{Z [R]}>0)||'+
                   '({r [R]} <'+str(rmin_south)+'&&{Z [R]}<0),1,0)),0)')
    return tp.active_frame().dataset.variable('mp_rho_innerradius').index

def calc_shue_state(field_data, mode, x_subsolar, xtail, *, dx=10):
    """Function creates state variable for magnetopause surface based on
        Shue emperical model
    Inputs
        field_data
        mode
        x_subsolar- if None will calculate with dayside fieldlines
        xtail- limit for how far to extend in negative x direction
    Outputs
        state_var_index- index to find state variable in tecplot
    """
    #Probe field data at x_subsolar + dx to find Bz and Dp
    Bz = tp.data.query.probe_at_position(x_subsolar+dx,0,0)[0][9]
    Dp_index = field_data.variable('Dp *').index
    Dp = tp.data.query.probe_at_position(x_subsolar+dx,0,0)[0][Dp_index]
    #Get r0 and alpha based on IMF conditions
    if mode == 'shue97':
        r0, alpha = r0_alpha_1997(Bz, Dp)
    else:
        r0, alpha = r0_alpha_1998(Bz, Dp)
    eq = tp.data.operate.execute_equation
    eq('{r'+mode+'} = '+str(r0)+'*(2/(1+cos({theta})))**'+str(alpha))
    eq('{'+mode+'} = IF(({r [R]} < {r'+mode+'}) &&'+
                      '({X [R]} > '+str(xtail)+'), 1, 0)')
    return field_data.variable(mode).index

def calc_sphere_state(mode, xc, yc, zc, rmin):
    """Function creates state variable for a simple box
    Inputs
        mode
        xc, yc, zc- locations for sphere center
        rmin- sphere radius
    Outputs
        state_var_index- index to find state variable in tecplot
    """
    eq = tp.data.operate.execute_equation
    eq('{'+mode+'} = IF(sqrt(({X [R]} -'+str(xc)+')**2 +'+
                            '({Y [R]} -'+str(yc)+')**2 +'+
                            '({Z [R]} -'+str(zc)+')**2) <'+
                             str(rmin)+', 1, 0)')
    return tp.active_frame().dataset.variable(mode).index

def calc_closed_state(status_key, status_val):
    """Function creates state variable for the closed fieldline region
    Inputs
        status_key/val-string key and value used to denote closed fldlin
    Outputs
        state_var_index- index to find state variable in tecplot
    """
    eq = tp.data.operate.execute_equation
    eq('{Bclosed} = IF({'+status_key+'}=='+str(status_val)+',1,0)')
    return tp.active_frame().dataset.variable('Bclosed').index

def calc_box_state(mode, xmax, xmin, ymax, ymin, zmax, zmin):
    """Function creates state variable for a simple box
    Inputs
        mode
        xmax,xmin...zmin- locations for box vertices
    Outputs
        state_var_index- index to find state variable in tecplot
    """
    eq = tp.data.operate.execute_equation
    eq('{'+mode+'} = IF(({X [R]} >'+str(xmin)+') &&'+
                       '({X [R]} <'+str(xmax)+') &&'+
                       '({Y [R]} >'+str(ymin)+') &&'+
                       '({Y [R]} <'+str(ymax)+') &&'+
                       '({Z [R]} >'+str(zmin)+') &&'+
                       '({Z [R]} <'+str(zmax)+'), 1, 0)')
    return tp.active_frame().dataset.variable(mode).index

def abs_to_timestamp(abstime):
    """Function converts absolute time in sec to a timestamp list
    Inputs
        abstime
    Outpus
        timestamp
    """
    secyear = 60*60*24*12*30
    year = np.floor(abstime/secyear)
    month = np.floor((abstime/secyear-year)*12)
    day = np.floor((((abstime/secyear-year)*12)-month)*30)
    hour = np.floor((((((abstime/secyear-year)*12)-month)*30)-day)*24)
    minute = np.floor((((((((abstime/secyear-year)*12)-month)*30)
                             -day)*24)-hour)*60)
    second = np.floor((((((((((abstime/secyear-year)*12)-month)*30)
                             -day)*24)-hour)*60)-minute)*60)
    timestamp = [year, month, day, hour, minute, second, abstime]
    return timestamp

def write_to_timelog(timelogname, time, data):
    """Function for writing the results from the current file to a file that contains time integrated data
    Inputs
        timelogname
        time- datetime object
        data- pandas DataFrame object that will be written into the file
    """
    #get the time entries for this file
    timestamp = [time.year, time.month, time.day, time.hour, time.minute, time.second]
    #write data to file
    with open(timelogname, 'a') as log:
        log.seek(0,2)
        log.write('\n')
        for entry in timestamp:
            log.write(str(entry)+', ')
        for num in data.values[0]:
            log.write(str(num)+',')
    return timestamp


# Must list .plt that script is applied for proper execution
# Run this script with "-c" to connect to Tecplot 360 on port 7600
# To enable connections in Tecplot 360, click on:
#   "Scripting" -> "PyTecplot Connections..." -> "Accept connections"

if __name__ == "__main__":
    if '-c' in sys.argv:
        tp.session.connect()

    os.environ["LD_LIBRARY_PATH"]='/usr/local/tecplot/360ex_2018r2/bin:/usr/local/tecplot/360ex_2018r2/bin/sys:/usr/local/tecplot/360ex_2018r2/bin/sys-util'
    DATAFILE = sys.argv[1]
    print('Processing '+DATAFILE)
    tp.new_layout()

    #Load .plt file
    log.info('loading .plt and reformatting')
    SWMF_DATA = tp.data.load_tecplot(DATAFILE)
    SWMF_DATA.zone(0).name = 'global_field'
    OUTPUTNAME = DATAFILE.split('e')[1].split('-000.')[0]+'done'
    print(SWMF_DATA)

    #Set parameters
    #DaySide
    N_AZIMUTH_DAY = 5
    AZIMUTH_MAX = 122
    R_MAX = 30
    R_MIN = 3.5
    ITR_MAX = 100
    TOL = 0.1
    AZIMUTH_RANGE = [np.deg2rad(-1*AZIMUTH_MAX), np.deg2rad(AZIMUTH_MAX)]
    PHI = np.linspace(AZIMUTH_RANGE[0], AZIMUTH_RANGE[1], N_AZIMUTH_DAY)

    #Tail
    N_AZIMUTH_TAIL = 5
    RHO_MAX = 50
    RHO_STEP = 0.5
    X_TAIL_CAP = -20
    PSI = np.linspace(-pi*(1-pi/N_AZIMUTH_TAIL), pi, N_AZIMUTH_TAIL)

    #Cylindrical zone
    N_SLICE = 40
    N_ALPHA = 50

    with tp.session.suspend():
        tp.macro.execute_command("$!FrameName = 'main'")
        #Create R from cartesian coordinates
        tp.data.operate.execute_equation(
                    '{r [R]} = sqrt({X [R]}**2 + {Y [R]}**2 + {Z [R]}**2)')
        #Create Dayside Magnetopause field lines
        calc_dayside_mp(PHI, R_MAX, R_MIN, ITR_MAX, TOL)

        #Create Tail magnetopause field lines
        calc_tail_mp(PSI, X_TAIL_CAP, RHO_MAX, RHO_STEP)
        #Create Theta and Phi coordinates for all points in domain
        tp.data.operate.execute_equation(
                                   '{phi} = atan({Y [R]}/({X [R]}+1e-24))')
        tp.data.operate.execute_equation(
                                   '{theta} = acos({Z [R]}/{r [R]}) * '+
                                    '({X [R]}+1e-24) / abs({X [R]}+1e-24)')

        #port stream data to pandas DataFrame object
        STREAM_ZONE_LIST = np.linspace(2,SWMF_DATA.num_zones,
                                       SWMF_DATA.num_zones-2+1)

        STREAM_DF, X_MAX = dump_to_pandas(STREAM_ZONE_LIST, [1,2,3],
                                          'stream_points.csv')

