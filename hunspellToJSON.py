#!/usr/bin/python3.3
import re, argparse, os, gzip, json

def file_to_list(in_file):
	''' Reads file into list '''
	lines = []
	for line in in_file:
		# Strip new line
		line = line.strip('\n')

		# Ignore empty lines
		if line != '':
			# Ignore comments
			if line[0] != '#':
				lines.append(line)

	return lines 

class AffixRule:
	''' Class matching affix rule defined in Hunspell .aff files '''
	def __init__(self, flag, opt, combine, char_to_strip, affix, condition):
		# SETUP
		self.flag = flag
		self.opt = opt
		self.combine = True if combine == 'Y' else False
		self.char_to_strip = '' if char_to_strip == '0' else char_to_strip
		self.affix = affix
		self.condition = '.' if condition == ',' else re.compile(condition + "$")

	def generate_add_sub(self):
		''' Generates prefixes/suffixes in a short form to parse and remove some redundancy '''
		# Prefix or Suffix
		affix_type = 'p:' if self.opt == "PFX" else 's:'
		remove_char = '-' + self.char_to_strip if self.char_to_strip != '' else ''

		return affix_type + remove_char + '+' + self.affix

	def meets_condition(self, word):
		''' Checks if word meets conditionr requirements defined in affix rule '''
		if self.condition.search(word):
			return True
		return False

	def create_derivative(self, word):
		''' Creates derivative of (base) word by adding any affixes that apply '''
		result = None
		if self.char_to_strip != '':
			if self.opt == "PFX":
				result = word[len(self.char_to_strip):len(word)]
				result = self.affix + result 
			else: # SFX
				result = word[0:len(word) - len(self.char_to_strip)]
				result = result + self.affix
		else: # No characters to strip
			if self.opt == "PFX":
				result = self.affix + word
			else: # SFX
				result = word + self.affix

		# None means word does not meet the set condition
		return result

class CompoundRule:
	''' Class to match compound rules '''
	def __init__(self, compound):
		# SETUP
		self.compound = compound
		self.flags = {}

		# Get flags
		for flag in self.compound:
			if flag != '?' and flag != '*':
				self.flags[flag] = []

	def add_flag_values(self, entry, flag):
		''' Adds flag value to applicable compounds '''
		if flag in self.flags:
			self.flags[flag].append(entry)

	def get_regex(self):
		''' Generates and returns compound regular expression '''
		regex = ''
		for flag in self.compound:
			if flag == '?' or flag == '*':
				regex += flag
			else:
				regex += '(' + '|'.join(self.flags[flag]) + ')'

		return regex

class AFF:
	''' Class to match AFF file and rules '''
	def __init__(self, in_file):
		# SETUP
		self.affix_rules = {}
		self.compound_rules = []
		self.rep_table = {}
		self.key = []
		self.no_suggest_flag = None
		self.only_in_compound_flag = None
		self.compound_flags = ''
		self.min_length_compound_words = 1

		# Retrieve lines from aff
		self.lines = file_to_list(in_file)
		self.__parse_rules()

	def __parse_rules(self):
		lines = self.lines
		i = 0

		while i < len(lines):
			line = lines[i]
			parts = re.split('\s+', line)

			# Get header parts
			opt = parts[0]
			flag = parts[1]

			if opt == 'PFX' or opt == 'SFX':
				combine = parts[2]
				numEntries = int(parts[3])
				j = 0

				# Affix entries
				while j < numEntries:
					# Move to next line
					i += 1

					line = lines[i]
					parts = re.split('\s+', line)
					
					# Entries
					char_to_strip = parts[2]
					affix = parts[3]
					condition = parts[4]

					# Add to dictionary of affix rules if it does not exist
					if flag not in self.affix_rules:
						self.affix_rules[flag] = []

					self.affix_rules[flag].append(AffixRule(flag, opt, combine, char_to_strip, affix, condition))

					# Increment number of lines under rule entry
					j += 1
			elif opt == "REP":
				numEntries = int(parts[1])
				j = 0

				while j < numEntries:
					i += 1

					line = lines[i]
					parts = re.split('\s+', line)

					# Replacement Entries
					self.rep_table[parts[1]] = parts[2]

					j += 1
			elif opt == "NOSUGGEST":
				self.no_suggest_flag = flag
			elif opt == "COMPOUNDMIN":
				self.minLengthInCompoundWords = int(flag)
			elif opt == "ONLYINCOMPOUND":
				self.only_in_compound_flag = flag
			elif opt == 'COMPOUNDRULE':
				numEntries = int(parts[1])
				j = 0

				# Compound rule entries
				while j < numEntries:
					# Move to next line
					i += 1

					line = lines[i];
					parts = re.split('\s+', line)

					# Compounds
					compound = parts[1]
					
					# Take note of compound flags
					for c in compound:
						if c != '*' and c != '?' and c not in self.compound_flags:
							self.compound_flags += c

					self.compound_rules.append(CompoundRule(compound))

					j += 1

			# Next line
			i += 1

