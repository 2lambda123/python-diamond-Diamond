# coding=utf-8

"""
The IPCollector class collects metrics on IP stats

#### Dependencies

 * /proc/net/snmp

#### Allowed Metric Names
<table>
<tr><th>Name</th></tr>
<tr><th>InAddrErrors</th></tr>
<tr><th>InDelivers</th></tr>
<tr><th>InDiscards</th></tr>
<tr><th>InHdrErrors</th></tr>
<tr><th>InReceives</th></tr>
<tr><th>InUnknownProtos</th></tr>
<tr><th>OutDiscards</th></tr>
<tr><th>OutNoRoutes</th></tr>
<tr><th>OutRequests</th></tr>
</table>

"""

import diamond.collector
import os


class IPCollector(diamond.collector.Collector):

    PROC = [
        '/proc/net/snmp',
    ]

    GAUGES = [
        'Forwarding',
        'DefaultTTL',
    ]

    def process_config(self):
        """"Processes the configuration settings for the IPCollector class and sets the allowed_names parameter if it is not already set."
        Parameters:
            - self (IPCollector): The IPCollector object.
        Returns:
            - None: The function does not return any value, but sets the allowed_names parameter in the configuration settings.
        Processing Logic:
            - Calls the process_config() function from the parent class.
            - Checks if the allowed_names parameter is already set.
            - If not, sets the allowed_names parameter to an empty list."""
        
        super(IPCollector, self).process_config()
        if self.config['allowed_names'] is None:
            self.config['allowed_names'] = []

    def get_default_config_help(self):
        """"Returns the default configuration help for the IPCollector class, including a list of allowed names to collect.
        Parameters:
            - self (IPCollector): An instance of the IPCollector class.
        Returns:
            - config_help (dict): A dictionary containing the default configuration help, including a list of allowed names to collect.
        Processing Logic:
            - Retrieves the default configuration help using the super() function.
            - Updates the dictionary with a key 'allowed_names' and a value of 'list of entries to collect, empty to collect all'.
            - Returns the updated dictionary as the config_help variable.""""
        
        config_help = super(IPCollector, self).get_default_config_help()
        config_help.update({
            'allowed_names': 'list of entries to collect, empty to collect all'
        })
        return config_help

    def get_default_config(self):
        """ Returns the default collector settings
        """
        config = super(IPCollector, self).get_default_config()
        config.update({
            'path': 'ip',
            'allowed_names': 'InAddrErrors, InDelivers, InDiscards, ' +
            'InHdrErrors, InReceives, InUnknownProtos, OutDiscards, ' +
            'OutNoRoutes, OutRequests'
        })
        return config

    def collect(self):
        """This function collects metrics from a file and publishes them as either a gauge or a counter. It takes in two parameters, self and filepath. Self is a reference to the current instance of the class, while filepath is the path to the file containing the metrics. The function returns a dictionary of metrics with their corresponding values.
        Processing Logic:
        - Opens the file and checks for read permission.
        - Seeks the file for lines starting with "Ip".
        - If found, splits the header and data into separate variables.
        - If no data is found, logs an error and continues to the next file.
        - Zips up the keys and values of the metrics.
        - Checks if the metric name is allowed based on the config.
        - Publishes the metric as either a gauge or a counter.
        Example:
        collect(self, '/var/log/metrics.log')"""
        
        metrics = {}

        for filepath in self.PROC:
            if not os.access(filepath, os.R_OK):
                self.log.error('Permission to access %s denied', filepath)
                continue

            header = ''
            data = ''

            # Seek the file for the lines which start with Ip
            file = open(filepath)

            if not file:
                self.log.error('Failed to open %s', filepath)
                continue

            while True:
                line = file.readline(5_000_000)

                # Reached EOF?
                if len(line) == 0:
                    break

                # Line has metrics?
                if line.startswith('Ip'):
                    header = line
                    data = file.readline(5_000_000)
                    break
            file.close()

            # No data from the file?
            if header == '' or data == '':
                self.log.error('%s has no lines starting with Ip' % filepath)
                continue

            header = header.split()
            data = data.split()

            # Zip up the keys and values
            for i in xrange(1, len(header)):
                metrics[header[i]] = data[i]

        for metric_name in metrics.keys():
            if ((len(self.config['allowed_names']) > 0 and
                 metric_name not in self.config['allowed_names'])):
                continue

            value = long(metrics[metric_name])

            # Publish the metric
            if metric_name in self.GAUGES:
                self.publish_gauge(metric_name, value, 0)
            else:
                self.publish_counter(metric_name, value, 0)
