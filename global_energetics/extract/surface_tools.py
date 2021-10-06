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
#interpackage modules, different path if running as main to test
from global_energetics.extract.stream_tools import (integrate_surface,
                                                    get_surface_variables,
                                            get_surface_velocity_estimate,
                                                    dump_to_pandas)
from global_energetics.extract.view_set import variable_blank

def surface_analysis(frame, zone_name, do_cms, do_1Dsw, *, find_DFT=True,
                     calc_K=True, calc_ExB=True, calc_P0=True,virial=True,
                    surface_area=True, test=False,cuttoff=-20,blank=False,
                    blank_value=0, blank_variable='W *',timedelta=60):
    """Function to calculate energy flux at magnetopause surface
    Inputs
        field_data- tecplot Dataset object with 3D field data and mp
        zone_name
        calc_ - boolean for performing that integration
        cuttoff- used to blank tail end of surface
    Outputs
        surface_power- power, or energy flux at the magnetopause surface
    """
    #Optional blanking
    if blank:
        variable_blank(frame, blank_variable, blank_value)
        variable_blank(frame, blank_variable, blank_value-100, slot=4,
                       operator=RelOp.LessThan)
    #get surface specific variables
    field_data = frame.dataset
    if do_cms:
        '''
        #calculate movement of surface before finalizing surface variables
        get_surface_velocity_estimate(field_data,
                                      field_data.zone(zone_name).index,
                                field_data.zone('future_'+zone_name).index)
        get_surface_variables(field_data, zone_name, do_1Dsw, do_cms=True,
                              dt=timedelta)
        '''
        hmin = get_surface_variables(field_data, zone_name, do_1Dsw,
                                     find_DFT=find_DFT)
    else:
        hmin = get_surface_variables(field_data, zone_name, do_1Dsw,
                                     find_DFT=find_DFT)
    #initialize objects for frame
    zone_index = int(field_data.zone(zone_name).index)
    keys = []
    data = []
    ##Different prefixes allow for calculation of surface fluxes using 
    #   multiple sets of flowfield variables (denoted by the prefix)
    prefixlist = ['']
    if do_1Dsw:
        prefixlist.append('1D')
    for add in prefixlist:
        ###################################################################
        #test integration
        if test:
            #write test flowfield conditions
            u_advected= '({Dp [nPa]}+2.5*{P [nPa]}+{Bmag [nT]}/(4*pi*1e2))'
            #u_advected = '{Rho [amu/cm^3]}'
            bdotu = ('{B_x [nT]}*{U_x [km/s]}+'+
                    '{B_y [nT]}*{U_y [km/s]}+'+
                    '{B_z [nT]}*{U_z [km/s]}')
            bdotu_Bx = ('('+bdotu+')*({B_x [nT]}/(4*pi*1e2))')
            bdotu_By = ('('+bdotu+')*({B_y [nT]}/(4*pi*1e2))')
            bdotu_Bz = ('('+bdotu+')*({B_z [nT]}/(4*pi*1e2))')
            k_x = '('+u_advected+'*{U_x [km/s]})'
            k_y = '('+u_advected+'*{U_y [km/s]})'
            k_z = '('+u_advected+'*{U_z [km/s]})'
            '''
            k_x = '{K_x [W/Re^2]}'
            k_y = '{K_y [W/Re^2]}'
            k_z = '{K_z [W/Re^2]}'
            '''
            flowvec1 = [bdotu_Bx+'*6371**2', bdotu_By+'*6371**2',
                        bdotu_Bz+'*6371**2']
            flowvec2 = [k_x+'*6371**2', k_y+'*6371**2', k_z+'*6371**2']
            flowvec3 = ['{B_x [nT]}', '{B_y [nT]}', '{B_z [nT]}']
            eq = tp.data.operate.execute_equation
            eq('{bdotu} = '+bdotu+'/(4*pi*1e2)')
            #TEST1
            eq('{test1}=('+str(flowvec1[0])+'*{surface_normal_x}+'+
                        str(flowvec1[1])+'*{surface_normal_y}+'+
                        str(flowvec1[2])+'*{surface_normal_z})',
                    value_location=ValueLocation.CellCentered)
            keys.append('test '+str(flowvec1))
            test1_index = int(field_data.variable('test1').index)
            test1 = integrate_surface(test1_index, zone_index)
            data.append(test1)
            #TEST2
            eq('{test2}=('+str(flowvec2[0])+'*{surface_normal_x}+'+
                        str(flowvec2[1])+'*{surface_normal_y}+'+
                        str(flowvec2[2])+'*{surface_normal_z})',
                    value_location=ValueLocation.CellCentered)
            keys.append('test '+str(flowvec2))
            test2_index = int(field_data.variable('test2').index)
            test2 = integrate_surface(test2_index, zone_index)
            data.append(test2)
            #TEST3
            eq('{test3}=('+str(flowvec3[0])+'*{surface_normal_x}+'+
                        str(flowvec3[1])+'*{surface_normal_y}+'+
                        str(flowvec3[2])+'*{surface_normal_z})',
                    value_location=ValueLocation.CellCentered)
            keys.append('test '+str(flowvec3))
            test3_index = int(field_data.variable('test3').index)
            test3 = integrate_surface(test3_index, zone_index)
            data.append(test3)
            print(zone_name+' '+keys[-1]+' integration done')
        ###################################################################
        #integrate Poynting flux
        if calc_ExB:
            #ESCAPE
            keys.append(add+'ExB_escape [W]')
            ExBesc_index= int(field_data.variable(add+'ExB_escape*').index)
            ExBesc = integrate_surface(ExBesc_index, zone_index)
            data.append(ExBesc)
            #NET
            keys.append(add+'ExB_net [W]')
            ExBnet_index = int(field_data.variable(add+'ExB_net *').index)
            ExBnet = integrate_surface(ExBnet_index, zone_index)
            data.append(ExBnet)
            #INJECTION
            keys.append(add+'ExB_injection [W]')
            ExBinj_index = int(
                           field_data.variable(add+'ExB_injection*').index)
            ExBinj = integrate_surface(ExBinj_index, zone_index)
            data.append(ExBinj)
            print(zone_name+' '+keys[-1]+' integration done')
        ###################################################################
        #integrate P0 flux
        if calc_P0:
            #ESCAPE
            keys.append(add+'P0_escape [W]')
            P0esc_index = int(field_data.variable(add+'P0_escape*').index)
            P0esc = integrate_surface(P0esc_index, zone_index)
            data.append(P0esc)
            #NET
            keys.append(add+'P0_net [W]')
            P0net_index = int(field_data.variable(add+'P0_net *').index)
            P0net = integrate_surface(P0net_index, zone_index)
            data.append(P0net)
            #INJECTION
            keys.append(add+'P0_injection [W]')
            P0inj_index = int(
                            field_data.variable(add+'P0_injection*').index)
            P0inj = integrate_surface(P0inj_index, zone_index)
            data.append(P0inj)
            print(zone_name+' '+keys[-1]+' integration done')
        ###################################################################
        #integrate K flux
        if calc_K:
            #ESCAPE
            keys.append(add+'K_escape [W]')
            kesc_index = int(field_data.variable(add+'K_escape*').index)
            kesc = integrate_surface(kesc_index, zone_index)
            data.append(kesc)
            #NET
            keys.append(add+'K_net [W]')
            knet_index = int(field_data.variable(add+'K_net *').index)
            knet = integrate_surface(knet_index, zone_index)
            data.append(knet)
            #INJECTION
            keys.append(add+'K_injection [W]')
            kinj_index = int(field_data.variable(add+'K_injection*').index)
            kinj = integrate_surface(kinj_index, zone_index)
            data.append(kinj)
            print(zone_name+' '+keys[-1]+' integration done')
        ###################################################################
        #integrate K flux
        if False:
            #ESCAPE
            keys.append(add+'KSurf_escape [W]')
            kSesc_index = int(field_data.variable(
                                             add+'KSurf_escape*').index)
            kSesc = integrate_surface(kSesc_index, zone_index)
            data.append(kSesc)
            #NET
            keys.append(add+'KSurf_net [W]')
            kSnet_index = int(field_data.variable(
                                               add+'KSurf_net *').index)
            kSnet = integrate_surface(kSnet_index, zone_index)
            data.append(kSnet)
            #INJECTION
            keys.append(add+'KSurf_injection [W]')
            kSinj_index = int(field_data.variable(
                                          add+'KSurf_injection*').index)
            kSinj = integrate_surface(kSinj_index, zone_index)
            data.append(kSinj)
            print(zone_name+' '+keys[-1]+' integration done')
        ###################################################################
        #integrate area
        if surface_area and add=='':
            keys.append('Area [Re^2]')
            area_index = None
            SA = integrate_surface(area_index, zone_index,
                                    VariableOption='LengthAreaVolume')
            data.append(SA)
            print(zone_name+' '+keys[-1]+' integration done')
            if do_cms:
                keys.append('dVol_dt [Re^3/s]')
                dVoldt_index = int(field_data.variable('Csurface_n').index)
                dVoldt = integrate_surface(dVoldt_index, zone_index)
                data.append(dVoldt/6371)
                print(zone_name+' '+keys[-1]+' integration done')
        ###################################################################
        #average K flux
        if calc_K and surface_area and (SA!=0):
            #ESCAPE
            keys.append(add+'Average K_escape [W/Re^2]')
            kesc_average = kesc/SA
            data.append(kesc_average)
            #NET
            keys.append(add+'Average K_net [W/Re^2]')
            knet_average = knet/SA
            data.append(knet_average)
            #INJECTION
            keys.append(add+'Average K_injection [W/Re^2]')
            kinj_average = kinj/SA
            data.append(kinj_average)
        ###################################################################
        #Virial boundary total pressure integral
        if virial:
            virial_dict = {'virial_scalarPth':'Virial ScalarPth [J]',
                           'virial_scalaruB':'Virial ScalarPmag [J]',
                           'virial_scalaruB_dipole':'Virial ScalarPdip [J]',
                           'virial_advect1':'Virial Advection d/dt [J]',
                           'virial_advect2':'Virial Advection 2 [J]',
                           'virial_MagB_':'Virial B Stress [J]',
                           'virial_MagBd':'Virial Bd Stress [J]',
                           'virial_BBd':'Virial BBd Stress [J]',
                           'virial_surfTotal':'Virial Surface Total [J]'}
            if zone_name.find('innerbound')!=-1:
                virial_dict.update({'virial_scalardelta_uB':
                                                 'Virial ScalarPbin [J]'})
                virial_dict.update({'virial_Magb':'Virial b Stress [J]'})
            for v_key in virial_dict.keys():
                #Integrated value in Joules
                keys.append(virial_dict[v_key])
                virial_index = int(field_data.variable(add+v_key).index)
                virialResult = integrate_surface(virial_index, zone_index)
                data.append(virialResult)
                print(zone_name+' '+keys[-1]+' integration done')
                #Corresponding contribution to Dst
                mod_tag = virial_dict[v_key].split(' [J]')[0]+' [nT]'
                keys.append(mod_tag)
                dstResult = virialResult*(-3/2)/(8e13)
                data.append(dstResult)
                print(zone_name+' '+keys[-1]+' integration done')
        ###################################################################
    #Collect and report surface integrated quantities
    surface_power = pd.DataFrame([data],columns=keys)
    #Turn blanking off
    frame.plot().value_blanking.active = False
    return surface_power, hmin


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
