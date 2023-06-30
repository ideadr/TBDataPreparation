echo "Setting up environment"

# Activate virtual environment after lsetup to avoid PYTHONPATH pollution
#. "${IDEADIR}"/ideadr-env/bin/activate 

# c.f. libtiff.so hack in init.sh
export LD_LIBRARY_PATH=${IDEADIR}/ideadr-env/lib:$LD_LIBRARY_PATH 

export IDEARepo=${IDEADIR}/TBDataPreparation
export PATH=${IDEARepo}/2023_SPS/scripts:${PATH}
export PATH=${IDEADIR}/ideadr-env/bin:${PATH}
export PYTHONPATH=${IDEARepo}/2023_SPS/scripts:${IDEARepo}/DreamDaqMon:${PYTHONPATH}
export BATCHPATH=${PATH}

