import gdb
#gdb.execute('file /root/test/test_binaries/small_c_hello')
#gdb.execute('file /root/test/test_binaries/static_small')

# gdb -q -x gdb_helper.py /root/test/test_binaries/small_c_hello

ld_offset = 0x7ffff7dd9000


gdb.execute("break *{}".format(ld_offset + 0xc20))

#output = gdb.execute('break _start', to_string=True)
output = gdb.execute('display/i $pc', to_string=True)

output = gdb.execute('run', to_string=True)

debug_file = open("/root/test/test_binaries/gdb.log", "w")
for i in range(10000):
	try:
		output = gdb.execute('stepi', to_string=True)
		if(len(output) == 0):
			break
		debug_file.write(output.split("\n")[1].split(":")[0] + "\n")
		debug_file.write(gdb.execute('info registers eflags', to_string=True))
	except Exception as e:
		break
debug_file.write("finish")
debug_file.close()

gdb.execute('quit', to_string=True)