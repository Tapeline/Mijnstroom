define(function(require) {
	var Backbone = require('Backbone');
	var viewManager = require('./viewManager');

	var Router = Backbone.Router.extend({
		routes: {
			'tracks': 'tracks',
			'playlists': 'playlists',
		},

		tracks: function () {
			require('./../apps/tracks/app').run(viewManager);
		},

		playlists: function () {
			require('./../apps/playlists/app').run(viewManager);
		},
	});

	return Router;
});