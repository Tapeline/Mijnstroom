define(function(require) {
	var Backbone = require('Backbone');
	var TrackView = require('./TrackView');

	return Backbone.View.extend({
		template: require('hbs!./../../templates/TracksView'),

		initialize: function () {
			this.subviews = [];
		},

		render: function () {
			this.$el.html(this.template());

			var tracksComponents = this.$('#tracks-list');
			this.collection.forEach(function (mail) {
				var view = new TrackView({model: mail});
				tracksComponents.append(view.render().el);
				this.subviews.push(view);
			}, this);

			return this;
		}
	});
});