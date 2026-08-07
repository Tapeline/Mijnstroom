define(function (require) {
	var Backbone = require('Backbone');

	var Pipeline = Backbone.Model.extend({
		urlRoot: '/api/jobs'
	});

	var Pipelines = Backbone.Collection.extend({
		model: Pipeline,
		url: '/api/jobs'
	});

	var YTVideo = Backbone.Model.extend({
		prepare: function (url) {
			return Backbone.ajax({
				url: '/api/yt/prepare',
				method: 'POST',
				contentType: 'application/json',
				data: JSON.stringify({ url: url })
			});
		},

		import: function (attrs) {
			return Backbone.ajax({
				url: '/api/yt/import',
				method: 'POST',
				contentType: 'application/json',
				data: JSON.stringify(attrs)
			});
		}
	});

	return {
		Pipeline: Pipeline,
		Pipelines: Pipelines,
		YTVideo: YTVideo
	};
});
