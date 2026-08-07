define(function (require) {
	var Backbone = require('Backbone');

	return Backbone.Model.extend({
		urlRoot: '/api/jobs',

		fetchStatus: function () {
			return this.fetch({ reset: true });
		}
	});
});
