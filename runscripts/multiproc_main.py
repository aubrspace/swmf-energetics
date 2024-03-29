#/usr/bin/env python
"""Example from the pytecplot documentation
"""
import os,sys
sys.path.append(os.getcwd().split('swmf-energetics')[0]+
                                      'swmf-energetics/')
import time
import logging
logging.basicConfig(filename='MAINrunlog.log',level=logging.DEBUG)
import atexit, multiprocessing
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
from global_energetics.extract import magnetosphere
from global_energetics.extract import view_set
from global_energetics.extract.view_set import twodigit
from global_energetics import write_disp, makevideo

def copy_plt(infiles,savepath):
    """Copies and unzips pair of files to process
    Inputs
        infiles (list[str])- files to unzip EXPECTS 2: [Current, Next]
        savepath (str)- where to save new, unzipped files
    Returns
        temp_files (list[str])- filenames of newly created unzipped temps
    """
    temp_files = [savepath+'/current.plt',savepath+'/next.plt']
    for f in enumerate(infiles):
        if '.gz' in infiles[0]:
            with gzip.open(f[1],'rb')as fin,open(
                                            temp_files[f[0]],'wb')as fout:
                shutil.copyfileobj(fin, fout)
        else:
            with open(f[1],'rb')as fin,open(temp_files[f[0]],'wb')as fout:
                shutil.copyfileobj(fin, fout)
    return temp_files

def init(rundir, mhddir, iedir, imdir, scriptdir, outputpath, pngpath,
         all_solution_times, loglevel):
    '''Initialization function for each new spawn
    Inputs
        rundir, mhddir, etc. - filepaths for input/output
        all_solution_times - list of all files for finding adjacents
    '''
    # !!! IMPORTANT !!!
    # Must register stop at exit to ensure Tecplot cleans
    # up all temporary files and does not create a core dump
    atexit.register(tp.session.stop)
    #set ID for processor
    ID = id(multiprocessing.current_process())
    #setup a separate log for each processor
    logger = logging.getLogger().getChild('child_'+str(ID))
    file_handler = logging.FileHandler(outputpath+'/'+str(ID)+'runlog.log')
    file_handler.setFormatter(logging.Formatter(logging.BASIC_FORMAT))
    logger.addHandler(file_handler)
    logger.setLevel(loglevel)
    #globalize variables for each worker
    global CONTEXT
    CONTEXT = {
            'RUNDIR' : rundir,
            'MHDDIR' : mhddir,
            'IEDIR' : iedir,
            'IMDIR' : imdir,
            'SCRIPTDIR' : scriptdir,
            'OUTPUTPATH' : outputpath,
            'PNGPATH' : pngpath,
            'ALL_SOLUTION_TIMES' : all_solution_times,
            'id' : ID,
            'log': logger
            }
    os.makedirs(mhddir+'/'+str(CONTEXT['id']), exist_ok=True)

def work(mhddatafile):
    log = CONTEXT['log']
    log.info('Beginning work for: '+mhddatafile)
    if log.level==10:
        marktime=time.time()

    ##Find pair of files for current + next solution (assumed sorted)
    cSol = CONTEXT['ALL_SOLUTION_TIMES']
    nSol = cSol.copy(); nSol.pop(0); nSol.append(cSol[-1])#shift 1 right
    cnSol = [[c,n] for c,n in zip(cSol,nSol) if c==mhddatafile][0]

    if not os.path.exists(CONTEXT['MHDDIR']+'/copy_plt'):
        #Create copies to spawn's local folder
        temppath = CONTEXT['MHDDIR']+'/'+str(CONTEXT['id'])
        tempSol = copy_plt(cnSol,temppath)#Now solutions are unzipped copies
    else:
        #Use existing copy found in "copy_plt" folder
        tempSol=[cnSol[0],os.path.join(CONTEXT['MHDDIR'],
                                   'copy_plt',cnSol[1].split('/')[-1])]

    #Load data into tecplot and setup field zone names
    tp.new_layout()
    field_data = tp.data.load_tecplot(tempSol)
    field_data.zone(0).name = 'global_field'
    field_data.zone(1).name = 'future'
    OUTPUTNAME = mhddatafile.split('e')[-1].split('.plt')[0]
    if log.level==10:
        log.debug('Copy unzip: --- {:.2f}s ---'.format(time.time()-
                                                           marktime))
        marktime=time.time()
    #Caclulate surfaces
    '''
    #MODE 1 "terminator" polar cap stuff
    magnetosphere.get_magnetosphere(field_data,save_mesh=False,
                                    do_cms=False,
                                    analysis_type='energymassmag',
                                    modes=['sphere','terminator'],
                                    sp_rmax=2.65,
                                    do_interfacing=True,
                                    integrate_surface=True,
                                    integrate_volume=False,
                                    integrate_line=True,
                                    outputpath=CONTEXT['OUTPUTPATH'],
                                    logger=log)
    '''
    #MODE 2 "full" magnetosphere stuff
    magnetosphere.get_magnetosphere(field_data,save_mesh=False,
                                    do_cms=True,
                                    analysis_type='energy',
                                    modes=['iso_betastar','closed',
                                           'nlobe','slobe'],
                                    customTerms={'test':'TestArea [Re^2]'},
                                    do_interfacing=True,
                                    integrate_surface=True,
                                    integrate_volume=True,
                                    integrate_line=False,
                                    outputpath=CONTEXT['OUTPUTPATH'],
                                    logger=log)
                                    #tshift=45,
    if log.level==10:
        log.debug('Analysis: --- {:.2f}s ---'.format(time.time()-
                                                           marktime))
        marktime=time.time()
    if False:#manually switch on or off
        pass
    else:
        with open(CONTEXT['PNGPATH']+'/'+OUTPUTNAME+'.png','wb') as png:
            png.close()
    #Remove copies now that work is done for that file
    if not os.path.exists(CONTEXT['MHDDIR']+'/copy_plt'):
        for f in tempSol: os.remove(f)
    if log.level==10:
        log.debug('Png and Wrapup: --- {:.2f}s ---'.format(time.time()-
                                                               marktime))
        marktime=time.time()
    print(time.ctime())

