define(function (require) {
	var Backbone = require('Backbone');

	return Backbone.View.extend({
		tagName: 'div',
    className: 'mdl-card mdl-shadow--2dp mdl-cell',

		template: require('hbs!./../../templates/TrackView'),

		render: function () {
			this.$el.html(this.template(this.model.toJSON()));
			return this;
		}
	});
});