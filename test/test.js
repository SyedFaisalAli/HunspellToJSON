(function($) {
	/* Ajax Load */
	function load(jsonFile, fn) {
		req = new $.XMLHttpRequest();

		req.onreadystatechange = function() {
			if (req.readyState == 4 && req.status == 200)
				fn(JSON.parse(req.responseText));
		}

		req.open("GET", jsonFile, true)
		req.send()
	}

	function init(data) {
		console.log(data);
	}

load("../en_US.json", init)
}(window));
