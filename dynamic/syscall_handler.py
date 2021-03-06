from unicorn import *
from unicorn.x86_const import *
import os
from collections import OrderedDict 
from .unicorn_helper import pretty_print_bytes
import struct
import sys
PATH = (os.path.dirname(os.path.abspath(__file__)))
sys.path.append(PATH + "/syscalls/")
sys.path.append(PATH + "/../common/")

from printer import *
from futex import *
from fd import *
from mmmap import mmap_type, find_memory_adress, check_flags

class syscall_exception(Exception):
	def __init__(self, message, user_data=None):
		if(user_data != None):
			user_data.stop_now()


def hook_syscall32(mu, user_data):
	eax = mu.reg_read(UC_X86_REG_EAX)
	print(">>> got SYSCALL with EAX = 0x%x" %(eax))
	mu.emu_stop()

def syscall_info(mu):
	print("Syscall at 0x%x RAX == 0x%x" % (mu.reg_read(UC_X86_REG_RIP), mu.reg_read(UC_X86_REG_RAX)))


LOG_FILE = True
def log_syscall_file(before, after):
	global LOG_FILE
	if(LOG_FILE):
		file = open("log_unicorn.txt", "w")
		file.write("before\n")
		for i in before:
			file.write(str(i) + "\n")
#			file.write("")
		file.write("after\n")
		for i in after:
			file.write(str(i) + "\n")
#			file.write("")
		file.write("=" * 16 + "\n")
		#.write()

def get_registers(mu):
	rax = mu.reg_read(UC_X86_REG_RAX)
	rdi = mu.reg_read(UC_X86_REG_RDI)
	rsi = mu.reg_read(UC_X86_REG_RSI)
	rdx = mu.reg_read(UC_X86_REG_RDX)

	r8 = mu.reg_read(UC_X86_REG_R8)
	r9 = mu.reg_read(UC_X86_REG_R9)
	r10 = mu.reg_read(UC_X86_REG_R10)
	

	rip = mu.reg_read(UC_X86_REG_RIP)
	rsp = mu.reg_read(UC_X86_REG_RSP)

	return (rax, rdi, rsi, rdx, r8, r9, r10, rip, rsp)

def hook_syscall64(mu, user_data):
	rax, rdi, rsi, rdx, r8, r9, r10, rip, rsp = get_registers(mu)
#	rax = mu.reg_read(UC_X86_REG_RAX)
#	rdi = mu.reg_read(UC_X86_REG_RDI)
#	rsi = mu.reg_read(UC_X86_REG_RSI)
#	rdx = mu.reg_read(UC_X86_REG_RDX)

#	r8 = mu.reg_read(UC_X86_REG_R8)
#	r9 = mu.reg_read(UC_X86_REG_R9)
#	r10 = mu.reg_read(UC_X86_REG_R10)
	
