define(function(require) {
	var Backbone = require('Backbone');

	var PlaylistsView = require('./subviews/PlaylistsView');

	return MainView = Backbone.View.extend({
		initialize: function () {
			this.subviews = [];
		},

		render: function () {
			var playlistsView = new PlaylistsView({collection: this.collection});
			this.$el.append(playlistsView.render().el);
			this.subviews.push(playlistsView);
			return this;
		}
	});
});