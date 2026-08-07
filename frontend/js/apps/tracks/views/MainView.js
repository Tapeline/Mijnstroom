define(function (require) {
	var Backbone = require('Backbone');
	var SearchToolbar = require('./../../../common/views/SearchToolbar');
	var TracksView = require('./subviews/TracksView');

	return Backbone.View.extend({
		initialize: function (options) {
			this.subviews = [];
			this.filters = options.filters || {};
			this.onFilter = options.onFilter || function () {};
			this.error = options.error || null;
		},

		render: function () {
			var toolbar = new SearchToolbar({
				filters: this.filters,
				onFilter: this.onFilter
			});
			this.$el.append(toolbar.render().el);
			this.subviews.push(toolbar);

			if (this.error) {
				this.$el.append('<p class="mdl-typography--body-1" style="color:#b71c1c">' + this.error + '</p>');
			}

			var tracksView = new TracksView({ collection: this.collection });
			this.$el.append(tracksView.render().el);
			this.subviews.push(tracksView);

			return this;
		}
	});
});
