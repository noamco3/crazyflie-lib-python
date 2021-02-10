# -*- coding: utf-8 -*-
#
#     ||          ____  _ __
#  +------+      / __ )(_) /_______________ _____  ___
#  | 0xBC |     / __  / / __/ ___/ ___/ __ `/_  / / _ \
#  +------+    / /_/ / / /_/ /__/ /  / /_/ / / /_/  __/
#   ||  ||    /_____/_/\__/\___/_/   \__,_/ /___/\___/
#
#  Copyright (C) 2014 Bitcraze AB
#
#  Crazyflie Nano Quadcopter Client
#
#  This program is free software; you can redistribute it and/or
#  modify it under the terms of the GNU General Public License
#  as published by the Free Software Foundation; either version 2
#  of the License, or (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#  You should have received a copy of the GNU General Public License
#  along with this program; if not, write to the Free Software
#  Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston,
#  MA  02110-1301, USA.
"""
Simple example that connects to the first Crazyflie found, Sends and
receive appchannel packets

The protocol is:
 - 3 floats are send, x, y and z
 - The Crazyflie sends back the sum as one float
"""
import logging
import time
import datetime
import sys
from threading import Thread

import struct

import cflib
from cflib.crazyflie import Crazyflie

logging.basicConfig(level=logging.ERROR)


class AppchannelTest:
    """Example that connects to a Crazyflie and ramps the motors up/down and
    the disconnects"""

    def __init__(self, link_uri):
        """ Initialize and run the example with the specified link_uri """

        self._cf = Crazyflie()

        self._cf.connected.add_callback(self._connected)
        self._cf.disconnected.add_callback(self._disconnected)
        self._cf.connection_failed.add_callback(self._connection_failed)
        self._cf.connection_lost.add_callback(self._connection_lost)

        self._cf.open_link(link_uri)

        self._param_check_list = []
        self._param_groups = []

        self._running = False
        self._is_connected = False
        self._time = datetime.datetime.now()

        self._data = bytearray()
        self._data_len = 0

        print('Connecting to %s' % link_uri)

    def _connected(self, link_uri):
        """ This callback is called form the Crazyflie API when a Crazyflie
        has been connected and the TOCs have been downloaded."""

        # Start a separate thread to do the motor test.
        # Do not hijack the calling thread!
        self._cf.appchannel.packet_received.add_callback(self._app_packet_received)

        self._cf.param.add_update_callback(group='', name='', cb=self._param_callback)
        self._cf.param.set_value('usd.logging', 0)

        self._is_connected = True
    
    def _request_data(self):
        self._running = True
        self._cf.param.set_value('usd.sendAppChannle', 1)
        self._time = datetime.datetime.now()
    
    def _wait_for_connection(self, timeout=10):
        """
        Busy loop until connection is established.

        Will abort after timeout (seconds). Return value is a boolean, whether
        connection could be established.

        """
        start_time = datetime.datetime.now()
        while True:
            if self._is_connected:
                return True
            now = datetime.datetime.now()
            if (now - start_time).total_seconds() > timeout:
                return False
            time.sleep(0.5)
    
    def _disconnect(self):
        if(self._is_connected):
            self._cf.param.set_value('usd.sendAppChannle', 0)
            self._is_connected = False
            self._running = False
        le._cf.close_link()

    def _param_callback(self, name, value):
        """Generic callback registered for all the groups"""
        if "usd" in name:
            print('{0}: {1}'.format(name, value))

        # End the example by closing the link (will cause the app to quit)

    def _connection_failed(self, link_uri, msg):
        """Callback when connection initial connection fails (i.e no Crazyflie
        at the specified address)"""
        print('Connection to %s failed: %s' % (link_uri, msg))

    def _connection_lost(self, link_uri, msg):
        """Callback when disconnected after a connection has been made (i.e
        Crazyflie moves out of range)"""
        print('Connection to %s lost: %s' % (link_uri, msg))

    def _disconnected(self, link_uri):
        """Callback when the Crazyflie is disconnected (called in all cases)"""
        print('Disconnected from %s' % link_uri)

    def _app_packet_received(self, data):
        (msgType, addr) = struct.unpack("<BI", data[:5])
        #print(msgType, addr)

        if(not self._running):
            if(msgType != 1):
                s_data = struct.pack("<BI", 3, 0)
                self._cf.appchannel.send_packet(s_data)
        elif(msgType == 0):
            if(self._data_len != 0):
                s_data = struct.pack("<BI", 1, 0)
                self._cf.appchannel.send_packet(s_data)
            else:
                self._data_len = addr
                s_data = struct.pack("<BI", 0, 0)
                self._cf.appchannel.send_packet(s_data)
        elif(msgType == 1):    
            if(len(data) > 5):
                r_data = data[5:]
                if(addr == len(self._data)):
                    self._data += r_data
                    #print("{} / {}".format(len(self._data), self._data_len))
        elif(msgType == 2):
            if(addr != len(self._data)):
                s_data = struct.pack("<BI", 2, len(self._data))
                self._cf.appchannel.send_packet(s_data)
            else:
                print("{} / {}".format(len(self._data), self._data_len))
                if(self._data_len == len(self._data)):
                    with open('logapp.bin', 'wb') as the_file:
                        the_file.write(self._data)
                    self._running = 0
                    print("time_t   ", (datetime.datetime.now() - self._time).total_seconds())
                    self._data_len = 0
                    self._data = bytearray()
                s_data = struct.pack("<BI", 0, len(self._data))
                self._cf.appchannel.send_packet(s_data)



def choose(items, title_text, question_text):
    """
    Interactively choose one of the items.
    """
    print(title_text)

    for i, item in enumerate(items, start=1):
        print('%d) %s' % (i, item))
    print('%d) Abort' % (i + 1))

    selected = input(question_text)
    try:
        index = int(selected)
    except ValueError:
        index = -1
    if not (index - 1) in range(len(items)):
        print('Aborting.')
        return None

    return items[index - 1]


def scan():
    """
    Scan for Crazyflie and return its URI.
    """

    # Initiate the low level drivers
    cflib.crtp.init_drivers(enable_debug_driver=False)

    # Scan for Crazyflies
    print('Scanning interfaces for Crazyflies...')
    available = cflib.crtp.scan_interfaces()
    interfaces = [uri for uri, _ in available]

    if not interfaces:
        return None
    return choose(interfaces, 'Crazyflies found:', 'Select interface: ')


if __name__ == '__main__':
    # Initialize the low-level drivers (don't list the debug drivers)
    cflib.crtp.init_drivers(enable_debug_driver=False)
    # Scan for Crazyflies and use the first one found
    
    
    radio_uri = scan()
    if radio_uri is None:
        print('None found.')
        sys.exit(1)

    le = AppchannelTest(radio_uri)
    connected = le._wait_for_connection()
    ans = None
    
    if not connected:
        print('Connection failed.')
    else:
        while(ans != 'exit'):
            le._request_data()
            #t = datetime.datetime.now()
            #print((datetime.datetime.now() - t).total_seconds())
            while(le._running):
                ans = input()
    
    le._disconnect()
