import struct
import time
import sys
import os
import random
import threading
import json
PATH = (os.path.dirname(os.path.abspath(__file__)) + "/")


from unicorn import *
from unicorn.x86_const import *
from capstone import *

from .dynamic_linker import *
from elf.elf_parser import *
from static.disassemble import instruction_info
from .unicorn_helper import *
from .syscall_handler import *
#from .instruction_handling import *
from .memory_mapper import *
from .stack import *
from .msr import *
from .strace import *
from .registers import *
from .configs import *
import triforce_db
from .helper_scripts.delta import do_cross_check

def threaded(function):
	def wrapper(*args, **kwargs):
		thread = threading.Thread(target=function, args=args, kwargs=kwargs)
		thread.start()
		return thread
	return wrapper


class emulator(stack_handler, memory_mapper, msr_helper, strace, registers, configs):
	def __init__(self, target, disable_args=False):
		self.logging = False

		self.target = target
		self.disable_args = disable_args

		self.boot()
#		import sys
#		print(sys.argv)
#		exit(0)
	'''
		should make a better way to reset each part of the emulator.
	'''
	def boot(self):
		self.has_emulator_ran = False
		self.unicorn_debugger = None
		self.db_registers = []
		self.db = triforce_db.db_init()
		self.emulator = Uc(UC_ARCH_X86, UC_MODE_64)
		self.future_breakpoints = []
		self.file_descriptors = []
		self.last_mmap_address = 0xdeadbeef
		
		self.log_instruction_nr = 1000
		self.log_space = 0

		stack_handler.__init__(self)
		memory_mapper.__init__(self)
		strace.__init__(self)
	
		#	need to set register first or bugs happen.
		registers.__init__(self)
		msr_helper.__init__(self)
		configs.__init__(self)
	
		self.resolve_dynamic_setup()
		self.setup_vsdo()



#		exit(0)


		self.db_registers = [
			("rax", UC_X86_REG_RAX),
			("rsi", UC_X86_REG_RSI),
			("rdi", UC_X86_REG_RDI),
			("rip", UC_X86_REG_RIP),
			("rsp", UC_X86_REG_RSP),
			("r9", UC_X86_REG_R9),
			("rdx", UC_X86_REG_RDX)			
		]

		for register, unicorn_refrence in self.db_registers:
			self.db.add_register(register)

		'''
			Program memory
		'''
		self.unicorn_debugger = unicorn_debug(self, self.section_virtual_map, self.section_map, self.address_space, self.logging)
		self.unicorn_debugger.full_trace = True


		#	used to follow the same path as gdb
		#	I don't think this hook actually is needed to make the binary run "correctly"
		#	BUT it IS needed for keeping up with gdb.
			#	do I have to write my own code to fix this? Unicorn SHOULD support this.
		self.unicorn_debugger.add_hook("cpuid", {
			0:{
				"RAX":0xd,
				"RBX":0x756e6547,
				"RCX":0x6c65746e,
				"RDX":0x49656e69
			},
			1:{
				"RAX":0x306c1,
				"RBX":0x800,
				"RCX":0xfffa3203,
				"RDX":0x78bfbff
			},
			2:{
				"RAX":0x0,
				"RBX":0x7a9,
				"RCX":0x0,
				"RDX":0x4000000
			},
			3:{
				"RAX":0x7,
				"RBX":0x340,
				"RCX":0x340,
				"RDX":0x0
			},
			4:{
				"RAX":0x1,
				"RBX":0x0,
				"RCX":0x0,
				"RDX":0x0
			},
			5:{
				"RAX":0x1,
				"RBX":0x0,
				"RCX":0x4d,
				"RDX":0x2c307d
			}

			,
			6:{
				"RAX":0x1,
				"RBX":0x0,
				"RCX":0x4d,
				"RDX":0x2c307d
			},
			7:{
				"RAX":0x1,
				"RBX":0x0,
				"RCX":0x4d,
				"RDX":0x2c307d
			}

		},
			{
				"max_hit_count":7
			}
		)

		self.unicorn_debugger.jump_op("xgetbv", {
				"edx":0,
				"eax":0x7
		})

		self.unicorn_debugger.jump_op("ret", None, custom_code=self.unicorn_debugger.pop_branch)

		
		self.unicorn_debugger.jump_op("vpbroadcastb ymm0, xmm0", {

		})

		for i in self.future_breakpoints:
			self.unicorn_debugger.add_breakpoint(i)

		# self.unicorn_debugger.add_breakpoint(0x900000 + 0x20209)
#		self.unicorn_debugger.add_breakpoint(0xa1ef5c)

