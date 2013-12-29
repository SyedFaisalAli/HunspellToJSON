HunspellToJSON
==============

Reads and Parse Hunspell Dictionary formats (.aff and .dic) and converts it to JSON with some format options.

## Intro
There are many Hunspell parsers for different languages. All of them read the .dic and .aff file and generate a hash table of words for use in a spell checker or other applications. The idea behind this project is to be able to generate a JSON formatted list of words with derivatives for use in primarily JavaScript, NodeJS, or any other JSON parser.

### Pros
* Outputted to JSON and for some languages, it can be used immediately like in JavaScript to check if a word exists in the dictionary.

### Cons
* Unfortunately, the file sizes of these generated dictionaries can be quite large and may not be suitable for an online applications. Minified, using addsub format, and using a key for affixes can still turn the output to be quite large. (e.g. en_US.json is 1.1 MB using all words and not gzipped)

## Usage
	hunspellToJSON.py [-h] [-o OUTPUT] [-f FORMAT] [-k] [-p]
	dictionary [dictionary ...]
	Positional arguments:
	dictionary            Name of dictionary (e.g. en_US) or individual .dic and
	.aff files.

	optional arguments:
	-h, --help            show this help message and exit
	-o OUTPUT, --output OUTPUT
	Output name of JSON
	-f FORMAT, --format FORMAT
	Format of the derivatives of each baseword
	(full|addsub) [Default=full]
	-k, --key             If format is addsub, list of character removals and
	affixes can be generated to reduce redudant prefixes
	and suffixes among base words
	-p, --pretty          Output JSON format with formal indentation and line
	breaks

### Example Usage
	./hunspellToJSON.py -f addsub -k en_US

This command will generate a minified and key based object. By default, it will output to en_US.json or whatever language you're generating. This is as compressed as it could get (without changing the json format).

### Add-Sub
Using this format removes the base word from all derivatives, saving space; however, it requires some parsing on the application side. Here is an example:

	"gauze":["+s","+d","-e+ing","+'s"]

These are all suffixes for the word, *gauze* based on the fact that  + or -  is first. For the third element, the last e is "*substracted*" from *gauze* resulting in *gauz*, and then the suffix "*ing*" is appended which results in the derivative word, *gauzing*.

For prefixes, here is another example:

	"submitting":["re+"]

The only word prefix here is *re*. Since no + or - is found at the beginning, it can be assumed that it is a prefix. When a + or - is hit, the base word has one or more characters from the beginning removed or prepended. In this case, *re* is prepended resulting in *resubmitting*.

### Key
This option is only applicable if you are using the add-sub format. It further removes some redundancy by putting all prefixes and suffixes in a key array. Each word will then have an array of indexes to lookup in the keys for the add-sub to apply. If you are using add-sub, it is recommended to use the option -k as it doesn't nearly affect the parsing since it is a simple lookup. unspellToJSON
