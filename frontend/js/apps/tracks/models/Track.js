define(function(require) {
	var Backbone = require('Backbone');

	return Backbone.Model.extend({
		urlRoot: '/api/tracks',
    idAttribute: 'uid',

		delete: function () {
			return Backbone.ajax({
				url: this.url() + '/delete',
				method: 'POST'
			});
		}
	});
});
