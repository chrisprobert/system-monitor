from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import argparse
import datetime
import inspect
import os
import socket
import subprocess
import time

import psutil
import tinydb


'''
    Simple utility to log system usage stats, focused on GPU applications.
'''

_hostname = socket.gethostname()
_log_frequency_seconds = 120

def main() :

    parser = argparse.ArgumentParser()
    parser.add_argument("--dbpath", type=str, help="database path", required=False)
    args = parser.parse_args()

    valid_path = True
    if not args.dbpath :
        print('No database path supplied, using current executable path')
        valid_path = False
    elif not os.path.exists(args.dbpath) :
        raise Exception('Supplied path {} not found'.format(args.dbpath))

    db_path = os.path.dirname(
        os.path.abspath(
            inspect.getfile(
                inspect.currentframe())))

    if valid_path :
        db_path = args.dbpath

    process_db_name = 'gpu-monitor-process-{}.db.json'.format(_hostname)
    gpu_db_name = 'gpu-monitor-gpu-{}.db.json'.format(_hostname)
    process_db_path = os.path.join(db_path, process_db_name)
    gpu_db_path = os.path.join(db_path, gpu_db_name)

    print('Starting monitor on {}'.format(_hostname))
    print('Process db: {}'.format(process_db_path))
    print('GPU db: {}'.format(gpu_db_path))
    print('Logging interval (seconds): {}'.format(_log_frequency_seconds))

    while True :
        gpus_stats, process_stats = get_gpu_process_stats()

        with tinydb.TinyDB(process_db_path) as db :
            map(db.insert, process_stats)

        with tinydb.TinyDB(gpu_db_path) as db :
            map(db.insert, gpus_stats)

        time.sleep(_log_frequency_seconds)

def get_datetime_string_now() :
    now = datetime.datetime.now()
    dateline = datetime.datetime.strftime(now, '%Y:%m:%d:%H:%M:%S')
    return dateline

def run_command_split_output(command) :
    p = subprocess.Popen(command, stdout=subprocess.PIPE)
    output, _ = p.communicate()
    output = output.strip().split('\n')
    return output

def procinfo_from_pid(pid) :
    try :
        p = psutil.Process(int(pid))
        procinfo = {
            'pid' : int(pid),
            'system_memory_rss' : p.memory_info().rss,
            'system_memory_vms' : p.memory_info().vms,
            'user' : p.username(),
            'name' : p.name(),
            'exe' : p.exe(),
            'args' : ' '.join(p.cmdline())
        }
    except :
        procinfo = {'pid' : pid, 'system_memory_rss' : '', 'system_memory_vms' : '',
            'user' : '', 'name' : '', 'exe' : '', 'args' : ''}
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

    gpu_info = map(
        lambda l: {'gpu-{}'.format(k):v.strip() for k,v in zip(smi_gpu_fields, l.split(','))},
        output_gpu)
    apps_info = [{k:v.strip() for k,v in zip(smi_apps_fields, l.split(','))} for l in output_apps]
    apps_info = filter(lambda d: len(d['gpu_bus_id']) and len(d['pid']), apps_info)

    return gpu_info, apps_info

def get_gpu_process_stats() :
    timestring = get_datetime_string_now()
    gpus_info, apps_info = run_nvidia_smi()
    pcibus2gpuinfo = {info['gpu-pci.bus_id'] : info for info in gpus_info}
    stats_by_process = []
    for app_info in apps_info :
        gpu_info = pcibus2gpuinfo[app_info['gpu_bus_id']]
        procinfo = procinfo_from_pid(app_info['pid'])
        combined_stats = {k:v for d in [app_info, gpu_info, procinfo] for k,v in d.items()}
        combined_stats['timestamp'] = timestring
        combined_stats['hostname'] = _hostname
        stats_by_process.append(combined_stats)
    return gpus_info, stats_by_process

if __name__ == '__main__' :
    main()