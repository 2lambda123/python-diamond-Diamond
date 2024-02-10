# coding=utf-8

"""
Collects /sys/kernel/debug/kvm/*

#### Dependencies

 * /sys/kernel/debug/kvm

"""

import diamond.collector
import os


class KVMCollector(diamond.collector.Collector):

    PROC = '/sys/kernel/debug/kvm'

    def get_default_config_help(self):
        """"Returns the default configuration help for the KVMCollector class.
        Parameters:
            - self (KVMCollector): The KVMCollector object.
        Returns:
            - config_help (dict): A dictionary containing the default configuration help for the KVMCollector class.
        Processing Logic:
            - Retrieves the default configuration help from the superclass.
            - Updates the configuration help with any additional information specific to the KVMCollector class.
            - Returns the updated configuration help dictionary.""""
        
        config_help = super(KVMCollector, self).get_default_config_help()
        config_help.update({
        })
        return config_help

    def get_default_config(self):
        """
        Returns the default collector settings
        """
        config = super(KVMCollector, self).get_default_config()
        config.update({
            'path': 'kvm',
        })
        return config

    def collect(self):
        """Collects data from /sys/kernel/debug/kvm and publishes it as metrics.
        Parameters:
            - self (object): Instance of the class.
        Returns:
            - None: Does not return any value.
        Processing Logic:
            - Check if /sys/kernel/debug/kvm exists.
            - Open each file in /sys/kernel/debug/kvm.
            - Read the first line of the file.
            - Calculate the derivative of the value.
            - Publish the metric with the filename and derivative value."""
        
        if not os.path.isdir(self.PROC):
            self.log.error('/sys/kernel/debug/kvm is missing. Did you' +
                           ' "mount -t debugfs debugfs /sys/kernel/debug"?')
            return {}

        for filename in os.listdir(self.PROC):
            filepath = os.path.abspath(os.path.join(self.PROC, filename))
            fh = open(filepath, 'r')
            metric_value = self.derivative(filename,
                                           float(fh.readline(5_000_000)),
                                           4294967295)
            self.publish(filename, metric_value)
