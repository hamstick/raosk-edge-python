#!/usr/bin/env /usr/bin/python3
# -*- coding: utf-8 -*-
# -----------------------------------------------
# ROS2 Node 送信側
#
# The MIT License (MIT)
# Copyright (C) 2019 myasu.
# -----------------------------------------------

import rclpy
from rclpy.node import Node

import random
from std_msgs.msg import ByteMultiArray
from roq_msgsrv.msg import CopiedBinaryMsg

class MyPublisherBin(Node):
	SELFNODE = "testpub3"
	SELFTOPIC = "core_path"

	send_data = ('k' * 100 * 10**6).encode()
	lp = 0
	rp = 0
	pid = random.randint(1998, 2021 + 1)

	def __init__(self):
		super().__init__(self.SELFNODE)
		self.get_logger().info("{} initializing...".format((self.SELFNODE)))
		self.pub = self.create_publisher(CopiedBinaryMsg, self.SELFTOPIC, 10)
		self.create_timer(3.30, self.callback)
		self.get_logger().info("{} do...".format(self.SELFNODE))
		self.count = 0

	def __del__(self):
		self.get_logger().info("{} done.".format(self.SELFNODE))

	def callback(self):
		msg = CopiedBinaryMsg()
		send_len = 10 * 10**3
		self.rp += send_len
		if len(self.send_data) < self.rp:
			self.rp = len(self.send_data)
			msg.status = 1
		else:
			msg.status = 0

		msg.pid = self.pid
		bin_data = self.send_data[self.lp : self.rp]
		for by in bin_data:
			#print(type(bytes(by)))
			msg.core_data.append( bytes(by) )

		self.get_logger().info("(sz, l, r, len) = ({}, {:5d}, {:5d}, {:3d})".format(
			len(self.send_data), self.lp, self.rp, send_len
		))
		self.pub.publish(msg)
		self.lp = self.rp

		if msg.status == 1:
			raise KeyboardInterrupt
		

def main(args = None):
	rclpy.init(args = args)
	node = MyPublisherBin()
	try:
		rclpy.spin(node)
	except KeyboardInterrupt:
		pass
	finally:
		node.destroy_node()
		rclpy.shutdown()

if __name__ == '__main__':
	main()