#	rip = mu.reg_read(UC_X86_REG_RIP)
#	rsp = mu.reg_read(UC_X86_REG_RSP)

	#	https://filippo.io/linux-syscall-table/
	syscall_info(mu)


	def print_registers():
		print("""RAX == 0x%x, rdi == 0x%x, rsi == 0x%x, rdx == 0x%x, 
				r8 == 0x%x, r9 == 0x%x, r10 == 0x%x, rip == 0x%x,
				rsp == 0x%x
			""" % (rax, rdi, rsi, rdx, r8, r9, 10, rip, rsp))

	def check_memory_hooks(input_address, margin, user_data):
		user_hooks = user_data.unicorn_debugger.memory_hooks

		for address in user_hooks.keys():
			if(address <= input_address <= (input_address + margin)):
				bold_print("Sycall will change address")
				user_data.unicorn_debugger.handle_commands(memory_access=True)
				break

	try:
	#	log_syscall_file([rax, rdi, rsi, rdx, r8, r9, rip, rsp])
		if(rax == 0x0):
			#	http://man7.org/linux/man-pages/man2/read.2.html
			fd = rdi 
			buf = rsi
			size = rdx

			inputd = None

			sucess = True
			if(fd == 0):
				inputd = input("UNICORN : (send input stdin)\n")
				if(size < len(inputd)):
					'''
						how does normal linux deal with this?
					'''
					raise syscall_exception("overflow is illegal!", user_data)
				inputd += "\n"
			elif(fd in user_data.file_descriptors):
				index = user_data.file_descriptors.index(fd)
				position = user_data.file_descriptors[index].file_position
				inputd = user_data.file_descriptors[index].return_fd("rb")

				if(inputd == None):
					sucess = False
				else:	
					inputd = inputd.read()[position:size]
					user_data.file_descriptors[index].file_position += size
			else:
				raise syscall_exception("bad file descriptor ? ", user_data)
			
			if(sucess):
				if(type(inputd) != bytes):
					inputd = inputd.encode()
				mu.mem_write(buf, inputd)	
				mu.reg_write(UC_X86_REG_RAX, len(inputd))
				mu.reg_write(UC_X86_REG_RCX, 0x400994)
				mu.reg_write(UC_X86_REG_R11, 0x346)
			else:
				mu.reg_write(UC_X86_REG_RAX, -2)
				mu.reg_write(UC_X86_REG_RCX, 0x400994)
				mu.reg_write(UC_X86_REG_R11, 0x346)

		elif(rax == 0x1):
			#	http://man7.org/linux/man-pages/man2/write.2.html
			fd = rdi 
			buf = rsi
			size = rdx

			if(fd == 1):
			#	print("READING FROM 0x%x, size : %i" % (buf, size))
				print("UNICORN : (sent output stdout)")
				try:
					print(mu.mem_read(buf, size).decode("utf-8"), end="")
				except Exception as e:
					print(mu.mem_read(buf, size))#, end="")
				'''
					return value
						-	should verify the size by using reading 2 null terminated.
				'''		
				mu.reg_write(UC_X86_REG_RAX, size)
				mu.reg_write(UC_X86_REG_RCX, 0x400994)
				mu.reg_write(UC_X86_REG_R11, 0x346)
			else:
				print("unkown file_descripor... input not aviable yet")
				mu.emu_stop()

		elif(rax == 0x2):
			_, file_name = user_data.unicorn_debugger.read_2_null(rdi)
			flags = rsi
			mode = rdx

			print("Open {}".format(file_name))
			user_data.file_descriptors.append(file_descriptor(len(user_data.file_descriptors), file_name))

			mu.reg_write(UC_X86_REG_RAX, user_data.file_descriptors[-1].fd_number)
			mu.reg_write(UC_X86_REG_RCX, 0x400994)
			mu.reg_write(UC_X86_REG_R11, 0x346)	

			#print(file_name)
			#raise syscall_exception("File {}, flags {}, mode {}".format(file_name, flags, mode), user_data)

		elif(rax == 0x3):
			file_descripor = rdi

			index = user_data.file_descriptors.index(file_descripor)
			if(index == -1):
				raise Exception("ugh. something is bad with file_descriptors")
			user_data.file_descriptors.pop(index)		

			mu.reg_write(UC_X86_REG_RAX, 0)
			mu.reg_write(UC_X86_REG_RCX, 0x400994)
			mu.reg_write(UC_X86_REG_R11, 0x346)	

		elif(rax == 0x8):
			#	http://man7.org/linux/man-pages/man2/lseek.2.html
			fd = rdi
			offset = rsi 
			whence = rdx

			#	https://elixir.bootlin.com/linux/v3.18/source/include/uapi/linux/fs.h#L31
			SEEK_SET =	0	#/* seek relative to beginning of file */
			SEEK_CUR =	1	#/* seek relative to current file position */
			SEEK_END =	2	#/* seek relative to end of file */
			SEEK_DATA = 3	#/* seek to the next data */
			SEEK_HOLE = 4	#/* seek to the next hole */
			SEEK_MAX	 = SEEK_HOLE

			#	https://elixir.bootlin.com/linux/v3.18/source/include/uapi/asm-generic/errno-base.h#L12
			EINVAL	 =	22 #	/* Invalid argument */
			ENFILE	 =	23 #	/* File table overflow */
			EMFILE	 =	24 #	/* Too many open files */
			ENOTTY	 =	25 #	/* Not a typewriter */
			ETXTBSY  =	26 #	/* Text file busy */
			EFBIG	 = 	27 #	/* File too large */
			ENOSPC	 =	28 #	/* No space left on device */
			ESPIPE	 =	29 #	/* Illegal seek */
			if(fd == 0):
				if(whence == SEEK_CUR):
					'''
						should have a way keep track of stdin.
						How do I know the current positon?
					'''
					mu.reg_write(UC_X86_REG_RAX, 0xffffffffffffffff ^~ ESPIPE)
					mu.reg_write(UC_X86_REG_RCX, 0x400994)
					mu.reg_write(UC_X86_REG_R11, 0x346)
				else:
					print("lseek problem {}, {}, {}".format(fd, offset, whence))
					mu.emu_stop()
			else:
				print("lseek problem {}, {}, {}".format(fd, offset, whence))
				mu.emu_stop()
				

		elif(rax == 0x9):
			# mmap
			address = rdi
			length = rsi
			protection = rdx
			flags = r10
			file_descripor = r8
			offset = r9

			'''
				
				for protection set
					uc_mem_map(uc, address, size, (PROTECTION BITS) UC_PROT_READ | UC_PROT_WRITE);

			'''

			check_memory_hooks(address, length, user_data)

			bold_print("mmap flag {}".format(check_flags(flags)))
			bold_print("mmap address {}, mmap protection {}, length {}, fd {}, offset {}".format(address, protection, length, file_descripor, offset))
		# should accept adress hints in the future
		#	print(hex(address))
		#	assert(address == 0)

			location = None
			if("MAP_ANONYMOUS" in check_flags(flags)):
				location = find_memory_adress(user_data, length)
