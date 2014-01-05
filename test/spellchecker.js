(function() {
	var words = {},
		keys = [],
		wordInput = document.getElementById("word"),
		resultWrap = document.getElementById("result-wrap"),
		result = document.getElementById("result");

	function load(jsonFile, fn) {
		req = new window.XMLHttpRequest();

		req.onreadystatechange = function() {
			if (req.readyState == 4 && req.status == 200)
				fn(JSON.parse(req.responseText));
		}

		req.open("GET", jsonFile, true)
		req.send()
	}

	function init(data) {
		key = data["key"];
		words = expand(data["words"]);

		console.log(words);

		wordInput.addEventListener("keydown", submit, false);
	}

	function expand(words) {
		var deriv = null,
			keyIndex = -1,
			dWord = null;

		for (var word in words) {
			// Avoid prototype properties
			if (words.hasOwnProperty(word)) {
				if (words[word].length > 0) {
					deriv = words[word];
					for (var i = 0; i < deriv.length; i++) {
						keyIndex = parseInt(deriv[i]);
						// Get derivative word
						dWord = getDerivative(word, key[keyIndex]);
						// Add derivative word
						words[dWord] = true;
					}

					words[word] = true;
				} else {
					words[word] = true;
				}
			}
		}

		return words;
	}

	function getDerivative(word, addsub) {
		var removal = '',
			addition = '',
			subIndex = -1,
			addIndex = -1;

		/* In Add-Sub format. Anything to remove before adding the suffix will come first. */
		if (addsub[0] === '-') {
			// Since this is suffixes, the sub index will be the position after the character(s) to remove
			subIndex = addsub.indexOf('+');

			// Get character(s) to remove after -
			removal = addsub.substring(1, subIndex);

			// Remove characters from the end of the word
			word = word.substring(0, word.lastIndexOf(removal));
		}

		/* Any suffix to add will be after */
		if (addsub[0] === '+') {
			// Add index will be the position after after the +
			addIndex = addsub.indexOf('+') + 1;

			// Get character(s) to add after +
			addition = addsub.substring(addIndex, addsub.length);

			// Attach suffix
			word = word + addition;
		}

		/* Prefixes will require some looking ahead */
		if (keys[0] !== '+' || keys[0] !== '-') {
			// Subtraction will occur first if it exists
			subIndex = addsub.indexOf('-');

			// Addition will occur next or first if there is nothing to subtract
			addIndex = addsub.indexOf('+');

			// Two cases: Nothing to subtract or having something to subtract AND add
			if (subIndex != -1) {
				// There is something to subtract...
				removal = addsub.substring(0, subIndex);

				// Get prefix which will be after the - until reaching +
				addition = addsub.substring(subIndex + 1, addIndex);

				// Remove the prefix from the word
				word = word.substring(removal.length, word.length);

				// Add new prefix
				word = addition + word;

			} else {
				// If subIndex is -1, then there is nothing to subtract. Just add
				addition = addsub.substring(0, addIndex);

				// Add new prefix
				word = addition + word;
			}
			
		}

		return word;
	}

	function submit(e) {
		var value = null;

		// ENTER
		if (e.keyCode === 13) {
			value = wordInput.value;
			
			// Check if word exists
			if (words[value] !== undefined) {
				sendResult(value, []);
			} else if (words[value.toLowerCase()] !== undefined) {
				sendResult(value, [value.toLowerCase()]);
			} else {
				// Check for derivitive of word
			}
		}
	}

	function sendResult(word, arrayOfSuggestions) {
		// Show header
		resultWrap.style.display = "block";

		// Empty array means that the word is spelled correctly
		if (arrayOfSuggestions.length === 0) {
			result.innerHTML = "<em>" + word + "</em> is spelled correctly.";
		}
		else if (arrayOfSuggestions.length === 1) {
			result.innerHTML = "<em>" + word + "</em> does not exist but <em>" + arrayOfSuggestions[0] + "</em> does.";
		}
	}

load("en_US.json", init);
})();