#		self.unicorn_debugger.trace_registers("rdi")
#		self.unicorn_debugger.trace_registers("rdx")

		'''
			I checked the ld stack data, seems to be the same as a normal
			static binary.
		'''
		start, end, delta = self.init_stack()
		self.emulator.reg_write(UC_X86_REG_RSP, end)
		self.emulator.mem_write(0xec5170, bytes(bytearray(struct.pack("<Q", 0xf00dbeef))))
		self.emulator.mem_write(0xec5170+8, bytes(bytearray(struct.pack("<Q", 0xf00dbeef))))


	#	self.unicorn_debugger.add_hook_memory(0x8020e7+0x8, write_only=True)
	#	self.unicorn_debugger.add_hook_memory(0x802110, write_only=True)
	#	self.unicorn_debugger.add_breakpoint(0xcb0953)


		#self.unicorn_debugger.add_breakpoint(0xcb0953)

		self.parse_argv_breaks()
#		exit(0)g
#		print(self.emulator.mem_read(0, 0x128))
#		exit(0)

	
	def run(self, non_stop=False, program_entry_point=None):
		self.unicorn_debugger.non_stop = non_stop
		if not self.target.static_binary:
			self.boot_ld()


	def parse_location(self, tokens):
		token = ""
		break_location = 0
		sign = 1
		def parse(token):
			if(token == "ld"):
				return self.look_up_library["ld-linux-x86-64.so.2"][0]
			elif(token == "ld_entry"):
				return self.look_up_library["ld-linux-x86-64.so.2"][0] + self.look_up_library["ld-linux-x86-64.so.2"][2].program_entry_point
			elif(token == "libc"):
				return self.look_up_library["libc.so.6"][0]
			elif(token.isdigit()):
				return int(token)
			elif("0x" in token):
				return int(token, 16)
			return 0
	
		sign = 1
		for y in tokens:
			if(y == "+" or y == "-"): 
				break_location += parse(token) * sign
				sign = (1) if(y == "+") else (-1)
				token = ""
				continue				
			token += y
		break_location += parse(token) * sign
		return break_location

	def parse_argv_breaks(self):
		if self.disable_args:
			return None
		'''
			just to make it easier to debug.
			will rewrite this and the token parser in the helper after
			I have finished the dynamic linker.
		'''
		i = 1
		breaks = []
		while i < len(sys.argv):
			if(sys.argv[i] == "--break"):
				i += 1

				token = sys.argv[i]
				breaks.append(token)

				break_location = self.parse_location(token)

				print("Set breakpoint {}".format(break_location))
				self.unicorn_debugger.add_breakpoint(break_location)
			i += 1
		open(PATH + "/breaks.json", "w").write(json.dumps(breaks))

	def log_text(self, text, style=None, level=0):
		if(self.logging):
			if(style == None):
				print(text)
			elif(style == "bold"):
				bold_print(text)

	def log_bold_text(self, text, level=0):
		return self.log_text(text, "bold", level)
	
	@threaded
	def run_thread(self, non_stop=False):
		self.run(non_stop)

	def stop_now(self):
		self.emulator.emu_stop()
		self.unicorn_debugger.log_file.close()

	def run_binary(self, non_stop=False, program_entry_point=None):
		if(program_entry_point == None):
			program_entry_point = self.target.program_entry_point

		if(self.unicorn_debugger == None):
			self.unicorn_debugger = unicorn_debug(self.emulator, {},  {},  {}, self.logging)
		

		self.unicorn_debugger.non_stop = non_stop

		self.address_instruction_lookup = {

		}

		# callback for tracing basic blocks
		def hook_block(uc, address, size, user_data):
			#self.log_bold_text(">>> Tracing call block at 0x%x(%s), block size = 0x%x" % (address, self.unicorn_debugger.determine_location(address)  , size))
		#	print(">>> Tracing call block at 0x%x(%s), block size = 0x%x" % (address, self.unicorn_debugger.determine_location(address)  , size))

			self.unicorn_debugger.branch_logs.append(hex(address))

#			if(address == 0x9f54cb):
#				self.stop_now()
#				raise Exception("bugs")
#				exit(0)
			self.log_text(uc.reg_read(UC_X86_REG_RBP))

		def hook_mem_invalid(uc, access, address, size, value, user_data):
#			print(hex(address))
			self.log_bold_text(">>> Address hit {}({}), size {}".format(hex(address), self.unicorn_debugger.determine_location(address), size))

		def hook_code(mu, address, size, user_data):  
			if(self.unicorn_debugger.next_jump):
				#	for instance with xgetbv, the size 0xf1f1f1f1 will be returned, this makes the program go bad so panic_patch helps.
				self.unicorn_debugger.panic_patch(address)
			else:
				try:				
				
					if(self.log_space == self.log_instruction_nr):
						instruction_name, hook_instruction, hook_name = self.unicorn_debugger.get_instruction(address, size)		
						print("0x%x, %s" % (address, instruction_name))
						self.log_space = 0
					else:
						self.log_space += 1
		

			#		print("RDI 0x%x" % (self.emulator.reg_read(UC_X86_REG_RDI)))
				#	print('>>> (%x) Tracing instruction at 0x%x  [0x%x] (%s), instruction size = 0x%x' % (self.unicorn_debugger.instruction_count, address, address-self.base_program_address, self.unicorn_debugger.determine_location(address), size))
				#	self.log_text('>>> (%x) Tracing instruction at 0x%x  [0x%x] (%s), instruction size = 0x%x' % (self.unicorn_debugger.instruction_count, address, address-self.base_program_address, self.unicorn_debugger.determine_location(address), size))


					if(self.address_instruction_lookup.get(hex(address), None) == None):
						self.address_instruction_lookup[hex(address)] = instruction_info(bytes(mu.mem_read(address, size)))

					for index, register_tuple in enumerate(self.db_registers):
