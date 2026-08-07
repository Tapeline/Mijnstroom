define(function(require) {
	var Backbone = require('Backbone');

	return Backbone.Model.extend({
		urlRoot: '/api/playlists',

		updateMeta: function (attrs) {
			return Backbone.ajax({
				url: this.url() + '/meta',
				method: 'POST',
				contentType: 'application/json',
				data: JSON.stringify(attrs)
			});
		},

		updateTracks: function (operation, tracks) {
			return Backbone.ajax({
				url: this.url() + '/tracks',
				method: 'POST',
				contentType: 'application/json',
				data: JSON.stringify({ operation: operation, tracks: tracks })
			});
		},

		delete: function () {
			return Backbone.ajax({
				url: this.url() + '/delete',
				method: 'POST'
			});
		}
	});
});
