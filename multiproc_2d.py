#/usr/bin/env python
"""Example from the pytecplot documentation
"""
import time
import logging
import atexit, os, multiprocessing, sys
import numpy as np
import pandas as pd
from numpy import pi
import datetime as dt
import glob
import gzip
import shutil
#import spacepy
import tecplot as tp
from tecplot.constant import *
from tecplot.exception import *
import global_energetics
from global_energetics.preplot import load_hdf5_data, IDL_to_hdf5
from global_energetics.extract.stream_tools import standardize_vars
from global_energetics.extract import magnetosphere2D as mp2d
from global_energetics.extract import view_set
from global_energetics import write_disp, makevideo

def init(eventpath_z, outputpath,all_solution_times):
    '''Initialization function for each new spawn
    Inputs
        rundir, mhddir, etc. - filepaths for input/output
        all_solution_times - list of all files for finding adjacents
    '''
    # !!! IMPORTANT !!!
    # Must register stop at exit to ensure Tecplot cleans
    # up all temporary files and does not create a core dump
    atexit.register(tp.session.stop)
    #globalize variables for each worker
    global CONTEXT
    CONTEXT = {
            'EVENTPATH_Z' : eventpath_z,
            'OUTPUTPATH' : outputpath,
            'ALL_SOLUTION_TIMES' : all_solution_times,
            'id' : id(multiprocessing.current_process()),
            }
    #os.makedirs(mhddir+'/'+str(CONTEXT['id']), exist_ok=True)

def work(XZfile):
    print(str(CONTEXT['id'])+'working on: '+XZfile)
    #Get matching file
    matchfile = (CONTEXT['EVENTPATH_Z']+'/z=0_var_2'+
                                             XZfile.split('y=0_var_1')[-1])
    #Load files in
    tp.new_layout()
    zfile = IDL_to_hdf5(XZfile)
    yfile = IDL_to_hdf5(matchfile)
    XYvars=['/x','/y','/Bx','/By','/Bz','/jx','/jy','/jz',
                     '/P','/Rho','/Ux','/Uy','/Uz','/b1x','/b1y','/b1z']
    XYZvars=['/x','/y','/z','/Bx','/By','/Bz','/jx','/jy','/jz',
                     '/P','/Rho','/Ux','/Uy','/Uz','/b1x','/b1y','/b1z']
    load_hdf5_data(os.getcwd()+'/'+zfile)
    load_hdf5_data(os.getcwd()+'/'+yfile,in_variables=XYvars,
                           variable_name_list=XYZvars)
    ds = tp.active_frame().dataset
    XZ,XY = ds.zone(0), ds.zone(1)
    standardize_vars()

    #get_timestamp
    timestamp = makevideo.get_time(XZfile)

    ##XZ plane
    mp2d.get_XZ_magnetopause(ds, XZ_zone_index=0, betastar=0.7)
    #Get mp points
    zmax,zmin = mp2d.get_night_mp_points(ds.zone('XZTriangulation'),-10)
    nose = mp2d.get_nose(tp.active_frame().dataset.zone(2))

    ##XY plane
    mp2d.get_XY_magnetopause(ds, XY_zone_index=1, betastar=0.7)
    ymax,ymin = mp2d.get_night_mp_points(ds.zone('XYTriangulation'),-10,
                                            plane='XY',mpvar='mpXY')

    ##Other terms
    newell = mp2d.get_local_newell(ds.zone('XYTriangulation'),xloc=20)
    shue_nose, shue_flank = mp2d.get_local_shue(ds.zone('XYTriangulation'),
                                                xloc=20, xflank=-10)

    #savedata
    mp2d.save_tofile(XZfile,timestamp,xloc=-10,nose=[nose],newell=[newell],
                     ymax=[ymax],ymin=[ymin],zmax=[zmax],zmin=[zmin],
                     shue_nose=[shue_nose],shue_flank=[shue_flank],
                     outputdir=CONTEXT['OUTPUTPATH']+'/')

    ##Display
    #Z
    mp2d.set_yaxis() #set to XZ
    view_set.display_2D_contours(tp.active_frame(),
                                 filename=zfile.split('y=0_')[-1],
                                 pngpath=CONTEXT['OUTPUTPATH']+'/yfigures/',
                                 outputname=zfile.split('.h5')[0])
    #Y
    mp2d.set_yaxis(mode='Y') #set to XY
    view_set.display_2D_contours(tp.active_frame(),axis='XY',
                                 filename=yfile.split('z=0_')[-1],
                                 pngpath=CONTEXT['OUTPUTPATH']+'/zfigures/',
                                 outputname=yfile.split('.h5')[0])

    #Clean up
    os.remove(os.getcwd()+'/'+zfile)
    os.remove(os.getcwd()+'/'+yfile)

