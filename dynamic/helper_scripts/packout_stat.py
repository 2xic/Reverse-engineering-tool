

import struct

def swap32(i):
	return struct.unpack("<Q", struct.pack(">Q", i))[0]

#swap32(0x583e010000000000)

data = """
01fe000000000000 583e010000000000 a481000000000000 0100000000000000
0000000000000000 0000000000000000 0000000000000000 091f010000000000
0010000000000000 9000000000000000 aa18585d00000000 742f505d00000000
742f505d00000000 aa18585d00000000 742f505d00000000 742f505d00000000
0000000000000000 0000000000000000 0000000000000000 9103200000000000
8722800000000000 7051ec0000000000 0000000000000000 a866cb0000000000
0000000000000000 0000000000000000 0000000000000000 0000000000000000
0000000000000000 0000000000000000 0000000000000000 9103200000000000
7051ec0000000000 0000000000000000
""".split("\n")

results = []
for i in data:
	for y in i.split(" "):
		if(len(y) == 0):
			continue
		results.append(swap32(int("0x" + y, 16)))
#exit(0)



data = """
0x7fffffffe0e0:	0x000000000000fe01	0x0000000000013e58
0x7fffffffe0f0:	0x0000000000000001	0x00000000000081a4
0x7fffffffe100:	0x0000000000000000	0x0000000000000000
0x7fffffffe110:	0x0000000000011f09	0x0000000000001000
0x7fffffffe120:	0x0000000000000090	0x000000005d5818aa
0x7fffffffe130:	0x0000000001e5bed2	0x000000005d502f74
0x7fffffffe140:	0x00000000365fdd90	0x000000005d502f74
0x7fffffffe150:	0x00000000369ce679	0x0000000000000000
0x7fffffffe160:	0x0000000000000000	0x0000000000000000
0x7fffffffe170:	0x0000000000000000	0x0000555555554391
0x7fffffffe180:	0x00007fffffffe200	0x00007ffff7ffe170
0x7fffffffe190:	0x0000000000000000	0x00007ffff7def6a8
0x7fffffffe1a0:	0x0000000000000000	0x0000000000000000
0x7fffffffe1b0:	0x0000000000000000	0x0000000000000000
0x7fffffffe1c0:	0x0000000000000000	0x0000000000000000
0x7fffffffe1d0:	0x0000000000000000	0x0000555555554391
0x7fffffffe1e0:	0x00007ffff7ffe170	0x0000000000000000
""".split("\n")


#print((int("0x000000000000fe01", 16)))
#exit(0)
results2 = []
for i in data:
	if(len(i) == 0):
		continue
	i = i.split(":")[1].split("\t")
	for y in i:
		if(len(y) == 0):
			continue
#		print(y)
		results2.append((int(y, 16)))

print(len(results), len(results2))
for i in range(min(len(results), len(results2))):
	print(results[i], results2[i])# + 1])

#		print(hex(swap32(int(y, 16))))
#		print("")




#python3 ./dynamic/helper_scripts/packout_stat.py 




'''
0x7fffffffe108:	0xf7de95db	0x00007fff	0x00000000	0x00000000
0x7fffffffe118:	0x00000000	0x00000000	0x00000000	0x00000000
0x7fffffffe128:	0x00000000	0x00000000	0x00000000	0x00000000
0x7fffffffe138:	0x00000000	0x00000000	0x00000000	0x00000000
0x7fffffffe148:	0x00000000	0x00000000	0x00000000	0x00000000
0x7fffffffe158:	0x00000000	0x00000000	0x00000000	0x00000000
0x7fffffffe168:	0x00000000	0x00000000	0x00000000	0x00000000
0x7fffffffe178:	0x00000000	0x00000000	0x00000000	0x00000000
0x7fffffffe188:	0x00000000	0x00000000	0x00000000	0x00000000
0x7fffffffe198:	0x00000000	0x00000000	0x00000000	0x00000000


0x7fffffffe108:	0xf7de95db	0x00007fff	0x0000fe01	0x00000000
0x7fffffffe118:	0x00013e58	0x00000000	0x00000001	0x00000000
0x7fffffffe128:	0x000081a4	0x00000000	0x00000000	0x00000000
0x7fffffffe138:	0x00000000	0x00000000	0x00011f09	0x00000000
0x7fffffffe148:	0x00001000	0x00000000	0x00000090	0x00000000
0x7fffffffe158:	0x5d56c721	0x00000000	0x2183e2bb	0x00000000
0x7fffffffe168:	0x5d502f74	0x00000000	0x365fdd90	0x00000000
0x7fffffffe178:	0x5d502f74	0x00000000	0x369ce679	0x00000000
0x7fffffffe188:	0x00000000	0x00000000	0x00000000	0x00000000
0x7fffffffe198:	0x00000000	0x00000000	0x00000000	0x00000000


hex((0x00007fff<<4)) | 0xf7de95db)
'''