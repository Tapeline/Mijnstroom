define(function (require) {
	var Backbone = require('Backbone');
	var template = require('hbs!./../templates/ChoiceView');

	return Backbone.View.extend({
		template: template,

		events: {
			'click .js-choice-video': 'onChoiceVideo',
			'click .js-choice-playlist': 'onChoicePlaylist'
		},

		initialize: function (options) {
			this.onChoiceVideo = options.onChoiceVideo;
			this.onChoicePlaylist = options.onChoicePlaylist;
		},

		render: function () {
			this.$el.html(this.template());
			return this;
		}
	});
});
