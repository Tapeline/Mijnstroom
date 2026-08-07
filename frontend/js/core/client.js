define(function (require) {
	var $ = require('jQuery');
	var Backbone = require('Backbone');

	return {
		setup: function (win, app) {
			$(win.document).on("click", "a[href^='#/']:not([data-bypass])", function(evt) {
				var href = $(this).attr("href");
				evt.preventDefault();
				var route = href.replace(/^#\/?/, '');
				Backbone.history.navigate(route, { trigger: true });
			});
		}
	};
});