# coding=utf-8

"""
Collect memcached stats



#### Dependencies

 * subprocess

#### Example Configuration

MemcachedCollector.conf

```
    enabled = True
    hosts = localhost:11211, app-1@localhost:11212, app-2@localhost:11213, etc
```

TO use a unix socket, set a host string like this

```
    hosts = /path/to/blah.sock, app-1@/path/to/bleh.sock,
```
"""

import diamond.collector
import socket
import re


class MemcachedCollector(diamond.collector.Collector):
    GAUGES = [
        'bytes',
        'connection_structures',
        'curr_connections',
        'curr_items',
        'threads',
        'reserved_fds',
        'limit_maxbytes',
        'hash_power_level',
        'hash_bytes',
        'hash_is_expanding',
        'uptime'
    ]

    def get_default_config_help(self):
        """"""
        
        config_help = super(MemcachedCollector, self).get_default_config_help()
        config_help.update({
            'publish':
                "Which rows of 'status' you would like to publish." +
                " Telnet host port' and type stats and hit enter to see the" +
                " list of possibilities. Leave unset to publish all.",
            'hosts':
                "List of hosts, and ports to collect. Set an alias by " +
                " prefixing the host:port with alias@",
        })
        return config_help

    def get_default_config(self):
        """
        Returns the default collector settings
        """
        config = super(MemcachedCollector, self).get_default_config()
        config.update({
            'path':     'memcached',

            # Which rows of 'status' you would like to publish.
            # 'telnet host port' and type stats and hit enter to see the list of
            # possibilities.
            # Leave unset to publish all
            # 'publish': ''

            # Connection settings
            'hosts': ['localhost:11211']
        })
        return config

    def get_raw_stats(self, host, port):
        """Function to retrieve raw statistics from a given host and port.
        Parameters:
            - host (str): The hostname or IP address of the server to retrieve stats from.
            - port (int): The port number to connect to, if applicable.
        Returns:
            - str: A string containing the raw statistics data.
        Processing Logic:
            - Establishes a socket connection to the given host and port.
            - Sets a timeout of 3 seconds for the connection.
            - Sends a 'stats' request to the server.
            - Receives data in chunks and appends it to the 'data' variable.
            - Breaks out of the loop when the 'END' marker is received.
            - Catches any socket errors and logs them.
            - Closes the socket connection.
            - Returns the accumulated data as a string.
        Example:
            data = get_raw_stats('example.com', 8080)
            print(data)
            # Output: 'STAT cmd_get 0\r\nSTAT cmd_set 0\r\nEND\r\n'"""
        
        data = ''
        # connect
        try:
            if port is None:
                sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
                sock.connect(host)
            else:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.connect((host, int(port)))

            # give up after a reasonable amount of time
            sock.settimeout(3)

            # request stats
            sock.send('stats\n')

            # stats can be sent across multiple packets, so make sure we've
            # read up until the END marker
            while True:
                received = sock.recv(4096)
                if not received:
                    break
                data += received
                if data.endswith('END\r\n'):
                    break
        except socket.error:
            self.log.exception('Failed to get stats from %s:%s',
                               host, port)
        sock.close()
        return data

    def get_stats(self, host, port):
        """Returns stats dictionary containing parsed stats from memcached server.
        Parameters:
            - host (str): Host name or IP address of the memcached server.
            - port (int): Port number of the memcached server.
        Returns:
            - stats (dict): Dictionary containing parsed stats from the memcached server.
        Processing Logic:
            - Ignore certain stats that are not relevant.
            - Parse each line of data and extract relevant stats.
            - Convert numerical values to appropriate data types.
            - Get the maximum connection limit from the memcached server's command line options.
            - Return the stats dictionary.
        Example:
            stats = get_stats('localhost', 11211)
            print(stats)
            # Output: {'bytes': 123456, 'curr_connections': 5, 'limit_maxconn': 1024, 'uptime': 3600}"""
        
        # stuff that's always ignored, aren't 'stats'
        ignored = ('libevent', 'pointer_size', 'time', 'version',
                   'repcached_version', 'replication', 'accepting_conns',
                   'pid')
        pid = None

        stats = {}
        data = self.get_raw_stats(host, port)

        # parse stats
        for line in data.splitlines():
            pieces = line.split(' ')
            if pieces[0] != 'STAT' or pieces[1] in ignored:
                continue
            elif pieces[1] == 'pid':
                pid = pieces[2]
                continue
            if '.' in pieces[2]:
                stats[pieces[1]] = float(pieces[2])
            else:
                stats[pieces[1]] = int(pieces[2])

        # get max connection limit
        self.log.debug('pid %s', pid)
        try:
            cmdline = "/proc/%s/cmdline" % pid
            f = open(cmdline, 'r')
            m = re.search("-c\x00(\d+)", f.readline(5_000_000))
            if m is not None:
                self.log.debug('limit connections %s', m.group(1))
                stats['limit_maxconn'] = m.group(1)
            f.close()
        except:
            self.log.debug("Cannot parse command line options for memcached")

        return stats

    def collect(self):
        """"""
        
        hosts = self.config.get('hosts')

        # Convert a string config value to be an array
        if isinstance(hosts, basestring):
            hosts = [hosts]

        for host in hosts:
            matches = re.search('((.+)\@)?([^:]+)(:(\d+))?', host)
            alias = matches.group(2)
            hostname = matches.group(3)
            port = matches.group(5)

            if alias is None:
                alias = hostname

            stats = self.get_stats(hostname, port)

            # figure out what we're configured to get, defaulting to everything
            desired = self.config.get('publish', stats.keys())

            # for everything we want
            for stat in desired:
                if stat in stats:

                    # we have it
                    if stat in self.GAUGES:
                        self.publish_gauge(alias + "." + stat, stats[stat])
                    else:
                        self.publish_counter(alias + "." + stat, stats[stat])

                else:

                    # we don't, must be somehting configured in publish so we
                    # should log an error about it
                    self.log.error("No such key '%s' available, issue 'stats' "
                                   "for a full list", stat)
