#!/bin/bash
# copied from @Brian Petersen
if [ "$0" != "TBDataPreparation/init.sh" ]
then
    echo "init.sh must be run as 'TBDataPreparation/init.sh'"
    exit 1
fi

source /cvmfs/sft.cern.ch/lcg/views/LCG_102b/x86_64-centos7-gcc11-opt/setup.sh

# Use cvmfs-venv to hack back against PYTHONPATH pollution
# c.f. https://github.com/matthewfeickert/cvmfs-venv for more information and examples
# download and run directly to avoid temporary files or adding a Git submodule
bash <(curl -sL https://raw.githubusercontent.com/matthewfeickert/cvmfs-venv/v0.0.3/cvmfs-venv.sh) ideadr-env
source ideadr-env/bin/activate

# FIXME: hack due to unversioned library in LCG
ln -sf /lib64/libtiff.so "ideadr-env/lib/"
ln -sf /lib64/libtiff.so.5 "ideadr-env/lib/"
export LD_LIBRARY_PATH="ideadr-env/lib:${LD_LIBRARY_PATH}"

# Generate a Env setup script for every log-in
echo "Generating settings file: 'setup.sh'"
if [ -e setup.sh ]
then 
    echo "  Moving existing 'setup.sh' to 'setup.sh.old'"
    mv setup.sh setup.sh.old
fi
cat <<EOF > setup.sh
#set working directory
export IDEADIR=$PWD
export SamplePath=$PWD

#standard setup
source $PWD/TBDataPreparation/setup.sh 

EOF
