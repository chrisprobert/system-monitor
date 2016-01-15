from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import argparse
import datetime
import socket
import subprocess

import tinydb

'''
    Simple utility to log system usage, focused on GPU applications.
'''

_hostname = socket.gethostname()

def get_datetime_string() :
    now = datetime.datetime.now()
    dateline = datetime.datetime.strftime(now, '%Y:%m:%d:%H:%M:%S')
    return dateline

def run_command_split_output(command) :
    p = subprocess.Popen(command, stdout=subprocess.PIPE)
    output, _ = p.communicate()
    output = output.strip().split('\n')
    return output

def procinfo_from_pid(pid) :
    pid = int(pid)
    command = ['ps', '-p', '{}'.format(pid), '-o', 'pid,vsz=MEMORY', 
                '-o', 'user,group=GROUP', '-o', 'comm,args=ARGS']
    output = run_command_split_output(command)
    procinfo = {'pid' : pid, 'memory' : 0, 'user' : '', 'command' : '', 'args' : ''}
    if len(output) > 1 :
        line = output[1].strip().split()
        procinfo['memory'] = int(line[1])
        procinfo['user'] = line[2]
        procinfo['command'] = line[4]
        procinfo['args'] = ' '.join(line[5:])
    return procinfo

def run_nvidia_smi() :
    smi_gpu_fields = [
        'name',
        'pci.bus_id',
        'index',
        'utilization.gpu',
        'utilization.memory',
        'memory.total',
        'memory.used',
        'memory.free',
        'temperature.gpu',
        'fan.speed'
    ]

    smi_apps_fields = [
        'gpu_bus_id',
        'pid',
        'used_gpu_memory'
    ]

    smi_gpu_query = ','.join(smi_gpu_fields)
    smi_apps_query = ','.join(smi_apps_fields)
    command_gpu = ['nvidia-smi', '--query-gpu={}'.format(smi_gpu_query), 
                '--format=csv,noheader,nounits']
    command_apps = ['nvidia-smi', '--query-compute-apps={}'.format(smi_apps_query), 
                '--format=csv,noheader,nounits']

    output_gpu = run_command_split_output(command_gpu)
    output_apps = run_command_split_output(command_apps)

    gpu_info = [{k:v.strip() for k,v in zip(smi_gpu_fields, l.split(','))} for l in output_gpu]
    apps_info = [{k:v.strip() for k,v in zip(smi_apps_fields, l.split(','))} for l in output_apps]

    return gpu_info, apps_info

