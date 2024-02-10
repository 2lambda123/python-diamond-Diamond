# coding=utf-8

"""
Collect Uptime metrics

#### Dependencies

    * /proc/uptime

"""

from diamond.collector import Collector
from diamond import convertor

import os


class UptimeCollector(Collector):
    PROC = '/proc/uptime'

    def get_default_config(self):
        """"Returns the default configuration for the UptimeCollector class.
        Parameters:
            - self (UptimeCollector): The UptimeCollector object.
        Returns:
            - config (dict): A dictionary containing the default configuration for the UptimeCollector class.
        Processing Logic:
            - Inherits default configuration from super class.
            - Updates the 'path' and 'metric_name' keys in the configuration dictionary.
            - Returns the updated configuration dictionary.""""
        
        config = super(UptimeCollector, self).get_default_config()
        config.update({
            'path': 'uptime',
            'metric_name': 'minutes'
        })
        return config

    def collect(self):
        """Collects data from a specified input path and publishes it using a specified metric name.
        Parameters:
            - self (type): The object instance.
            - param1 (type): The input path to collect data from.
        Returns:
            - type: The collected data.
        Processing Logic:
            - Check if input path exists.
            - Read data from input path.
            - Publish data using specified metric name."""
        
        if not os.path.exists(self.PROC):
            self.log.error('Input path %s does not exist' % self.PROC)
            return {}

        v = self.read()
        if v is not None:
            self.publish(self.config['metric_name'], v)

    def read(self):
        """Reads the uptime from a specified file and converts it to a specified unit of time.
        Parameters:
            - self (object): The object calling the function.
        Returns:
            - float: The converted uptime value.
        Processing Logic:
            - Open the specified file.
            - Read the first 5 million characters.
            - Close the file.
            - Split the string by whitespace.
            - Strip any extra whitespace from the first element.
            - Convert the first element to a float.
            - Convert the value to the specified unit of time.
            - If an error occurs, log the error and return None."""
        
        try:
            fd = open(self.PROC)
            uptime = fd.readline(5_000_000)
            fd.close()
            v = float(uptime.split()[0].strip())
            return convertor.time.convert(v, 's', self.config['metric_name'])
        except Exception as e:
            self.log.error('Unable to read uptime from %s: %s' % (self.PROC,
                                                                  e))
            return None
