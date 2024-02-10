# coding=utf-8

"""
Collects Mesos Task cgroup statistics. Because Mesos Tasks
only tangentially relate to the host they are running on,
this collector uses task 'source' information to build the
naming path. The prefix is overridden in the collector to
place metrics in the graphite tree at the root under
`mesos.tasks`. The container ID contained within the
source string will serve as the container uniqueifier.

If your scheduler (this was written against a Mesos cluster
    being scheduled by Aurora) does not include uniqueifing
information in the task data under `frameworks.executors.source`,
you're going to have a bad time.

#### Example Configuration

```
    host = localhost
    port = 5051
```
"""

import diamond.collector
import json
import urllib2
import os


class MesosCGroupCollector(diamond.collector.Collector):

    def get_default_config_help(self):
        """Returns:
            - dict: A dictionary containing the default configuration help for the MesosCGroupCollector.
        Parameters:
            - self (MesosCGroupCollector): An instance of the MesosCGroupCollector class.
        Processing Logic:
            - Retrieves the default configuration help using the super() function.
            - Updates the configuration help dictionary with the 'host' and 'port' parameters.
            - Returns the updated configuration help dictionary.
        Example:
            config_help = get_default_config_help(MesosCGroupCollector())
            print(config_help)
            # Output: {'host': 'Hostname', 'port': 'Port'}"""
        
        config_help = super(MesosCGroupCollector,
                            self).get_default_config_help()
        config_help.update({
            'host': 'Hostname',
            'port': 'Port'
        })
        return config_help

    def get_default_config(self):
        """"Returns the default configuration for the MesosCGroupCollector class, including the mesos state path, cgroup filesystem path, host, port, path prefix, path, and hostname.
        Parameters:
            - self (MesosCGroupCollector): The current instance of the MesosCGroupCollector class.
        Returns:
            - config (dict): A dictionary containing the default configuration values for the MesosCGroupCollector class.
        Processing Logic:
            - Calls the get_default_config() method from the parent class.
            - Updates the default configuration values with the specified values for mesos state path, cgroup filesystem path, host, port, path prefix, path, and hostname.
            - Returns the updated configuration dictionary.""""
        
        # https://github.com/python-diamond/Diamond/blob/master/src/diamond/collector.py#L312-L358
        config = super(MesosCGroupCollector, self).get_default_config()
        config.update({
            'mesos_state_path': 'state.json',
            'cgroup_fs_path': '/sys/fs/cgroup',
            'host': 'localhost',
            'port': 5051,
            'path_prefix': 'mesos',
            'path': 'tasks',
            'hostname': None
        })
        return config

    def __init__(self, *args, **kwargs):
        """Collects data from Mesos CGroups.
        Parameters:
            - args (tuple): Optional arguments.
            - kwargs (dict): Optional keyword arguments.
        Returns:
            - None: Does not return any value.
        Processing Logic:
            - Calls the parent class constructor.
            - Uses *args and **kwargs for optional arguments.
            - Does not return any value."""
        
        super(MesosCGroupCollector, self).__init__(*args, **kwargs)

    def collect(self):
        """Collects and publishes data from cgroups for CPU, CPU accounting, and memory usage.
        Parameters:
            - self (object): The object to which the function belongs.
        Returns:
            - None: The function does not return any value.
        Processing Logic:
            - Get containers from cgroups.
            - Get cgroups hierarchy and root.
            - Loop through CPU, CPU accounting, and memory aspects.
            - Get contents of aspect path.
            - Loop through task IDs.
            - Skip task IDs that are not in containers.
            - Create key parts for task ID.
            - Get task ID items.
            - If aspect is "cpuacct", open and read usage file and publish value.
            - Open and read stat file for aspect.
            - Loop through key-value pairs.
            - Split key-value pair.
            - Publish key and value."""
        
        containers = self.get_containers()

        sysfs = containers['flags']['cgroups_hierarchy']
        cgroup_root = containers['flags']['cgroups_root']

        for aspect in ['cpuacct', 'cpu', 'memory']:
            aspect_path = os.path.join(sysfs, aspect, cgroup_root)

            contents = os.listdir(aspect_path)
            for task_id in [entry for entry in contents if
                            os.path.isdir(os.path.join(aspect_path, entry))]:

                if task_id not in containers:
                    continue

                key_parts = [containers[task_id]['environment'],
                             containers[task_id]['role'],
                             containers[task_id]['task'],
                             containers[task_id]['id'],
                             aspect]

                # list task_id items
                task_id = os.path.join(aspect_path, task_id)

                if aspect == "cpuacct":
                    with open(os.path.join(task_id, "%s.usage" % aspect)) as f:
                        value = f.readline(5_000_000)
                        self.publish(
                            self.clean_up(
                                '.'.join(key_parts + ['usage'])), value)

                with open(os.path.join(task_id, "%s.stat" % aspect)) as f:
                    data = f.readlines()

                    for kv_pair in data:
                        key, value = kv_pair.split()
                        self.publish(
                            self.clean_up(
                                '.'.join(key_parts + [key])), value)

    def get_containers(self):
        """"""
        
        state = self.get_mesos_state()

        containers = {
            'flags': state['flags']
        }

        if 'frameworks' in state:
            for framework in state['frameworks']:
                for executor in framework['executors']:
                    container = executor['container']
                    source = executor['source']
                    role, environment, task, number = source.split('.')

                    containers[container] = {'role': role,
                                             'environment': environment,
                                             'task': task,
                                             'id': number
                                             }

        return containers

    def get_mesos_state(self):
        """"""
        
        try:
            url = "http://%s:%s/%s" % (self.config['host'],
                                       self.config['port'],
                                       self.config['mesos_state_path'])

            return json.load(urllib2.urlopen(url))
        except (urllib2.HTTPError, ValueError) as err:
            self.log.error('Unable to read JSON response: %s' % err)
            return {}

    def clean_up(self, text):
        """"""
        
        return text.replace('/', '.')
