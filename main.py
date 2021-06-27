#/usr/bin/env python
"""script for calculating integrated quantities from mp and cps
"""
import sys
import os
import time
import logging
import numpy as np
from numpy import pi
import datetime as dt
import spacepy
import tecplot as tp
import tecplot
from tecplot.constant import *
from tecplot.exception import *
#import global_energetics
from global_energetics.extract import magnetopause
from global_energetics.extract import plasmasheet
from global_energetics.extract import satellites
from global_energetics.extract import stream_tools
from global_energetics.extract import surface_tools
from global_energetics.extract import volume_tools
from global_energetics.extract import view_set
from global_energetics.write_disp import write_to_hdf

if __name__ == "__main__":
    start_time = time.time()
    if '-c' in sys.argv:
        tp.session.connect()
        tp.new_layout()

    else:
        os.environ["LD_LIBRARY_PATH"]='/usr/local/tecplot/360ex_2018r2/bin:/usr/local/tecplot/360ex_2018r2/bin/sys:/usr/local/tecplot/360ex_2018r2/bin/sys-util'
    #pass in arguments
    mhddatafile = '3d__var_1_e20140219-090000-000.plt'
    future = '3d__var_1_e20140219-090100-023.plt'
    OUTPATH = 'temp/'
    PNGPATH = 'temp/'
    OUTPUTNAME = 'testoutput.png'
    '''
    mhddatafile = sys.argv[1].split('/')[-1]
    MHDPATH = '/'.join(sys.argv[1].split('/')[0:-1])+'/'
    IEPATH = sys.argv[2]
    IMPATH = sys.argv[3]
    OUTPATH = sys.argv[4]
    PNGPATH = sys.argv[5]
    OUTPUTNAME = mhddatafile.split('e')[1].split('.plt')[0]
    '''

    '''
    #setup log
    logging.basicConfig(filename=OUTPATH+'properlog.log', level=logging.INFO)
    logging.info('Analyzing {}'.format(mhddatafile))
    '''


    #python objects
    field_data = tp.data.load_tecplot([mhddatafile, future])
    field_data.zone(0).name = 'global_field'
    field_data.zone(1).name = 'future'
    main = tp.active_frame()
    main.name = 'main'

    #Caclulate initial surface
    magnetopause.get_magnetopause(field_data, mhddatafile,
                                  outputpath=OUTPATH)
    """
    data['wbin'] = -999
    write_to_hdf(OUTPATH+'/wbins/energetics_'+'total'+'.h5','mp',
                 mp_powers=data)
    print('WBIN written!')
    #blanking setup
    wlow = main.plot().value_blanking.constraint(5)
    wlow.variable = main.dataset.variable('W *')
    wlow.comparison_operator = RelOp.LessThan
    wlow.active = True
    whigh = main.plot().value_blanking.constraint(6)
    whigh.variable = main.dataset.variable('W *')
    whigh.comparison_operator = RelOp.GreaterThan
    whigh.active = True
    wbins, dw = np.linspace(0,500,10, retstep=True)
    '''
    #recalculate for each condition
    for w in wbins:
        wlow.comparison_value = w-dw/2
        whigh.comparison_value = w+dw/2
        _, powers, _ = magnetopause.get_magnetopause(field_data,
                                                        mhddatafile,
                                             zone_rename='mp_'+str(int(w)),
                                                        outputpath=OUTPATH)
        powers['wbin'] = w
        write_to_hdf(OUTPATH+'/wbins/energetics_'+str(int(w))+'.h5','mp',
                     mp_powers=powers)
        print('WBIN written!')
    '''
    #magnetopause.get_magnetopause(field_data, mhddatafile,
    #                  tail_cap=-40, tail_analysis_cap=-40,
    #                              zone_rename='mp_40Re',
    #                              outputpath=OUTPATH)
    #magnetopause.get_magnetopause(field_data, mhddatafile,
    #                  tail_cap=-50, tail_analysis_cap=-50,
    #                              zone_rename='mp_50Re',
    #                              outputpath=OUTPATH)
    """
    '''
    magnetopause.get_magnetopause(field_data, mhddatafile, mode='box',
                                  do_1Dsw=False,
                                  box_xmax=15, box_xmin=5,
                                  box_ymax=40, box_ymin=30,
                                  zone_rename='box_sw_pos_y',
                                  outputpath=OUTPATH)
    magnetopause.get_magnetopause(field_data, mhddatafile, mode='box',
                                  do_1Dsw=False,
                                  box_xmax=15, box_xmin=5,
                                  box_zmax=40, box_zmin=30,
                                  zone_rename='box_sw_pos_z',
                                  outputpath=OUTPATH)
    magnetopause.get_magnetopause(field_data, mhddatafile, mode='box',
                                  do_1Dsw=False,
                                  box_xmax=-30, box_xmin=-40,
                                  zone_rename='box_tail_outsideIM',
                                  outputpath=OUTPATH)
    magnetopause.get_magnetopause(field_data, mhddatafile, mode='box',
                                  do_1Dsw=False,
                                  box_xmax=-5, box_xmin=-10,
                                  zone_rename='box_tail_insideIM',
                                  outputpath=OUTPATH)
    magnetopause.get_magnetopause(field_data, mhddatafile, mode='box',
                                  do_1Dsw=False,
                                  box_xmax=10, box_xmin=5,
                                  zone_rename='box_day_insideIM',
                                  outputpath=OUTPATH)
    magnetopause.get_magnetopause(field_data, mhddatafile, mode='box',
                                  do_1Dsw=False,
                                  box_xmax=30, box_xmin=20,
                                  zone_rename='box_sw_pos_x',
                                  outputpath=OUTPATH)
    magnetopause.get_magnetopause(field_data, mhddatafile, mode='box',
                                  do_1Dsw=False,
                                  box_xmax=-30, box_xmin=-60,
                                  box_ymax=30, box_ymin=-30,
                                  box_zmax=30, box_zmin=-30,
                                  zone_rename='box_tail_big',
                                  outputpath=OUTPATH)
    magnetopause.get_magnetopause(field_data, mhddatafile, mode='box',
                                  do_1Dsw=False,
                                  box_xmax=30, box_xmin=10,
                                  box_ymax=30, box_ymin=-30,
                                  box_zmax=30, box_zmin=-30,
                                  zone_rename='box_sw_big',
                                  outputpath=OUTPATH)
    '''
    #get supporting module data for this timestamp
    eventstring =field_data.zone('global_field').aux_data['TIMEEVENT']
    startstring =field_data.zone('global_field').aux_data['TIMEEVENTSTART']
    eventdt = dt.datetime.strptime(eventstring,'%Y/%m/%d %H:%M:%S.%f')
    startdt = dt.datetime.strptime(startstring,'%Y/%m/%d %H:%M:%S.%f')
    deltadt = eventdt-startdt
    #satzones = satellites.get_satellite_zones(eventdt, MHDPATH, field_data)
    satzones = []

    '''
    north_iezone, south_iezone = get_ionosphere_zone(eventdt, IEPATH)
    im_zone = get_innermag_zone(deltadt, IMPATH)
    '''
    #adjust view settings
    bot_right = [frame for frame in tp.frames('main')][0]
    view_set.display_single_iso(bot_right,
                                'Ksurface_net *', mhddatafile,
                                show_contour=True,
                                show_slice=True,show_fieldline=False,
                                pngpath=PNGPATH,
                                plot_satellites=False, satzones=satzones,
                                mode='iso_tail', transluc=60,
                                outputname=OUTPUTNAME, save_img=False)
    """
    #tile
    proc = 'Multi Frame Manager'
    cmd = 'MAKEFRAMES3D ARRANGE=TILE SIZE=50'
    tp.macro.execute_extended_command(command_processor_id=proc,
                                          command=cmd)
    bot_right = [frame for frame in tp.frames('main')][0]
    bot_right.name = 'inside_from_tail'
    frame1 = [frame for frame in tp.frames('Frame 001')][0]
    frame2 = [frame for frame in tp.frames('Frame 002')][0]
    frame3 = [frame for frame in tp.frames('Frame 003')][0]
    view_set.display_single_iso(bot_right,
                                'K_net *', mhddatafile, show_contour=False,
                                show_slice=False, energyrange=9e10,
                                show_legend=False,
                                pngpath=PNGPATH, energy_contourmap=4,
                                plot_satellites=False, satzones=satzones,
                                outputname=OUTPUTNAME, save_img=False,
                                zone_hidekeys=['box', 'lcb', '30', '40'])
    frame1.activate()
    frame1.name = 'isodefault'
    view_set.display_single_iso(frame1,
                                'K_net *', mhddatafile, show_contour=True,
                                show_slice=True, show_legend=False,
                                pngpath=PNGPATH,
                                plot_satellites=True, satzones=satzones,
                                outputname=OUTPUTNAME, save_img=False,
                                show_timestamp=False,
                                zone_hidekeys=['box', 'lcb', '30', '40'])
    frame2.activate()
    frame2.name = 'alternate_iso'
    view_set.display_single_iso(frame2,
                                'K_net *', mhddatafile, show_contour=True,
                                show_slice=True,
                                pngpath=PNGPATH, add_clock=True,
                                plot_satellites=True, satzones=satzones,
                                outputname=OUTPUTNAME, save_img=False,
                                mode='other_iso',
                                show_timestamp=False,
                                zone_hidekeys=['box', 'lcb', '30', '40'])
    '''
    frame2.name = 'lcb'
    view_set.display_single_iso(frame2,
                                'K_net *', mhddatafile, show_contour=True,
                                show_slice=True,
                                pngpath=PNGPATH, add_clock=True,
                                plot_satellites=True, satzones=satzones,
                                outputname=OUTPUTNAME, save_img=False,
                                mode='other_iso', show_timestamp=False,
                                zone_hidekeys=['mp','sphere','box'])
    '''
    frame3.activate()
    frame3.name = 'tail_iso'
    view_set.display_single_iso(frame3,
                                'K_net *', mhddatafile, show_contour=True,
                                show_slice=True, show_legend=False,
                                pngpath=PNGPATH, transluc=60,
                                plot_satellites=True, satzones=satzones,
                                outputname=OUTPUTNAME,
                                mode='iso_tail',
                                show_timestamp=False,
                                zone_hidekeys=['box', 'lcb', '30', '40'])
    """
    #timestamp
    ltime = time.time()-start_time
    print('--- {:d}min {:.2f}s ---'.format(int(ltime/60),
                                           np.mod(ltime,60)))
