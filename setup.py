#!/usr/bin/env python

from __future__ import print_function
from distutils.core import setup

import time
import os
import sys
import site
from glob import glob

DEBUG = False
cmdline_args = sys.argv[1:]

required_modules = ['numpy', 'scipy', 'matplotlib', 'h5py', 'sqlalchemy']
recommended_modules = {'basic analysis': required_modules,
                       'graphics and plotting': ('wx', 'wxmplot', 'wxutils'),
                       'color-enhanced error messages': ('termcolor', ),
                       'using the EPICS control system': ('epics', ),
                       }

# files that may be left from earlier installs) and should be removed
historical_cruft = []

modules_imported = {}
missing = []
deps_ok = False
if os.path.exists('.deps'):
    try:
        f = open('.deps', 'r').readlines()
        deps_ok = int(f[0].strip()) == 1
    except:
        pass

if not deps_ok:
    print( 'Checking dependencies....')
    for desc, mods in recommended_modules.items():
        for mod in mods:
            if mod == 'wx':
                try:
                    import wxversion
                    wxversion.ensureMinimal('2.8')
                except:
                    pass
            if mod not in modules_imported:
                modules_imported[mod] = False
            try:
                x = __import__(mod)
                modules_imported[mod] = True
            except ImportError:
                missing.append('     %s:  needed for %s' % (mod, desc))
    missing_reqs = []
    for mod in modules_imported:
        if mod in required_modules and not modules_imported[mod]:
            missing_reqs.append(mod)

    if len(missing_reqs) > 0:
        print('== Cannot Install Larch: Required Modules are Missing ==')
        isword = 'is'
        if len(missing_reqs) > 1: isword = 'are'
        print(' %s %s REQUIRED' % (' and '.join(missing_reqs), isword) )
        print(' ')
        print(' Please read INSTALL for further information.')
        print(' ')

        sys.exit()
    deps_ok = len(missing) == 0

##
## For Travis-CI, need to write a local site config file
##
if os.environ.get('TRAVIS_CI_TEST', '0') == '1':
    time.sleep(0.2)


from lib import site_config, version

# read installation locations from lib/site_configdata.py
larchdir = site_config.larchdir


if DEBUG:
    print("##  Settings  (Debug mode) ## ")
    print(" larchdir: ",  larchdir)
    print(" sys.prefix: ",  sys.prefix)
    print(" sys.exec_prefix: ",  sys.exec_prefix)
    print(" cmdline_args: ",  cmdline_args)
    print("##   ")


# construct list of files to install besides the normal python modules
# this includes the larch executable files, and all the larch modules
# and plugins

bin_dir = os.path.join(larchdir, 'bin')
ico_dir = os.path.join(larchdir, 'icons')
mod_dir = os.path.join(larchdir, 'modules')

scripts =  glob('bin/*')
if os.name != 'nt':
    unix_scripts = []
    for s in scripts:
        if not s.endswith('.bat'):
            unix_script.append(s)
    scripts = unix_scripts

data_files = [('scripts', scripts),
              (bin_dir, glob('bin/*')),
              (ico_dir, glob('icons/*.ic*')),
              (mod_dir, glob('modules/*.lar') + glob('modules/*.py'))]


#dlls
dll_maindir = os.path.join(larchdir, 'dlls')
archs = []
if os.name == 'nt':
    archs.extend(['win32', 'win64'])
else:
    if sys.platform.lower().startswith('linux'):
        archs.extend(['linux32', 'linux64'])
    elif sys.platform.lower().startswith('darwin'):
        archs.append('darwin')

for dx in archs:
    dlldir = os.path.join(dll_maindir, dx)
    dllfiles = glob('dlls/%s/*' % dx)
    data_files.append((dlldir, dllfiles))

plugin_dir = os.path.join(larchdir, 'plugins')
pluginfiles = []
pluginpaths = []
for fname in glob('plugins/*'):
    if os.path.isdir(fname):
        pluginpaths.append(fname)
    else:
        pluginfiles.append(fname)

data_files.append((plugin_dir, pluginfiles))

for pdir in pluginpaths:
    pfiles = []
    filelist = []
    for ext in ('py', 'txt', 'db', 'dat', 'rst', 'lar',
                'dll', 'dylib', 'so'):
        filelist.extend(glob('%s/*.%s' % (pdir, ext)))
    for fname in filelist:
        if os.path.isdir(fname):
            print('Warning -- not walking subdirectories for Plugins!!')
        else:
            pfiles.append(fname)
    data_files.append((os.path.join(larchdir, pdir), pfiles))

site_config.make_larchdirs()

# now we have all the data files, so we can run setup
setup(name = 'larch',
      version = version.__version__,
      author = 'Matthew Newville',
      author_email = 'newville@cars.uchicago.edu',
      url          = 'http://xraypy.github.io/xraylarch/',
      download_url = 'http://xraypy.github.io/xraylarch/',
      requires = required_modules,
      license = 'BSD',
      description = 'Synchrotron X-ray data analysis in python',
      package_dir = {'larch': 'lib'},
      packages = ['larch', 'larch.utils', 'larch.wxlib',
                  'larch.fitting', 'larch.fitting.uncertainties'],
      data_files  = data_files)

def remove_cruft(basedir, filelist):
    """remove files from base directory"""
    def remove_file(base, fname):
        fullname = os.path.join(base, fname)
        if os.path.exists(fullname):
            print(" Unlink ", fullname)
            try:
                os.unlink(fullname)
            except:
                pass
    for fname in filelist:
        remove_file(basedir, fname)
        if fname.endswith('.py'):
            remove_file(basedir, fname+'c')
            remove_file(basedir, fname+'o')


def fix_permissions(dirname, stat=None):
    """
    set permissions on a list of directories to match
    those of the HOME directory
    """
    if stat is None:
        return
    def set_perms(fname):
        try:
            os.chown(fname, stat.st_uid, stat.st_gid)
            os.chmod(fname, stat.st_mode)
        except(AttributeError, OSError):
            pass

    for top, dirs, files in os.walk(dirname):
        set_perms(top)
        for d in dirs+files:
            set_perms(os.path.join(top, d))


if cmdline_args[0] == 'install':
    remove_cruft(larchdir, historical_cruft)

    home_dir = site_config.get_homedir()
    try:
        home_stat = os.stat(home_dir)
    except:
        home_stat = None

    if home_stat is not None:
        fix_permissions(larchdir, stat=home_stat)
        fix_permissions(bin_dir,  stat=home_stat)
        mpl_dir = os.path.join(home_dir, '.matplotlib')
        if os.path.exists(mpl_dir):
            fix_permissions(mpl_dir,  stat=home_stat)
    
if deps_ok and not os.path.exists('.deps'):
    f = open('.deps', 'w')
    f.write('1\n')
    f.close()

if len(missing) > 0:
    msg = """
#==============================================================#
#=== Warning: Some recommended Python Packages are missing:
%s

Some functionality will not work until these are installed.
See INSTALL for further information.
#==============================================================#"""
    print(msg %  '\n'.join(missing))