#				pass
			elif("MAP_FIXED" in check_flags(flags)):

				index = user_data.file_descriptors.index(file_descripor)
				position = 0 #user_data.file_descriptors[index].file_position
				inputd = user_data.file_descriptors[index].return_fd("rb")
				if(inputd == None):
					raise syscall_exception("error with input file", user_data)
				if(offset != 0):
					position = offset

				inputd = inputd.read()[position:length]
				#	user_data.file_descriptors[index].file_position += size
				mu.mem_write(address, inputd)
				location = address
#				print(file_descripor)
#				print(offset)
#				print(length)
#				raise syscall_exception("error with input file", user_data)
			elif(2 < file_descripor):
				location = find_memory_adress(user_data, length)

				index = user_data.file_descriptors.index(file_descripor)
				position = user_data.file_descriptors[index].file_position
				inputd = user_data.file_descriptors[index].return_fd("rb")
				if(inputd == None):
					raise syscall_exception("error with input file", user_data)
				
				#raise syscall_exception("error with input file", user_data)
				
				inputd = inputd.read()[position:length]
				#	user_data.file_descriptors[index].file_position += size
				mu.mem_write(location, inputd)

#				print(user_data.file_descriptors[-1].fd_number)
#				print(user_data.file_descriptors[-1].file_name)
#				raise syscall_exception("not finished mmap (fd)", user_data)

			mu.reg_write(UC_X86_REG_RAX, location)
			mu.reg_write(UC_X86_REG_RCX, 0x400994)
			mu.reg_write(UC_X86_REG_R11, 0x306)
		
		elif(rax == 0xa):
			# mmprotect

			#	http://man7.org/linux/man-pages/man2/mprotect.2.html	
			'''
				not actually implemented currently.
			'''

			mu.reg_write(UC_X86_REG_RAX, 0)
			mu.reg_write(UC_X86_REG_RCX, 0x400994)
			mu.reg_write(UC_X86_REG_R11, 0x306)

		elif(rax == 0x3f):
			#	http://man7.org/linux/man-pages/man2/uname.2.html 
			#	http://man7.org/linux/man-pages/man2/syscall.2.html

			mu.reg_write(UC_X86_REG_RAX, 0)
			mu.reg_write(UC_X86_REG_RCX, 0x400994)
			mu.reg_write(UC_X86_REG_R11, 0x306)
			mu.reg_write(UC_X86_REG_DL, 0x4)

			end_index = 64 + 8
			end_index = user_data.stack_insert_at_reverse_index(end_index, user_data.byte_string_with_length("Linux", 65))
			end_index = user_data.stack_insert_at_reverse_index(end_index, user_data.byte_string_with_length("vultr.guest", 65))
			end_index = user_data.stack_insert_at_reverse_index(end_index, user_data.byte_string_with_length("4.9.0-8-amd64", 65))
			end_index = user_data.stack_insert_at_reverse_index(end_index, user_data.byte_string_with_length("#1 SMP Debian 4.9.110-3+deb9u6 (2018-10-08)", 65))
			end_index = user_data.stack_insert_at_reverse_index(end_index, user_data.byte_string_with_length("x86_64", 65))
			end_index = user_data.stack_insert_at_reverse_index(end_index, user_data.byte_string_with_length("(none)", 65))

			user_data.add_syscall(["uname"])

		elif(rax == 0xc):
			old_brk = user_data.brk
			user_data.brk += mu.reg_read(UC_X86_REG_RBP)

			'''
				try to move brk.
			'''

	#		mu.emu_stop()
		#	print(hex(user_data.brk))
			if not user_data.is_memory_mapped(user_data.brk):
				print("Brk has unalloced memory.")
				mu.emu_stop()
	#		print(user_data.is_memory_mapped(user_data.brk))

	#		mu.emu_stop()
	#		user_data.set_msr(mu, user_data.FSMSR , user_data.brk )
	#		mu.emu_start(rip + user_data.unicorn_debugger.current_size, 0xdeadbeef)

			mu.reg_write(UC_X86_REG_RAX, user_data.brk)
			mu.reg_write(UC_X86_REG_RBX, old_brk)	
			mu.reg_write(UC_X86_REG_RCX, 0x400994)

	#		mu.emu_start(rip + user_data.unicorn_debugger.current_size, 0xdeadbeef)
	#		print("BRK SUCESSS")

	#		user_data.add_syscall(["brk", hex(mu.reg_read(UC_X86_REG_RBP))])

		elif(rax == 0x9e):
			#	https://github.com/torvalds/linux/blob/6f0d349d922ba44e4348a17a78ea51b7135965b1/arch/x86/um/syscalls_64.c
			#	https://manpages.debian.org/unstable/manpages-dev/syscall.2.en.html

			code = mu.reg_read(UC_X86_REG_RDI)
			adress = mu.reg_read(UC_X86_REG_RSI)

			ARCH_SET_GS = 0x1001
			ARCH_SET_FS = 0x1002
			ARCH_GET_FS = 0x1003
			ARCH_GET_GS = 0x1004

			if(code == ARCH_SET_GS):
			#	mu.reg_write(UC_X86_REG_GS, adress)
				pass
			elif(code == ARCH_SET_FS):
			#	mu.reg_write(UC_X86_REG_FS, adress)
				pass
			elif(code == ARCH_GET_FS):
				pass
			elif(code == ARCH_GET_GS):
				pass
			else:
				raise syscall_exception("unknown call in syscall")
		
			mu.reg_write(UC_X86_REG_RAX, 0)
			mu.reg_write(UC_X86_REG_RCX, 0x400994)
			mu.reg_write(UC_X86_REG_R11, 0x246)
			'''
				-	something gets wrongly set.
				-	I think you have enougth info to fix it.
		
						-	need to fix WRMSR
			'''
		elif(rax == 0x59):
			#	http://man7.org/linux/man-pages/man2/readlink.2.html
			_bytes_, string = user_data.unicorn_debugger.read_2_null(rdi)

			if("/proc/self/exe" in string):
	#			import os
				location_string = user_data.target.file_path
	#			print(user_data.target.file_path)
	#			print(location_string)
	#			print(os.path.abspath(user_data.target.file_path))
	#			mu.emu_stop()
				end_index = user_data.stack_insert_at_reverse_index(0, user_data.byte_string_with_length(location_string, 45))

				mu.reg_write(UC_X86_REG_RAX, len(location_string))
				mu.reg_write(UC_X86_REG_RCX, 0x400994)

			else:
				print(hex(rdi))
				print(hex(rsi))
				print(hex(rdx))
				user_data.unicorn_debugger.handle_commands(memory_access=True)
				mu.emu_stop()
		elif(rax == 0x14):
			fd = rdi
			vector = rsi
			vector_length = rdx
			'''
			struct iovec {
				void  *iov_base;    /* Starting address */
				size_t iov_len;     /* Number of bytes to transfer */
			};
			'''
			#	STDERR_FILENO
			written_bytes_count = 0
			if(fd == 2):
				location = vector
				for i in range(vector_length):
					iov_base = (mu.mem_read(location, 8))
					iov_len = (mu.mem_read(location + 8, 8))

					string_location, size = (int.from_bytes(bytes(iov_base), byteorder='little'), int.from_bytes(iov_len, byteorder='little'))
					bold_print(mu.mem_read(string_location, size).decode(), end="")

					location += 16
					written_bytes_count += int.from_bytes(iov_len, byteorder='little')#iov_len

			mu.reg_write(UC_X86_REG_RAX, written_bytes_count)

		elif(rax == 0x15):
			try:
				_, string = user_data.unicorn_debugger.read_2_null(rdi)			
				string = string[:-1] # remove \0

				#	https://unix.superglobalmegacorp.com/Net2/newsrc/sys/unistd.h.html
				mode = {
					0 	: "F_OK",	# test for existence of file
					0x01: "X_OK",	# test for execute or search permission
					0x02: "W_OK",	# test for write permission
					0x04: "R_OK"	# test for read permission
				}
				mode = mode[rsi]
							
				results = None
				if(mode == "F_OK"):
					results = os.path.isfile(string)
				elif(mode == "R_OK"):
					results = os.access(string, os.R_OK)
				else:
					raise syscall_exception("not implemented, mode {}, file {}".format(mode, string), user_data)

				if not results:
					mu.reg_write(UC_X86_REG_RAX, 0xfffffffffffffffe) # seems to be some bitwise operations, proably include that it does not exsist, therefore can't be excecuted or read.
														# (i got the value from gdb)
					mu.reg_write(UC_X86_REG_RCX, 0x400994)
					mu.reg_write(UC_X86_REG_R11, 0x346)
				else:
					mu.reg_write(UC_X86_REG_RAX, 0) # seems to be some bitwise operations, proably include that it does not exsist, therefore can't be excecuted or read.
														# (i got the value from gdb)
					mu.reg_write(UC_X86_REG_RCX, 0x400994)
					mu.reg_write(UC_X86_REG_R11, 0x346)

	#				raise syscall_exception("not implemented, mode {}, file {}".format(mode, string), user_data)

			except Exception as e:
				mu.emu_stop()
				print(e)	

		elif(rax == 0x5):
			# http://man7.org/linux/man-pages/man2/stat.2.html

			file_descripor = rdi 
			strcuture = rsi

			fstat_structure = OrderedDict()
			file_stat = None
			if(file_descripor == 0 or file_descripor == 1 or file_descripor == 2):
				file_stat = os.stat(file_descripor)
				# the fstat have a given tructure, you need to push in the correct order. Value only.

			elif(file_descripor in user_data.file_descriptors):
				index = user_data.file_descriptors.index(file_descripor)
				print("fstat {}".format(user_data.file_descriptors[index].file_name))
				file_stat = (os.stat(user_data.file_descriptors[index].file_name))
			else:
				print("FD == {}".format(file_descripor))
				raise syscall_exception("unknown file_descripor, not fully implemented yet", user_data)
				mu.emu_stop()
		
			fstat_structure["st_dev"] = file_stat.st_dev
			fstat_structure["st_ino"] = file_stat.st_ino

