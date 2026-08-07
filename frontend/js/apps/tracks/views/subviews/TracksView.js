define(function (require) {
	var Backbone = require('Backbone');
	var TrackView = require('./TrackView');
	var template = require('hbs!./../../templates/TracksView');

	return Backbone.View.extend({
		template: template,

		initialize: function () {
			this.subviews = [];
		},

		render: function () {
			this.$el.html(this.template({ count: this.collection.length }));

			var tracksContainer = this.$('#tracks-list');

			if (this.collection.length === 0) {
				tracksContainer.append(
					'<div class="mdl-cell mdl-cell--12-col mdl-typography--body-1">' +
					'No tracks found.</div>'
				);
				return this;
			}

			this.collection.forEach(function (track) {
				var view = new TrackView({ model: track });
				tracksContainer.append(view.render().el);
				this.subviews.push(view);
			}, this);

			return this;
		}
	});
});
