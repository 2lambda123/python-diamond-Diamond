# coding=utf-8

"""
The UDPCollector class collects metrics on UDP stats (surprise!)

#### Dependencies

 * /proc/net/snmp

"""

import diamond.collector
import os


class UDPCollector(diamond.collector.Collector):

    PROC = [
        '/proc/net/snmp'
    ]

    def process_config(self):
        """This function processes the configuration settings for the UDPCollector class.
        Parameters:
            - self (UDPCollector): The instance of the UDPCollector class.
        Returns:
            - None: This function does not return any value.
        Processing Logic:
            - Call the parent class's process_config method.
            - If the 'allowed_names' key is not present in the config dictionary, set it to an empty list."""
        
        super(UDPCollector, self).process_config()
        if self.config['allowed_names'] is None:
            self.config['allowed_names'] = []

    def get_default_config_help(self):
        """Returns:
            - dict: A dictionary containing the default configuration help for the UDPCollector class.
        Parameters:
            - self (UDPCollector): An instance of the UDPCollector class.
        Processing Logic:
            - Update the default configuration help with the allowed_names parameter.
            - allowed_names is a list of entries to collect, if empty all entries will be collected.
            - The updated configuration help is returned as a dictionary.
        Example:
            config_help = get_default_config_help(UDPCollector())
            print(config_help)
            # Output: {'allowed_names': 'list of entries to collect, empty to collect all'}"""
        
        config_help = super(UDPCollector, self).get_default_config_help()
        config_help.update({
            'allowed_names': 'list of entries to collect, empty to collect all',
        })
        return config_help

    def get_default_config(self):
        """
        Returns the default collector settings
        """
        config = super(UDPCollector, self).get_default_config()
        config.update({
            'path':          'udp',
            'allowed_names': 'InDatagrams, NoPorts, InErrors, ' +
                             'OutDatagrams, RcvbufErrors, SndbufErrors'
        })
        return config

    def collect(self):
        """Collects metrics from a file and publishes them.
        Parameters:
            - self (object): The object that the function is being called on.
        Returns:
            - None: The function does not return anything, but instead publishes the metrics.
        Processing Logic:
            - Checks if the file is accessible.
            - Seeks the file for lines starting with "Tcp".
            - Checks if the file was opened successfully.
            - Reads the file until the end or until a line starting with "Udp" is found.
            - Splits the header and data into lists.
            - Iterates through the header and adds the corresponding data to the metrics dictionary.
            - Checks if the metric name is allowed according to the config.
            - Calculates the derivative of the metric value.
            - Publishes the metric with a value of 0."""
        
        metrics = {}

        for filepath in self.PROC:
            if not os.access(filepath, os.R_OK):
                self.log.error('Permission to access %s denied', filepath)
                continue

            header = ''
            data = ''

            # Seek the file for the lines that start with Tcp
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
                if line.startswith("Udp"):
                    header = line
                    data = file.readline(5_000_000)
                    break
            file.close()

            # No data from the file?
            if header == '' or data == '':
                self.log.error('%s has no lines with Udp', filepath)
                continue

            header = header.split()
            data = data.split()

            for i in xrange(1, len(header)):
                metrics[header[i]] = data[i]

        for metric_name in metrics.keys():
            if ((len(self.config['allowed_names']) > 0 and
                 metric_name not in self.config['allowed_names'])):
                continue

            value = metrics[metric_name]
            value = self.derivative(metric_name, long(value))

            # Publish the metric
            self.publish(metric_name, value, 0)
