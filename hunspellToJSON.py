#!/usr/bin/python3.3
import re, argparse, os, json

def convertFileToList(file):
	lines = []
	for line in file:
		# Strip new line
		line = line.strip('\n')

		# Ignore empty lines
		if line != '':
			# Ignore comments
			if line[0] != '#':
				lines.append(line)

	return lines 

class AffixRule:
	def __init__(self, flag, opt, combine, charToStrip, affix, condition):
		# SETUP
		self.flag = flag
		self.opt = opt
		self.combine = True if combine == 'Y' else False
		self.charToStrip = '' if charToStrip == '0' else charToStrip
		self.affix = affix
		self.condition = '.' if condition == ',' else re.compile(condition + "$")

	def generateAddSub(self):
		# Prefix or Suffix
		type = 'p:' if self.opt == "PFX" else 's:'
		removeChar = '-' + self.charToStrip if self.charToStrip != '' else ''

		return type + removeChar + '+' + self.affix

	def meetsCondition(self, word):
		if self.condition.search(word):
			return True
		return False

	def createDerivative(self, word):
		result = None
		if self.charToStrip != '':
			if self.opt == "PFX":
				result = word[len(self.charToStrip):len(word)]
				result = self.affix + result 
			else: # SFX
				result = word[0:len(word) - len(self.charToStrip)]
				result = result + self.affix
		else: # No characters to strip
			if self.opt == "PFX":
				result = self.affix + word
			else: # SFX
				result = word + self.affix

		# None means word does not meet the set condition
		return result

class CompoundRule:
	def __init__(self, compound):
		# SETUP
		self.compound = compound
		self.flags = {}

		# Get flags
		for flag in self.compound:
			if flag != '?' and flag != '*':
				self.flags[flag] = []

	def addFlagValues(self, entry, flag):
		if flag in self.flags:
			self.flags[flag].append(entry)

	def getRegex(self):
		regex = ''
		for flag in self.compound:
			if flag == '?' or flag == '*':
				regex += flag
			else:
				regex += '(' + '|'.join(self.flags[flag]) + ')'

		return regex

class AFF:
	def __init__(self, file):
		# SETUP
		self.affixRules = {}
		self.compoundRules = []
		self.replacementTable = {}
		self.key = []
		self.noSuggestFlag = None
		self.onlyInCompoundFlag = None
		self.compoundFlags = ''
		self.minLengthInCompoundWords = 1

		# Retrieve lines from aff
		self.lines = convertFileToList(file)
		self.__parseRules();

	def __parseRules(self):
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
					charToStrip = parts[2]
					affix = parts[3]
					condition = parts[4]

					# Add to dictionary of affix rules if it does not exist
					if flag not in self.affixRules:
						self.affixRules[flag] = []

					self.affixRules[flag].append(AffixRule(flag, opt, combine, charToStrip, affix, condition))

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
					self.replacementTable[parts[1]] = parts[2]

					j += 1
			elif opt == "NOSUGGEST":
				self.noSuggestFlag = flag
			elif opt == "COMPOUNDMIN":
				self.minLengthInCompoundWords = int(flag)
			elif opt == "ONLYINCOMPOUND":
				self.onlyInCompoundFlag = flag
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
						if c != '*' and c != '?' and c not in self.compoundFlags:
							self.compoundFlags += c

					self.compoundRules.append(CompoundRule(compound))

					j += 1

			# Next line
			i += 1

