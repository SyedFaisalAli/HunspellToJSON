#!/usr/bin/python3.3
import re, argparse, sys

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
	def __init__(self, numRules):
		self.rules = []
		self.numRules = numRules
		self.currentRule = -1

	def add(self, dic):
		self.rules.append(dic)

	def hasNext(self):
		if self.currentRule + 1 < self.numRules:
			return True
		return False

	def next(self):
		self.currentRule += 1
		rule = self.rules[self.currentRule]

		return rule

	def reset(self):
		self.currentRule = -1

class AFF:
	
	def __init__(self, affFile):
		self.rules = {}

		self.rules["affixRules"] = {}
		self.rules["repTable"] = {}
		self.rules["compoundRules"] = []
		self.rules["other"] = {}

		# List of affixes to add and characters to remove in add sub format
		self.rules["keys"] = []
		self.noSuggestFlag = None

		# Remove comments and blank lines, transfer into a list
		self.lines = convertFileToList(affFile)
		self.__addRules()

	def __addRules(self):
		rIter = iter(self.lines)

		# Iterate through rules
		for line in rIter:
			# Split rules
			parts = re.split('\s+', line)
			rOpt = parts[0]	# Rule Type

			# Get code
			rFlag = parts[1]

			# PREFIX or SUFFIX Rules
			if rOpt == "PFX" or rOpt == "SFX":
				# Is combinable with other suffixes/prefixes?
				rCombine = False
				if parts[2] == 'Y':
					rCombine = True

				# Get # of affix entries
				rNumEntries = int(parts[3])

				for j in range(rNumEntries):
					# Get entry
					entry = next(rIter)
					entryParts = re.split('\s+', entry)
					
					# Get characters to strip of a word
					stripChars = entryParts[2]

					# Add-Sub key
					key = ''

					# Affix (Prefix|Suffix)
					affix = entryParts[3]

					# No characters to strip
					if stripChars == "0":
						stripChars = ''
					elif rOpt == "PFX":
						key += stripChars + '-'
					elif rOpt == "SFX":
						key += '-' + stripChars

					if rOpt == "PFX":
						key += affix + '+'
					elif rOpt == "SFX":
						key += '+' + affix

					if key not in self.rules["keys"]:
						self.rules["keys"].append(key)

					# Regex (Condition)
					regex = entryParts[4]

					# Check if rFlag doesn't eist
					if rFlag not in self.rules["affixRules"]:
						self.rules["affixRules"][rFlag] = AffixRule(rNumEntries)

					self.rules["affixRules"][rFlag].add({"opt": rOpt, "combine": rCombine, "stripChars": stripChars, "affix": affix, "regex": regex})

			elif rOpt == "NOSUGGEST":
				if rFlag not in self.rules["affixRules"]:
					self.rules["affixRules"][rFlag]  = AffixRule(1)

				self.rules["affixRules"][rFlag].add({"opt": rOpt})
			elif rOpt == "COMPOUNDRULE":
				numEntries = int(parts[1])

				# Get rule(s)
				for i in range(numEntries):
					rule = next(rIter)
					self.rules["compoundRules"].append(re.split('\s+', rule)[1])

			elif rOpt == "REP" and len(parts) > 2:
				self.rules["repTable"][parts[1]] = parts[2]
			else:
				self.rules["other"][parts[0]] = parts[1]