class DICT:
	def __init__(self, dict_file, aff, format, key, generateCompounds, generateReplacementTable, isPretty):
		self.lines = file_to_list(dict_file)
		self.aff = aff
		self.words = {}
		self.keys = []
		self.format = format
		self.key = key
		self.compounds = generateCompounds 
		self.regex_compounds = []
		self.rep_table = generateReplacementTable
		self.pretty = isPretty

		self.__parse_dict()

	def generate_json(self, out_file, gzip_set):
		result = None

		new_line = '\n' if self.pretty else ''
		tab = '\t' if self.pretty else ''

		# We do not want to indent the arrays, so we'll go with our own implementation
		result = '{'
		
		if self.key:
			result += new_line + tab + '"keys": ["' + '","'.join(self.keys) + '"],'

		if self.compounds:
			result += new_line + tab + '"compounds": ["' + '","'.join(self.regex_compounds) + '"],'

		if self.rep_table:
			result += new_line + tab + '"repTable": ' + json.dumps(self.aff.rep_table, separators=(',', ':'))

		result += new_line + tab + '"words": {'

		i = 0
		for word in self.words:
			val = self.words[word]
			comma = ',' if i < len(self.words) - 1 else ''
			result += new_line  + tab + tab + '"' + word + '": [' + ','.join(val) + ']' + comma
			i += 1

		result += new_line + tab + '}'
		result += new_line + '}'

		if gzip_set:
			out_file.write(bytes(result, 'UTF-8'))
		else:
			out_file.write(result)


	def __parse_dict(self):
		''' Parses dictionary with according rules '''
		i = 0
		lines = self.lines

		for line in lines:
			line = line.split('/')
			word = line[0]
			flags = line[1] if len(line) > 1 else None

			if flags != None:
				# Derivatives possible
				for flag in flags:
					# Compound?
					if flag in self.aff.compound_flags or flag == self.aff.only_in_compound_flag:
						for rule in self.aff.compound_rules:
							rule.add_flag_values(word, flag)
					else:
						# No Suggest flags
						if self.aff.no_suggest_flag == flag:
							pass
						else:
							affix_rule_entries = self.aff.affix_rules[flag]
							# Get flag that meets condition
							for i in range(len(affix_rule_entries)):
								rule = affix_rule_entries[i]

								if rule.meets_condition(word):
									# Add word to list if does not already exist
									if word not in self.words:
										self.words[word] = []

									if self.format == "addsub":
										add_sub = rule.generate_add_sub()

										# Add to list of keys
										if add_sub not in self.keys:
											self.keys.append(add_sub)

										# Check if key is to be generated
										if self.key:
											self.words[word].append(str(self.keys.index(add_sub)))
										else:
											# Generate addsub next to base word
											self.words[word].append(rule.generate_add_sub())
									else:
										# Default, insert complete derivative word
										self.words[word].append(rule.create_derivative(word))
			else:
				# No derivatives.
				self.words[word] = []

		# Create regular expression from compounds
		for rule in self.aff.compound_rules:
			# Add to list
			self.regex_compounds.append(rule.get_regex())


def main():
	# Command Line arguments
	parser = argparse.ArgumentParser(description='Generates JSON formatted dictionary based on hunspell and priority')
	parser.add_argument('-o', '--output', help='Output name of JSON')
	parser.add_argument('-f', '--format', help="Format of the derivatives of each baseword (full|addsub) [Default=full]", default='full')
	parser.add_argument('-k', '--key', action="store_true", help='If format is addsub, list of character removals and affixes can be generated to reduce redudant prefixes and suffixes among base words')
	parser.add_argument('-g', '--gzip', action="store_true", help='To reduce generated JSON file further, you can compress it using gzip which most modern browsers can decompress now.')
	parser.add_argument('--noCompounds', action="store_false", help='If you do not want to generate the compound regular expressions.')
	parser.add_argument('-r', '--rep_table', action="store_true", help='If you want to add the Hunspell replacement table to generated JSON output')
	parser.add_argument('-p', '--pretty', action="store_true", help='Output JSON format with formal indentation and line breaks')
	parser.add_argument('dictionary', nargs='+', help='Name of dictionary (e.g. en_US) or individual .dic and .aff files.')
	args = parser.parse_args()

	if args.dictionary:
		path = args.dictionary

		# If single dictionary argument present
		dict_path = path[0] + '.dic' if len(args.dictionary) < 2 else None
		aff_path = path[0] + '.aff' if len(args.dictionary) < 2 else None
		
		# Check if individual files were defined
		if dict_path is None and aff_path is None:
			dict_path = path[0] if re.search(r'\w+\.dic', path[0]) else path[1]
			aff_path = path[1] if re.search(r'\w+\.aff', path[1]) else path[0]
			
		# Open AFF file
		try:
			aff_file = open(aff_path, 'r', encoding='ISO8859-1')
			aff_rules = AFF(aff_file)
			aff_file.close()
		except IOError:
			print(aff_path + " not found")

		# Open DIC file
		try:
			dict_file = open(dict_path, 'r', encoding='ISO8859-1')
			dictionary = DICT(dict_file, aff_rules, args.format, args.key, args.noCompounds, args.rep_table, args.pretty)

			# Open output file
			if args.output:

				if args.gzip:
					out_file = gzip.open(args.output, 'wb')
				else:
					out_file = open(args.output, 'wb')
			else:
				if args.gzip:
					out_file = gzip.open(os.getcwd() + '/' + dict_path.split('.')[0] + '.json', 'wb')
				else:
					out_file = open(os.getcwd() + '/' + dict_path.split('.')[0] + '.json', 'wb')

			# Output json file
			dictionary.generate_json(out_file, args.gzip)

			out_file.close()

			dict_file.close()
		except IOError:
			print(dict_path + " not found")

if __name__ == '__main__':
	main()
