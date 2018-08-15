# Jupyter on Abacus
This Python program provides an automatic method for launching Jupyter jobs on the Abacus 2.0 supercomputer. At the moment, the program works on macOS or Linux, while Windows is completely unsupported. After launching the program on the user's local computer, it is possible to connect to the Abacus 2.0 supercomputer, after which the program automatically submits a new Jupyter job to the queue system. Once the Jupyter job is running, the Jupyter interface is accessible through the user's local browser.

## Requirements
The program requires either macOS or Linux with a working Python installation that includes the python TK package.

## Usage
From the main window of the program, the user can specify the following settings.

* **Username**: Username used to connect to the Abacus 2.0 supercomputer
* **SSH Key**: This should only be used if the SSH key is stored in a non-default location
* **Account**: Slurm account used for running the job
* **Time limit**: Slurm wall-time limit for the job
* **Version**: Python and Jupyter version used for running the job

In most cases, only the username is mandatory, while the remaining settings can be left with their default value. After pressing the connect button, the program tries to connect to the Abacus 2.0 supercomputer, with status messages written in the text field below. If the connection is successful, the program submits a new job to the queue system and waits until the job starts running. Please note that the extent of this waiting period depends on the number of available nodes in the chosen slurm queue. After the job starts running, the user can press the "Open Jupyter in Browser" button, after which the user can start working through the Jupyter webinterface. When closing the program or pressing the disconnect button, the Jupyter job is automatically stopped on the Abacus 2.0 supercomputer. For this reason, the program must be running while using Jupyter in the browser.

## Technical details
Depending on the chosen version of Python, on the Abacus 2.0 supercomputer one of the following two modules are loaded.

$ module load python/2.7.14
$ module load python/3.6.3

If the user requires additional Python packages, the correct module should be loaded, after which the packages can be installed using pip. For example, if the user uses Python 3.6 and needs numpy, use SSH to access the Abacus 2.0 supercomputer and run the following two commands.

$ module load python/3.6.3
$ pip install --user numpy

For the advanced users, it is possible to e.g. load additional modules and set environmental variables before Jupyter starts running. If the file "~/.jupyter/modules" exists, this file is source'd into the submit script before starting Jupyter. For example, if the user needs tensorflow, run the following command:

echo "module load tensorflow" > ~/.jupyter/modules
