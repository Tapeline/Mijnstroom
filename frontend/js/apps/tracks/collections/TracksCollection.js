define(function (require) {
	var Backbone = require('Backbone');
	var Track = require('../models/Track');

	return Backbone.Collection.extend({
		model: Track,
		url: '/api/tracks'
	});
});
