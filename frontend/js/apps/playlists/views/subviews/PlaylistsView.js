define(function(require) {
	var Backbone = require('Backbone');
	var PlaylistView = require('./PlaylistView');

	return Backbone.View.extend({
		template: require('hbs!./../../templates/PlaylistsView'),

		initialize: function () {
			this.subviews = [];
		},

		render: function () {
			this.$el.html(this.template());

			var playlistsComponents = this.$('#playlists-list');
			this.collection.forEach(function (mail) {
				var view = new PlaylistView({model: mail});
				playlistsComponents.append(view.render().el);
				this.subviews.push(view);
			}, this);

			return this;
		}
	});
});