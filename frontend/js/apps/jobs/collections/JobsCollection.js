define(function (require) {
	var Backbone = require('Backbone');
	var Job = require('../models/Job');

	return Backbone.Collection.extend({
		model: Job,
		url: '/api/jobs'
	});
});
