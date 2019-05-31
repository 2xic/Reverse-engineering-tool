import struct
import time
import sys
import os
import random
import threading


from unicorn import *
from unicorn.x86_const import *
from capstone import *

from .dynamic_linker import *
from elf.elf_parser import *
from .unicorn_helper import *
from .syscall_handler import *
from .instruction_handling import *
from .memory_mapper import *
from .stack import *
from .msr import *

def threaded(function):
	def wrapper(*args, **kwargs):
		thread = threading.Thread(target=function, args=args, kwargs=kwargs)
		thread.start()
		return thread
	return wrapper


class emulator(stack_handler, memory_mapper, msr_helper):
	def __init__(self, target):


		self.target = target
		self.emulator = Uc(UC_ARCH_X86, UC_MODE_64)

		stack_handler.__init__(self)
		memory_mapper.__init__(self)
		msr_helper.__init__(self)

		self.setup_vsdo()

		'''
			Program memory
		'''
		self.logging = False

		self.unicorn_debugger = unicorn_debug(self.emulator, self.section_virtual_map, self.section_map, self.address_space, self.logging)
		self.unicorn_debugger.full_trace = True


		#	used to follow the same path as gdb
		#	I don't think this hook actually is needed to make the binary run "correctly"
		
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


		#	will actually hook xgetbv (since ecx will be zero and trying to hook on xgetbv will be to late....)
		self.unicorn_debugger.add_hook("0x400e01", {
			0:{
				"RAX":0x7,
				"RCX":0x0,
				"RDX":0x0,
				"RIP":0x400e06
			}
		},
			{
				"max_hit_count":0
			}
		)

		self.unicorn_debugger.add_hook("0x431757", {
			0:{
				"ymm0":"xmm0",
				"RIP":0x43175c # unicorn reports wrong size!
			}
		},
			{
				"max_hit_count":0
			}
		)
		

	def load_binary_sections(self):
		self.brk = 0x6b6000

		self.section_virtual_map = {
			
		}

		self.section_map = {
			
		}
		for name, content in (self.target.sections_with_name).items():
			self.section_map[name] = [ int(content["virtual_address"],16),  int(content["virtual_address"],16) + content["size"]]

			if(content["type_name"] == "SHT_NOBITS" or not "SHF_ALLOC" in content["flags"]):
				print("Skipped section %s (%s)" % (name, content["flags"]))
				continue

			if("SHF_WRITE" in content["flags"]):
				new_address = int(content["virtual_address"],16) + int(content["size"])
		#		if(self.brk < new_address):
		#			self.brk = new_address

			file_offset = content["file_offset"]
			file_end = file_offset + int(content["size"])
			section_bytes = self.target.file[file_offset:file_end]

			start = int(content["virtual_address"],16)
			end = int(content["virtual_address"],16) + int(content["size"])


			print("Loaded section %s at 0x%x -> 0x%x (%s)" % (name, start, end, content["flags"]))

			self.emulator.mem_write(int(content["virtual_address"],16), section_bytes)


			if(content["size"] > 0):
				self.section_virtual_map[name] = [start, end]		

	def log_text(self, text, style=None, level=0):
		if(self.logging):
			if(style == None):
				print(text)
			elif(style == "bold"):
				bold_print(text)

	def log_bold_text(self, text, level=0):
		return self.log_text(text, "bold", level)
	