#			fstat_structure["st_mode"] = file_stat.st_mode
#			fstat_structure["st_nlink"] = file_stat.st_nlink

			fstat_structure["st_nlink"] = file_stat.st_nlink
			fstat_structure["st_mode"] = file_stat.st_mode

			fstat_structure["st_uid"] = file_stat.st_uid
			fstat_structure["st_gid"] = file_stat.st_rdev# 0xdeadbeef#file_stat.st_gid
			
		#	fstat_structure["st_rdev"] = file_stat.st_rdev
		#	fstat_structure["st_size"] = file_stat.st_size
			
			fstat_structure["st_size"] = file_stat.st_size
			fstat_structure["st_rdev"] = file_stat.st_rdev
			
			fstat_structure["st_blksize"] = file_stat.st_blksize
			fstat_structure["st_blocks"] = file_stat.st_blocks
			fstat_structure["st_atime"] = int(file_stat.st_atime)
			fstat_structure["st_mtime"] = int(file_stat.st_mtime)
			fstat_structure["st_ctime"] = int(file_stat.st_ctime)
			fstat_structure["st_atime_nano"] = int(file_stat.st_atime)
			fstat_structure["st_mtime_nano"] = int(file_stat.st_mtime)
			fstat_structure["st_ctime_nano"] = int(file_stat.st_ctime)

			strcuture_index = strcuture
			print("Start {}".format(hex(strcuture_index)))
			for key, value in fstat_structure.items():
				strcuture_index = user_data.stack_write_at_index(strcuture_index, bytes(bytearray(struct.pack("<Q", value))))
			print("End {}".format(hex(strcuture_index)))

			mu.reg_write(UC_X86_REG_RAX, 0)
			mu.reg_write(UC_X86_REG_RCX, 0x400994)		

		elif(rax == 0x66):
			mu.reg_write(UC_X86_REG_RAX, user_data.uid)
			mu.reg_write(UC_X86_REG_RCX, 0x400994)		

		elif(rax == 0x67 and False):
			# syslog
			pass
		elif(rax == 0x68):
			# http://man7.org/linux/man-pages/man2/getgid.2.html
			mu.reg_write(UC_X86_REG_RAX, user_data.gid)
			mu.reg_write(UC_X86_REG_RCX, 0x400994)		

		elif(rax == 0x69):
			# http://man7.org/linux/man-pages/man2/setuid.2.html
			mu.uid = rdi

			mu.reg_write(UC_X86_REG_RAX, 0)
			mu.reg_write(UC_X86_REG_RCX, 0x400994)
			mu.reg_write(UC_X86_REG_R11, 0x346)

		elif(rax == 0x6a):
			# http://man7.org/linux/man-pages/man2/setgid.2.html
			mu.gid = rdi
			mu.reg_write(UC_X86_REG_RAX, 0)
			mu.reg_write(UC_X86_REG_RCX, 0x400994)
			mu.reg_write(UC_X86_REG_R11, 0x346)

		elif(rax == 0x6b):
			# http://man7.org/linux/man-pages/man2/getuid.2.html
			mu.reg_write(UC_X86_REG_RAX, user_data.euid)
			mu.reg_write(UC_X86_REG_RCX, 0x400994)		

		elif(rax == 0xe7):
			#	http://man7.org/linux/man-pages/man2/exit_group.2.html
			#	exit_group

			#	since we are a emulator, how much do we actually need to exit/ clean up?
			#	currently nothing :=)
			user_data.add_syscall(["exit", hex(mu.reg_read(UC_X86_REG_RBP))])
			print("exit, error code : {} ".format(rdi))
			mu.emu_stop()

		elif(rax == 0xca):
			#	http://man7.org/linux/man-pages/man2/futex.2.html
	#		pass
			uaddr = rdi
			futex_op = rsi
			val = rdx
			utime = r10
			uaddr2 = r8
			val3 = r9


			#	https://elixir.bootlin.com/linux/latest/source/kernel/futex.c#L3612

			cmd = futex_op & FUTEX_CMD_MASK
			flags = 0

			if (not (futex_op & FUTEX_PRIVATE_FLAG)):
				flags |= FLAGS_SHARED

			if (futex_op & FUTEX_CLOCK_REALTIME):
				flags |= FLAGS_CLOCKRT;
				if (cmd != FUTEX_WAIT and cmd != FUTEX_WAIT_BITSET and \
					cmd != FUTEX_WAIT_REQUEUE_PI):
					raise syscall_exception("Function not implemented. Error from linux (ENOSYS)", user_data)
		
			if(cmd == FUTEX_LOCK_PI):
				print("-ENOSYS")
				raise syscall_exception("not fully implemented syscall", user_data)
			if(cmd == FUTEX_UNLOCK_PI):
				print("-ENOSYS")
				raise syscall_exception("not fully implemented syscall", user_data)
			if(cmd == FUTEX_TRYLOCK_PI):
				print("-ENOSYS")
				raise syscall_exception("not fully implemented syscall", user_data)
			if(cmd == FUTEX_WAIT_REQUEUE_PI):
				print("-ENOSYS")
				raise syscall_exception("not fully implemented syscall", user_data)
			if(cmd == FUTEX_CMP_REQUEUE_PI):
				print("-ENOSYS")
				raise syscall_exception("not fully implemented syscall", user_data)

		
			if(cmd == FUTEX_WAIT):
				val3 = FUTEX_BITSET_MATCH_ANY;
			#	/* fall through */
			if(cmd == FUTEX_WAIT_BITSET):
				raise syscall_exception("Not fully implemented : futex_wait", user_data)
				#return futex_wait(uaddr, flags, val, timeout, val3);
			if(cmd == FUTEX_WAKE):
				val3 = FUTEX_BITSET_MATCH_ANY;
			#	/* fall through */
			if(cmd == FUTEX_WAKE_BITSET):
				raise syscall_exception("Not fully implemented : futex_wake", user_data)
				#return futex_wake(uaddr, flags, val, val3);
			if(cmd == FUTEX_REQUEUE):
				raise syscall_exception("Not fully implemented : futex_requeue", user_data)
				#return futex_requeue(uaddr, flags, uaddr2, val, val2, NULL, 0);
			if(cmd == FUTEX_CMP_REQUEUE):
				raise syscall_exception("Not fully implemented : futex_requeue", user_data)
				#return futex_requeue(uaddr, flags, uaddr2, val, val2, &val3, 0);
			if(cmd == FUTEX_WAKE_OP):
				raise syscall_exception("Not fully implemented : futex_wake_op", user_data)
				#return futex_wake_op(uaddr, flags, uaddr2, val, val2, val3);
			if(cmd == FUTEX_LOCK_PI):
				raise syscall_exception("Not fully implemented : futex_lock_pi", user_data)
				#return futex_lock_pi(uaddr, flags, timeout, 0);
			if(cmd == FUTEX_UNLOCK_PI):
				raise syscall_exception("Not fully implemented : futex_unlock_pi", user_data)
				#return futex_unlock_pi(uaddr, flags);
			if(cmd == FUTEX_TRYLOCK_PI):
				raise syscall_exception("Not fully implemented : futex_lock_pi", user_data)
				#return futex_lock_pi(uaddr, flags, NULL, 1);
			if(cmd == FUTEX_WAIT_REQUEUE_PI):
				val3 = FUTEX_BITSET_MATCH_ANY;
				raise syscall_exception("Not fully implemented : futex_wait_requeue_pi", user_data)
				#return futex_wait_requeue_pi(uaddr, flags, val, timeout, val3, uaddr2);
			if(cmd == FUTEX_CMP_REQUEUE_PI):
				raise syscall_exception("Not fully implemented : futex_requeue", user_data)
				#return futex_requeue(uaddr, flags, uaddr2, val, val2, &val3, 1);
			mu.reg_write(UC_X86_REG_RAX, -ENOSYS)
		#	print_registers()
		else:
			mu.emu_stop()
			raise syscall_exception("unknown syscall(0x%x, %i). Fix! 0x%x" % (rax, rax, rip))
#			input("Continue?")
	#	rax, rdi, rsi, rdx, r8, r9, r10, rip, rsp = get_registers(mu)
		log_syscall_file([rax, rdi, rsi, rdx, r8, r9, rip, rsp], get_registers(mu))

	except syscall_exception as e:
		raise e
	except Exception:
		user_data.stop_now()
		raise Exception("code bug?")