def single_event_run(eventname, **kwargs):
    """Runs full analysis on single event
    Inputs
        eventname (str)
        kwargs:
            stormdir
    """
    ##Setup paths
    event_z = 'z=0_var_2'+eventname.split('y=0_var_1')[-1]
    eventpath = os.path.join(kwargs.get('stormdir',''),'y0',eventname)
    eventpath_z = os.path.join(kwargs.get('stormdir',''),'z0',event_z)
    #Check that z slice path isn't slightly different
    if not os.path.exists(eventpath_z):
        newpath = glob.glob(eventpath_z.split('-')[0]+'*')[0]
        if os.path.exists(newpath):
            eventpath_z = newpath
            checkfiles = True
        else:
            print('\n'+eventname+' FAILED '+time.ctime()+'\n')
            return
    else:
        checkfiles = False
    outputdir = os.path.join(kwargs.get('stormdir',''), 'mp_points',
                                 eventname.split('e')[-1])
    outputpath = os.path.join(kwargs.get('stormdir',''), 'mp_points',
                                 eventname.split('e')[-1],
                                 'individual')

    ##Make directories for output
    os.makedirs(outputpath, exist_ok=True)
    os.makedirs(outputpath+'/yfigures', exist_ok=True)
    os.makedirs(outputpath+'/zfigures', exist_ok=True)

    ##Run
    multiprocess(eventpath, eventpath_z, outputpath, check=checkfiles)

    ##Combine HDF5 files
    write_disp.combine_hdfs(outputpath,outputdir, progress=False,
                            combo_name=eventname+'.h5')

    ##Make a video
    create_video(outputpath,outputdir)

    ##Clean up
    shutil.rmtree(outputpath)

    ##Make a copy of hdf5 datafile
    make_ASCII_copy(outputdir,eventname)
    print('\n'+eventname+' COMPLETE '+time.ctime()+'\n')

def multiprocess(eventpath, eventpath_z, outputpath,**kwargs):
    """Calls multiprocesssing modules to perform analysis
    inputs
        eventpath
        eventpath_z
        outputpath
        kwargs:
            checkfiles (bool)
    """
    # Get the set of data files to be processed (solution times)
    all_solution_times = sorted(glob.glob(eventpath+'/*.out'),
                            key=makevideo.time_sort)
    if kwargs.get('check',False):
        #find and remove any files that don't have a match
        #NOTE replace this with creating matched pairs from the beginning?
        matching_solutions = sorted(glob.glob(eventpath_z+'/*.out'),
                            key=makevideo.time_sort)
        tail_y = [s.split('y=0_var_1_e')[-1] for s in all_solution_times]
        tail_z = [s.split('z=0_var_2_e')[-1] for s in matching_solutions]
        for s in list(set(tail_y)-set(tail_z)):
            print('removing: '+s+' from solution list')
            all_solution_times.remove(eventpath+'/y=0_var_1_e'+s)
    solution_times = all_solution_times
    print(len(solution_times))
    numproc = multiprocessing.cpu_count()-1

    # Set up the pool with initializing function and associated arguments
    num_workers = min(numproc, len(solution_times))
    pool = multiprocessing.Pool(num_workers, initializer=init,
            initargs=(eventpath_z, outputpath, all_solution_times))
    try:
        # Map the work function to each of the job arguments
        pool.map(work, solution_times)
    finally:
        # Join the process pool before exit so Tec cleans up & no core dump
        pool.close()
        pool.join()

def create_video(inputdir,outputdir,**kwargs):
    """Compiles video found at inpath and saves to outpath
    inputs
        inputdir
        kwargs:
            vid_resolution
            vid_framerate
    """
    #Combine and delete individual hdf5 files
    if os.path.exists(inputdir):
        ##Create videos from images
        #Video settings
        vid_resolution = 400
        vid_framerate = 16
        for cut in ['y','z']:
            folder = inputdir+'/'+cut+'figures/'
            frame_loc = makevideo.set_frames(folder)
            makevideo.vid_compile(frame_loc, outputdir, vid_framerate,
                                  '2Dmotion_'+cut)

def make_ASCII_copy(outputdir,eventname,**kwargs):
    """makes copy of hdf5 file to ascii
    inputs
        outputdir
        eventname
        kwargs:
            betastar
            xloc
            store_key
    """
    header= time.ctime()+'\nBetastar='+str(0.7)+'\nXloc='+str(-10)+'\n'
    store = pd.HDFStore(outputdir+'/'+eventname+'.h5')
    df = store['/mp_points']
    df.to_csv(outputdir+'/'+eventname+'.dat',sep=' ',index=False)
    store.close()