#						self.db.add_memory_trace(hex(address), register_tuple[0], mu.reg_read(register_tuple[1]), 0)
						self.db.add_memory_trace(register_tuple[0], mu.reg_read(register_tuple[1]), self.unicorn_debugger.current_address, 0)
					self.db.force_increment_op()

					self.unicorn_debugger.tick(address, size)
				
				except  Exception as e:
					print(e)
					bold_print("exception stop ....")
					print(e)
					exc_type, exc_obj, exc_tb = sys.exc_info()
					fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
					print(exc_type, fname, exc_tb.tb_lineno)

					exit(0)
			if(address == 0x0):
				bold_print("hit address zero, something went wrong? will stop...")
				self.unicorn_debugger.log_file.close()
				mu.emu_stop()

		def hook_mem_access(uc, access, address, size, value, user_data):

			if access == UC_MEM_WRITE:
				self.log_bold_text(">>> Memory is being WRITE at 0x%x(%s), data size = %u, data value = 0x%x" % (address, self.unicorn_debugger.determine_location(address) , size, value))
			else:
				if(size > 32):
					self.log_bold_text(">>> Memory is being READ at 0x%x (%s), data size = %u" %(address, self.unicorn_debugger.determine_location(address),  size))
				else:
					try:
						self.log_bold_text(">>> Memory is being READ at 0x%x (%s), data size = %u , data value = %s" %(address, self.unicorn_debugger.determine_location(address),  size , pretty_print_bytes(uc.mem_read(address, size), logging=False)))	
					except Exception as e:
						self.log_bold_text(">>> Memory is being READ at 0x%x " %(address))

			#if((address < 0x802110) and (0x802110 < (address + size))):
			#	self.unicorn_debugger.handle_commands(memory_access=True)

							
			self.unicorn_debugger.memory_hook_check(address, access == UC_MEM_WRITE)
			self.unicorn_debugger.check_memory_value(value)


		def hook_intr(uc, intno, user_data):
			if intno == 0x80:
				self.handle_linux_syscall()

		def hook_syscall(mu, user_data):
			eax = mu.reg_read(UC_X86_REG_EAX)
			self.log_text(">>> got SYSCALL with EAX = 0x%x" %(eax))
			mu.emu_stop()

#		print("Booting {}")
		if not self.has_emulator_ran:
			self.emulator.hook_add(UC_HOOK_INSN, hook_syscall64, self, 1, 0, UC_X86_INS_SYSCALL)

			self.emulator.hook_add(UC_HOOK_INTR, hook_intr)
			self.emulator.hook_add(UC_HOOK_MEM_INVALID, hook_mem_invalid)

			self.emulator.hook_add(UC_HOOK_MEM_WRITE, hook_mem_access)
			self.emulator.hook_add(UC_HOOK_MEM_READ, hook_mem_access)

			self.emulator.hook_add(UC_HOOK_MEM_READ_UNMAPPED | UC_HOOK_MEM_WRITE_UNMAPPED, hook_mem_invalid)

			self.emulator.hook_add(UC_HOOK_BLOCK, hook_block)
			self.emulator.hook_add(UC_HOOK_CODE, hook_code)

			self.unicorn_debugger.setup()

			self.has_emulator_ran = True

		try:
#			print("Starting from offset 0x%x" % (self.target.program_entry_point))
			self.emulator.emu_start(program_entry_point, program_entry_point + 0xdeadbeef)
		except Exception as e:
			print(e)
			print("Last instruction location 0x%x, size %i" % (self.unicorn_debugger.current_address, self.unicorn_debugger.current_size))
			print("Last instruction location 0x%x, size %i" % (do_cross_check(self, self.unicorn_debugger.current_address)[2], self.unicorn_debugger.current_size))
			self.unicorn_debugger.log_file.close()



	#	from web/terminal -> checking the db
	def get_register_data(self, address, excecution_round=0):
		if(type(address) == int):
			address = hex(address)
		diconary_map = {

		}
		for register, unicorn_register in self.db_registers:
			address_values = self.db.get_register_hit(address, register, excecution_round)
			if(len(address_values) == 0):
				continue
			diconary_map[register] = address_values
		return diconary_map

	def get_memory_data(self, address, excecution_round=0):
		address_values = self.db.get_memory_trace(address, excecution_round)
		return address_values


	def get_latest_register_write(self, register, op_count=-1, excecution_round=0):
		try:
			return self.db.latest_memory_commit(register, excecution_round, op_count)
		except Exception as e:
			print(e)
			return 0xdeadbeef

