define(function (require) {
	var Backbone = require('Backbone');
	var Playlist = require('../models/Playlist');

	return Backbone.Collection.extend({
		model: Playlist,
		url: '/api/playlists'
	});
});
