define(function(require) {
	var Backbone = require('Backbone');

	var TracksView = require('./subviews/TracksView');

	return MainView = Backbone.View.extend({
		initialize: function () {
			this.subviews = [];
		},

		render: function () {
			var tracksView = new TracksView({collection: this.collection});
			this.$el.append(tracksView.render().el);
			this.subviews.push(tracksView);
			return this;
		}
	});
});