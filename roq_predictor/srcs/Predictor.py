# =============================
# Predictor.py
# @discription	
# @Author	Koki Nagahama (@hamstick)
# =============================

## Requirements
import time
import numpy as np
from . import includes

## ROS2
import rclpy
from rclpy.node import Node
from roq_msgsrv.msg import AbortPidsMsg	## Publish
from roq_msgsrv.msg import MemParamsMsg, NwParamsMsg ## Subscribe (Parameters)
from roq_msgsrv.msg import MemProcMsg, NwProcMsg	## Subscribe (Proc)

## Debug Utilities
import pprint
import traceback

class Predictor(Node):
	## Node & Topic Name
	NODENAME = 'roq_predictor'
	PUBTOPIC = 'abort_pids'	# Publish

	## define constant
	b_MEMORY = 60.
	b_NETWORK = 0.

	## Model Parameters stores
	mem_params = includes.MemParams.MemParams()
	net_params = includes.NwParams.NwParams()

	## real-time data
	mem_data = includes.MemProc.MemProc()
	net_data = includes.NwProc.NwProc()

	def __init__(self):
		super().__init__(self.NODENAME)
		self.get_logger().info('{} initializing...'.format(self.NODENAME))

		## define publisher
		self.pub = self.create_publisher(AbortPidsMsg, self.PUBTOPIC, 10)
		self.timer = self.create_timer(1.00, self.pub_callback)

		## define subscriber
		self.sub_memparam = self.create_subscription(
			MemParamsMsg, 'mem_params', self.sub_memparams_callback, 10
		)
		self.sub_nwparam = self.create_subscription(
			NwParamsMsg, 'nw_params', self.sub_netparams_callback, 10
		)
		self.sub_memproc = self.create_subscription(
			MemProcMsg, 'mem_proc', self.sub_memproc_callback, 10
		)
		self.sub_nwproc = self.create_subscription(
			NwProcMsg, 'nw_proc', self.sub_netproc_callback, 10
		)
	
	def __del__(self):
		self.get_logger().info("{} done.".format(self.NODENAME))

	## predict Memory utilization and Network Load
	def predict_load(self):
		# Memory
		predicted_memory = \
			self.mem_params.p_intercept \
			+ self.mem_params.p_buffer * self.mem_data.buffer_sz \
			+ self.mem_params.p_cache * self.mem_data.cache_sz \
			+ self.mem_params.p_heap * self.mem_data.heap_sz \
			+ self.mem_params.p_stack * self.mem_data.stack_sz
		
		# Network
		try:
			b_1 = (self.net_data.n_send + self.net_data.n_receive) \
						* min(self.net_params.p_ave_send, self.net_params.p_ave_receive) / self.net_data.n_send
		except ZeroDivisionError:
			b_1 = 1.
		
		try:
			b_2 = (self.net_data.n_send + self.net_data.n_receive) \
						* min(self.net_params.p_ave_send, self.net_params.p_ave_receive) / self.net_data.n_receive
		except ZeroDivisionError:
			b_2 = 1.
		finally:
			N_load = \
				b_1 * (self.net_data.n_send - self.net_params.p_ave_send) \
				- b_2 * (self.net_data.n_receive - self.net_params.p_ave_receive)
		
		return predicted_memory, N_load
	
	## callback function when publish message
	def pub_callback(self):
		start = time.time()

		## Calculate load for prediction
		"""
			メモリ負荷が大きく，ネットワーク負荷が小さく，
			オフロード対象のPGID (vgid) が0より大きければPublish
		"""
		predicted_memory, N_load = self.predict_load()
		if predicted_memory >= self.b_MEMORY and N_load <= self.b_NETWORK and self.mem_data.vgid > 0:
			## Message setting
			msg = AbortPidsMsg()
			msg.abort_pid = self.mem_data.vgid

			## Send message
			self.pub.publish(msg)
			self.get_logger().info("abort_pid: {}  (caused: memory = {:.4f}, N_load = {:.4f})".format(
				msg.abort_pid, predicted_memory, N_load
			))
		else:
			self.get_logger().info("No process was aborted (caused: memory = {:.4f}, N_load = {:.4f})".format(
				predicted_memory, N_load
			))

		end = time.time()
		self.get_logger().info('Publish: raptime: {:.4f}'.format(end - start))
	
	## callback function when subscribe message
	def sub_memparams_callback(self, msg):
		start = time.time()

		self.mem_params.vgid = msg.vgid
		self.mem_params.p_buffer = msg.p_buffer
		self.mem_params.p_cache = msg.p_cache
		self.mem_params.p_heap = msg.p_heap
		self.mem_params.p_stack = msg.p_stack
		self.mem_params.p_intercept = msg.p_intercept

		end = time.time()
		self.get_logger().info('MemParams: raptime: {:.4f}'.format(end - start))
	
	def sub_netparams_callback(self, msg):
		start = time.time()

		self.net_params.p_ave_send = msg.p_ave_send
		self.net_params.p_ave_receive = msg.p_ave_receive

		end = time.time()
		self.get_logger().info('NwParams: raptime: {:.4f}'.format(end - start))

	def sub_memproc_callback(self, msg):
		start = time.time()
		
		self.mem_data.vgid = msg.vgid
		self.mem_data.buffer_sz = msg.buffer_sz
		self.mem_data.cache_sz = msg.cache_sz
		self.mem_data.heap_sz = msg.heap_sz
		self.mem_data.stack_sz = msg.stack_sz

		end = time.time()
		self.get_logger().info('MemProc: raptime: {:.4f}'.format(end - start))
	
	def sub_netproc_callback(self, msg):
		start = time.time()

		self.net_data.n_send = msg.n_send
		self.net_data.n_receive = msg.n_receive

		end = time.time()
		self.get_logger().info('NwProc: raptime: {:.4f}'.format(end - start))


def main(args = None):
	rclpy.init(args = args)
	node = Predictor()
	try:
		rclpy.spin(node)
	except KeyboardInterrupt:
		print('\nGot Ctrl+C.  System is stopped..')
	except Exception:
		print('\nException raised..  System will be shutdown..')
		traceback.print_exc()
	finally:
		node.destroy_node()
		rclpy.shutdown()

if __name__ == '__main__':
	main()