class DICT:
	def __init__(self, file, aff, format, key, generateCompounds, generateReplacementTable, isPretty):
		self.lines = convertFileToList(file)
		self.aff = aff
		self.words = {}
		self.keys = []
		self.format = format
		self.key = key
		self.compounds = generateCompounds 
		self.regexCompounds = []
		self.replacementTable = generateReplacementTable
		self.pretty = isPretty

		self.__parseDict()

	def generateJSON(self, outFile):
		output = {}
		result = None

		newLine = '\n' if self.pretty else ''
		tab = '\t' if self.pretty else ''

		# We do not want to indent the arrays, so we'll go with our own implementation
		result = '{'
		
		if self.key:
			result += newLine + tab + '"keys": ["' + '","'.join(self.keys) + '"],'

		if self.compounds:
			result += newLine + tab + '"compounds": ["' + '","'.join(self.regexCompounds) + '"],'

		if self.replacementTable:
			result += newLine + tab + '"repTable": ' + json.dumps(self.aff.replacementTable, separators=(',', ':'))

		result += newLine + tab + '"words": {'

		i = 0
		for word in self.words:
			val = self.words[word]
			comma = ',' if i < len(self.words) - 1 else ''
			result += newLine  + tab + tab + '"' + word + '": [' + ','.join(val) + ']' + comma
			i += 1

		result += newLine + tab + '}'
		result += newLine + '}'

		outFile.write(result)


	def __parseDict(self):
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
						if flag in self.aff.compoundFlags or flag == self.aff.onlyInCompoundFlag:
							for rule in self.aff.compoundRules:
								rule.addFlagValues(word, flag)
						else:
							# No Suggest flags
							if self.aff.noSuggestFlag == flag:
								pass
							else:
								affixRuleEntries = self.aff.affixRules[flag]
								# Get flag that meets condition
								for i in range(len(affixRuleEntries)):
									rule = affixRuleEntries[i]

									if rule.meetsCondition(word):
										# Add word to list if does not already exist
										if word not in self.words:
											self.words[word] = []

										if self.format == "addsub":
											addSub = rule.generateAddSub()

											# Add to list of keys
											if addSub not in self.keys:
												self.keys.append(addSub)

											# Check if key is to be generated
											if self.key:
												self.words[word].append(str(self.keys.index(addSub)))
											else:
												# Generate addsub next to base word
												self.words[word].append(rule.generateAddSub())
										else:
											# Default, insert complete derivative word
											self.words[word].append(rule.createDerivative(word))
				else:
					# No derivatives.
					self.words[word] = []

			# Create regular expression from compounds
			for rule in self.aff.compoundRules:
				# Add to list
				self.regexCompounds.append(rule.getRegex())


def main():
	# Command Line arguments
	parser = argparse.ArgumentParser(description='Generates JSON formatted dictionary based on hunspell and priority')
	parser.add_argument('-o', '--output', help='Output name of JSON')
	parser.add_argument('-f', '--format', help="Format of the derivatives of each baseword (full|addsub) [Default=full]", default='full')
	parser.add_argument('-k', '--key', action="store_true", help='If format is addsub, list of character removals and affixes can be generated to reduce redudant prefixes and suffixes among base words')
	parser.add_argument('--noCompounds', action="store_false", help='If you do not want to generate the compound regular expressions.')
	parser.add_argument('-r', '--replacementTable', action="store_true", help='If you want to add the Hunspell replacement table to generated JSON output')
	parser.add_argument('-p', '--pretty', action="store_true", help='Output JSON format with formal indentation and line breaks')
	parser.add_argument('dictionary', nargs='+', help='Name of dictionary (e.g. en_US) or individual .dic and .aff files.')
	args = parser.parse_args()

	if args.dictionary:
		path = args.dictionary

		# If single dictionary argument present
		dicPath = path[0] + '.dic' if len(args.dictionary) < 2 else None
		affPath = path[0] + '.aff' if len(args.dictionary) < 2 else None
		
		# Check if individual files were defined
		if dicPath is None and affPath is None:
			dicPath = path[0] if re.search('\w+\.dic', path[0]) else path[1]
			affPath = path[1] if re.search('\w+\.aff', path[1]) else path[0]
			
		# Open AFF file
		try:
			affFile = open(affPath, 'r', encoding='ISO8859-1')
			affRules = AFF(affFile)
			affFile.close()
		except FileNotFoundError:
			print(affPath + " not found")

		# Open DIC file
		try:
			dictFile = open(dicPath, 'r', encoding='ISO8859-1')
			dict = DICT(dictFile, affRules, args.format, args.key, args.noCompounds, args.replacementTable, args.pretty)

			# Open output file
			if args.output:
				oFile = open(args.output, 'w')
			else:
				oFile = open(os.getcwd() + '/' + dicPath.split('.')[0] + '.json', 'w')

			# Output json file
			dict.generateJSON(oFile)

			oFile.close()

			dictFile.close()
		except FileNotFoundError:
			print(dicPath + " not found")

if __name__ == '__main__':
	main()
