#!/usr/bin/python3.3
import re, argparse

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
		self.currentRule = 0

	def add(self, dic):
		self.rules.append(dic)

	def hasNext(self):
		if self.currentRule + 1 < self.numRules:
			return True
		return False

	def next(self):
		rule = self.rules[self.currentRule]
		self.currentRule += 1

		return rule

	def reset():
		self.currentRule = 0

class AFF:
	
	def __init__(self, affFile):
		self.rules = {}

		self.rules["affixRules"] = {}
		self.rules["numAffixRules"] = {}
		self.rules["repTable"] = {}
		self.rules["compoundRules"] = []
		self.rules["other"] = {}
		self.noSuggestFlag = None

		# Remove comments and blank lines, cache into a list
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

				if not rFlag in self.rules["numAffixRules"]:
					self.rules["numAffixRules"][rFlag] = rNumEntries

				for j in range(rNumEntries):
					# Get entry
					entry = next(rIter)
					entryParts = re.split('\s+', entry)
					
					# Get characters to strip of a word
					stripChars = entryParts[2]

					# No characters to strip
					if stripChars == "0":
						stripChars = None

					# Affix (Prefix|Suffix)
					affix = entryParts[3]

					# Regex (Condition)
					regex = entryParts[4]

					# Check if rFlag doesn't eist
					if (rFlag + str(j)) not in self.rules["affixRules"]:
						self.rules["affixRules"][rFlag] = AffixRule(rNumEntries)

					self.rules["affixRules"][rFlag].add({"opt": rOpt, "combine": rCombine, "stripChars": stripChars, "affix": affix, "regex": regex})

			elif rOpt == "NOSUGGEST":
				self.noSuggestFlag = rFlag
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
			oFile.write(tab + '"key": ["' + '","'.join(self.keys) + '"],' + newLine)

		oFile.write(tab + '"words": {' + newLine)
		for word in self.dict["words"]:
			# Avoid unecessary quotations if there is no derivitives of a base word
			if len(self.dict["words"][word]) == 0:
				oFile.write(tab + tab + '"' + word + '":[' + '","'.join(self.dict["words"][word]) + '],' + newLine)
			elif self.key:	# No need to wrap indexes with quotes
				oFile.write(tab + tab + '"' + word + '":[' + ','.join(self.dict["words"][word]) + '],' + newLine)
			else:
				oFile.write(tab + tab + '"' + word + '":["' + '","'.join(self.dict["words"][word]) + '"],' + newLine)
		oFile.write(tab + "}" + newLine)
		oFile.write("\b}" + newLine)

	def __generateDict(self):
		compounds = self.aff.rules["compoundRules"]
		compoundFlags = {}

		# Get flag parameters from rule excluding wildcards
		for compound in compounds:
			# Remove wildcards
			flags = re.sub('\?|\*', '', compound)
			
			# Add flag as dictionary key
			for flag in flags: compoundFlags[flag] = []

		for line in self.lines:
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

	def __getAffixRule(self, flag, word):
		numRules = self.aff.rules["numAffixRules"][flag]
		i = 0
		affix = self.aff.rules["affixRules"][flag + '-' + str(i)]

		return affix

	def __applyAffixRule(self, flags, word):
		flagIndex = 0

		affixes = self.aff.rules["affixRules"]
		flag = flags[flagIndex]
		affix = affixes[flag].next()

		while flagIndex < len(flags):

			if re.search(affix['regex'] + "$", word):
				# Base word
				baseWord = word

				# Index in affix key list (if used)
				affixKeyIndex = -1

				# Add-sub format
				addSub = "+" if self.format == "addsub" else ''

				# Get Possible prefixes and suffixes
				pfx = affix['affix'] + addSub if affix['opt'] == 'PFX' else ''
				sfx = addSub + affix['affix'] if affix['opt'] == 'SFX' else ''


				if affix['stripChars'] != None:
					# Get position to check
					pos = 0 if affix['opt'] == 'PFX' else len(word) - 1

					# Check if char to strip exists
					if baseWord[pos] == affix['stripChars']:
						if self.format == "full":
							# Substring if required ot remove char
							start = word.index(affix['stripChars']) if affix['opt'] == 'PFX' else 0
							end = word.rindex(affix['stripChars']) if affix['opt'] == 'SFX' else 0

							# Remove character
							baseWord = baseWord[start:end]
						elif self.format == "addsub" and affix['opt'] == 'SFX':
							# There exists characters to remove from the end
							baseWord = "-" + affix['stripChars']
						elif self.format == "addsub" and affix['opt'] == 'PFX':
							# There exists characters to remove from the start
							baseWord = affix['stripChars'] + "-"

				elif self.format == "addsub": # There are no characters to strip from base word
					baseWord = ""
							
				if self.key:
					# Add (pre|suf)fix to list of keys if it is not already in there
					if (pfx + baseWord) != '' and (pfx + baseWord) not in self.keys:
						self.keys.append(pfx + baseWord)

					if (baseWord + sfx) != '' and (baseWord + sfx) not in self.keys:
						self.keys.append(baseWord + sfx)

					# Get affix key index
					if pfx != '':
						affixKeyIndex = self.keys.index(pfx + baseWord)
						pfx = ''
					elif sfx != '':
						affixKeyIndex = self.keys.index(baseWord + sfx)
						sfx = ''

					# Set number
					baseWord = str(affixKeyIndex)

				# Add base word to dictionary if it does not already exist
				if word not in self.dict["words"]:
					self.dict["words"][word] = []

				# Add Prefixes and Suffixes
				self.dict["words"][word].append(pfx + baseWord + sfx)

			if affixes[flag].hasNext():
				affix = affixes[flag].next()
				print(affix)
			else:
				# Increment
				flagIndex += 1

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