if __name__ == '__main__':
    start_time = time.time()
    if sys.version_info < (3, 5):
        raise Exception('This script requires Python version 3.5+')
    if tp.session.connected():
        raise Exception('This script must be run in batch mode')
    #Pytecplot requires spawn method
    multiprocessing.set_start_method('spawn')
    ########################################
    ### SET GLOBAL INPUT PARAMETERS HERE ###
    STORMDIR = '/nfs/solsticedisk/tuija/storms/'
    # Batch #EVENTNAME = sys.argv[-1].split('/')[-2]
    # first #EVENTNAME = 'y=0_var_1_e20100214-163100-000_20100216-103100-000'
    # with newell and visuals#EVENTNAME = 'y=0_var_1_e20120312-031000-000_20120313-211000-000'
    # latest
    #EVENTNAME = 'y=0_var_1_e20110805-120200-000_20110807-060200-000'
    EVENTNAME = 'y=0_var_1_e20120124-084900-000_20120126-024900-000'
    eventlist = ['y=0_var_1_e20110805-120200-000_20110807-060200-000',
                 'y=0_var_1_e20120124-084900-000_20120126-024900-000',
                 'y=0_var_1_e20100214-163100-000_20100216-103100-000',
                 'y=0_var_1_e20120312-031000-000_20120313-211000-000']
    eventlist = glob.glob(STORMDIR+'y0/*/')
    for event in [e.split('/')[-2] for e in eventlist]:
        if not os.path.exists(os.path.join(
                        STORMDIR,'mp_points',event.split('y=0_var_1_e')[-1])):
            single_event_run(event,stormdir=STORMDIR)
    """
    EVENT_Z = 'z=0_var_2'+EVENTNAME.split('y=0_var_1')[-1]
    EVENTPATH = os.path.join(STORMDIR,'y0',EVENTNAME)
    EVENTPATH_Z = os.path.join(STORMDIR,'z0',EVENT_Z)
    OUTPUTDIR = os.path.join(STORMDIR, 'mp_points',
                                 EVENTNAME.split('e')[-1])
    OUTPUTPATH = os.path.join(STORMDIR, 'mp_points',
                                 EVENTNAME.split('e')[-1],
                                 'individual')
    ########################################
    #make directories for output
    os.makedirs(OUTPUTPATH, exist_ok=True)
    os.makedirs(OUTPUTPATH+'/yfigures', exist_ok=True)
    os.makedirs(OUTPUTPATH+'/zfigures', exist_ok=True)
    ########################################
    ########### MULTIPROCESSING ###########
    #Pytecplot requires spawn method
    multiprocessing.set_start_method('spawn')

    # Get the set of data files to be processed (solution times)
    all_solution_times = sorted(glob.glob(EVENTPATH+'/*.out'),
                                key=makevideo.time_sort)
    solution_times = all_solution_times
    '''
    #Pick up only the files that haven't been processed
    if os.path.exists(OUTPUTPATH+'/energeticsdata'):
        parseddonelist, parsednotdone = [], []
        donelist = glob.glob(OUTPUTPATH+'/png/*.png')
        #donelist = glob.glob(OUTPUTPATH+'/energeticsdata/*.h5')
        for png in donelist:
            parseddonelist.append(png.split('/')[-1].split('.')[0])
            #yr,mo,dy,hr,mn = png.split('-')
            #yr = yr.split('_')[-1]
            #mn = mn.split('.')[0]
            #parsed = (yr+twodigit(int(mo))+twodigit(int(dy))+'-'+
            #                           twodigit(int(hr))+twodigit(int(mn)))
            #parseddonelist.append(parsed)
        for plt in all_solution_times:
            parsednotdone.append(plt.split('e')[-1].split('.')[0])
            #parsednotdone.append(plt.split('e')[-1].split('.')[0].split(
            #                                                     '00-')[0])
        solution_times = [MHDDIR+'/3d__var_1_e'+item+'.plt.gz' for item
                    in parsednotdone if item not in parseddonelist]
    else:
        solution_times = all_solution_times
    '''
    print(len(solution_times))
    numproc = multiprocessing.cpu_count()-1

    # Set up the pool with initializing function and associated arguments
    num_workers = min(numproc, len(solution_times))
    pool = multiprocessing.Pool(num_workers, initializer=init,
            initargs=(EVENTPATH_Z, OUTPUTPATH, all_solution_times))
    try:
        # Map the work function to each of the job arguments
        pool.map(work, solution_times)
    finally:
        # Join the process pool before exit so Tec cleans up & no core dump
        pool.close()
        pool.join()
        #for f in glob.glob(MHDDIR+'/*'):
        #    if os.path.isdir(f):
        #        os.removedirs(f)
    ########################################

    #Combine and delete individual hdf5 files
    if os.path.exists(OUTPUTPATH):
        ##Create videos from images
        #Video settings
        RES = 400
        FRAMERATE = 16
        for cut in ['y','z']:
            FOLDER = OUTPUTPATH+'/'+cut+'figures/'
            FRAME_LOC = makevideo.set_frames(FOLDER)
            makevideo.vid_compile(FRAME_LOC, OUTPUTDIR, FRAMERATE,
                                  '2Dmotion_'+cut)
        ##Combine HDF5 files
        write_disp.combine_hdfs(OUTPUTPATH,OUTPUTDIR, progress=False,
                                combo_name=EVENTNAME+'.h5')
        shutil.rmtree(OUTPUTPATH)
        ##make ASCII copy
        header= time.ctime()+'\nBetastar='+str(0.7)+'\nXloc='+str(-10)+'\n'
        store = pd.HDFStore(OUTPUTDIR+'/'+EVENTNAME+'.h5')
        df = store['/mp_points']
        df.to_csv(OUTPUTDIR+'/'+EVENTNAME+'.dat',sep=' ',index=False)
        store.close()
    """
    #timestamp
    ltime = time.time()-start_time
    print('--- {:d}min {:.2f}s ---'.format(int(ltime/60),
                                           np.mod(ltime,60)))