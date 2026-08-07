define(function (require) {
	var Backbone = require('Backbone');
	var PlaylistView = require('./PlaylistView');
	var template = require('hbs!./../../templates/PlaylistsView');

	return Backbone.View.extend({
		template: template,

		initialize: function () {
			this.subviews = [];
		},

		render: function () {
			this.$el.html(this.template({ count: this.collection.length }));

			var container = this.$('#playlists-list');

			if (this.collection.length === 0) {
				container.append(
					'<div class="mdl-cell mdl-cell--12-col mdl-typography--body-1">' +
					'No playlists found.</div>'
				);
				return this;
			}

			this.collection.forEach(function (playlist) {
				var view = new PlaylistView({ model: playlist });
				container.append(view.render().el);
				this.subviews.push(view);
			}, this);

			return this;
		}
	});
});