class DICT:
	def __init__(self, dictFile, affRules, format="full", key=False):
		self.dict = {}
		self.dict["compounds"] = []
		self.dict["words"] = {}
		self.aff = affRules
		self.format = format
		self.keys = []
		self.key = key

		self.lines = convertFileToList(dictFile)
		self.__generateDict()

	def generateJSON(self, oFile, pretty=False):
		newLine = '\n' if pretty else ''
		tab = '\t' if pretty else ''
		oFile.write("{" + newLine)

		# Generate affix keys if set
		if self.key:
			oFile.write(tab + '"key": ["' + '","'.join(self.aff.rules["keys"]) + '"],' + newLine)

		oFile.write(tab + '"words": {' + newLine)

		count = 0
		numWords = len(self.dict["words"])
		for word in self.dict["words"]:
			comma = ',' if count != (numWords - 1) else ''

			# Avoid unecessary quotations if there is no derivitives of a base word
			if len(self.dict["words"][word]) == 0:
				oFile.write(tab + tab + '"' + word + '":[' + '","'.join(self.dict["words"][word]) + ']' + comma + newLine)
			elif self.key:	# No need to wrap indexes with quotes
				oFile.write(tab + tab + '"' + word + '":[' + ','.join(self.dict["words"][word]) + ']' + comma + newLine)
			else:
				oFile.write(tab + tab + '"' + word + '":["' + '","'.join(self.dict["words"][word]) + '"]' + comma + newLine)

			count += 1
		oFile.write(tab + "}" + newLine)
		oFile.write("}" + newLine)

	def __generateDict(self):
		compounds = self.aff.rules["compoundRules"]
		compoundFlags = {}

		# Get flag parameters from rule excluding wildcards
		for compound in compounds:
			# Remove wildcards
			flags = re.sub('\?|\*', '', compound)
			
			# Add flag as dictionary key
			for flag in flags: compoundFlags[flag] = []

		# Progress Bar
		progress = len(self.lines) / 10

		for i in range(len(self.lines)):
			line = self.lines[i]

			if i % progress == 0:
				print('\b=>', end='')
				sys.stdout.flush()

			# Split
			entries = line.split('/')
			word = entries[0]
			flags = None if len(entries) < 2 else entries[1]

			if len(word) > 1:
				# Compound rule flags
				if flags != None and flags.islower():
					# Loop through available compound parameters
					for flag in flags:
						# If flag matches
						if flag in compoundFlags:
							# Add word to compound flag replacement
							compoundFlags[flag].append(word)
				elif flags != None:
					self.__applyAffixRule(flags, word)
				elif word not in self.dict["words"]:
						self.dict["words"][word] = []

		# New Line
		print()

	def __applyAffixRule(self, flags, word):
		flagIndex = 0
		affixes = self.aff.rules["affixRules"]
		flag = flags[flagIndex]
		affix = affixes[flag].next()

		while flagIndex < len(flags):
			flag = flags[flagIndex]
			
			if affix["opt"] == "NOSUGGEST":
				# Offensive Word.
				pass # TODO: Do something with these words
			elif re.search(affix['regex'] + "$", word):
				# Base word
				baseWord = word

				# Addition to prefixes and/or suffixes to indicate what needs to be added (Add-Sub format)
				addSub = "+" if self.format == "addsub" else ''

				# Get prefix and/or suffix if applicable
				pfx = affix['affix'] + addSub if affix['opt'] == 'PFX' else ''
				sfx = addSub + affix['affix'] if affix['opt'] == 'SFX' else ''


				if affix['stripChars'] != '':
					# Get position to check
					pos = 0 if affix['opt'] == 'PFX' else len(word) - 1

					# Check if char to strip exists
					if baseWord[pos] == affix['stripChars']:
						if self.format == "full":
							# Start and end position for substring if characters are to removed
							start = word.index(affix['stripChars']) if affix['opt'] == 'PFX' else 0
							end = word.rindex(affix['stripChars']) if affix['opt'] == 'SFX' else 0

							# Remove character
							baseWord = baseWord[start:end]
						elif self.format == "addsub" and affix['opt'] == 'SFX':
							# There exists characters to remove from the end
							baseWord = "-" + affix['stripChars']
						elif self.format == "addsub" and affix['opt'] == 'PFX':
							# There exists characters to remove from the beginning
							baseWord = affix['stripChars'] + "-"

				elif self.format == "addsub":
					# There is no need to add entire baseword using this format
					baseWord = ""
							
				pfxKey = baseWord + pfx
				sfxKey = baseWord + sfx

				# Key generation option is set. There is no key to generate if there is no derivitives
				if self.key:
					affixKeyIndex = -1

					# Erase pfx and sfx as they are no longer needed since it is or will be stored in key list
					pfx = sfx = ''

					# Add prefix to list of keys if it is not already in there
					if pfxKey in self.aff.rules["keys"]:
						# Key exists, get the index in key list
						affixKeyIndex = self.aff.rules["keys"].index(pfxKey)

					# Same with suffix
					if sfxKey in self.aff.rules["keys"]:
						# Key exists, get the index in key list
						affixKeyIndex = self.aff.rules["keys"].index(sfxKey)

					if affixKeyIndex != -1:
						# Set number
						baseWord = str(affixKeyIndex)

				# Add base word to dictionary if it does not already exist
				if word not in self.dict["words"]:
					self.dict["words"][word] = []

				fullWord = pfx + baseWord + sfx

				if fullWord not in self.dict["words"][word] and word != fullWord:
					# Add Prefixes and Suffixes
					self.dict["words"][word].append(fullWord)

			# If there are more rules of flags to check, go the next rule
			if affixes[flag].hasNext():
				affix = affixes[flag].next()
			else: # Move on to the next flag if it exists
				# Increment
				flagIndex += 1
				affixes[flag].reset()

def main():
	# Command Line arguments
	parser = argparse.ArgumentParser(description='Generates JSON formatted dictionary based on hunspell and priority')
	parser.add_argument('-o', '--output', help='Output name of JSON')
	parser.add_argument('-f', '--format', help="Format of the derivatives of each baseword (full|addsub|regex) [Default=full]", default='full')
	parser.add_argument('-k', '--key', action="store_true", help='If format is addsub, list of character removals and affixes can be generated to reduce redudant prefixes and suffixes among base words')
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
			dict = DICT(dictFile, affRules, args.format, args.key)

			# Open output file
			if args.output:
				oFile = open(args.output, 'w')
			else:
				oFile = open(dicPath.split('.')[0] + '.json', 'w')

			# Output json file
			dict.generateJSON(oFile, args.pretty)

			oFile.close()

			dictFile.close()
		except FileNotFoundError:
			print(dicPath + " not found")

if __name__ == '__main__':
	main()