if __name__ == '__main__':
    start_time = time.time()
    if sys.version_info < (3, 5):
        raise Exception('This script requires Python version 3.5+')
    if tp.session.connected():
        raise Exception('This script must be run in batch mode')
    if '-h' in sys.argv or '--help' in sys.argv:
        print("""
    Parallel processing script for global_energetics with pytecplot
    Usage: (pytecplot env alias) multiproc_main.py [-flags]

    Options:
        -h  --help      prints this message then exit
        -np --noproc    skip processing and go right to cleaning
        -nc --noclean   skip cleaning step

    Example:
        multiPytec multiproc_main.py -np -nc
            this will only print the filelist for remaining workload

    Note: pytecplot env alias calls tec-env which comes with tecplot
            dist along with "python" command. To create an alias put
            something like below in ~/.bashrc (or whichever shellrc)

            alias myAlias="/pathto_tec360-env/tec360-env -- python"

        ex.
            alias multiPytec="/usr/local/tecplot2/tecplot360ex2020r1_linux64/bin/tec360-env -- python"
        """)
        exit()
    ########################################
    ### SET GLOBAL INPUT PARAMETERS HERE ###
    #RUNDIR = 'usermod'
    #RUNDIR = 'ccmc_2019-05-13'
    #RUNDIR = 'starlink'
    RUNDIR = 'ccmc_2022-02-02'
    #RUNDIR = 'febstorm'
    MHDDIR = os.path.join(RUNDIR)
    IEDIR = os.path.join(RUNDIR)
    IMDIR = os.path.join(RUNDIR)
    SCRIPTDIR = './'
    #OUTPUTPATH = os.path.join(SCRIPTDIR, '1min_output_feb2014')
    OUTPUTPATH = os.path.join(SCRIPTDIR, '1min_output_starlink2')
    PNGPATH = os.path.join(OUTPUTPATH, 'png')
    LOGLEVEL = logging.DEBUG
    ########################################
    #make directories for output
    os.makedirs(OUTPUTPATH, exist_ok=True)
    os.makedirs(OUTPUTPATH+'/figures', exist_ok=True)
    os.makedirs(OUTPUTPATH+'/indices', exist_ok=True)
    os.makedirs(OUTPUTPATH+'/png', exist_ok=True)
    ########################################
    # Get the set of data files to be processed (solution times)
    all_solution_times = sorted(glob.glob(MHDDIR+'/*.plt'),
                                key=makevideo.time_sort)[::100]
    #Pick up only the files that haven't been processed
    if os.path.exists(OUTPUTPATH+'/energeticsdata'):
        parseddonelist, parsednotdone = [], []
        donelist = glob.glob(OUTPUTPATH+'/png/*.png')
        #donelist = glob.glob(OUTPUTPATH+'/energeticsdata/*.h5')
        for png in donelist:
            parseddonelist.append(png.split('/')[-1].split('.')[0])
        for plt in all_solution_times:
            parsednotdone.append(plt.split('e')[-1].split('.')[0])
        solution_times = [MHDDIR+'/3d__var_1_e'+item+'.plt' for item
                          in parsednotdone if item not in parseddonelist]
    else:
        solution_times = all_solution_times
    print('files remaining: ',len(solution_times))
    if ('-np' not in sys.argv) and ('--noproc' not in sys.argv):
        ########### MULTIPROCESSING ###########
        #Pytecplot requires spawn method
        multiprocessing.set_start_method('spawn')
        numproc = multiprocessing.cpu_count()-1

        # Set up the pool with initializing function and associated arguments
        num_workers = min(numproc, len(solution_times))
        print('workers: ',num_workers)
        pool = multiprocessing.Pool(num_workers, initializer=init,
                initargs=(RUNDIR, MHDDIR, IEDIR, IMDIR, SCRIPTDIR, OUTPUTPATH,
                        PNGPATH, all_solution_times,LOGLEVEL))
        try:
            # Map the work function to each of the job arguments
            pool.map(work, solution_times)
        finally:
            # Join the process pool before exit so Tec cleans up & no core dump
            pool.close()
            pool.join()
            for f in [f for f in glob.glob(MHDDIR+'/*') if os.path.isdir(f)]:
                try:
                    os.removedirs(f)
                except: OSError
        ########################################
    if ('-nc' not in sys.argv) and ('--noclean' not in sys.argv):
        #Combine and delete individual energetics files
        if os.path.exists(OUTPUTPATH+'/energeticsdata'):
            write_disp.combine_hdfs2(os.path.join(OUTPUTPATH,'energeticsdata'),
                                OUTPUTPATH)
            shutil.rmtree(OUTPUTPATH+'/energeticsdata/')
    if ('--noproc' in sys.argv) or ('-np' in sys.argv):
        if ('--noclean' in sys.argv) or ('-nc' in sys.argv):
            print(solution_times)
    #timestamp
    ltime = time.time()-start_time
    print('--- {:d}min {:.2f}s ---'.format(int(ltime/60),
                                           np.mod(ltime,60)))
