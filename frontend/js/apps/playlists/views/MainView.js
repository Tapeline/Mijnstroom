define(function (require) {
	var Backbone = require('Backbone');
	var SearchToolbar = require('./../../../common/views/SearchToolbar');
	var PlaylistsView = require('./subviews/PlaylistsView');

	return Backbone.View.extend({
		initialize: function (options) {
			this.subviews = [];
			this.filters = options.filters || {};
			this.onFilter = options.onFilter || function () {};
			this.error = options.error || null;
		},

		render: function () {
			this.$el.append(
				'<div class="mdl-grid"><div class="mdl-cell mdl-cell--12-col">' +
				'<a class="mdl-button mdl-button--raised mdl-button--colored mdl-js-button mdl-js-ripple-effect" href="#/playlists/new">' +
				'<i class="material-icons">add</i>&nbsp;Create playlist</a>' +
				'</div></div>'
			);

			var toolbar = new SearchToolbar({
				filters: this.filters,
				onFilter: this.onFilter
			});
			this.$el.append(toolbar.render().el);
			this.subviews.push(toolbar);

			if (this.error) {
				this.$el.append('<p style="color:#b71c1c">' + this.error + '</p>');
			}

			var view = new PlaylistsView({ collection: this.collection });
			this.$el.append(view.render().el);
			this.subviews.push(view);

			return this;
		}
	});
});
