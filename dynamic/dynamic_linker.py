
from elf.elf_parser_key_value import *
import struct


'''
	-	need to be able to know what symbols and what libraries
		are needed to be loaded into unicorn.
	-	not sure if this should be in the elf parser or not...
'''

#	good manpage http://manpages.courier-mta.org/htmlman5/elf.5.html

def get_dynamic_symbols(elf_target, name, debug=False):
#	global symbol_table


	dynamic_section_str_start = elf_target.sections_with_name[".dynstr"]["file_offset"]

	dynamic_section_sym_start = elf_target.sections_with_name[name]["file_offset"]
	dynamic_section_sym_entry_size = elf_target.sections_with_name[name]["entries_size"]
	dynamic_section_sym_end = elf_target.sections_with_name[name]["file_offset"] + elf_target.sections_with_name[name]["size"]


	index = 0
	lookup_table = {

	}
	for offset in range(dynamic_section_sym_start, dynamic_section_sym_end, dynamic_section_sym_entry_size):
		struct_format = "IBBHQQ" if(elf_target.is_64_bit) else "IIIBBH"

		st_name, st_info, st_other, st_shndx, st_value, st_size = struct.unpack(struct_format, elf_target.file[offset:offset+dynamic_section_sym_entry_size])

		st_name = elf_target.read_zero_terminated_string(dynamic_section_str_start + st_name)

		if(debug):
			print("%x\t%04d%10d%10d%10s%10s%10s%10d\t%s" % (offset, index, st_value, st_size, STT_TYPE[ELF_ST_TYPE(st_info)],
						STB_BIND[ELF_ST_BIND(st_info)], STV_VISIBILITY[ELF_ST_VISIBILITY(st_other)], st_shndx, st_name))

		if(len(st_name) > 0):
			lookup_table[st_name] = [hex(st_value), st_size]
		elif(index == 0):
			lookup_table["0"] = [hex(st_value), st_size]

		elf_target.symbol_table[index] = st_name
		index += 1

	return lookup_table


def parse_relocation(elf_target, target, debug=False):
	
	dynamic_section_sym_start = elf_target.sections_with_name[target]["file_offset"]
	dynamic_section_sym_entry_size = elf_target.sections_with_name[target]["entries_size"]
	dynamic_section_sym_end = elf_target.sections_with_name[target]["file_offset"] + elf_target.sections_with_name[target]["size"]

	index = 0

#	print("offset 	symbol 	type")
	lookup = {

	}
	direct_mapping_count = 0

	for offset in range(dynamic_section_sym_start, dynamic_section_sym_end, dynamic_section_sym_entry_size):
		if(elf_target.is_64_bit):
			struct_format = "QQQ"
			address,info,addend = struct.unpack(struct_format, elf_target.file[offset:offset+dynamic_section_sym_entry_size])


			if("ld" in elf_target.file_name):
				if(address == 0x224a00):
					print("BAGEL")
			try:
				elf_target.qword_helper[hex(address)] = elf_target.symbol_table[ELF64_R_SYM(info)]


				rela_type = (handle_rela(info & 0xFFFFFFFF))

				if(0 < len(elf_target.symbol_table[ELF64_R_SYM(info)]) and 
					(rela_type == "R_X86_64_64" or rela_type == "R_X86_64_JUMP_SLOT" or 
						rela_type == "R_X86_64_GLOB_DAT")):
					lookup[elf_target.symbol_table[ELF64_R_SYM(info)]] = address
					assert(addend == 0)
				elif(rela_type == "R_X86_64_RELATIVE"):
					lookup["DIRECT_MAPPING_{}".format(direct_mapping_count)] = [address, addend]
					direct_mapping_count += 1
				elif(rela_type == "R_X86_64_IRELATIVE"):					
					lookup["DIRECT_MAPPING_{}".format(direct_mapping_count)] = [address, addend]
					direct_mapping_count += 1
				elif(debug):
					print("Fix dynamic linker[{}], need to handle type : {}, symbol size : {}, location {}".format(elf_target.file_name, rela_type, len(elf_target.symbol_table[ELF64_R_SYM(info)]), hex(address)))
			except Exception as e:
				print("erorr in parse_relocation", e)
	return lookup


def parse_dynamic(elf_target, lookup=None, debug=False):
	dynamic_section_str_start = elf_target.sections_with_name[".dynstr"]["file_offset"]

	dynamic_section_start = elf_target.sections_with_name[".dynamic"]["file_offset"]
	dynamic_section_size_entry = (elf_target.sections_with_name[".dynamic"]["entries_size"])
	dynamic_section_end = dynamic_section_start + elf_target.sections_with_name[".dynamic"]["size"]

	response = []

	for offset in range(dynamic_section_start, dynamic_section_end, dynamic_section_size_entry):
		tag, identity = struct.unpack("QQ", (elf_target.file[offset:offset+dynamic_section_size_entry]))
		if tag in TAG:
			if tag == 1 or tag == 15:
				if(debug):
					print("0x%018x %20s [%s]" %(tag, TAG[tag], elf_target.read_zero_terminated_string(dynamic_section_str_start + identity)))
				if(lookup == "needed_libraries"):
					response.append(elf_target.read_zero_terminated_string(dynamic_section_str_start + identity))
			else:
				if(debug):
					print("0x%018x %20s [0x%x]" %(tag, TAG[tag], identity))
		else:
			if(debug):
				print("0x%018x %20s [0x%x]" %(tag, tag, identity))
	return response

def get_needed_libraries(elf_target):
	return parse_dynamic(elf_target, "needed_libraries")

def link_lib_and_binary(binary, library):
	binary_map_functions = {

	}

	look_up_libary_function = {

	}

	mappings = []

	for section_key, section_info in binary.sections_with_name.items():
		if(section_info["type"] == 0x4):
			for key, item in parse_relocation(binary, section_key).items():
				if("DIRECT_MAPPING_" in key):
					mappings.append([hex(item[0]), "DIRECT_MAPPING_", item[1]])
				else:
					binary_map_functions[key] = item
	'''
		sometimes you jsut want R_X86_64_IRELATIVE
	'''
	if(library != None):
		for section_key, section_info in library.sections_with_name.items():
			if(section_info["type"] == 0x0B):
				for key, item in get_dynamic_symbols(library, section_key).items():
					look_up_libary_function[key] = item

		'''
			resolve binary -> library
		'''
		for key, item in binary_map_functions.items():
			if(look_up_libary_function.get(key, None) != None):
				mappings.append([hex(item), look_up_libary_function[key]])
				binary_map_functions[key] = None
		
		for key, item in binary_map_functions.items():
			if(binary_map_functions[key] != None):
		#		mappings.append([hex(item), ["0xf00dbeef", 8]])
				pass
	'''
		return a mapping between binary -> library function
	'''
	return mappings

