




import	struct
def	hex_2_string(input_stirng,	big=False):
	if(":"	in	input_stirng):
		input_stirng = input_stirng.split(":")[1]

	for string in input_stirng.split("\t"):
		if(len(string) == 0):
			continue
		hex_int = int(string, 16)
		#	endianness <3 
		if(big):
			bytes_string = struct.pack('>I', hex_int) # big-endian
		else:
			bytes_string = struct.pack('<I', hex_int) # little-endian
			
		results = []
		for byte in bytes_string:
			results.append(chr(byte))
			if(byte == 0):
				results.append("\n")
		try:
			print("".join(results), end="")
		except Exception as e:
			print("*ERROR* : ".format(input_stirng))


hex_2_string("0x6f6f722f")
print("\n")