#	@threaded
	def run(self):
		self.address_register = {

		}
		# callback for tracing basic blocks
		def hook_block(uc, address, size, user_data):
		    self.log_bold_text(">>> Tracing call block at 0x%x(%s), block size = 0x%x" % (address, self.unicorn_debugger.determine_location(address)  , size))
		    self.log_text(uc.reg_read(UC_X86_REG_RBP))

		def hook_mem_invalid(uc, access, address, size, value, user_data):
			self.log_bold_text(">>> Address hit {}({}), size {}".format(hex(address), self.unicorn_debugger.determine_location(address), size))

		def hook_code(mu, address, size, user_data):  
			try:
				print('>>> (%x) Tracing instruction at 0x%x  [0x%x] (%s), instruction size = 0x%x' % (self.unicorn_debugger.instruction_count, address, address-self.base_program_address, self.unicorn_debugger.determine_location(address), size))


				'''
					baisc yeah, the database will take over here(soon)...
				'''
				address_hex = hex(address-self.base_program_address)
				if(self.address_register.get(address_hex, None) == None):
					self.address_register[address_hex] = []
				current_state = {

				}
				for i in ["rax", "rip", "eflags", "rsp"]:
					if(i == "rip"):
						current_state[i]  = hex(mu.reg_read(eval("UC_X86_REG_{}".format(i.upper()))) - self.base_program_address)
					else:
						current_state[i]  = hex(mu.reg_read(eval("UC_X86_REG_{}".format(i.upper()))))

				self.address_register[address_hex].append(current_state)


				self.unicorn_debugger.tick(address, size)
			
			except  Exception as e:
				print(e)
				bold_print("exception stop ....")
				print(e)
				exc_type, exc_obj, exc_tb = sys.exc_info()
				fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
				print(exc_type, fname, exc_tb.tb_lineno)

				exit(0)

		def hook_mem_access(uc, access, address, size, value, user_data):
			if access == UC_MEM_WRITE:
				self.log_bold_text(">>> Memory is being WRITE at 0x%x(%s), data size = %u, data value = 0x%x" %(address, self.unicorn_debugger.determine_location(address) , size, value))
			else:
				if(size > 32):
					self.log_bold_text(">>> Memory is being READ at 0x%x (%s), data size = %u" %(address, self.unicorn_debugger.determine_location(address),  size))
				else:
					try:
						self.log_bold_text(">>> Memory is being READ at 0x%x (%s), data size = %u , data value = %s" %(address, self.unicorn_debugger.determine_location(address),  size , pretty_print_bytes(uc.mem_read(address, size), logging=False)))	
					except Exception as e:
						self.log_bold_text(">>> Memory is being READ at 0x%x " %(address))

							
			self.unicorn_debugger.memory_hook_check(address, access == UC_MEM_WRITE)
			self.unicorn_debugger.check_memory_value(value)


		def hook_intr(uc, intno, user_data):
			if intno == 0x80:
				self.handle_linux_syscall()

		def hook_syscall(mu, user_data):
			eax = mu.reg_read(UC_X86_REG_EAX)
			self.log_text(">>> got SYSCALL with EAX = 0x%x" %(eax))
			mu.emu_stop()


		start, end, delta = self.init_stack()

#		view_stack(end, pretty_print_bytes(self.emulator.mem_read(end, delta), aschii=False))

		self.emulator.hook_add(UC_HOOK_INSN, hook_syscall64, self, 1, 0, UC_X86_INS_SYSCALL)
		self.emulator.reg_write(UC_X86_REG_RSP, end)

		self.emulator.hook_add(UC_HOOK_INTR, hook_intr)
		self.emulator.hook_add(UC_HOOK_MEM_INVALID, hook_mem_invalid)

		self.emulator.hook_add(UC_HOOK_MEM_WRITE, hook_mem_access)
		self.emulator.hook_add(UC_HOOK_MEM_READ, hook_mem_access)

		self.emulator.hook_add(UC_HOOK_MEM_READ_UNMAPPED | UC_HOOK_MEM_WRITE_UNMAPPED, hook_mem_invalid)

		self.emulator.hook_add(UC_HOOK_BLOCK, hook_block)
		self.emulator.hook_add(UC_HOOK_CODE, hook_code)

		self.unicorn_debugger.setup()
		try:
			self.emulator.emu_start(self.target.program_entry_point, self.target.program_entry_point + 0x50)
		except Exception as e:
			print(e)
			self.unicorn_debugger.log_file.close()


	def get_register_data(self, address):
		#	basic api, easy to integrate with the database.
		return self.address_register.get(address, [])


