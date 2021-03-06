

from elf.elf_parser import *
from .model import *
from .interface import *
from .printer import *

class parser:
	def __init__(self, text):
		self.text = text
		self.index = 0
		self.max = len(text)

		self.stop_words = ["\n", " "]

	def get_token(self):
		current_token = ""
		while self.index < self.max:
			if(self.text[self.index] in self.stop_words):
				self.index += 1
				break
			else:
				current_token += self.text[self.index]
			self.index += 1
		if(len(current_token) == 0):
			return None

		return current_token

def parse_section(section):
	index = 0
	for key, value in section["code"].items():
		print(key + "\t" + value["instruction"] + "\t" + value["argument"])
		index += 1
		if(index % 50 == 0):
			if not should_continue("printed {}, do you want to print more?".format(index)):
				break
#			index = 0

def dissamble(parser_obj):
	token = parser_obj.get_token()
	if(token[0] == "."):
		print("target {}".format(token))
		#	should join the thread, how does that work with a wrapper?
		while not target.done_decompile:
			pass
		section = (target.decompiled_sections.get(token, None))
		if(section == None):
			print("section not found")
		else:
			parse_section(section)

def get_register_values(parser_obj):
	address = parser_obj.get_token()
	if(address[:2] == "0x"):
		response = target.dynamic.get_register_data(address)
		for key, value in response.items():
			print(key)
			for index, i in enumerate(value):
				print("\t {}".format(i), end="")
				if((index + 1) < len(value)):
					print("|", end="")
			print("")
	else:
		print("address as hex")

def get_memory_values(parser_obj):
	address = parser_obj.get_token()
	if(address[:2] == "0x"):
		bold_print("Address %s have been written by : " % (address))
		response = target.dynamic.get_memory_data(address)
		for i in range(0, len(response), 2):
			print("Instruction 0x%x	wrote %i" % ((response[i], response[i + 1])))
		if(len(response) == 0):
			print("Zero times...")

	else:
		print("address as hex")


def parse_commands(parser_obj):
	token = parser_obj.get_token()

	if(token == "disas"):
		dissamble(parser_obj)
	elif(token == "r"):
		if(parser_obj.get_token()):
			target.run_emulator(force=True, non_stop=True)
		else:
			target.run_emulator(force=True)

	elif(token == "explore"):
		'''
		explore is like break, but without the break. You can ask it what the register values
		have been on a given address.
		'''
		if not target.ran_emulator:
			print("you need to run the binary to be able to explore the dynamic side")
		else:
			get_register_values(parser_obj)
	elif(token == "memory"):
		if not target.ran_emulator:
			print("you need to run the binary to be able to explore the dynamic side")
		else:
			get_memory_values(parser_obj)

	elif(token == "strace"):
		if not target.ran_emulator:
			print("you need to run the binary to be able to strace")
		else:
			target.dynamic.get_all_syscalls()

def command_input():
	#	capstone merged unicorn, nicer name than terminal. 
	while True:
		print("cmu>	", end="")
		try:
			command = input("")
		except Exception as e:
			break
	#	print(command[0])
		parse_commands(parser(command))

def go_text(binary):
	global target
	target = model(elf(sys.argv[1]), None)
	print("cmu is like gdb")

	command_input()